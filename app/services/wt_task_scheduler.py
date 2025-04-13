import logging
import asyncio
from typing import Dict, Callable, List, Any, Optional
from sqlalchemy.orm import Session
from app.db.session import SessionLocal
from app.models.task import Task
from contextlib import asynccontextmanager
from weakref import WeakValueDictionary

logger = logging.getLogger(__name__)

class WTTaskScheduler:
    """
    WT任务调度器 - 负责调度文件传输任务
    针对WT任务采用设备串行+任务并行的调度策略：
    1. 同一设备的任务串行执行（防止设备冲突）
    2. 不同设备的任务可以并行执行
    """
    
    def __init__(
        self,
        executor,
        max_concurrent_devices: int = 5
    ):
        """
        初始化WT任务调度器
        
        Args:
            executor: 任务执行器
            max_concurrent_devices: 最大并发设备数
        """
        self.executor = executor
        self.max_concurrent_devices = max_concurrent_devices
        self.device_semaphore = asyncio.Semaphore(max_concurrent_devices)
        self.device_locks = WeakValueDictionary()  # 设备ID -> 锁
        self._logger = logging.getLogger(f"{__name__}.WTTaskScheduler")
    
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
        
        # 使用信号量限制并发设备数
        async with self.device_semaphore:
            # 对同一设备的任务进行串行处理
            async with device_lock:
                self._logger.info(f"开始执行WT任务 {task.id}，设备ID: {device_id}")
                
                # 获取新的数据库会话
                async with self._get_db() as db:
                    # 执行任务
                    try:
                        success = await self.executor.execute_wt_task(task, db)
                        self._logger.info(f"WT任务 {task.id} 执行{'成功' if success else '失败'}")
                        
                        # 调用回调
                        if callback:
                            callback(task.id, success)
                            
                    except Exception as e:
                        self._logger.error(f"执行WT任务 {task.id} 时出错: {str(e)}")
                        if callback:
                            callback(task.id, False)
    
    @asynccontextmanager
    async def _get_db(self):
        """获取数据库会话"""
        db = SessionLocal()
        try:
            yield db
        finally:
            db.close() 