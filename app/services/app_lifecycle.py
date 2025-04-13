import asyncio
import logging
import signal
from typing import Optional

from app.services.task_scanner import TaskScanner
from app.services.task_dispatcher import TaskDispatcher
from app.services.wt_task_scheduler import WTTaskScheduler
from app.services.pending_task_scheduler import PendingTaskScheduler
from app.services.task_executor import TaskExecutor
from app.services.device_operation_service import DeviceOperationService
from app.services.adb_transfer import ADBTransferService
from app.services.automation_service import AutomationService
from app.services.garbage_cleanup import GarbageCleanupService

logger = logging.getLogger(__name__)

class AppLifecycle:
    """应用程序生命周期管理"""
    
    def __init__(
        self,
        task_scanner: Optional[TaskScanner] = None,
        task_dispatcher: Optional[TaskDispatcher] = None,
        wt_scheduler: Optional[WTTaskScheduler] = None,
        pending_scheduler: Optional[PendingTaskScheduler] = None,
        task_executor: Optional[TaskExecutor] = None,
        device_operation_service: Optional[DeviceOperationService] = None,
        adb_service: Optional[ADBTransferService] = None,
        automation_service: Optional[AutomationService] = None,
        garbage_cleanup: Optional[GarbageCleanupService] = None
    ):
        """
        初始化应用程序生命周期管理
        
        Args:
            task_scanner: 任务扫描器
            task_dispatcher: 任务分发器
            wt_scheduler: WT任务调度器
            pending_scheduler: PENDING任务调度器
            task_executor: 任务执行器
            device_operation_service: 设备操作服务
            adb_service: ADB传输服务
            automation_service: 自动化服务
            garbage_cleanup: 垃圾清理服务
        """
        self.task_scanner = task_scanner
        self.task_dispatcher = task_dispatcher
        self.wt_scheduler = wt_scheduler
        self.pending_scheduler = pending_scheduler
        self.task_executor = task_executor
        self.device_operation_service = device_operation_service
        self.adb_service = adb_service
        self.automation_service = automation_service
        self.garbage_cleanup = garbage_cleanup
    
    async def startup(self):
        """应用程序启动时执行"""
        if self.task_scanner:
            await self.task_scanner.start()
            logger.info("任务扫描器已启动")
    
    async def shutdown(self, loop=None, signal=None):
        """
        应用程序关闭时执行
        
        Args:
            loop: 事件循环
            signal: 触发关闭的信号
        """
        if signal:
            print(f"\n收到退出信号 {signal.name if signal else 'unknown'}")
        
        print("正在关闭所有组件...")
        
        # 停止扫描器
        if self.task_scanner:
            await self.task_scanner.stop()
            print("任务扫描器已停止")
        
        # 关闭PENDING调度器的线程池
        if self.pending_scheduler:
            self.pending_scheduler.shutdown()
            print("PENDING任务调度器已停止")
        
        # 关闭ADB服务
        try:
            # 先关闭ADB传输服务
            if self.adb_service and hasattr(self.adb_service, 'adb_service'):
                self.adb_service.adb_service.kill_server()
                print("ADB传输服务已停止")
                
            # 再关闭设备操作服务的ADB服务
            if self.device_operation_service and hasattr(self.device_operation_service, 'adb_service'):
                self.device_operation_service.adb_service.kill_server()
                print("设备操作服务已停止")
        except Exception as e:
            print(f"关闭ADB服务出错: {e}")
        
        # 关闭垃圾清理服务
        if self.garbage_cleanup:
            await self.garbage_cleanup.stop()
            print("垃圾清理服务已停止")
        
        if loop:
            # 取消所有任务
            tasks = [t for t in asyncio.all_tasks() if t is not asyncio.current_task()]
            print(f"正在取消 {len(tasks)} 个后台任务...")
            for task in tasks:
                task.cancel()
                
            await asyncio.gather(*tasks, return_exceptions=True)
            
            loop.stop()
            
        print("所有服务已安全关闭") 