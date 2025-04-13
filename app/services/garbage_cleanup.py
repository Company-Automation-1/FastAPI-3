import os
import shutil
import logging
import asyncio
import time
from datetime import datetime, timedelta
from typing import Optional, Dict, Set
from app.core.config import settings
from app.services.adb_transfer import ADBTransferService
from app.db.session import SessionLocal
from app.models.task import Task
from app.models.upload import Upload
from app.models.device import Device
from sqlalchemy import and_
from app.utils.file import get_file_paths, get_device_file_paths
from app.utils.time_utils import get_current_timestamp

logger = logging.getLogger(__name__)

class GarbageCleanupService:
    def __init__(self):
        self.adb_service = ADBTransferService()
        self.cleanup_interval = int(settings.GARBAGE_CLEANUP_INTERVAL)
        self.expiration_hours = int(settings.GARBAGE_EXPIRATION_HOURS)
        self.retry_delay = int(settings.GARBAGE_RETRY_DELAY)
        self.is_running = False
        self._cleanup_task: Optional[asyncio.Task] = None
        self._processing_devices: Dict[str, Set[str]] = {}  # 设备名 -> 设备ID集合

    async def start(self):
        """启动垃圾清理服务"""
        if self.is_running:
            logger.warning("垃圾清理服务已经在运行中")
            return
        
        self.is_running = True
        self._cleanup_task = asyncio.create_task(self._cleanup_loop())
        logger.info("垃圾清理服务已启动")

    async def stop(self):
        """停止垃圾清理服务"""
        if not self.is_running:
            return
        
        self.is_running = False
        if self._cleanup_task:
            self._cleanup_task.cancel()
            try:
                await self._cleanup_task
            except asyncio.CancelledError:
                pass
        logger.info("垃圾清理服务已停止")

    async def _cleanup_loop(self):
        """垃圾清理主循环"""
        while self.is_running:
            try:
                await self._cleanup_expired_tasks()
                await asyncio.sleep(self.cleanup_interval)
            except Exception as e:
                logger.error(f"垃圾清理过程中发生错误: {str(e)}")
                await asyncio.sleep(self.retry_delay)

    async def _cleanup_expired_tasks(self):
        """清理过期任务"""
        db = SessionLocal()
        try:
            # 计算过期时间点
            current_time = get_current_timestamp()
            expiration_time = current_time - (self.expiration_hours * 3600)
            
            # 查询过期的任务
            expired_tasks = db.query(Task).filter(
                and_(Task.time < expiration_time)
            ).all()

            # 处理每个任务
            for task in expired_tasks:
                try:
                    # 获取设备信息
                    device = db.query(Device).filter(Device.device_name == task.device_name).first()
                    if not device:
                        logger.error(f"找不到设备信息: {task.device_name}")
                        continue

                    # 检查设备是否正在被处理
                    if self._is_device_processing(device.device_id):
                        logger.info(f"设备 {device.device_name}({device.device_id}) 正在被处理，跳过当前任务")
                        continue

                    # 检查设备是否被占用
                    if await self.adb_service.is_device_busy(device.device_id):
                        logger.info(f"设备 {device.device_name}({device.device_id}) 正在被使用，跳过当前任务")
                        continue

                    # 标记设备为处理中
                    self._mark_device_processing(device.device_name, device.device_id)
                    try:
                        # 清理文件
                        await self._cleanup_task_files(task, device)
                        
                        # 获取关联的upload记录
                        upload = db.query(Upload).filter(Upload.id == task.upload_id).first()
                        
                        # 删除upload记录（会级联删除task记录）
                        if upload:
                            db.delete(upload)
                            logger.info(f"已删除上传记录: {upload.id}")
                        else:
                            # 如果没有找到upload记录，直接删除task
                            db.delete(task)
                            logger.info(f"已删除任务记录: {task.id}")
                        
                        db.commit()
                        logger.info(f"已清理过期任务: {task.id}")
                    finally:
                        # 无论成功与否，都移除处理标记
                        self._unmark_device_processing(device.device_name, device.device_id)

                except Exception as e:
                    logger.error(f"清理任务 {task.id} 时发生错误: {str(e)}")
                    db.rollback()
                    continue

        except Exception as e:
            logger.error(f"查询过期任务时发生错误: {str(e)}")
            db.rollback()
        finally:
            db.close()

    def _is_device_processing(self, device_id: str) -> bool:
        """检查设备ID是否正在被处理"""
        # 检查设备ID是否在处理集合中
        for device_names in self._processing_devices.values():
            if device_id in device_names:
                return True
        return False

    def _mark_device_processing(self, device_name: str, device_id: str):
        """标记设备为处理中"""
        if device_id not in self._processing_devices:
            self._processing_devices[device_id] = set()
        self._processing_devices[device_id].add(device_name)

    def _unmark_device_processing(self, device_name: str, device_id: str):
        """移除设备的处理标记"""
        if device_id in self._processing_devices:
            self._processing_devices[device_id].discard(device_name)
            if not self._processing_devices[device_id]:
                del self._processing_devices[device_id]

    async def _cleanup_task_files(self, task: Task, device: Device):
        """清理任务相关的文件"""
        try:
            # 获取任务创建时间的时间戳
            timestamp = task.timestamp
            
            # 获取本地文件路径列表
            local_paths = get_file_paths(task.files, task.device_name, timestamp)
            
            # 清理本地文件
            for local_path in local_paths:
                if os.path.exists(local_path):
                    try:
                        # 删除文件
                        os.remove(local_path)
                        logger.info(f"已清理本地文件: {local_path}")
                    except Exception as e:
                        logger.error(f"清理本地文件 {local_path} 时发生错误: {str(e)}")
            
            # 获取设备文件路径列表
            device_paths = get_device_file_paths(task.files, task.device_name, device.device_path, timestamp)
            
            # 清理设备文件
            if device_paths:
                try:
                    # 连接设备并解锁
                    await self.adb_service.connect_device(device.device_id)
                    await self.adb_service.unlock_device(device.device_id, device.password)
                    
                    # 清理每个设备文件
                    for device_path in device_paths:
                        try:
                            await self.adb_service.remove_device_file(device_path)
                            logger.info(f"已清理设备文件: {device_path}")
                        except Exception as e:
                            logger.error(f"清理设备文件 {device_path} 时发生错误: {str(e)}")
                            continue
                    
                    # 熄屏
                    await self.adb_service.turn_off_screen(device.device_id)
                    
                    # 断开设备连接
                    await self.adb_service.disconnect_device(device.device_id)
                except Exception as e:
                    logger.error(f"清理设备文件时发生错误: {str(e)}")
            
        except Exception as e:
            logger.error(f"清理任务文件时发生错误: {str(e)}")

    async def _wait_for_device_available(self, device_id: str, max_retries: int = 5):
        """等待设备可用"""
        for _ in range(max_retries):
            try:
                # 检查设备是否被占用
                if not await self.adb_service.is_device_busy(device_id):
                    return
                await asyncio.sleep(self.retry_delay)
            except Exception as e:
                logger.error(f"检查设备 {device_id} 状态时发生错误: {str(e)}")
                await asyncio.sleep(self.retry_delay)
        
        raise TimeoutError(f"设备 {device_id} 在指定时间内无法使用") 