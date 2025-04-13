from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger
from sqlalchemy.orm import Session, joinedload
from app.db.session import SessionLocal
from app.models.task import Task, TaskStatus
import logging
import asyncio
from typing import Dict, Callable, Awaitable, Optional, List
from contextlib import asynccontextmanager
from app.models.device import Device
from weakref import WeakValueDictionary
from app.utils.time_utils import get_current_timestamp, get_current_datetime

logger = logging.getLogger(__name__)

class TaskScheduler:
    """
    任务调度器 - 只负责轮询和分发任务
    轮询数据库中的任务，并根据任务状态分发给不同的处理服务
    """
    
    def __init__(
        self,
        task_handlers: Dict[str, Callable[[Task, Session], Awaitable[bool]]],
        check_interval: int = 30,
        max_concurrent_tasks: int = 5
    ):
        """
        初始化任务调度器
        
        Args:
            task_handlers: 任务处理函数字典，key为任务状态，value为处理函数
            check_interval: 检查任务间隔（秒）
            max_concurrent_tasks: 最大并发任务数
        """
        self.scheduler = AsyncIOScheduler()
        self.task_handlers = task_handlers
        self.check_interval = check_interval
        self.max_concurrent_tasks = max_concurrent_tasks
        
        # 并发控制
        self.semaphores = {
            status: asyncio.Semaphore(max_concurrent_tasks)
            for status in task_handlers.keys()
        }
        
        # 设备锁管理
        self._device_locks = WeakValueDictionary()  # 自动回收锁
        
        # 处理中的任务ID集合
        self.processing_tasks = set()
        
        # 运行状态标志
        self._running = False
        self._logger = logging.getLogger(f"{__name__}.TaskScheduler")
    
    async def start(self):
        """启动调度器"""
        if self._running:
            return
            
        self._running = True
        
        # 启动任务检查
        self.scheduler.add_job(
            self.check_tasks,
            trigger=IntervalTrigger(seconds=self.check_interval),
            id='check_tasks',
            replace_existing=True
        )
        self.scheduler.start()
        
        self._logger.info("任务调度器已启动，支持的任务状态: %s", list(self.task_handlers.keys()))

    async def stop(self):
        """停止调度器"""
        if not self._running:
            return
            
        self._running = False
        
        # 停止调度器
        self.scheduler.shutdown()
        
        self._logger.info("任务调度器已停止")

    async def check_tasks(self):
        """检查和分发任务"""
        try:
            async with self._get_db() as db:
                for status, handler in self.task_handlers.items():
                    # 获取指定状态的任务
                    tasks = self._get_tasks_by_status(db, status)
                    
                    if not tasks:
                        continue
                    
                    self._logger.info(f"发现 {len(tasks)} 个 {status} 状态的任务")
                    
                    # 处理每个任务
                    for task in tasks:
                        # 跳过已在处理中的任务
                        if task.id in self.processing_tasks:
                            self._logger.debug(f"任务 {task.id} 已在处理中，跳过")
                            continue
                        
                        # 标记任务为处理中
                        self.processing_tasks.add(task.id)
                        
                        # 异步处理任务
                        asyncio.create_task(
                            self._handle_task(task, status, handler, db)
                        )
                        
        except Exception as e:
            self._logger.error(f"检查任务时出错: {str(e)}")
    
    def _get_tasks_by_status(self, db: Session, status: str) -> List[Task]:
        """获取指定状态的任务"""
        tasks = []
        
        if status == TaskStatus.WT:
            # WT状态的任务直接获取
            tasks = db.query(Task).options(
                joinedload(Task.device),
                joinedload(Task.upload)
            ).filter(Task.status == status).all()
        
        elif status == TaskStatus.PENDING:
            # PENDING状态需要考虑时间
            current_time = get_current_timestamp()
            tasks = db.query(Task).options(
                joinedload(Task.device),
                joinedload(Task.upload)
            ).filter(
                Task.status == status,
                Task.time <= current_time
            ).all()
        
        return tasks
    
    async def _handle_task(self, task: Task, status: str, handler: Callable, db: Session):
        """处理单个任务"""
        try:
            device = task.device
            if not device:
                self._logger.error(f"任务 {task.id} 关联的设备不存在")
                self.processing_tasks.remove(task.id)
                return
            
            # 获取设备锁
            lock = self._device_locks.setdefault(device.device_id, asyncio.Lock())
            
            # 使用设备锁和状态信号量控制并发
            async with lock, self.semaphores[status]:
                # 获取新的数据库会话
                async with self._get_db() as new_db:
                    # 重新获取任务，确保状态最新
                    fresh_task = new_db.query(Task).options(
                        joinedload(Task.device),
                        joinedload(Task.upload)
                    ).filter(Task.id == task.id).first()
                    
                    if not fresh_task or fresh_task.status != status:
                        self._logger.debug(f"任务 {task.id} 状态已变更或不存在，跳过处理")
                    else:
                        # 调用对应的处理函数
                        self._logger.info(f"开始处理 {status} 任务: {task.id}")
                        try:
                            success = await handler(fresh_task, new_db)
                            self._logger.info(f"任务 {task.id} 处理{'成功' if success else '失败'}")
                        except Exception as e:
                            self._logger.error(f"处理任务 {task.id} 时出错: {str(e)}")
        except Exception as e:
            self._logger.error(f"处理任务过程中出错: {str(e)}")
        finally:
            # 无论成功失败，都从处理中任务集合移除
            try:
                self.processing_tasks.remove(task.id)
            except KeyError:
                pass

    @asynccontextmanager
    async def _get_db(self):
        """获取数据库会话"""
        db = SessionLocal()
        try:
            yield db
        finally:
            db.close() 