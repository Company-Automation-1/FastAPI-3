from typing import Optional
from sqlalchemy.orm import Session
from app.models.task import Task, TaskStatus
from app.services.device_operation_service import DeviceOperationService
from app.services.task_data_provider import TaskDataProvider
from app.automation.android_automation import AndroidAutomation
from app.utils.time_utils import timestamp_to_datetime
import logging

logger = logging.getLogger(__name__)

class AutomationService:
    """自动化任务服务 - 专注于UI自动化执行"""

    def __init__(self, device_operation: Optional[DeviceOperationService] = None):
        """
        初始化自动化任务服务
        
        Args:
            device_operation: 设备操作服务实例，如果为None则创建新实例
        """
        self.device_operation = device_operation if device_operation else DeviceOperationService()
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
            
            # 获取任务数据
            task_data = TaskDataProvider.get_task_data(task, db)
            device = task_data["device"]
            upload = task_data["upload"]
            
            # 验证数据完整性
            if not device:
                self._logger.error(f"未找到设备: {task.device_name}")
                return False
            
            if not upload:
                self._logger.error(f"未找到上传记录: {task.upload_id}")
                return False
            
            # 检查设备连接状态
            device_connected = await self.device_operation.check_device_connection(device)
            if not device_connected:
                self._logger.error(f"设备 {device.device_id} 未连接或离线")
                return False
            
            # 解锁设备
            unlock_success = await self.device_operation.unlock_screen(device)
            if not unlock_success:
                self._logger.error(f"设备 {device.device_id} 解锁失败")
                return False
            
            self._logger.info(f"设备 {device.device_id} 解锁成功，准备执行UI自动化")

            # 从task.time获取时间文件夹名称
            time_str = timestamp_to_datetime(task.time)
            
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