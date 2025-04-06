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

logger = logging.getLogger(__name__)

class TaskScheduler:
    def __init__(
        self,
        task_executor: Callable[[Task, Session], Awaitable[bool]],  # 新增通用任务执行器
        check_interval: int = 30,
        max_retries: int = 3,
        retry_delay: int = 2,
        max_concurrent_tasks: int = 5
    ):
        """
        通用任务调度器
        
        Args:
            task_executor: 异步任务执行函数，接收Task和Session参数，返回bool
            check_interval: 检查任务间隔（秒）
            max_retries: 最大重试次数
            retry_delay: 重试延迟（秒）
            max_concurrent_tasks: 最大并发任务数
        """
        self.scheduler = AsyncIOScheduler()
        self.task_executor = task_executor
        self.check_interval = check_interval
        self.max_retries = max_retries
        self.retry_delay = retry_delay
        self.max_concurrent_tasks = max_concurrent_tasks
        self.semaphore = asyncio.Semaphore(max_concurrent_tasks)
        self.processing_tasks = set()  # 正在处理的任务ID集合

    async def start(self):
        """启动调度器"""
        self.scheduler.add_job(
            self.check_waiting_tasks,
            trigger=IntervalTrigger(seconds=self.check_interval),
            id='check_waiting_tasks',
            replace_existing=True
        )
        self.scheduler.start()
        logger.info("通用任务调度器已启动")

    async def stop(self):
        """停止调度器"""
        self.scheduler.shutdown()
        logger.info("通用任务调度器已停止")

    async def check_waiting_tasks(self):
        """检查等待中的任务"""
        try:
            async with self._get_db() as db:
                # 获取等待中的任务
                wt_tasks = TaskService.get_tasks_by_status(db, TaskStatus.WT)
                if not wt_tasks:
                    return

                logger.info(f"发现 {len(wt_tasks)} 个等待任务")
                
                # 过滤掉正在处理的任务
                new_tasks = [
                    task for task in wt_tasks 
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
            logger.error(f"检查等待任务时出错: {str(e)}")

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
                # 标记任务为处理中
                self.processing_tasks.add(task.id)
                
                # 处理任务
                success = await self.process_task(task, db)
                
                # 更新任务状态
                if success:
                    logger.info(f"任务 {task.id} 处理成功")
                    TaskService.update_task_status(db, task.id, TaskStatus.PENDING)
                else:
                    logger.error(f"任务 {task.id} 处理失败")
                    TaskService.update_task_status(db, task.id, TaskStatus.WTERR)
                    
            except Exception as e:
                logger.error(f"处理任务 {task.id} 时出错: {str(e)}")
                TaskService.update_task_status(db, task.id, TaskStatus.WTERR)
            finally:
                # 移除处理中标记
                self.processing_tasks.remove(task.id)

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