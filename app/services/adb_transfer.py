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

logger = logging.getLogger(__name__)

class ADBTransferService:
    """ADB传输服务 - 专注于设备解锁功能"""

    print('这是ADB传输服务')
    
    def __init__(self):
        self.adb_service = ADBService()
        print("ADBTransferService 初始化")

    async def check_device_lock_status(self, device: Device, db: Session) -> Optional[bool]:
        """
        检查设备锁屏状态
        
        Args:
            device: 设备对象
            db: 数据库会话
            
        Returns:
            Optional[bool]: True表示已锁屏，False表示未锁屏，None表示检查失败
        """
        try:
            print(f"正在通过ADB检查设备 {device.device_name}({device.device_id}) 的锁屏状态...")
            
            try:
                # 尝试使用ADB命令
                result = self.adb_service.connection._execute_command([
                    self.adb_service.connection.adb_path,
                    "-s", device.device_id,
                    "shell", "dumpsys window | grep mDreamingLockscreen"
                ])
                
                if 'mDreamingLockscreen=true' in result:
                    print(f"ADB命令返回结果: {result}")
                    print(f"锁屏状态: 已锁屏")
                    return True
                elif 'mDreamingLockscreen=false' in result:
                    print(f"ADB命令返回结果: {result}")
                    print(f"锁屏状态: 未锁屏")
                    return False
                else:
                    print(f"ADB命令返回结果无法确定锁屏状态: {result}")
                    return None  # 无法确定锁屏状态
                
            except Exception as e:
                print(f"ADB命令执行出错: {str(e)}")
                return None  # 检查失败返回None
            
        except Exception as e:
            logger.error(f"检查设备锁屏状态失败: {str(e)}")
            print(f"检查锁屏状态过程出错: {str(e)}")
            return None  # 检查失败返回None

    async def check_screen_status(self, device: Device) -> str:
        """检查设备屏幕状态（点亮或熄灭）"""
        try:
            print(f"正在检查设备 {device.device_name}({device.device_id}) 的屏幕状态...")
            
            try:
                result = self.adb_service.connection._execute_command([
                    self.adb_service.connection.adb_path,
                    "-s", device.device_id,
                    "shell", "dumpsys power"  # 获取完整的power信息
                ])
                
                print(f"电源状态检查完整结果: {result[:200]}...")  # 只打印前200个字符
                
                # 分析更多可能的状态标识
                if "mWakefulness=Awake" in result:
                    return "ON"  # 设备处于唤醒状态
                elif "mWakefulness=Asleep" in result:
                    return "OFF"  # 设备处于睡眠状态
                elif "mWakefulness=Dozing" in result:
                    return "DOZE"  # 设备处于打盹状态
                else:
                    # 尝试其他可能的标识
                    if "Display Power: state=ON" in result:
                        return "ON"
                    elif "Display Power: state=OFF" in result:
                        return "OFF"
                    else:
                        return "UNKNOWN"
            except Exception as e:
                print(f"ADB命令执行出错: {str(e)}")
                return "UNKNOWN"
        except Exception as e:
            print(f"检查屏幕状态过程出错: {str(e)}")
            return "UNKNOWN"

    async def wake_screen(self, device: Device) -> bool:
        """
        唤醒设备屏幕
        
        Args:
            device: 设备对象
            
        Returns:
            bool: 是否成功唤醒屏幕
        """
        try:
            print(f"正在唤醒设备 {device.device_name}({device.device_id}) 的屏幕...")
            
            # 按下电源键唤醒屏幕
            self.adb_service.connection._execute_command([
                self.adb_service.connection.adb_path,
                "-s", device.device_id,
                "shell", "input keyevent 26"  # KEYCODE_POWER
            ])
            
            # 等待屏幕唤醒
            await asyncio.sleep(1)
            
            # 检查屏幕是否已唤醒
            screen_status = await self.check_screen_status(device)
            if screen_status == "ON":
                print("屏幕已成功唤醒")
                return True
            else:
                print(f"屏幕唤醒失败，当前状态: {screen_status}")
                return False
        
        except Exception as e:
            print(f"唤醒屏幕出错: {str(e)}")
            return False

    async def unlock_screen(self, device: Device, db: Session) -> bool:
        """
        解锁设备屏幕
        
        Args:
            device: 设备对象
            db: 数据库会话
            
        Returns:
            bool: 解锁是否成功
        """
        try:
            print(f"正在尝试解锁设备 {device.device_name}({device.device_id})...")
            
            # 1. 检查锁屏状态
            lock_status = await self.check_device_lock_status(device, db)
            if lock_status is True:
                print("设备已锁屏，直接执行解锁操作...")
            else:
                print("设备未锁屏，先返回桌面并锁屏...")
                # 返回桌面
                self.adb_service.connection._execute_command([
                    self.adb_service.connection.adb_path,
                    "-s", device.device_id,
                    "shell", "input keyevent 3"  # KEYCODE_HOME
                ])
                await asyncio.sleep(0.5)
                
                # 锁屏
                self.adb_service.connection._execute_command([
                    self.adb_service.connection.adb_path,
                    "-s", device.device_id,
                    "shell", "input keyevent 26"  # KEYCODE_POWER
                ])
                await asyncio.sleep(1)
            
            # 2. 唤醒屏幕
            print("唤醒屏幕...")
            wake_success = await self.wake_screen(device)
            if not wake_success:
                print("屏幕唤醒失败，无法继续解锁")
                return False
            
            # 3. 执行解锁滑动操作
            print("执行滑动解锁操作...")
            self.adb_service.connection._execute_command([
                self.adb_service.connection.adb_path,
                "-s", device.device_id,
                "shell", "input touchscreen swipe 540 1500 540 500 300"
            ])
            
            # 等待滑动动画完成
            await asyncio.sleep(0.5)
            
            # 4. 如果设置了密码，则输入密码
            if device.password:
                print(f"输入密码: {device.password}...")
                self.adb_service.connection._execute_command([
                    self.adb_service.connection.adb_path,
                    "-s", device.device_id,
                    "shell", f"input text {device.password}"
                ])
            
            # 5. 等待解锁动作完成
            print("等待解锁动作完成...")
            await asyncio.sleep(1)
            
            return True
        
        except Exception as e:
            print(f"解锁屏幕失败: {str(e)}")
            return False

    async def execute_transfer(self, task: Task, db: Session) -> bool:
        """
        执行设备解锁任务并传输文件
        
        Args:
            task: 任务对象
            db: 数据库会话
            
        Returns:
            bool: 任务是否成功
        """
        print(f"====== 任务执行器被调用了! 任务ID: {task.id if task else 'None'} ======")
        
        try:
            if not task:
                print("任务对象为空")
                return False
            
            print(f"任务信息: ID={task.id}, 设备={task.device_name}, 上传ID={task.upload_id}, 时间={task.time}, 状态={task.status}")
            
            # 获取设备信息
            device = db.query(Device).filter(Device.device_name == task.device_name).first()
            if not device:
                print(f"\n未找到关联设备: {task.device_name}")
                return False
            
            print("\n关联设备信息:")
            print(f"  设备名称: {device.device_name}")
            print(f"  设备ID: {device.id}")
            print(f"  物理ID: {device.device_id}")
            print(f"  存储路径: {device.device_path}")
            print(f"  密码: {device.password}")
            print(f"  创建时间: {device.createtime}")
            print(f"  更新时间: {device.updatetime}")
            
            # 检查设备连接
            device_connected = await self.check_device_connection(device)
            if not device_connected:
                print("\n设备未连接或离线，无法继续操作")
                return False
            
            # 获取上传记录
            from app.models.upload import Upload
            upload = db.query(Upload).filter(Upload.id == task.upload_id).first()
            if not upload:
                print(f"\n未找到关联上传记录: {task.upload_id}")
                return False
            
            print("\n关联上传信息:")
            print(f"  上传ID: {upload.id}")
            print(f"  设备名称: {upload.device_name}")
            print(f"  时间: {upload.time}")
            print(f"  标题: {upload.title}")
            print(f"  内容: {upload.content}")
            print(f"  文件列表: {upload.files}")
            print(f"  创建时间: {upload.createtime}")
            print(f"  更新时间: {upload.updatetime}")
            
            # 解锁设备
            if hasattr(self, 'adb_service') and self.adb_service:
                unlock_success = await self.unlock_screen(device, db)
                if not unlock_success:
                    print("\n=== 设备解锁失败，无法继续传输文件 ===")
                    return False
                print("\n=== 设备解锁成功 ===")
            
            # 准备传输文件
            try:
                # 获取本地文件路径
                from app.utils.file import get_file_paths, get_device_file_paths
                local_file_paths = get_file_paths(upload.files, task.device_name, task.time)
                print("\n本地文件路径:")
                for path in local_file_paths:
                    print(f"  - {path}")
                
                if not local_file_paths:
                    print("没有找到有效的本地文件，无法传输")
                    return False
                
                # 获取设备上的文件路径
                device_file_paths = get_device_file_paths(
                    upload.files, 
                    task.device_name,
                    device.device_path,
                    task.time
                )
                print("\n设备上的目标路径:")
                for path in device_file_paths:
                    print(f"  - {path}")
                
                # 执行文件传输
                transfer_success = await self.transfer_all_files(
                    device, 
                    local_file_paths, 
                    device_file_paths
                )
                
                if transfer_success:
                    print("\n=== 所有文件传输成功 ===")
                    return True
                else:
                    print("\n=== 文件传输失败 ===")
                    return False
                
            except Exception as e:
                print(f"准备传输文件时出错: {str(e)}")
                return False
        
        except Exception as e:
            print(f"任务执行过程中出错: {str(e)}")
            return False

    async def check_device_connection(self, device: Device) -> bool:
        """检查设备连接状态"""
        try:
            print(f"检查设备 {device.device_name}({device.device_id}) 连接状态...")
            
            # 获取所有设备列表
            result = self.adb_service.connection._execute_command([
                self.adb_service.connection.adb_path,
                "devices"
            ])
            
            print(f"设备列表: {result}")
            
            # 检查设备是否存在且状态是否为device
            if f"{device.device_id}\tdevice" in result:
                print(f"设备 {device.device_id} 已连接且状态正常")
                return True
            elif f"{device.device_id}\toffline" in result:
                print(f"设备 {device.device_id} 已连接但状态为离线")
                return False
            else:
                print(f"设备 {device.device_id} 未连接")
                return False
        except Exception as e:
            print(f"检查设备连接状态出错: {str(e)}")
            return False

    async def transfer_file(self, device: Device, local_path: str, remote_path: str) -> bool:
        """将文件从本地传输到设备"""
        try:
            print(f"正在传输文件：{os.path.basename(local_path)}")
            print(f"  本地路径: {local_path}")
            print(f"  目标路径: {remote_path}")
            
            # 检查文件是否可访问
            try:
                with open(local_path, 'rb') as f:
                    # 只读取一小部分以验证文件可访问
                    f.read(1)
            except (IOError, FileNotFoundError) as e:
                print(f"文件无法访问: {local_path}, 错误: {str(e)}")
                return False
            
            # 创建目标目录
            remote_dir = os.path.dirname(remote_path)
            # 处理路径中的空格问题
            remote_dir = remote_dir.strip()
            
            # 推送文件
            try:
                push_result = self.adb_service.connection._execute_command([
                    self.adb_service.connection.adb_path,
                    "-s", device.device_id,
                    "push", local_path, remote_path
                ])
                
                print(f"文件传输结果: {push_result if push_result else '无输出'}")
                
                # 验证文件是否存在
                verify_result = self.adb_service.connection._execute_command([
                    self.adb_service.connection.adb_path,
                    "-s", device.device_id,
                    "shell", f"ls -la {remote_path}"
                ])
                
                if "No such file or directory" in verify_result:
                    print(f"验证失败: 设备上未找到文件")
                    return False
                else:
                    print(f"验证成功: 文件已成功传输到设备")
                    print(f"  设备上文件信息: {verify_result}")
                    return True
                
            except Exception as e:
                print(f"推送文件时出错: {str(e)}")
                return False
            
        except Exception as e:
            print(f"传输文件时出错: {str(e)}")
            return False

    async def transfer_all_files(self, device: Device, local_files: List[str], remote_files: List[str]) -> bool:
        """
        批量传输文件
        
        Args:
            device: 设备对象
            local_files: 本地文件路径列表
            remote_files: 设备上的目标路径列表
            
        Returns:
            bool: 所有文件是否全部传输成功
        """
        if len(local_files) != len(remote_files):
            print(f"错误: 本地文件数量({len(local_files)})与远程文件数量({len(remote_files)})不匹配")
            return False
        
        total_files = len(local_files)
        successful_transfers = 0
        
        print(f"\n开始传输 {total_files} 个文件到设备 {device.device_name}...")
        
        # 检查设备连接状态
        device_connected = await self.check_device_connection(device)
        if not device_connected:
            print("设备未连接，无法传输文件")
            return False
        
        # 传输所有文件
        for i, (local_path, remote_path) in enumerate(zip(local_files, remote_files)):
            print(f"\n[{i+1}/{total_files}] 传输文件...")
            
            # 每个文件允许重试3次
            for retry in range(3):
                if retry > 0:
                    await asyncio.sleep(2)  # 重试前等待
                    print(f"  重试 #{retry+1}...")
                
                success = await self.transfer_file(device, local_path, remote_path)
                if success:
                    successful_transfers += 1
                    break
                elif retry == 2:  # 最后一次重试失败
                    print(f"  文件传输失败，已达最大重试次数")
                    return False
        
        print(f"\n文件传输完成: {successful_transfers}/{total_files} 成功")
        
        # 发送媒体扫描广播
        try:
            print("\n发送媒体扫描广播...")
            self.adb_service.connection._execute_command([
                self.adb_service.connection.adb_path,
                "-s", device.device_id,
                "shell", "am broadcast -a android.intent.action.MEDIA_SCANNER_SCAN_FILE -d file:///sdcard/Pictures"
            ])
            print("媒体扫描请求已发送")
        except Exception as e:
            print(f"发送媒体扫描广播失败: {str(e)}")
        
        return successful_transfers == total_files