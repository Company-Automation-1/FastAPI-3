import logging
import asyncio
from typing import Optional
from app.models.device import Device
from app.adb.service import ADBService

logger = logging.getLogger(__name__)

class DeviceOperationService:
    """
    设备基础操作服务 - 负责设备的通用操作
    包括设备连接检测和屏幕解锁等与具体业务无关的操作
    """
    
    def __init__(self, adb_service: Optional[ADBService] = None):
        """
        初始化设备操作服务
        
        Args:
            adb_service: ADB服务实例，如果为None则创建新实例
        """
        self.adb_service = adb_service if adb_service else ADBService()
        self._logger = logging.getLogger(f"{__name__}.DeviceOperation")
        self._logger.info("初始化设备操作服务")
    
    async def check_device_connection(self, device: Device) -> bool:
        """
        检查设备连接状态
        
        Args:
            device: 设备对象
            
        Returns:
            bool: 设备是否连接正常
        """
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
    
    async def check_device_lock_status(self, device: Device) -> Optional[bool]:
        """
        检查设备锁屏状态
        
        Args:
            device: 设备对象
            
        Returns:
            Optional[bool]: True-已锁屏, False-未锁屏, None-无法确定
        """
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
        """
        检查设备屏幕状态
        
        Args:
            device: 设备对象
            
        Returns:
            str: 屏幕状态 - "ON"/"OFF"/"DOZE"/"UNKNOWN"
        """
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
        """
        唤醒设备屏幕
        
        Args:
            device: 设备对象
            
        Returns:
            bool: 是否成功唤醒
        """
        try:
            self._logger.info(f"正在唤醒设备 {device.device_name}({device.device_id}) 的屏幕...")
            
            self.adb_service.connection._execute_command([
                self.adb_service.connection.adb_path,
                "-s", device.device_id,
                "shell", "input keyevent 26"
            ])
            
            await asyncio.sleep(1)  # 等待屏幕唤醒
            
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
    
    async def unlock_screen(self, device: Device) -> bool:
        """
        解锁设备屏幕
        
        Args:
            device: 设备对象
            
        Returns:
            bool: 是否成功解锁
        """
        try:
            self._logger.info(f"正在尝试解锁设备 {device.device_name}({device.device_id})...")
            
            lock_status = await self.check_device_lock_status(device)
            if lock_status is True:
                self._logger.info("设备已锁屏，直接执行解锁操作...")
            else:
                self._logger.info("设备未锁屏或无法确定状态，先返回桌面并锁屏...")
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