from typing import Optional, List
from sqlalchemy.orm import Session
from app.models.device import Device
from app.models.task import Task
from app.adb.service import ADBService
from app.services.device_operation_service import DeviceOperationService
from app.services.task_data_provider import TaskDataProvider
import logging
import asyncio
import os
import time

logger = logging.getLogger(__name__)

class ADBTransferService:
    """ADB传输服务 - 专注于文件传输功能"""

    def __init__(self, adb_service: Optional[ADBService] = None, device_operation: Optional[DeviceOperationService] = None):
        """
        初始化ADB传输服务
        
        Args:
            adb_service: ADB服务实例，如果为None则创建新实例
            device_operation: 设备操作服务实例，如果为None则创建新实例
        """
        self.adb_service = adb_service if adb_service else ADBService()
        self.device_operation = device_operation if device_operation else DeviceOperationService(self.adb_service)
        self._logger = logging.getLogger(f"{__name__}.ADBTransfer")
        self._logger.info("ADBTransferService 初始化")

    async def execute_transfer(self, task: Task, db: Session) -> bool:
        """
        执行文件传输任务
        
        Args:
            task: 任务对象
            db: 数据库会话
            
        Returns:
            bool: 传输是否成功
        """
        self._logger.info(f"开始执行传输任务: {task.id}")
        
        try:
            if not task:
                self._logger.error("任务对象为空")
                return False
            
            # 使用数据提供者获取任务相关数据
            task_data = TaskDataProvider.get_task_data(task, db)
            device = task_data["device"]
            upload = task_data["upload"]
            local_file_paths = task_data["local_files"]
            device_file_paths = task_data["remote_files"]
            
            # 检查数据是否完整
            if not device:
                self._logger.error(f"未找到关联设备: {task.device_name}")
                return False
                
            if not upload:
                self._logger.error(f"未找到关联上传记录: {task.upload_id}")
                return False
            
            # 检查设备连接状态
            device_connected = await self.device_operation.check_device_connection(device)
            if not device_connected:
                self._logger.error("设备未连接或离线，无法继续操作")
                return False
            
            # 解锁设备
            unlock_success = await self.device_operation.unlock_screen(device)
            if not unlock_success:
                self._logger.error("设备解锁失败，无法继续传输文件")
                return False
            self._logger.info("设备解锁成功")
            
            # 检查文件路径
            if not local_file_paths:
                self._logger.error("没有找到有效的本地文件，无法传输")
                return False
            
            # 传输文件
            transfer_success = await self.transfer_all_files(
                device, 
                local_file_paths, 
                device_file_paths
            )
            
            if transfer_success:
                self._logger.info("所有文件传输成功")
                return True
            else:
                self._logger.error("文件传输失败")
                return False
                
        except Exception as e:
            self._logger.error(f"任务执行过程中出错: {str(e)}")
            return False

    async def transfer_file(self, device: Device, local_path: str, remote_path: str) -> bool:
        """
        将文件从本地传输到设备
        
        Args:
            device: 设备对象
            local_path: 本地文件路径
            remote_path: 设备上的目标路径
            
        Returns:
            bool: 传输是否成功
        """
        try:
            self._logger.info(f"正在传输文件：{os.path.basename(local_path)}")
            
            try:
                with open(local_path, 'rb') as f:
                    f.read()  # 验证文件可读
            except Exception as e:
                self._logger.error(f"本地文件读取失败: {str(e)}")
                return False
            
            # 确保远程目录存在
            remote_dir = os.path.dirname(remote_path)
            self.adb_service.connection._execute_command([
                self.adb_service.connection.adb_path,
                "-s", device.device_id,
                "shell", f"mkdir -p {remote_dir}"
            ])
            await asyncio.sleep(0.5)  # 等待目录创建完成
            
            # 使用adb push命令传输文件
            result = self.adb_service.connection._execute_command([
                self.adb_service.connection.adb_path,
                "-s", device.device_id,
                "push", local_path, remote_path
            ])
            
            # 检查传输结果
            if "error" in result.lower() or "failed" in result.lower():
                self._logger.error(f"文件传输失败: {result}")
                return False
            
            await asyncio.sleep(1)  # 等待文件传输完成
            
            # 验证文件是否成功传输到设备
            return await self.verify_file(device, local_path, remote_path)
            
        except Exception as e:
            self._logger.error(f"传输文件时出错: {str(e)}")
            return False

    async def verify_file(self, device: Device, local_path: str, remote_path: str) -> bool:
        """
        验证传输的文件
        
        Args:
            device: 设备对象
            local_path: 本地文件路径
            remote_path: 设备上的文件路径
            
        Returns:
            bool: 验证是否通过
        """
        try:
            # 验证文件是否存在
            verify_result = self.adb_service.connection._execute_command([
                self.adb_service.connection.adb_path,
                "-s", device.device_id,
                "shell", f"ls -l {remote_path}"
            ])
            
            if "No such file or directory" in verify_result:
                self._logger.error(f"文件传输验证失败: 设备上找不到文件 {remote_path}")
                return False
            
            # 获取本地文件大小
            local_size = os.path.getsize(local_path)
            
            # 获取远程文件大小
            size_result = self.adb_service.connection._execute_command([
                self.adb_service.connection.adb_path,
                "-s", device.device_id,
                "shell", f"stat -c %s {remote_path}"
            ])
            
            try:
                remote_size = int(size_result.strip())
                if remote_size != local_size:
                    self._logger.error(f"文件大小不匹配: 本地={local_size}字节, 远程={remote_size}字节")
                    return False
                
                # 获取文件权限信息
                perm_result = self.adb_service.connection._execute_command([
                    self.adb_service.connection.adb_path,
                    "-s", device.device_id,
                    "shell", f"stat -c %A {remote_path}"
                ])
                
                # 获取文件修改时间
                time_result = self.adb_service.connection._execute_command([
                    self.adb_service.connection.adb_path,
                    "-s", device.device_id,
                    "shell", f"stat -c %y {remote_path}"
                ])
                
                self._logger.info(
                    f"验证成功: 信息如下\n"
                    f"文件名: {os.path.basename(local_path)}\n"
                    f"本地路径: {local_path}\n"
                    f"远程路径: {remote_path}\n"
                    f"文件大小: {local_size} 字节\n"
                    f"文件权限: {perm_result.strip()}\n"
                    f"修改时间: {time_result.strip()}\n"
                    f"设备ID: {device.device_id}\n"
                    f"设备名称: {device.device_name}"
                )
                return True
                
            except ValueError:
                self._logger.error(f"无法获取远程文件大小: {size_result}")
                return False
            
        except Exception as e:
            self._logger.error(f"验证文件时出错: {str(e)}")
            return False

    async def transfer_all_files(self, device: Device, local_files: List[str], remote_files: List[str]) -> bool:
        """
        批量传输文件到设备
        
        Args:
            device: 设备对象
            local_files: 本地文件路径列表
            remote_files: 远程文件路径列表
            
        Returns:
            bool: 全部文件是否传输成功
        """
        if len(local_files) != len(remote_files):
            self._logger.error(f"本地文件数量({len(local_files)})与远程文件数量({len(remote_files)})不匹配")
            return False
        
        success_count = 0
        for i, (local_file, remote_file) in enumerate(zip(local_files, remote_files)):
            self._logger.info(f"传输第 {i+1}/{len(local_files)} 个文件: {os.path.basename(local_file)}")
            
            try:
                # 传输单个文件
                transfer_success = await self.transfer_file(device, local_file, remote_file)
                
                if transfer_success:
                    success_count += 1
                    self._logger.info(f"文件 {os.path.basename(local_file)} 传输成功 ({success_count}/{len(local_files)})")
                else:
                    self._logger.error(f"文件 {os.path.basename(local_file)} 传输失败")
            
            except Exception as e:
                self._logger.error(f"传输文件 {os.path.basename(local_file)} 时出错: {str(e)}")
        
        # 全部成功才返回True
        return success_count == len(local_files)