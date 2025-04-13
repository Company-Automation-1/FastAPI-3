import asyncio
import logging
import signal
from app.services.scheduler import TaskScheduler
from app.services.adb_transfer import ADBTransferService
from app.services.garbage_cleanup import GarbageCleanupService
from typing import Optional

logger = logging.getLogger(__name__)

class AppLifecycle:
    """应用程序生命周期管理"""
    
    def __init__(
        self,
        task_scheduler: Optional[TaskScheduler] = None,
        ui_scheduler: Optional[TaskScheduler] = None,
        adb_transfer_service: Optional[ADBTransferService] = None,
        garbage_cleanup: Optional[GarbageCleanupService] = None
    ):
        """
        初始化应用程序生命周期管理
        
        Args:
            task_scheduler: 文件传输任务调度器
            ui_scheduler: UI自动化任务调度器
            adb_transfer_service: ADB传输服务
            garbage_cleanup: 垃圾清理服务
        """
        self.task_scheduler = task_scheduler
        self.ui_scheduler = ui_scheduler
        self.adb_transfer_service = adb_transfer_service
        self.garbage_cleanup = garbage_cleanup
    
    async def startup(self):
        """应用程序启动时执行"""
        await self.task_scheduler.start()
        await self.ui_scheduler.start()
        logger.info("所有任务调度器已启动")
    
    async def shutdown(self, loop=None, signal=None):
        """
        应用程序关闭时执行
        
        Args:
            loop: 事件循环
            signal: 触发关闭的信号
        """
        if signal:
            print(f"\n收到退出信号 {signal.name if signal else 'unknown'}")
        
        print("正在关闭调度器...")
        
        # 停止调度器
        await self.task_scheduler.stop()
        await self.ui_scheduler.stop()
        
        print("正在关闭ADB服务...")
        try:
            # 关闭ADB服务
            if hasattr(self.adb_transfer_service, 'adb_service'):
                self.adb_transfer_service.adb_service.kill_server()
        except Exception as e:
            print(f"关闭ADB服务出错: {e}")
        
        if loop:
            # 取消所有任务
            tasks = [t for t in asyncio.all_tasks() if t is not asyncio.current_task()]
            print(f"正在取消 {len(tasks)} 个后台任务...")
            for task in tasks:
                task.cancel()
                
            await asyncio.gather(*tasks, return_exceptions=True)
            
            loop.stop()
            
        print("服务已安全关闭") 