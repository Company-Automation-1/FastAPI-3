# main.py
from fastapi import FastAPI, Depends
from app.core.config import settings
from app.api.v1 import device, upload, task
from fastapi.middleware.cors import CORSMiddleware
from app.services.scheduler import TaskScheduler
from app.services.adb_transfer import ADBTransferService
from app.models.task import TaskStatus
from app.services.automation_service import AutomationService
from app.db.session import engine, SessionLocal, close_db_connection
from app.db.base_class import Base
from app.services.task import TaskService
from app.services.app_lifecycle import AppLifecycle
# from app.services.garbage_cleanup import GarbageCleanupService
import logging
import asyncio
import signal
import sys
import time
from apscheduler.triggers.interval import IntervalTrigger
from fastapi import applications
from fastapi.openapi.docs import get_swagger_ui_html

def swagger_monkey_patch(*args, **kwargs):
    return get_swagger_ui_html(
        *args, **kwargs,
        swagger_js_url="https://cdn.staticfile.net/swagger-ui/5.1.0/swagger-ui-bundle.min.js",
        swagger_css_url="https://cdn.staticfile.net/swagger-ui/5.1.0/swagger-ui.min.css"
    )

applications.get_swagger_ui_html = swagger_monkey_patch

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# 项目基本配置
PROJECT_NAME: str = "FastAPI Device Manager"
API_V1_STR: str = "/api/v1"

# 添加状态码说明到描述中
API_DESCRIPTION = """
# FastAPI Device Manager API

## 状态码说明

### 成功状态码
- 200: 操作成功
- 201: 创建成功
- 202: 请求已接受

### 客户端错误状态码
- 400: 请求参数错误
- 401: 未授权
- 403: 禁止访问
- 404: 资源不存在
- 405: 方法不允许
- 409: 资源冲突

### 服务器错误状态码
- 500: 服务器内部错误
- 503: 服务不可用

### 业务状态码

#### 设备相关 (1000-1999)
- 1001: 设备不存在
- 1002: 设备已存在
- 1003: 设备连接失败
- 1004: 设备离线

#### 上传相关 (2000-2999)
- 2001: 上传失败
- 2002: 文件不存在
- 2003: 文件过大

#### 任务相关 (3000-3999)
- 3001: 任务不存在
- 3002: 任务已存在
- 3003: 任务执行失败

#### ADB相关 (4000-4999)
- 4001: ADB连接错误
- 4002: ADB命令执行错误
- 4003: ADB设备未找到
- 4004: ADB权限不足
"""

app = FastAPI(
    title=PROJECT_NAME,
    openapi_url=f"{API_V1_STR}/openapi.json",
    description=API_DESCRIPTION
)

# 添加CORS中间件
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 在生产环境中应该设置具体的域名
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 注册路由
app.include_router(device.router, prefix=API_V1_STR)
app.include_router(upload.router, prefix=API_V1_STR)
app.include_router(task.router, prefix=API_V1_STR)

@app.on_event("startup")
async def startup_event():
    """应用启动时的初始化操作"""
    try:
        # 初始化ADB传输服务
        adb_service = ADBTransferService()
        
        # 初始化自动化服务
        automation_service = AutomationService()
        
        # 创建任务调度器
        task_scheduler = TaskScheduler(
            task_executor=adb_service.execute_transfer,
            check_interval=30,
            max_retries=3,
            retry_delay=2,
            task_type="WT"  # 文件传输任务
        )
        
        # 创建UI调度器
        ui_scheduler = TaskScheduler(
            task_executor=automation_service.execute_pending_task,
            check_interval=30,
            max_retries=3,
            retry_delay=2,
            task_type="PENDING"  # UI自动化任务
        )
        
        # 创建垃圾清理服务
        # garbage_cleanup = GarbageCleanupService()
        
        # 启动调度器
        await task_scheduler.start()
        await ui_scheduler.start()
        # await garbage_cleanup.start()
        
        # 创建应用生命周期管理器
        global app_lifecycle
        app_lifecycle = AppLifecycle(
            task_scheduler=task_scheduler,
            ui_scheduler=ui_scheduler,
            adb_transfer_service=adb_service,
            # garbage_cleanup=garbage_cleanup
        )
        
        logger.info("所有任务调度器已启动")
        
    except Exception as e:
        logger.error(f"应用启动失败: {str(e)}")
        raise

@app.on_event("shutdown")
async def shutdown_event():
    """应用关闭时的清理操作"""
    try:
        # 关闭调度器
        if app_lifecycle.task_scheduler:
            await app_lifecycle.task_scheduler.stop()
        if app_lifecycle.ui_scheduler:
            await app_lifecycle.ui_scheduler.stop()
        # if app_lifecycle.garbage_cleanup:
        #     await app_lifecycle.garbage_cleanup.stop()
            
        # 关闭数据库连接池
        close_db_connection()
        
        logger.info("应用已安全关闭")
        
    except Exception as e:
        logger.error(f"应用关闭时出错: {str(e)}")

def signal_handler(signum, frame):
    """处理系统信号"""
    logger.info("收到关闭信号，正在关闭应用...")
    sys.exit(0)

# 注册信号处理器
signal.signal(signal.SIGINT, signal_handler)
signal.signal(signal.SIGTERM, signal_handler)