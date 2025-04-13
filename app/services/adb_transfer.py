from typing import Optional, List
from sqlalchemy.orm import Session
from app.models.device import Device
from app.adb.service import ADBService
import logging
import asyncio
from app.models.task import Task
from sqlalchemy.orm import joinedload
from sqlalchemy import text
import json
import os
from app.utils.file import get_file_paths
from app.core.config import settings
import time

logger = logging.getLogger(__name__)

class ADBTransferService:
    """ADB传输服务 - 专注于设备解锁功能"""

    def __init__(self):
        self.adb_service = ADBService()
        self._logger = logging.getLogger(f"{__name__}.ADBTransfer")
        self._logger.info("ADBTransferService 初始化")

    async def check_device_lock_status(self, device: Device, db: Session) -> Optional[bool]:
        """检查设备锁屏状态"""
        try:
            self._logger.info(f"正在通过ADB检查设备 {device.device_name}({device.device_id}) 的锁屏状态...")
            
            try:
                result = self.adb_service.connection._execute_command([
                    self.adb_service.connection.adb_path,
                    "-s", device.device_id,
                    "shell", "dumpsys window | grep mDreamingLockscreen"
                ])
                
                if 'mDreamingLockscreen=true' in result:
                    self._logger.info(f"设备已锁屏")
                    return True
                elif 'mDreamingLockscreen=false' in result:
                    self._logger.info(f"设备未锁屏")
                    return False
                else:
                    self._logger.warning(f"无法确定锁屏状态")
                    return None
                
            except Exception as e:
                self._logger.error(f"ADB命令执行出错: {str(e)}")
                return None
            
        except Exception as e:
            self._logger.error(f"检查设备锁屏状态失败: {str(e)}")
            return None

    async def check_screen_status(self, device: Device) -> str:
        """检查设备屏幕状态（点亮或熄灭）"""
        try:
            self._logger.info(f"正在检查设备 {device.device_name}({device.device_id}) 的屏幕状态...")
            
            try:
                result = self.adb_service.connection._execute_command([
                    self.adb_service.connection.adb_path,
                    "-s", device.device_id,
                    "shell", "dumpsys power"
                ])
                
                if "mWakefulness=Awake" in result:
                    return "ON"
                elif "mWakefulness=Asleep" in result:
                    return "OFF"
                elif "mWakefulness=Dozing" in result:
                    return "DOZE"
                else:
                    if "Display Power: state=ON" in result:
                        return "ON"
                    elif "Display Power: state=OFF" in result:
                        return "OFF"
                    else:
                        return "UNKNOWN"
            except Exception as e:
                self._logger.error(f"ADB命令执行出错: {str(e)}")
                return "UNKNOWN"
        except Exception as e:
            self._logger.error(f"检查屏幕状态过程出错: {str(e)}")
            return "UNKNOWN"

    async def wake_screen(self, device: Device) -> bool:
        """唤醒设备屏幕"""
        try:
            self._logger.info(f"正在唤醒设备 {device.device_name}({device.device_id}) 的屏幕...")
            
            self.adb_service.connection._execute_command([
                self.adb_service.connection.adb_path,
                "-s", device.device_id,
                "shell", "input keyevent 26"
            ])
            
            await asyncio.sleep(1)
            
            screen_status = await self.check_screen_status(device)
            if screen_status == "ON":
                self._logger.info("屏幕已成功唤醒")
                return True
            else:
                self._logger.error(f"屏幕唤醒失败，当前状态: {screen_status}")
                return False
        
        except Exception as e:
            self._logger.error(f"唤醒屏幕出错: {str(e)}")
            return False

    async def unlock_screen(self, device: Device, db: Session) -> bool:
        """解锁设备屏幕"""
        try:
            self._logger.info(f"正在尝试解锁设备 {device.device_name}({device.device_id})...")
            
            lock_status = await self.check_device_lock_status(device, db)
            if lock_status is True:
                self._logger.info("设备已锁屏，直接执行解锁操作...")
            else:
                self._logger.info("设备未锁屏，先返回桌面并锁屏...")
                self.adb_service.connection._execute_command([
                    self.adb_service.connection.adb_path,
                    "-s", device.device_id,
                    "shell", "input keyevent 3"
                ])
                await asyncio.sleep(0.5)
                
                self.adb_service.connection._execute_command([
                    self.adb_service.connection.adb_path,
                    "-s", device.device_id,
                    "shell", "input keyevent 26"
                ])
                await asyncio.sleep(1)
            
            wake_success = await self.wake_screen(device)
            if not wake_success:
                self._logger.error("屏幕唤醒失败，无法继续解锁")
                return False
            
            self.adb_service.connection._execute_command([
                self.adb_service.connection.adb_path,
                "-s", device.device_id,
                "shell", "input touchscreen swipe 540 1500 540 500 300"
            ])
            
            await asyncio.sleep(0.5)
            
            if device.password:
                self._logger.info(f"输入密码: {device.password}...")
                self.adb_service.connection._execute_command([
                    self.adb_service.connection.adb_path,
                    "-s", device.device_id,
                    "shell", f"input text {device.password}"
                ])
            
            await asyncio.sleep(1)
            
            return True
        
        except Exception as e:
            self._logger.error(f"解锁屏幕失败: {str(e)}")
            return False

    async def execute_transfer(self, task: Task, db: Session) -> bool:
        """执行设备解锁任务并传输文件"""
        self._logger.info(f"开始执行传输任务: {task.id}")
        
        try:
            if not task:
                self._logger.error("任务对象为空")
                return False
            
            device = db.query(Device).filter(Device.device_name == task.device_name).first()
            if not device:
                self._logger.error(f"未找到关联设备: {task.device_name}")
                return False
            
            device_connected = await self.check_device_connection(device)
            if not device_connected:
                self._logger.error("设备未连接或离线，无法继续操作")
                return False
            
            from app.models.upload import Upload
            upload = db.query(Upload).filter(Upload.id == task.upload_id).first()
            if not upload:
                self._logger.error(f"未找到关联上传记录: {task.upload_id}")
                return False
            
            if hasattr(self, 'adb_service') and self.adb_service:
                unlock_success = await self.unlock_screen(device, db)
                if not unlock_success:
                    self._logger.error("设备解锁失败，无法继续传输文件")
                    return False
                self._logger.info("设备解锁成功")
            
            try:
                from app.utils.file import get_file_paths, get_device_file_paths
                local_file_paths = get_file_paths(upload.files, task.device_name, task.time)
                
                if not local_file_paths:
                    self._logger.error("没有找到有效的本地文件，无法传输")
                    return False
                
                device_file_paths = get_device_file_paths(
                    upload.files, 
                    task.device_name,
                    device.device_path,
                    task.time
                )
                
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
                self._logger.error(f"准备传输文件时出错: {str(e)}")
                return False
        
        except Exception as e:
            self._logger.error(f"任务执行过程中出错: {str(e)}")
            return False

    async def check_device_connection(self, device: Device) -> bool:
        """检查设备连接状态"""
        try:
            self._logger.info(f"检查设备 {device.device_name}({device.device_id}) 连接状态...")
            
            result = self.adb_service.connection._execute_command([
                self.adb_service.connection.adb_path,
                "devices"
            ])
            
            if f"{device.device_id}\tdevice" in result:
                self._logger.info(f"设备 {device.device_id} 已连接且状态正常")
                return True
            elif f"{device.device_id}\toffline" in result:
                self._logger.error(f"设备 {device.device_id} 已连接但状态为离线")
                return False
            else:
                self._logger.error(f"设备 {device.device_id} 未连接")
                return False
        except Exception as e:
            self._logger.error(f"检查设备连接状态出错: {str(e)}")
            return False

    async def transfer_file(self, device: Device, local_path: str, remote_path: str) -> bool:
        """将文件从本地传输到设备"""
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
            
            self._logger.info("验证成功: 文件已成功传输到设备")
            return True
            
        except Exception as e:
            self._logger.error(f"传输文件时出错: {str(e)}")
            return False

    async def transfer_all_files(self, device: Device, local_files: List[str], remote_files: List[str]) -> bool:
        """批量传输文件到设备"""
        if len(local_files) != len(remote_files):
            self._logger.error(f"本地文件数量({len(local_files)})与远程文件数量({len(remote_files)})不匹配")
            return False
        
        success_count = 0
        for i, (local_file, remote_file) in enumerate(zip(local_files, remote_files)):
            self._logger.info(f"正在传输第 {i+1}/{len(local_files)} 个文件")
            if await self.transfer_file(device, local_file, remote_file):
                success_count += 1
                await asyncio.sleep(0.5)  # 每个文件传输完成后等待
            else:
                self._logger.error(f"传输文件失败: {os.path.basename(local_file)}")
        
        if success_count == len(local_files):
            self._logger.info(f"所有 {len(local_files)} 个文件传输成功")
            await asyncio.sleep(1)  # 所有文件传输完成后等待
            return True
        else:
            self._logger.error(f"文件传输部分成功: {success_count}/{len(local_files)}")
            return False

    async def verify_files_on_device(self, device: Device, remote_files: List[str]) -> bool:
        """验证设备上的文件是否存在且可访问"""
        try:
            self._logger.info(f"正在验证设备 {device.device_name} 上的 {len(remote_files)} 个文件")
            
            missing_files = []
            for remote_file in remote_files:
                # 检查文件是否存在
                result = self.adb_service.connection._execute_command([
                    self.adb_service.connection.adb_path,
                    "-s", device.device_id,
                    "shell", f"ls -l {remote_file}"
                ])
                
                if "No such file or directory" in result:
                    missing_files.append(remote_file)
                    self._logger.error(f"设备上找不到文件: {remote_file}")
                    continue
                
                # 检查文件权限
                if "Permission denied" in result:
                    self._logger.error(f"无法访问文件: {remote_file}")
                    missing_files.append(remote_file)
                    continue
                
                # 检查文件大小
                size_result = self.adb_service.connection._execute_command([
                    self.adb_service.connection.adb_path,
                    "-s", device.device_id,
                    "shell", f"stat -c %s {remote_file}"
                ])
                
                try:
                    file_size = int(size_result.strip())
                    if file_size == 0:
                        self._logger.error(f"文件大小为0: {remote_file}")
                        missing_files.append(remote_file)
                except ValueError:
                    self._logger.error(f"无法获取文件大小: {remote_file}")
                    missing_files.append(remote_file)
                
                await asyncio.sleep(0.3)  # 每个文件验证后等待
            
            if missing_files:
                self._logger.error(f"验证失败: {len(missing_files)}/{len(remote_files)} 个文件在设备上不可用")
                return False
            
            self._logger.info("所有文件验证成功")
            await asyncio.sleep(0.5)  # 验证完成后等待
            return True
            
        except Exception as e:
            self._logger.error(f"验证设备文件时出错: {str(e)}")
            return False