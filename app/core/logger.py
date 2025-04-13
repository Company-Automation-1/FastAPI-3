import logging
import sys
import os
from logging.handlers import TimedRotatingFileHandler
from datetime import datetime
import threading
import time
import traceback
import re

# 定义已知异常模式，用于减少堆栈信息输出
KNOWN_EXCEPTION_PATTERNS = [
    # 数据库连接错误
    r"Can't connect to MySQL server",
    r"Connection refused", 
    # 文件操作错误
    r"No such file or directory",
    r"Permission denied",
    # 网络请求错误
    r"Connection reset by peer",
    r"Connection timed out",
    # ADB相关错误
    r"device '[\w\-]+' not found",
    r"adb: command not found",
    # 时间解析错误
    r"time data .+ does not match format",
    # 内存错误
    r"MemoryError",
    # 键值错误
    r"KeyError: '\w+'"
]

def is_known_exception(exc_type, exc_message):
    """检查是否为已知异常类型
    
    参数:
        exc_type: 异常类型
        exc_message: 异常信息
    
    返回:
        bool: 是否为已知异常
    """
    # 某些特定类型的异常总是被视为已知异常
    known_exc_types = [
        "FileNotFoundError", 
        "PermissionError", 
        "ConnectionError",
        "TimeoutError", 
        "KeyError", 
        "ValueError",
        "MemoryError"
    ]
    
    if exc_type and exc_type.__name__ in known_exc_types:
        return True
        
    if not exc_message:
        return False
        
    error_message = str(exc_message)
    for pattern in KNOWN_EXCEPTION_PATTERNS:
        if re.search(pattern, error_message):
            return True
            
    return False

def setup_logger(log_level=logging.INFO):
    """配置增强的日志记录器
    
    参数:
        log_level: 日志级别，默认为INFO
    """
    # 创建logs目录（如果不存在）
    logs_dir = os.path.join(os.getcwd(), 'logs')
    if not os.path.exists(logs_dir):
        os.makedirs(logs_dir)
    
    # 生成日志文件名（包含日期）
    log_file = os.path.join(logs_dir, f'app_{datetime.now().strftime("%Y%m%d")}.log')
    
    # 创建日志格式
    log_format = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    
    # 配置根日志记录器
    root_logger = logging.getLogger()
    root_logger.setLevel(log_level)
    
    # 清除已有的处理器（避免重复）
    if root_logger.handlers:
        root_logger.handlers.clear()
    
    # 添加控制台处理器
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(log_format)
    root_logger.addHandler(console_handler)
    
    # 添加文件处理器（按天滚动）
    file_handler = TimedRotatingFileHandler(
        log_file,
        when='midnight',
        interval=1,
        backupCount=30,  # 保留30天的日志
        encoding='utf-8'
    )
    file_handler.setFormatter(log_format)
    root_logger.addHandler(file_handler)
    
    # 添加错误日志文件处理器（仅记录ERROR级别以上的日志）
    error_log_file = os.path.join(logs_dir, f'error_{datetime.now().strftime("%Y%m%d")}.log')
    error_file_handler = TimedRotatingFileHandler(
        error_log_file,
        when='midnight',
        interval=1,
        backupCount=30,
        encoding='utf-8'
    )
    error_file_handler.setFormatter(log_format)
    error_file_handler.setLevel(logging.ERROR)
    root_logger.addHandler(error_file_handler)
    
    # 添加运行报告日志文件处理器（记录所有级别的日志到专门的运行报告文件）
    runtime_report_dir = os.path.join(logs_dir, 'runtime_reports')
    if not os.path.exists(runtime_report_dir):
        os.makedirs(runtime_report_dir)
    
    runtime_report_file = os.path.join(runtime_report_dir, f'runtime_report_{datetime.now().strftime("%Y%m%d_%H%M%S")}.log')
    runtime_handler = logging.FileHandler(runtime_report_file, encoding='utf-8')
    runtime_handler.setFormatter(log_format)
    runtime_handler.setLevel(log_level)
    root_logger.addHandler(runtime_handler)
    
    # 禁用第三方库的过多日志
    logging.getLogger('urllib3').setLevel(logging.WARNING)
    logging.getLogger('sqlalchemy').setLevel(logging.WARNING)
    
    # 创建并启动自动日志记录线程
    start_runtime_monitor(runtime_report_file)
    
    # 设置全局异常处理器
    setup_global_exception_handler()
    
    logging.info("日志系统初始化完成，日志将保存到: %s", logs_dir)
    logging.info("运行报告将保存到: %s", runtime_report_file)
    
    return root_logger

def start_runtime_monitor(report_file):
    """启动运行时监控线程，定期记录系统状态
    
    参数:
        report_file: 运行报告文件路径
    """
    monitor_thread = threading.Thread(
        target=runtime_monitor_thread,
        args=(report_file,),
        daemon=True  # 守护线程，主程序退出时会自动结束
    )
    monitor_thread.start()
    logging.info("运行时监控线程已启动")

def runtime_monitor_thread(report_file):
    """运行时监控线程函数，定期记录系统状态
    
    参数:
        report_file: 运行报告文件路径
    """
    # 创建专用于此线程的日志记录器
    monitor_logger = logging.getLogger("runtime_monitor")
    
    # 导入需要的模块
    import psutil
    import platform
    from app.core.config import settings
    
    # 记录初始系统信息
    try:
        # 记录系统基本信息
        monitor_logger.info("=== 系统启动信息 ===")
        monitor_logger.info("操作系统: %s %s", platform.system(), platform.version())
        monitor_logger.info("Python版本: %s", sys.version.replace('\n', ' '))
        monitor_logger.info("CPU核心数: %s", psutil.cpu_count())
        monitor_logger.info("内存总量: %.2f GB", psutil.virtual_memory().total / (1024**3))
        monitor_logger.info("启动时间: %s", datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
        monitor_logger.info("工作目录: %s", os.getcwd())
        
        # 记录应用配置信息（排除敏感信息）
        monitor_logger.info("=== 应用配置信息 ===")
        for key, value in vars(settings).items():
            if not key.startswith("__") and not any(sensitive in key.lower() for sensitive in ["password", "token", "secret", "key"]):
                monitor_logger.info("配置项 %s: %s", key, value)
    except Exception as e:
        monitor_logger.error("记录系统信息时出错: %s", str(e))
        # 只有未知异常才记录完整堆栈
        if not is_known_exception(type(e), e):
            monitor_logger.error(traceback.format_exc())
        else:
            monitor_logger.error("错误类型: %s", type(e).__name__)
    
    # 定期记录系统状态
    interval = 300  # 每5分钟记录一次系统状态
    
    while True:
        try:
            time.sleep(interval)
            
            # 记录CPU使用率
            cpu_percent = psutil.cpu_percent(interval=1)
            
            # 记录内存使用情况
            mem = psutil.virtual_memory()
            
            # 记录磁盘使用情况
            disk = psutil.disk_usage('/')
            
            # 记录系统状态
            monitor_logger.info("=== 系统状态报告 (%s) ===", 
                              datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
            monitor_logger.info("CPU使用率: %.1f%%", cpu_percent)
            monitor_logger.info("内存使用: %.1f GB (%.1f%%)", 
                              mem.used / (1024**3), mem.percent)
            monitor_logger.info("磁盘使用: %.1f GB (%.1f%%)", 
                              disk.used / (1024**3), disk.percent)
            
            # 记录进程信息
            process = psutil.Process()
            monitor_logger.info("进程CPU使用率: %.1f%%", process.cpu_percent(interval=1))
            monitor_logger.info("进程内存使用: %.2f MB", 
                              process.memory_info().rss / (1024*1024))
            monitor_logger.info("进程运行时间: %.1f 分钟", 
                              (time.time() - process.create_time()) / 60)
            
            # 尝试收集并记录任务系统状态
            try:
                from app.db.session import SessionLocal
                from app.models.task import Task, TaskStatus
                from sqlalchemy import func
                
                db = SessionLocal()
                try:
                    # 获取各状态任务数量
                    task_counts = db.query(
                        Task.status, 
                        func.count(Task.id).label('count')
                    ).group_by(Task.status).all()
                    
                    # 获取今日任务数量
                    today = datetime.now().strftime("%Y%m%d")
                    today_count = db.query(func.count(Task.id)).filter(
                        func.substr(func.cast(Task.time, "text"), 1, 8) == today
                    ).scalar()
                    
                    # 记录任务状态
                    monitor_logger.info("=== 任务系统状态 ===")
                    monitor_logger.info("今日任务总数: %s", today_count)
                    for status, count in task_counts:
                        monitor_logger.info("状态 %s: %s 个任务", status, count)
                finally:
                    db.close()
            except Exception as e:
                monitor_logger.warning("收集任务状态信息失败: %s", str(e))
                # 只有未知异常才记录详细信息
                if not is_known_exception(type(e), e):
                    monitor_logger.warning("异常详情: %s", traceback.format_exc())
            
        except Exception as e:
            monitor_logger.error("运行监控线程出错: %s", str(e))
            # 只有未知异常才记录完整堆栈
            if not is_known_exception(type(e), e):
                monitor_logger.error(traceback.format_exc())
            else:
                monitor_logger.error("错误类型: %s", type(e).__name__)
        
        # 在每次迭代后检查报告文件是否仍然存在
        # 如果被删除或移动，则退出线程
        if not os.path.exists(report_file):
            monitor_logger.warning("运行报告文件不存在，监控线程退出")
            break 

def setup_global_exception_handler():
    """设置全局异常处理器，捕获未处理的异常并记录到日志"""
    original_hook = sys.excepthook
    
    def exception_handler(exc_type, exc_value, exc_traceback):
        """全局异常处理函数"""
        # 使用专用记录器记录未捕获的异常
        logger = logging.getLogger("uncaught_exception")
        
        # 检查是否为已知异常
        if is_known_exception(exc_type, exc_value):
            # 对于已知异常，只记录简要信息
            logger.error(
                "未捕获的异常: %s - %s", 
                exc_type.__name__, 
                str(exc_value)
            )
        else:
            # 对于未知异常，记录完整堆栈
            logger.critical(
                "未捕获的异常: %s",
                "".join(traceback.format_exception(exc_type, exc_value, exc_traceback))
            )
        
        # 调用原始的异常处理器
        original_hook(exc_type, exc_value, exc_traceback)
    
    # 设置全局异常处理器
    sys.excepthook = exception_handler 