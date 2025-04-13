import logging
import asyncio
import time
from typing import Optional, Callable, Dict, Any
from sqlalchemy.orm import Session

from app.models.task import Task, TaskStatus
from app.services.adb_transfer import ADBTransferService
from app.services.automation_service import AutomationService

logger = logging.getLogger(__name__)

class TaskExecutor:
    """任务执行器 - 负责执行任务的具体流程"""
    
    def __init__(
        self,
        adb_service: ADBTransferService,
        automation_service: AutomationService,
        status_update_callback: Optional[Callable[[Task, str, Session], None]] = None,
        max_retries: int = 3,
        retry_delay: int = 2
    ):
        """
        初始化任务执行器
        
        Args:
            adb_service: ADB传输服务
            automation_service: 自动化服务
            status_update_callback: 任务状态更新回调函数
            max_retries: 最大重试次数
            retry_delay: 重试延迟（秒）
        """
        self.adb_service = adb_service
        self.automation_service = automation_service
        self.status_update_callback = status_update_callback
        self.max_retries = max_retries
        self.retry_delay = retry_delay
        self._logger = logging.getLogger(f"{__name__}.TaskExecutor")
    
    def set_status_update_callback(self, callback: Callable[[Task, str, Session], None]):
        """
        设置状态更新回调函数
        
        Args:
            callback: 状态更新回调函数，接收任务、状态和数据库会话
        """
        self.status_update_callback = callback
    
    async def execute_wt_task(self, task: Task, db: Session) -> bool:
        """
        执行WT任务（文件传输）
        
        Args:
            task: 任务对象
            db: 数据库会话
            
        Returns:
            bool: 任务是否成功
        """
        start_time = time.time()
        task_id = task.id
        self._logger.info(f"开始执行文件传输任务: {task_id}")
        
        try:
            # 带重试的执行任务
            success = await self._execute_with_retry(
                self.adb_service.execute_transfer,
                task,
                db
            )
            
            # 通过回调更新任务状态
            if success:
                # 传输成功，状态更新为PENDING
                if self.status_update_callback:
                    self.status_update_callback(task, TaskStatus.PENDING, db)
                self._logger.info(f"文件传输任务 {task_id} 成功，状态更新为 PENDING")
            else:
                # 传输失败，状态更新为WTERR
                if self.status_update_callback:
                    self.status_update_callback(task, TaskStatus.WTERR, db)
                self._logger.error(f"文件传输任务 {task_id} 失败，状态更新为 WTERR")
            
            return success
            
        except Exception as e:
            # 发生异常，状态更新为WTERR
            if self.status_update_callback:
                self.status_update_callback(task, TaskStatus.WTERR, db)
            self._logger.error(f"文件传输任务 {task_id} 执行出错: {str(e)}")
            return False
        finally:
            elapsed_time = time.time() - start_time
            self._logger.info(f"文件传输任务 {task_id} 执行完成，耗时: {elapsed_time:.2f}秒")
    
    async def execute_pending_task(self, task: Task, db: Session) -> bool:
        """
        执行PENDING任务（UI自动化）
        
        Args:
            task: 任务对象
            db: 数据库会话
            
        Returns:
            bool: 任务是否成功
        """
        start_time = time.time()
        task_id = task.id
        self._logger.info(f"开始执行UI自动化任务: {task_id}")
        
        try:
            # 带重试的执行任务
            success = await self._execute_with_retry(
                self.automation_service.execute_pending_task,
                task,
                db
            )
            
            # 通过回调更新任务状态
            if success:
                # 执行成功，状态更新为RES
                if self.status_update_callback:
                    self.status_update_callback(task, TaskStatus.RES, db)
                self._logger.info(f"UI自动化任务 {task_id} 成功，状态更新为 RES")
            else:
                # 执行失败，状态更新为REJ
                if self.status_update_callback:
                    self.status_update_callback(task, TaskStatus.REJ, db)
                self._logger.error(f"UI自动化任务 {task_id} 失败，状态更新为 REJ")
            
            return success
            
        except Exception as e:
            # 发生异常，状态更新为REJ
            if self.status_update_callback:
                self.status_update_callback(task, TaskStatus.REJ, db)
            self._logger.error(f"UI自动化任务 {task_id} 执行出错: {str(e)}")
            return False
        finally:
            elapsed_time = time.time() - start_time
            self._logger.info(f"UI自动化任务 {task_id} 执行完成，耗时: {elapsed_time:.2f}秒")
    
    async def _execute_with_retry(self, executor_func, task: Task, db: Session) -> bool:
        """
        带重试逻辑的任务执行
        
        Args:
            executor_func: 执行函数
            task: 任务对象
            db: 数据库会话
            
        Returns:
            bool: 执行是否成功
        """
        retry_count = 0
        task_id = task.id
        
        while retry_count < self.max_retries:
            try:
                # 添加超时控制
                try:
                    self._logger.info(f"执行任务 {task_id}，尝试 {retry_count + 1}/{self.max_retries}")
                    success = await asyncio.wait_for(
                        executor_func(task, db),
                        timeout=300  # 5分钟超时
                    )
                except asyncio.TimeoutError:
                    self._logger.error(f"任务 {task_id} 执行超时")
                    retry_count += 1
                    if retry_count < self.max_retries:
                        self._logger.info(f"将在 {self.retry_delay} 秒后重试")
                        await asyncio.sleep(self.retry_delay)
                    continue
                
                if success:
                    return True
                
                retry_count += 1
                if retry_count < self.max_retries:
                    self._logger.info(f"任务 {task_id} 失败，将在 {self.retry_delay} 秒后重试")
                    await asyncio.sleep(self.retry_delay)
                
            except Exception as e:
                retry_count += 1
                self._logger.error(f"执行任务 {task_id} 出错: {str(e)}")
                if retry_count < self.max_retries:
                    self._logger.info(f"将在 {self.retry_delay} 秒后重试")
                    await asyncio.sleep(self.retry_delay)
        
        return False 