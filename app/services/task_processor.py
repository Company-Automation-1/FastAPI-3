from typing import Optional, Dict, Any
import asyncio
import logging
import time
from sqlalchemy.orm import Session

from app.models.task import Task, TaskStatus
from app.services.task import TaskService
from app.services.adb_transfer import ADBTransferService
from app.services.automation_service import AutomationService

logger = logging.getLogger(__name__)

class TaskProcessor:
    """任务处理器 - 负责执行任务的具体逻辑"""
    
    def __init__(
        self, 
        adb_service: ADBTransferService,
        automation_service: AutomationService,
        max_retries: int = 3,
        retry_delay: int = 2
    ):
        """
        初始化任务处理器
        
        Args:
            adb_service: ADB传输服务
            automation_service: 自动化服务
            max_retries: 最大重试次数
            retry_delay: 重试延迟（秒）
        """
        self.adb_service = adb_service
        self.automation_service = automation_service
        self.max_retries = max_retries
        self.retry_delay = retry_delay
        self._logger = logging.getLogger(f"{__name__}.TaskProcessor")
        
        # 注册任务处理函数
        self.task_handlers = {
            TaskStatus.WT: self.handle_wt_task,
            TaskStatus.PENDING: self.handle_pending_task
        }
    
    def get_handler_for_status(self, status: str):
        """获取指定状态的处理函数"""
        return self.task_handlers.get(status, None)
    
    async def handle_wt_task(self, task: Task, db: Session) -> bool:
        """
        处理WT（文件传输）任务
        
        Args:
            task: 任务对象
            db: 数据库会话
            
        Returns:
            bool: 任务是否成功
        """
        start_time = time.time()
        self._logger.info(f"开始处理文件传输任务: {task.id}")
        
        try:
            # 执行任务，包含重试逻辑
            success = await self._process_with_retry(
                self.adb_service.execute_transfer,
                task,
                db
            )
            
            # 更新任务状态
            if success:
                self._logger.info(f"文件传输任务 {task.id} 成功")
                # 传输成功后更新为PENDING状态
                TaskService.update_task_status(db, task.id, TaskStatus.PENDING)
            else:
                self._logger.error(f"文件传输任务 {task.id} 失败")
                # 传输失败更新为WTERR状态
                TaskService.update_task_status(db, task.id, TaskStatus.WTERR)
                
            return success
            
        except Exception as e:
            self._logger.error(f"文件传输任务 {task.id} 执行出错: {str(e)}")
            # 发生异常更新为WTERR状态
            TaskService.update_task_status(db, task.id, TaskStatus.WTERR)
            return False
        finally:
            elapsed_time = time.time() - start_time
            self._logger.info(f"文件传输任务 {task.id} 处理完成，耗时: {elapsed_time:.2f}秒")
    
    async def handle_pending_task(self, task: Task, db: Session) -> bool:
        """
        处理PENDING（UI自动化）任务
        
        Args:
            task: 任务对象
            db: 数据库会话
            
        Returns:
            bool: 任务是否成功
        """
        start_time = time.time()
        self._logger.info(f"开始处理UI自动化任务: {task.id}")
        
        try:
            # 执行任务，包含重试逻辑
            success = await self._process_with_retry(
                self.automation_service.execute_pending_task,
                task,
                db
            )
            
            # 更新任务状态
            if success:
                self._logger.info(f"UI自动化任务 {task.id} 成功")
                # 执行成功更新为RES状态
                TaskService.update_task_status(db, task.id, TaskStatus.RES)
            else:
                self._logger.error(f"UI自动化任务 {task.id} 失败")
                # 执行失败更新为REJ状态
                TaskService.update_task_status(db, task.id, TaskStatus.REJ)
                
            return success
            
        except Exception as e:
            self._logger.error(f"UI自动化任务 {task.id} 执行出错: {str(e)}")
            # 发生异常更新为REJ状态
            TaskService.update_task_status(db, task.id, TaskStatus.REJ)
            return False
        finally:
            elapsed_time = time.time() - start_time
            self._logger.info(f"UI自动化任务 {task.id} 处理完成，耗时: {elapsed_time:.2f}秒")
    
    async def _process_with_retry(self, executor_func, task: Task, db: Session) -> bool:
        """
        带重试逻辑的任务处理
        
        Args:
            executor_func: 任务执行函数
            task: 任务对象
            db: 数据库会话
            
        Returns:
            bool: 任务是否成功
        """
        retry_count = 0
        
        while retry_count < self.max_retries:
            try:
                # 执行任务
                self._logger.info(f"执行任务 {task.id}，尝试次数: {retry_count + 1}/{self.max_retries}")
                
                # 添加超时控制
                try:
                    success = await asyncio.wait_for(
                        executor_func(task, db),
                        timeout=300  # 5分钟超时
                    )
                except asyncio.TimeoutError:
                    self._logger.error(f"任务 {task.id} 执行超时")
                    retry_count += 1
                    if retry_count < self.max_retries:
                        await asyncio.sleep(self.retry_delay)
                    continue
                
                if success:
                    return True
                
                retry_count += 1
                if retry_count < self.max_retries:
                    self._logger.warning(f"任务 {task.id} 失败，将在 {self.retry_delay} 秒后重试")
                    await asyncio.sleep(self.retry_delay)
                
            except Exception as e:
                retry_count += 1
                self._logger.error(f"执行任务 {task.id} 出错: {str(e)}")
                if retry_count < self.max_retries:
                    self._logger.warning(f"将在 {self.retry_delay} 秒后重试")
                    await asyncio.sleep(self.retry_delay)
        
        return False 