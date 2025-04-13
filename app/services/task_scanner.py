import logging
import asyncio
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger
from sqlalchemy.orm import Session, joinedload
from app.db.session import SessionLocal
from app.models.task import Task, TaskStatus
from typing import Dict, Callable, List, Any
from contextlib import asynccontextmanager
from app.utils.time_utils import get_current_timestamp
import traceback
import re

logger = logging.getLogger(__name__)

# 定义已知任务扫描错误模式
KNOWN_SCANNER_ERROR_PATTERNS = [
    # 数据库连接错误
    r"Can't connect to MySQL server",
    r"Connection refused",
    r"Lost connection to MySQL server",
    # SQLAlchemy错误
    r"SQLAlchemy error",
    r"Database is not available",
    # 任务调度错误
    r"Task .+ already exists",
    r"No scheduler found for status",
    # 时间格式错误
    r"time data .+ does not match format"
]

class TaskScanner:
    """任务扫描器 - 只负责定期扫描数据库中的任务，然后将任务分发给任务分发器"""
    
    def __init__(
        self,
        dispatcher: 'TaskDispatcher',
        check_interval: int = 30
    ):
        """
        初始化任务扫描器
        
        Args:
            dispatcher: 任务分发器
            check_interval: 检查任务间隔（秒）
        """
        self.dispatcher = dispatcher
        self.check_interval = check_interval
        self.scheduler = AsyncIOScheduler()
        self._running = False
        self._logger = logging.getLogger(f"{__name__}.TaskScanner")
    
    async def start(self):
        """启动扫描器"""
        if self._running:
            return
            
        self._running = True
        
        # 启动任务检查
        self.scheduler.add_job(
            self.scan_tasks,
            trigger=IntervalTrigger(seconds=self.check_interval),
            id='scan_tasks',
            replace_existing=True
        )
        self.scheduler.start()
        
        self._logger.info(f"任务扫描器已启动，扫描间隔: {self.check_interval}秒")

    async def stop(self):
        """停止扫描器"""
        if not self._running:
            return
            
        self._running = False
        self.scheduler.shutdown()
        self._logger.info("任务扫描器已停止")

    async def scan_tasks(self):
        """扫描任务"""
        try:
            self._logger.debug("开始扫描任务...")
            async with self._get_db() as db:
                # 扫描WT状态的任务
                wt_tasks = self._get_tasks_by_status(db, TaskStatus.WT)
                if wt_tasks:
                    self._logger.info(f"发现 {len(wt_tasks)} 个 WT 状态的任务")
                    # 将任务交给分发器处理
                    for task in wt_tasks:
                        self.dispatcher.dispatch_task(task, TaskStatus.WT)
                
                # 扫描PENDING状态的任务
                pending_tasks = self._get_pending_tasks(db)
                if pending_tasks:
                    self._logger.info(f"发现 {len(pending_tasks)} 个待执行的 PENDING 状态任务")
                    # 将任务交给分发器处理
                    for task in pending_tasks:
                        self.dispatcher.dispatch_task(task, TaskStatus.PENDING)
                
        except Exception as e:
            # 判断是否为已知错误
            error_message = str(e)
            is_known_error = False
            
            # 检查是否为已知的数据库连接错误或其他常见错误
            for pattern in KNOWN_SCANNER_ERROR_PATTERNS:
                if re.search(pattern, error_message):
                    is_known_error = True
                    break
            
            # 记录错误信息
            if is_known_error:
                # 已知错误 - 只记录简要信息
                self._logger.error(f"扫描任务时出错: {error_message.split('(Background')[0]}")  # 移除背景信息链接
            else:
                # 未知错误 - 记录完整堆栈
                self._logger.error(f"扫描任务时出错: {error_message}")
                self._logger.error(traceback.format_exc())
    
    def _get_tasks_by_status(self, db: Session, status: str) -> List[Task]:
        """获取指定状态的任务"""
        return db.query(Task).options(
            joinedload(Task.device),
            joinedload(Task.upload)
        ).filter(Task.status == status).all()
    
    def _get_pending_tasks(self, db: Session) -> List[Task]:
        """获取需要执行的PENDING任务（到期的）"""
        current_time = get_current_timestamp()
        return db.query(Task).options(
            joinedload(Task.device),
            joinedload(Task.upload)
        ).filter(
            Task.status == TaskStatus.PENDING,
            Task.time <= current_time
        ).all()
    
    @asynccontextmanager
    async def _get_db(self):
        """获取数据库会话"""
        db = SessionLocal()
        try:
            yield db
        finally:
            db.close() 