import logging
from typing import Dict, Any, Set
from app.models.task import Task, TaskStatus

logger = logging.getLogger(__name__)

class TaskDispatcher:
    """
    任务分发器 - 负责将任务分发给对应的调度器
    不同状态的任务被分发给不同的调度器处理
    """
    
    def __init__(self):
        """初始化任务分发器"""
        self.schedulers = {}  # 状态 -> 调度器映射
        self.processing_tasks = set()  # 正在处理的任务ID集合
        self._logger = logging.getLogger(f"{__name__}.TaskDispatcher")
    
    def register_scheduler(self, task_status: str, scheduler):
        """
        注册调度器
        
        Args:
            task_status: 任务状态
            scheduler: 对应的调度器
        """
        self.schedulers[task_status] = scheduler
        self._logger.info(f"为 {task_status} 状态注册调度器: {scheduler.__class__.__name__}")
    
    def dispatch_task(self, task: Task, status: str):
        """
        分发任务给对应的调度器
        
        Args:
            task: 任务对象
            status: 任务状态
        """
        # 避免重复分发
        if task.id in self.processing_tasks:
            self._logger.debug(f"任务 {task.id} 已在处理中，跳过分发")
            return
        
        # 获取对应的调度器
        scheduler = self.schedulers.get(status)
        if not scheduler:
            self._logger.warning(f"未找到 {status} 状态的调度器，跳过任务 {task.id}")
            return
        
        # 分发任务
        try:
            self._logger.info(f"分发 {status} 任务 {task.id} 给 {scheduler.__class__.__name__}")
            self.processing_tasks.add(task.id)
            scheduler.schedule_task(task, self._task_callback)
        except Exception as e:
            self._logger.error(f"分发任务 {task.id} 时出错: {str(e)}")
            self.processing_tasks.discard(task.id)
    
    def _task_callback(self, task_id: int, success: bool):
        """
        任务完成回调函数
        
        Args:
            task_id: 任务ID
            success: 任务是否成功
        """
        self._logger.debug(f"任务 {task_id} 执行完成，成功: {success}")
        self.processing_tasks.discard(task_id)
        
    def get_processing_tasks(self) -> Set[int]:
        """获取正在处理的任务ID集合"""
        return self.processing_tasks.copy() 