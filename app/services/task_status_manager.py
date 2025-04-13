import logging
from typing import Optional
from sqlalchemy.orm import Session

from app.models.task import Task, TaskStatus
from app.services.task import TaskService

logger = logging.getLogger(__name__)

class TaskStatusManager:
    """
    任务状态管理器 - 作为任务执行层和服务层之间的桥梁
    负责处理任务状态的更新，使执行层不需要直接访问服务层
    """
    
    @staticmethod
    def update_task_status(task: Task, status: str, db: Session) -> bool:
        """
        更新任务状态
        
        Args:
            task: 任务对象
            status: 新状态
            db: 数据库会话
            
        Returns:
            更新是否成功
        """
        try:
            logger.info(f"更新任务 {task.id} 状态为 {status}")
            updated_task = TaskService.update_task_status(db, task.id, status)
            return updated_task is not None
        except Exception as e:
            logger.error(f"更新任务 {task.id} 状态时出错: {str(e)}")
            return False
    
    @staticmethod
    def get_status_transition_callback():
        """
        获取状态转换回调函数
        
        Returns:
            状态转换回调函数
        """
        def callback(task: Task, status: str, db: Session):
            TaskStatusManager.update_task_status(task, status, db)
        
        return callback 