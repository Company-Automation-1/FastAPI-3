import logging
import asyncio
import concurrent.futures
from typing import Dict, Callable, List, Any, Optional
from sqlalchemy.orm import Session
from app.db.session import SessionLocal
from app.models.task import Task
from contextlib import asynccontextmanager
from weakref import WeakValueDictionary
import time

logger = logging.getLogger(__name__)

class PendingTaskScheduler:
    """
    PENDING任务调度器 - 负责调度UI自动化任务
    针对PENDING任务采用设备串行+线程池的调度策略：
    1. 同一设备的任务串行执行（防止设备冲突）
    2. 使用线程池限制总体并发数
    """
    
    def __init__(
        self,
        executor,
        max_workers: int = 5
    ):
        """
        初始化PENDING任务调度器
        
        Args:
            executor: 任务执行器
            max_workers: 最大工作线程数
        """
        self.executor = executor
        self.max_workers = max_workers
        self.thread_pool = concurrent.futures.ThreadPoolExecutor(max_workers=max_workers)
        self.device_locks = WeakValueDictionary()  # 设备ID -> 锁
        self._logger = logging.getLogger(f"{__name__}.PendingTaskScheduler")
    
    def schedule_task(self, task: Task, callback: Optional[Callable] = None):
        """
        调度一个任务
        
        Args:
            task: 任务对象
            callback: 完成回调函数
        """
        # 创建异步任务
        asyncio.create_task(
            self._execute_task(task, callback)
        )
    
    async def _execute_task(self, task: Task, callback: Optional[Callable] = None):
        """
        执行任务的内部方法
        
        Args:
            task: 任务对象
            callback: 完成回调函数
        """
        if not task.device:
            self._logger.error(f"任务 {task.id} 没有关联设备，无法执行")
            if callback:
                callback(task.id, False)
            return
        
        device_id = task.device.device_id
        
        # 获取设备锁
        device_lock = self.device_locks.setdefault(device_id, asyncio.Lock())
        
        # 对同一设备的任务进行串行处理
        async with device_lock:
            self._logger.info(f"开始执行PENDING任务 {task.id}，设备ID: {device_id}")
            
            # 获取新的数据库会话
            async with self._get_db() as db:
                # 在线程池中执行UI自动化任务
                try:
                    # 将任务提交到线程池执行
                    loop = asyncio.get_event_loop()
                    future = await loop.run_in_executor(
                        self.thread_pool,
                        self._run_in_thread,
                        task, 
                        db
                    )
                    
                    success = future
                    self._logger.info(f"PENDING任务 {task.id} 执行{'成功' if success else '失败'}")
                    
                    # 调用回调
                    if callback:
                        callback(task.id, success)
                        
                except Exception as e:
                    self._logger.error(f"执行PENDING任务 {task.id} 时出错: {str(e)}")
                    if callback:
                        callback(task.id, False)
    
    def _run_in_thread(self, task: Task, db: Session) -> bool:
        """
        在线程中运行UI自动化任务
        
        Args:
            task: 任务对象
            db: 数据库会话
            
        Returns:
            bool: 任务是否成功
        """
        try:
            # 创建一个新的事件循环供线程使用
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            
            # 在线程自己的事件循环中执行异步任务
            success = loop.run_until_complete(
                self.executor.execute_pending_task(task, db)
            )
            
            # 关闭事件循环
            loop.close()
            
            return success
            
        except Exception as e:
            self._logger.error(f"线程执行任务 {task.id} 时出错: {str(e)}")
            return False
    
    @asynccontextmanager
    async def _get_db(self):
        """获取数据库会话"""
        db = SessionLocal()
        try:
            yield db
        finally:
            db.close()
            
    def shutdown(self):
        """关闭调度器"""
        if hasattr(self, 'thread_pool') and self.thread_pool:
            self.thread_pool.shutdown(wait=True)
            self._logger.info("线程池已关闭") 