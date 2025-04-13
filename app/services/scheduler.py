from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger
from sqlalchemy.orm import Session, joinedload
from app.db.session import SessionLocal
from app.models.task import Task, TaskStatus
from app.services.task import TaskService
import logging
import asyncio
from typing import List, Callable, Awaitable, Optional
from contextlib import asynccontextmanager
import time
import concurrent.futures
from app.models.device import Device
from weakref import WeakValueDictionary, WeakSet
import datetime
from app.utils.time_utils import get_current_timestamp, get_current_datetime
from app.core.config import settings

logger = logging.getLogger(__name__)

class TaskScheduler:
    def __init__(
        self,
        task_executor: Callable[[Task, Session], Awaitable[bool]],
        check_interval: int = 30,
        max_retries: int = 3,
        retry_delay: int = 2,
        max_concurrent_tasks: int = 5,
        task_type: str = "WT"  # 任务类型，WT或PENDING
    ):
        """
        通用任务调度器
        
        Args:
            task_executor: 异步任务执行函数，接收Task和Session参数，返回bool
            check_interval: 检查任务间隔（秒）
            max_retries: 最大重试次数
            retry_delay: 重试延迟（秒）
            max_concurrent_tasks: 最大并发任务数
            task_type: 任务类型，WT或PENDING
        """
        self.scheduler = AsyncIOScheduler()
        self.task_executor = task_executor
        self.check_interval = check_interval
        self.max_retries = max_retries
        self.retry_delay = retry_delay
        self.max_concurrent_tasks = max_concurrent_tasks
        self.semaphore = asyncio.Semaphore(max_concurrent_tasks)
        self.processing_tasks = WeakSet()  # 自动回收已完成任务
        self.task_type = task_type
        
        # 任务队列和执行器池
        self.task_queue = asyncio.Queue()
        self.executor_pool = concurrent.futures.ThreadPoolExecutor(max_workers=max_concurrent_tasks)
        self.consumers = []  # 任务消费者列表
        self._running = False
        self._logger = logging.getLogger(f"{__name__}.{task_type}")
        
        # 设备锁管理
        self._device_locks = WeakValueDictionary()  # 自动回收锁

    async def start(self):
        """启动调度器"""
        if self._running:
            return
            
        self._running = True
        
        # 启动任务检查
        self.scheduler.add_job(
            self.check_tasks,
            trigger=IntervalTrigger(seconds=self.check_interval),
            id=f'check_{self.task_type}_tasks',
            replace_existing=True
        )
        self.scheduler.start()
        
        # 启动任务消费者
        self.consumers = [
            asyncio.create_task(self.task_consumer())
            for _ in range(self.max_concurrent_tasks)
        ]
        
        self._logger.info(f"{self.task_type}任务调度器已启动")

    async def stop(self):
        """停止调度器"""
        if not self._running:
            return
            
        self._running = False
        
        # 停止调度器
        self.scheduler.shutdown()
        
        # 停止所有消费者
        for _ in self.consumers:
            await self.task_queue.put(None)  # 发送停止信号
        
        # 等待所有消费者完成
        if self.consumers:
            await asyncio.gather(*self.consumers)
            self.consumers = []
        
        self._logger.info(f"{self.task_type}任务调度器已停止")

    async def check_tasks(self):
        """检查任务"""
        try:
            async with self._get_db() as db:
                # 根据任务类型获取任务
                if self.task_type == "WT":
                    tasks = TaskService.get_tasks_by_status(db, TaskStatus.WT)
                else:  # PENDING
                    tasks = TaskService.get_tasks_by_status(db, TaskStatus.PENDING)
                    if tasks:
                        # 获取当前时间戳（使用本地时间）
                        current_time = get_current_timestamp()
                        current_datetime = get_current_datetime()
                        self._logger.debug(f"当前时间戳: {current_time}, 对应时间: {current_datetime}")
                        
                        # 过滤出到期的任务
                        tasks = [
                            task for task in tasks 
                            if task.time <= current_time and task.id not in self.processing_tasks
                        ]
                
                if not tasks:
                    return

                self._logger.info(f"发现 {len(tasks)} 个{self.task_type}任务")
                
                # 按设备ID分组任务
                tasks_by_device = {}
                for task in tasks:
                    # 检查任务是否已在处理中
                    if task.id in self.processing_tasks:
                        self._logger.debug(f"任务 {task.id} 已在处理中，跳过")
                        continue
                        
                    # 获取设备信息
                    device = task.device  # 直接从关联关系获取设备
                    if not device:
                        self._logger.error(f"找不到设备信息: {task.device_name}")
                        continue
                        
                    if device.device_id not in tasks_by_device:
                        tasks_by_device[device.device_id] = []
                    tasks_by_device[device.device_id].append((task, device))
                
                # 处理每个设备组的任务
                for device_id, device_tasks in tasks_by_device.items():
                    # 按device_name排序，确保同一设备的系统按顺序执行
                    device_tasks.sort(key=lambda x: x[0].device_name)
                    
                    # 将任务放入队列
                    for task, device in device_tasks:
                        await self.task_queue.put((task.id, device.device_id))

        except Exception as e:
            self._logger.error(f"检查{self.task_type}任务时出错: {str(e)}")

    async def task_consumer(self):
        """任务消费者"""
        while self._running:
            try:
                # 从队列获取任务
                item = await self.task_queue.get()
                if item is None:  # 停止信号
                    break
                    
                task_id, device_id = item
                
                async with self._get_db() as db:
                    # 使用joinedload优化查询
                    task = db.query(Task).options(
                        joinedload(Task.device)
                    ).filter(Task.id == task_id).first()
                    
                    if not task or task.status != self.task_type:
                        self._logger.debug(f"跳过任务 {task_id}: 状态不匹配或任务不存在")
                        continue
                        
                    device = task.device  # 直接从关联关系获取设备
                    if not device:
                        self._logger.error(f"任务 {task_id} 关联的设备不存在")
                        continue
                    
                    # 自动创建设备锁
                    lock = self._device_locks.setdefault(device.device_id, asyncio.Lock())
                    async with lock:
                        await self.handle_task(task, db, device)
            except Exception as e:
                self._logger.error(f"任务消费者出错: {str(e)}")
            finally:
                self.task_queue.task_done()

    async def handle_task(self, task: Task, db: Session, device: Device):
        """处理单个任务"""
        start_time = time.time()
        try:
            # 使用信号量控制并发
            async with self.semaphore:
                # 标记任务为处理中
                self.processing_tasks.add(task.id)
                
                # 处理任务（带超时控制）
                try:
                    success = await asyncio.wait_for(
                        self.process_task(task, db),
                        timeout=300  # 5分钟超时
                    )
                except asyncio.TimeoutError:
                    self._logger.error(f"任务 {task.id} 执行超时")
                    success = False
                
                # 更新任务状态
                if success:
                    self._logger.info(f"任务 {task.id} 处理成功")
                    if self.task_type == "PENDING":
                        # UI自动化任务成功 -> RES
                        TaskService.update_task_status(db, task.id, TaskStatus.RES)
                    else:
                        # 文件传输任务成功 -> PENDING
                        TaskService.update_task_status(db, task.id, TaskStatus.PENDING)
                else:
                    self._logger.error(f"任务 {task.id} 处理失败")
                    if self.task_type == "PENDING":
                        # UI自动化任务失败 -> REJ
                        TaskService.update_task_status(db, task.id, TaskStatus.REJ)
                    else:
                        # 文件传输任务失败 -> WTERR
                        TaskService.update_task_status(db, task.id, TaskStatus.WTERR)
        except Exception as e:
            self._logger.error(f"处理任务 {task.id} 时出错: {str(e)}")
            if self.task_type == "PENDING":
                # UI自动化任务异常 -> REJ
                TaskService.update_task_status(db, task.id, TaskStatus.REJ)
            else:
                # 文件传输任务异常 -> WTERR
                TaskService.update_task_status(db, task.id, TaskStatus.WTERR)
        finally:
            # 确保任务ID被移除，防止重复处理
            self.processing_tasks.discard(task.id)
            elapsed_time = time.time() - start_time
            self._logger.info(f"任务 {task.id} 处理完成，耗时: {elapsed_time:.2f}秒")

    async def process_task(self, task: Task, db: Session) -> bool:
        """任务处理的核心逻辑"""
        retry_count = 0
        
        while retry_count < self.max_retries:
            try:
                # 使用注入的任务执行器
                success = await self.task_executor(task, db)
                if success:
                    return True
                    
                retry_count += 1
                self._logger.warning(f"任务 {task.id} 失败，第 {retry_count} 次重试")
                await asyncio.sleep(self.retry_delay)
                
            except Exception as e:
                retry_count += 1
                self._logger.error(f"处理任务 {task.id} 出错: {str(e)}")
                await asyncio.sleep(self.retry_delay)
        
        return False

    @asynccontextmanager
    async def _get_db(self):
        """数据库会话管理器"""
        db = SessionLocal()
        try:
            yield db
        except Exception as e:
            db.rollback()
            self._logger.error(f"数据库会话出错: {str(e)}")
            raise
        finally:
            db.close()

    async def __aenter__(self):
        """异步上下文管理器入口"""
        await self.start()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """异步上下文管理器出口"""
        await self.stop() 