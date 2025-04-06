from typing import Optional, List, Set
import subprocess
import logging
from app.adb.exceptions import ADBConnectionError, ADBCommandError

logger = logging.getLogger(__name__)

class ADBConnection:
    """ADB基础连接类 - 只负责最基本的ADB通信"""
    
    def __init__(self, adb_path: str):
        """
        初始化ADB连接
        
        Args:
            adb_path: ADB可执行文件路径
        """
        self.adb_path = adb_path

    def _execute_command(self, command: List[str], timeout: int = 30) -> str:
        """
        执行ADB命令的核心方法
        
        Args:
            command: 完整的命令参数列表
            timeout: 命令超时时间（秒）
            
        Returns:
            命令执行结果
            
        Raises:
            ADBCommandError: 命令执行失败时抛出
        """
        try:
            result = subprocess.run(
                command,
                capture_output=True,
                text=True,
                check=False,
                timeout=timeout
            )
            
            if result.returncode != 0:
                error_msg = result.stderr or result.stdout
                raise ADBCommandError(f"Command failed: {error_msg}")
                
            return result.stdout.strip()
            
        except subprocess.TimeoutExpired:
            raise ADBCommandError(f"Command timed out after {timeout} seconds")
        except Exception as e:
            raise ADBCommandError(f"Command execution error: {str(e)}")

    def start_server(self) -> None:
        """启动ADB服务器"""
        try:
            self._execute_command([self.adb_path, 'start-server'])
        except ADBCommandError as e:
            raise ADBConnectionError(f"Failed to start ADB server: {str(e)}")

    def kill_server(self) -> None:
        """停止ADB服务器"""
        try:
            self._execute_command([self.adb_path, 'kill-server'])
        except ADBCommandError as e:
            raise ADBConnectionError(f"Failed to kill ADB server: {str(e)}")

    def get_devices(self) -> Set[str]:
        """
        获取已连接的设备列表
        
        Returns:
            设备ID集合
        """
        try:
            output = self._execute_command([self.adb_path, 'devices'])
            lines = output.split('\n')[1:]  # 跳过标题行
            return {
                line.split()[0] for line in lines 
                if line.strip() and 'device' in line
            }
        except ADBCommandError as e:
            raise ADBConnectionError(f"Failed to get device list: {str(e)}")

    def connect_device(self, device_id: str) -> bool:
        """
        连接设备
        
        Args:
            device_id: 设备ID
            
        Returns:
            连接是否成功
        """
        try:
            result = self._execute_command([self.adb_path, 'connect', device_id])
            return "connected" in result.lower() or "already connected" in result.lower()
        except ADBCommandError as e:
            raise ADBConnectionError(f"Failed to connect device {device_id}: {str(e)}")

    def execute_device_command(self, device_id: str, command: List[str]) -> str:
        """
        在指定设备上执行命令
        
        Args:
            device_id: 设备ID
            command: 命令参数列表
            
        Returns:
            命令执行结果
        """
        try:
            return self._execute_command([self.adb_path, '-s', device_id] + command)
        except ADBCommandError as e:
            raise ADBCommandError(f"Failed to execute command on device {device_id}: {str(e)}")

    def check_device_connection(self, device_id: str) -> bool:
        """
        检查设备连接状态
        
        Args:
            device_id: 设备ID
            
        Returns:
            bool: 设备是否在线
        """
        try:
            devices = self.get_devices()
            return device_id in devices
        except ADBCommandError:
            return False