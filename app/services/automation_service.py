from typing import Optional
from sqlalchemy.orm import Session
from app.models.task import Task, TaskStatus
from app.services.adb_transfer import ADBTransferService
from app.automation.android_automation import AndroidAutomation
from app.utils.time_utils import timestamp_to_datetime
import logging

logger = logging.getLogger(__name__)

class AutomationService:
    """自动化任务服务"""

    def __init__(self):
        self.adb_service = ADBTransferService()
        self._logger = logging.getLogger(f"{__name__}.Automation")
        self._logger.info("初始化自动化任务服务")

    async def execute_pending_task(self, task: Task, db: Session) -> bool:
        """
        执行待处理状态的任务
        
        Args:
            task: 处于PENDING状态的任务
            db: 数据库会话
        
        Returns:
            bool: 任务是否执行成功
        """
        try:
            task_id = task.id  # 保存任务ID
            self._logger.info(f"开始执行PENDING任务: {task_id}")
            
            # 重新从数据库加载任务，确保关联关系可用
            fresh_task = db.query(Task).filter(Task.id == task_id).first()
            if not fresh_task:
                self._logger.error(f"任务 {task_id} 不存在")
                return False
            
            # 直接通过关联关系获取设备和上传信息
            device = fresh_task.device
            upload = fresh_task.upload
            
            if not device:
                self._logger.error(f"未找到设备: {fresh_task.device_name}")
                return False
            
            if not upload:
                self._logger.error(f"未找到上传记录: {fresh_task.upload_id}")
                return False

            # 从task.time获取时间文件夹名称
            time_str = timestamp_to_datetime(fresh_task.time)
            
            # 创建UI自动化实例
            automation = AndroidAutomation(device.device_id, device.password)
            
            # 执行UI自动化任务
            success = await automation.execute_task(
                title=upload.title,
                content=upload.content,
                time_str=time_str
            )
            
            if success:
                self._logger.info(f"任务 {task_id} 执行成功")
                return True
            else:
                self._logger.error(f"任务 {task_id} 执行失败")
                return False
                
        except Exception as e:
            self._logger.error(f"执行任务时出错: {str(e)}")
            return False 