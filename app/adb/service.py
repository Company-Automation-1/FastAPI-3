from typing import Optional, List, Set, Dict
from fastapi import HTTPException
from .connection import ADBConnection
from .exceptions import ADBError, DeviceNotFoundError
from app.core.config import settings
from app.core.status_code import StatusCode
from app.models.device import Device
from sqlalchemy.orm import Session
import logging
import asyncio
from functools import wraps

logger = logging.getLogger(__name__)

def handle_adb_errors(func):
    """ADB错误处理装饰器"""
    @wraps(func)
    async def wrapper(*args, **kwargs):
        try:
            return await func(*args, **kwargs)
        except DeviceNotFoundError as e:
            logger.error(f"设备未找到: {str(e)}")
            raise HTTPException(
                status_code=StatusCode.ADB_DEVICE_NOT_FOUND.value,
                detail=StatusCode.get_message(StatusCode.ADB_DEVICE_NOT_FOUND.value)
            )
        except ADBError as e:
            logger.error(f"ADB操作失败: {str(e)}")
            raise HTTPException(
                status_code=StatusCode.ADB_COMMAND_ERROR.value,
                detail=StatusCode.get_message(StatusCode.ADB_COMMAND_ERROR.value)
            )
        except Exception as e:
            logger.error(f"未知错误: {str(e)}")
            raise HTTPException(
                status_code=StatusCode.INTERNAL_ERROR.value,
                detail=StatusCode.get_message(StatusCode.INTERNAL_ERROR.value)
            )
    return wrapper

class ADBService:
    """ADB服务类 - 提供高级ADB操作和业务逻辑"""
    
    def __init__(self):
        """初始化ADB服务"""
        try:
            self.connection = ADBConnection(settings.ADB_PATH)
            self.connection.start_server()
            logger.info("ADB服务器已启动")
        except Exception as e:
            logger.error(f"ADB服务初始化失败: {e}")
            raise HTTPException(
                status_code=StatusCode.ADB_CONNECTION_ERROR.value,
                detail=StatusCode.get_message(StatusCode.ADB_CONNECTION_ERROR.value)
            )

    async def get_device_from_db(self, device_name: str, db: Session) -> Optional[Device]:
        """
        从数据库获取设备信息
        
        Args:
            device_name: 设备名称
            db: 数据库会话
            
        Returns:
            Device对象或None
        """
        try:
            device = db.query(Device).filter(Device.device_name == device_name).first()
            if not device:
                logger.error(f"设备 {device_name} 未找到")
                return None
            return device
        except Exception as e:
            logger.error(f"获取设备信息失败: {str(e)}")
            return None

    async def _run_adb_command(self, func, *args):
        """执行ADB命令的通用方法"""
        try:
            loop = asyncio.get_event_loop()
            return await loop.run_in_executor(None, func, *args)
        except Exception as e:
            raise ADBError(str(e))

    @handle_adb_errors
    async def get_devices(self) -> Set[str]:
        """获取已连接的设备列表"""
        return await self._run_adb_command(self.connection.get_devices)

    @handle_adb_errors
    async def connect_device(self, device_name: str) -> bool:
        """连接设备
        Args:
            device_name: 设备名称（数据库中的device_name）
        """
        try:
            # 1. 从数据库获取设备信息
            device = await self.get_device_from_db(device_name)
            if not device:
                raise DeviceNotFoundError(f"设备 {device_name} 未找到")

            # 2. 使用物理ID连接设备
            result = await self._run_adb_command(
                self.connection.connect_device, 
                device.device_id  # 使用实际的物理ID
            )

            if not result:
                raise HTTPException(
                    status_code=StatusCode.DEVICE_CONNECTION_FAILED.value,
                    detail=StatusCode.get_message(StatusCode.DEVICE_CONNECTION_FAILED.value)
                )
            return result
        except ADBError:
            raise HTTPException(
                status_code=StatusCode.DEVICE_CONNECTION_FAILED.value,
                detail=StatusCode.get_message(StatusCode.DEVICE_CONNECTION_FAILED.value)
            )

    @handle_adb_errors
    async def execute_shell_command(self, device_name: str, command: str) -> str:
        """在设备上执行shell命令"""
        # 1. 从数据库获取设备信息
        device = await self.get_device_from_db(device_name)
        if not device:
            raise DeviceNotFoundError(f"设备 {device_name} 未找到")
            
        # 2. 使用物理ID执行命令
        return await self._run_adb_command(
            self.connection.execute_device_command,
            device.device_id,  # 使用物理ID
            ['shell', command]
        )

    @handle_adb_errors
    async def push_file(self, device_name: str, local_path: str, remote_path: str) -> bool:
        """推送文件到设备"""
        try:
            await self.execute_shell_command(device_name, f'mkdir -p {remote_path}')
            await self._run_adb_command(
                self.connection.execute_device_command,
                device_name,
                ['push', local_path, remote_path]
            )
            return True
        except Exception as e:
            logger.error(f"文件推送失败: {e}")
            raise HTTPException(
                status_code=StatusCode.UPLOAD_FAILED.value,
                detail=StatusCode.get_message(StatusCode.UPLOAD_FAILED.value)
            )

    def kill_server(self) -> bool:
        """关闭ADB服务器"""
        try:
            return bool(self.connection._execute_command([
                self.connection.adb_path,
                "kill-server"
            ]))
        except Exception as e:
            logger.error(f"关闭ADB服务器失败: {e}")
            raise HTTPException(
                status_code=StatusCode.ADB_CONNECTION_ERROR.value,
                detail=StatusCode.get_message(StatusCode.ADB_CONNECTION_ERROR.value)
            )

    def start_adb_server(self) -> bool:
        """启动ADB服务器"""
        try:
            return bool(self.connection._execute_command([
                self.connection.adb_path,
                "start-server"
            ]))
        except Exception as e:
            logger.error(f"Failed to start ADB server: {e}")
            return False
            
    def get_device_list(self) -> List[str]:
        """获取已连接的设备列表"""
        return self.connection.get_device_list()
        
    def disconnect_device(self, device_id: str) -> bool:
        """
        断开设备连接
        
        Args:
            device_id: 设备ID
            
        Returns:
            bool: 断开连接是否成功
        """
        return self.connection.disconnect_device(device_id)
        
    def verify_device_connection(self, device_id: str) -> bool:
        """验证设备连接状态"""
        return self.connection.check_device_connection(device_id)

    async def execute_device_command_async(self, device_name: str, command: List[str]) -> Optional[str]:
        """在指定设备上执行shell命令"""
        # 先尝试连接设备
        if not await self.connect_device(device_name):
            logger.error(f"无法连接设备: {device_name}")
            return None
        return self.connection.execute_shell_command(device_name, command)

    async def create_remote_directory_async(self, device_name: str, remote_dir: str) -> bool:
        """在设备上创建目录"""
        try:
            await self.execute_device_command_async(device_name, ['shell', f'mkdir -p {remote_dir}'])
            return True
        except Exception as e:
            logger.error(f"创建远程目录失败: {str(e)}")
            return False

    async def push_file_async(self, device_name: str, local_path: str, remote_path: str) -> bool:
        """推送文件到设备"""
        try:
            await self.execute_device_command_async(device_name, ['push', local_path, remote_path])
            return True
        except Exception as e:
            logger.error(f"推送文件失败: {str(e)}")
            return False 