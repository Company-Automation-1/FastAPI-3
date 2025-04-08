from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger
from sqlalchemy.orm import Session
from app.db.session import SessionLocal
from app.models.task import Task, TaskStatus
from app.services.task import TaskService
import logging
import asyncio
from typing import List, Callable, Awaitable
from contextlib import asynccontextmanager
import time

logger = logging.getLogger(__name__)

class TaskScheduler:
    def __init__(
        self,
        task_executor: Callable[[Task, Session], Awaitable[bool]],
        check_interval: int = 30,
        max_retries: int = 3,
        retry_delay: int = 2,
        max_concurrent_tasks: int = 5,
        task_type: str = "WT"  # 新增：任务类型，默认为WT
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
        self.processing_tasks = set()  # 正在处理的任务ID集合
        self.task_type = task_type  # 新增：任务类型

    async def start(self):
        """启动调度器"""
        self.scheduler.add_job(
            self.check_tasks,  # 修改：使用统一的检查方法
            trigger=IntervalTrigger(seconds=self.check_interval),
            id=f'check_{self.task_type}_tasks',
            replace_existing=True
        )
        self.scheduler.start()
        logger.info(f"{self.task_type}任务调度器已启动")

    async def stop(self):
        """停止调度器"""
        self.scheduler.shutdown()
        logger.info(f"{self.task_type}任务调度器已停止")

    async def check_tasks(self):  # 新增：统一的检查方法
        """检查任务"""
        try:
            async with self._get_db() as db:
                # 根据任务类型获取任务
                if self.task_type == "WT":
                    tasks = TaskService.get_tasks_by_status(db, TaskStatus.WT)
                else:  # PENDING
                    tasks = TaskService.get_tasks_by_status(db, TaskStatus.PENDING)
                    if tasks:
                        # 获取当前UTC时间戳，并加上8小时偏移量
                        current_utc_time = time.time() + 8 * 3600
                        # 过滤出到期的任务
                        tasks = [
                            task for task in tasks 
                            if task.time <= int(current_utc_time) and task.id not in self.processing_tasks
                        ]
                
                if not tasks:
                    return

                logger.info(f"发现 {len(tasks)} 个{self.task_type}任务")
                
                # 过滤掉正在处理的任务
                new_tasks = [
                    task for task in tasks 
                    if task.id not in self.processing_tasks
                ]
                
                if not new_tasks:
                    return
                
                # 创建任务处理协程
                tasks = [
                    self.handle_task(task, db) 
                    for task in new_tasks
                ]
                
                # 非阻塞方式启动任务处理
                asyncio.create_task(self.process_tasks(tasks))
                
        except Exception as e:
            logger.error(f"检查{self.task_type}任务时出错: {str(e)}")

    async def process_tasks(self, tasks: List[asyncio.Task]):
        """并发处理多个任务"""
        try:
            await asyncio.gather(*tasks)
        except Exception as e:
            logger.error(f"批量处理任务时出错: {str(e)}")

    async def handle_task(self, task: Task, db: Session):
        """处理单个任务"""
        # 使用信号量控制并发
        async with self.semaphore:
            try:
                task_id = task.id  # 保存任务ID
                # 标记任务为处理中
                self.processing_tasks.add(task_id)
                
                # 重新从数据库加载任务，确保关联关系可用
                fresh_task = db.query(Task).filter(Task.id == task_id).first()
                if not fresh_task:
                    logger.error(f"任务 {task_id} 不存在")
                    return False
                
                # 处理任务
                success = await self.process_task(fresh_task, db)
                
                # 更新任务状态
                if success:
                    logger.info(f"任务 {task_id} 处理成功")
                    # 根据任务类型更新状态
                    if self.task_type == "PENDING":
                        # UI自动化任务成功 -> RES
                        TaskService.update_task_status(db, task_id, TaskStatus.RES)
                    else:
                        # 文件传输任务成功 -> PENDING
                        TaskService.update_task_status(db, task_id, TaskStatus.PENDING)
                else:
                    logger.error(f"任务 {task_id} 处理失败")
                    # 根据任务类型更新状态
                    if self.task_type == "PENDING":
                        # UI自动化任务失败 -> REJ
                        TaskService.update_task_status(db, task_id, TaskStatus.REJ)
                    else:
                        # 文件传输任务失败 -> WTERR
                        TaskService.update_task_status(db, task_id, TaskStatus.WTERR)
                    
            except Exception as e:
                logger.error(f"处理任务 {task_id} 时出错: {str(e)}")
                # 根据任务类型更新状态
                if self.task_type == "PENDING":
                    # UI自动化任务异常 -> REJ
                    TaskService.update_task_status(db, task_id, TaskStatus.REJ)
                else:
                    # 文件传输任务异常 -> WTERR
                    TaskService.update_task_status(db, task_id, TaskStatus.WTERR)
            finally:
                # 移除处理中标记
                self.processing_tasks.remove(task_id)

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
                logger.warning(f"任务 {task.id} 失败，第 {retry_count} 次重试")
                await asyncio.sleep(self.retry_delay)
                
            except Exception as e:
                retry_count += 1
                logger.error(f"处理任务 {task.id} 出错: {str(e)}")
                await asyncio.sleep(self.retry_delay)
        
        return False

    @asynccontextmanager
    async def _get_db(self):
        """数据库会话管理器"""
        db = SessionLocal()
        try:
            yield db
        finally:
            db.close()

    async def __aenter__(self):
        """异步上下文管理器入口"""
        await self.start()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """异步上下文管理器出口"""
        await self.stop() 