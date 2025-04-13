import pytest
import asyncio
from unittest.mock import patch, MagicMock, AsyncMock
from app.services.task_executor import TaskExecutor
from app.services.task_dispatcher import TaskDispatcher
from app.services.wt_task_scheduler import WTTaskScheduler
from app.services.pending_task_scheduler import PendingTaskScheduler
from tests.conftest import TestTask
from app.models.task import TaskStatus

class TestTaskExecutor:
    """测试任务执行器"""
    
    @pytest.fixture
    def mock_adb_service(self):
        """创建模拟的ADB传输服务"""
        mock_service = MagicMock()
        mock_service.execute_transfer = AsyncMock(return_value=True)
        return mock_service
    
    @pytest.fixture
    def mock_automation_service(self):
        """创建模拟的自动化服务"""
        mock_service = MagicMock()
        mock_service.execute_pending_task = AsyncMock(return_value=True)
        return mock_service
    
    @pytest.fixture
    def task_executor(self, mock_adb_service, mock_automation_service):
        """创建任务执行器"""
        callback = MagicMock()
        return TaskExecutor(
            adb_service=mock_adb_service,
            automation_service=mock_automation_service,
            status_update_callback=callback,
            max_retries=2,
            retry_delay=0.1  # 加快测试速度
        )
    
    @pytest.mark.asyncio
    async def test_execute_wt_task_success(self, task_executor, db_session):
        """测试执行WT任务-成功"""
        # 创建测试任务
        task = TestTask(id=1, status=TaskStatus.WT)
        
        # 执行函数
        result = await task_executor.execute_wt_task(task, db_session)
        
        # 验证结果
        assert result is True
        task_executor.adb_service.execute_transfer.assert_called_once_with(task, db_session)
        task_executor.status_update_callback.assert_called_once_with(task, TaskStatus.PENDING, db_session)
    
    @pytest.mark.asyncio
    async def test_execute_wt_task_failure(self, task_executor, db_session):
        """测试执行WT任务-失败"""
        # 设置模拟
        task_executor.adb_service.execute_transfer = AsyncMock(return_value=False)
        
        # 创建测试任务
        task = TestTask(id=1, status=TaskStatus.WT)
        
        # 执行函数
        result = await task_executor.execute_wt_task(task, db_session)
        
        # 验证结果
        assert result is False
        task_executor.status_update_callback.assert_called_once_with(task, TaskStatus.WTERR, db_session)
    
    @pytest.mark.asyncio
    async def test_execute_pending_task_success(self, task_executor, db_session):
        """测试执行PENDING任务-成功"""
        # 创建测试任务
        task = TestTask(id=1, status=TaskStatus.PENDING)
        
        # 执行函数
        result = await task_executor.execute_pending_task(task, db_session)
        
        # 验证结果
        assert result is True
        task_executor.automation_service.execute_pending_task.assert_called_once_with(task, db_session)
        task_executor.status_update_callback.assert_called_once_with(task, TaskStatus.RES, db_session)
    
    @pytest.mark.asyncio
    async def test_execute_with_retry(self, task_executor, db_session):
        """测试重试逻辑"""
        # 设置模拟：第一次失败，第二次成功
        side_effect = [False, True]
        task_executor.adb_service.execute_transfer = AsyncMock(side_effect=side_effect)
        
        # 创建测试任务
        task = TestTask(id=1, status=TaskStatus.WT)
        
        # 执行函数
        result = await task_executor.execute_wt_task(task, db_session)
        
        # 验证结果
        assert result is True
        assert task_executor.adb_service.execute_transfer.call_count == 2


class TestTaskDispatcher:
    """测试任务分发器"""
    
    @pytest.fixture
    def mock_wt_scheduler(self):
        """创建模拟的WT任务调度器"""
        scheduler = MagicMock(spec=WTTaskScheduler)
        scheduler.schedule_task = MagicMock()
        return scheduler
    
    @pytest.fixture
    def mock_pending_scheduler(self):
        """创建模拟的PENDING任务调度器"""
        scheduler = MagicMock(spec=PendingTaskScheduler)
        scheduler.schedule_task = MagicMock()
        return scheduler
    
    @pytest.fixture
    def task_dispatcher(self, mock_wt_scheduler, mock_pending_scheduler):
        """创建任务分发器"""
        dispatcher = TaskDispatcher()
        dispatcher.register_scheduler(TaskStatus.WT, mock_wt_scheduler)
        dispatcher.register_scheduler(TaskStatus.PENDING, mock_pending_scheduler)
        return dispatcher
    
    def test_dispatch_wt_task(self, task_dispatcher):
        """测试分发WT任务"""
        # 创建测试任务
        task = TestTask(id=1, status=TaskStatus.WT)
        
        # 执行分发
        task_dispatcher.dispatch_task(task)
        
        # 验证结果
        wt_scheduler = task_dispatcher.schedulers[TaskStatus.WT]
        wt_scheduler.schedule_task.assert_called_once_with(task)
        
    def test_dispatch_pending_task(self, task_dispatcher):
        """测试分发PENDING任务"""
        # 创建测试任务
        task = TestTask(id=1, status=TaskStatus.PENDING)
        
        # 执行分发
        task_dispatcher.dispatch_task(task)
        
        # 验证结果
        pending_scheduler = task_dispatcher.schedulers[TaskStatus.PENDING]
        pending_scheduler.schedule_task.assert_called_once_with(task)
    
    def test_dispatch_unknown_task(self, task_dispatcher):
        """测试分发未知状态任务"""
        # 创建测试任务
        task = TestTask(id=1, status="UNKNOWN")
        
        # 执行分发
        task_dispatcher.dispatch_task(task)
        
        # 验证未调用任何调度器
        for scheduler in task_dispatcher.schedulers.values():
            scheduler.schedule_task.assert_not_called()


class TestTaskSchedulers:
    """测试任务调度器"""
    
    @pytest.fixture
    def mock_executor(self):
        """创建模拟的任务执行器"""
        executor = MagicMock(spec=TaskExecutor)
        return executor
    
    @pytest.mark.asyncio
    async def test_wt_scheduler(self, mock_executor):
        """测试WT任务调度器"""
        # 创建调度器
        scheduler = WTTaskScheduler(executor=mock_executor)
        
        # 创建测试任务
        task = TestTask(id=1, device_name="test_device")
        
        # 执行调度
        scheduler.schedule_task(task)
        
        # 等待调度队列处理
        await asyncio.sleep(0.2)
        
        # 检查是否添加到了设备队列
        assert task.device_name in scheduler.device_queues
        
        # 关闭调度器的任务队列
        for queue in scheduler.device_queues.values():
            queue.put_nowait(None)  # 发送终止信号
        
        # 等待所有任务结束
        for task in asyncio.all_tasks():
            if task != asyncio.current_task():
                try:
                    await asyncio.wait_for(task, timeout=0.5)
                except asyncio.TimeoutError:
                    pass
    
    def test_pending_scheduler(self, mock_executor):
        """测试PENDING任务调度器"""
        # 创建调度器
        scheduler = PendingTaskScheduler(executor=mock_executor, max_workers=2)
        
        try:
            # 创建测试任务
            task = TestTask(id=1, device_name="test_device")
            
            # 执行调度
            scheduler.schedule_task(task)
            
            # 由于线程池执行，这里只能做有限的测试
            assert scheduler.device_tasks[task.device_name] == [task]
        finally:
            # 清理线程池
            scheduler.shutdown() 