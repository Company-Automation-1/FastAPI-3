import logging
from typing import Optional, Tuple, Dict, Any, List
from sqlalchemy.orm import Session

from app.models.task import Task
from app.models.device import Device
from app.models.upload import Upload
from app.utils.file import get_file_paths, get_device_file_paths

logger = logging.getLogger(__name__)

class TaskDataProvider:
    """
    任务数据提供者 - 为底层服务提供任务相关数据
    避免底层服务直接访问数据库或进行跨层调用
    """
    
    @staticmethod
    def get_task_data(task: Task, db: Session) -> Dict[str, Any]:
        """
        获取任务相关数据
        
        Args:
            task: 任务对象
            db: 数据库会话
            
        Returns:
            包含任务相关数据的字典
        """
        result = {
            "task": task,
            "device": None,
            "upload": None,
            "local_files": [],
            "remote_files": []
        }
        
        try:
            # 获取关联设备
            if task.device:
                result["device"] = task.device
            else:
                device = db.query(Device).filter(Device.device_name == task.device_name).first()
                result["device"] = device
            
            # 获取关联上传记录
            if task.upload:
                result["upload"] = task.upload
            else:
                upload = db.query(Upload).filter(Upload.id == task.upload_id).first()
                result["upload"] = upload
            
            # 如果设备和上传记录都存在，处理文件路径
            if result["device"] and result["upload"]:
                device = result["device"]
                upload = result["upload"]
                
                # 获取本地文件路径和设备文件路径
                try:
                    result["local_files"] = get_file_paths(
                        upload.files, 
                        task.device_name, 
                        task.time
                    )
                    
                    result["remote_files"] = get_device_file_paths(
                        upload.files, 
                        task.device_name,
                        device.device_path,
                        task.time
                    )
                except Exception as e:
                    logger.error(f"处理文件路径时出错: {str(e)}")
        
        except Exception as e:
            logger.error(f"获取任务数据时出错: {str(e)}")
        
        return result
    
    @staticmethod
    def get_device(task: Task, db: Session) -> Optional[Device]:
        """
        获取任务关联的设备
        
        Args:
            task: 任务对象
            db: 数据库会话
            
        Returns:
            Device或None
        """
        try:
            if task.device:
                return task.device
            return db.query(Device).filter(Device.device_name == task.device_name).first()
        except Exception as e:
            logger.error(f"获取设备时出错: {str(e)}")
            return None
    
    @staticmethod
    def get_upload(task: Task, db: Session) -> Optional[Upload]:
        """
        获取任务关联的上传记录
        
        Args:
            task: 任务对象
            db: 数据库会话
            
        Returns:
            Upload或None
        """
        try:
            if task.upload:
                return task.upload
            return db.query(Upload).filter(Upload.id == task.upload_id).first()
        except Exception as e:
            logger.error(f"获取上传记录时出错: {str(e)}")
            return None
    
    @staticmethod
    def get_file_paths(task: Task, db: Session) -> Tuple[List[str], List[str]]:
        """
        获取任务相关的文件路径
        
        Args:
            task: 任务对象
            db: 数据库会话
            
        Returns:
            (本地文件路径列表, 远程文件路径列表)的元组
        """
        local_files = []
        remote_files = []
        
        try:
            device = TaskDataProvider.get_device(task, db)
            upload = TaskDataProvider.get_upload(task, db)
            
            if device and upload:
                local_files = get_file_paths(
                    upload.files, 
                    task.device_name, 
                    task.time
                )
                
                remote_files = get_device_file_paths(
                    upload.files, 
                    task.device_name,
                    device.device_path,
                    task.time
                )
        except Exception as e:
            logger.error(f"获取文件路径时出错: {str(e)}")
        
        return local_files, remote_files 