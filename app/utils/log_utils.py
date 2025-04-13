"""
日志工具模块 - 提供通用的日志处理函数
"""
import logging
import re
import traceback
from typing import Any, Dict, List, Type, Optional, Union

# 常见错误类型列表
COMMON_ERROR_TYPES = [
    "FileNotFoundError",
    "PermissionError",
    "ConnectionError",
    "TimeoutError",
    "KeyError",
    "ValueError",
    "TypeError",
    "AttributeError",
    "IndexError",
    "MemoryError",
    "IOError",
    "OSError"
]

# 常见错误消息模式
COMMON_ERROR_PATTERNS = [
    # 数据库错误
    r"Can't connect to \w+ server",
    r"Connection refused",
    r"Lost connection to \w+ server",
    r"Too many connections",
    r"Access denied for user",
    r"Table '\w+' doesn't exist",
    r"Unknown column '\w+' in",
    
    # 文件操作错误
    r"No such file or directory",
    r"Permission denied",
    r"File exists",
    r"Is a directory",
    r"Not a directory",
    r"Disk quota exceeded",
    r"No space left on device",
    
    # 网络错误
    r"Connection reset by peer",
    r"Connection timed out",
    r"Network is unreachable",
    r"Connection refused",
    r"Host is down",
    
    # 解析错误
    r"Syntax error",
    r"Invalid syntax",
    r"Invalid \w+",
    r"Malformed \w+",
    r"Expected \w+",
    
    # 设备错误
    r"Device not found",
    r"Device disconnected",
    r"Device busy",
    r"Device error",
    
    # 其他常见错误
    r"Operation timed out",
    r"Maximum recursion depth exceeded",
    r"Not enough memory",
    r"Out of memory",
    r"Resource temporarily unavailable",
    r"Token has expired"
]

def is_common_error(exc: Union[Exception, str, Type[Exception]]) -> bool:
    """检查是否为常见错误类型
    
    参数:
        exc: 异常对象、异常消息或异常类型
        
    返回:
        bool: 是否为常见错误
    """
    # 处理异常对象
    if isinstance(exc, Exception):
        exc_type = type(exc).__name__
        exc_message = str(exc)
    # 处理异常类型
    elif isinstance(exc, type) and issubclass(exc, Exception):
        exc_type = exc.__name__
        exc_message = ""
    # 处理异常消息
    else:
        exc_type = ""
        exc_message = str(exc)
    
    # 检查异常类型
    if exc_type in COMMON_ERROR_TYPES:
        return True
    
    # 检查异常消息模式
    for pattern in COMMON_ERROR_PATTERNS:
        if re.search(pattern, exc_message, re.IGNORECASE):
            return True
    
    return False

def log_exception(
    logger: logging.Logger, 
    exc: Exception, 
    message: str = "发生异常",
    level: int = logging.ERROR,
    include_traceback: Optional[bool] = None
) -> None:
    """智能记录异常，根据异常类型决定是否包含堆栈信息
    
    参数:
        logger: 日志记录器
        exc: 异常对象
        message: 日志消息前缀
        level: 日志级别
        include_traceback: 是否包含堆栈信息，如果为None则自动判断
    """
    exc_type = type(exc).__name__
    exc_message = str(exc)
    
    # 自动判断是否需要包含堆栈
    if include_traceback is None:
        include_traceback = not is_common_error(exc)
    
    # 截断可能过长的错误消息
    if len(exc_message) > 500:
        exc_message = exc_message[:500] + "..."
    
    # 移除背景信息链接
    if "(Background on this error at:" in exc_message:
        exc_message = exc_message.split("(Background")[0].strip()
    
    # 根据需要记录异常信息
    if include_traceback:
        logger.log(level, "%s: %s - %s", message, exc_type, exc_message, exc_info=True)
    else:
        logger.log(level, "%s: %s - %s", message, exc_type, exc_message)

def log_error(
    logger: logging.Logger, 
    message: str, 
    error: Optional[Exception] = None,
    include_traceback: Optional[bool] = None
) -> None:
    """记录错误信息，智能处理堆栈
    
    参数:
        logger: 日志记录器
        message: 错误消息
        error: 异常对象（可选）
        include_traceback: 是否包含堆栈信息，如果为None则自动判断
    """
    if error:
        log_exception(logger, error, message, logging.ERROR, include_traceback)
    else:
        logger.error(message)

def log_warning(
    logger: logging.Logger, 
    message: str, 
    error: Optional[Exception] = None,
    include_traceback: Optional[bool] = None
) -> None:
    """记录警告信息，智能处理堆栈
    
    参数:
        logger: 日志记录器
        message: 警告消息
        error: 异常对象（可选）
        include_traceback: 是否包含堆栈信息，如果为None则自动判断
    """
    if error:
        log_exception(logger, error, message, logging.WARNING, include_traceback)
    else:
        logger.warning(message)

def get_logger(name: str) -> logging.Logger:
    """获取日志记录器，并设置一些便捷方法
    
    参数:
        name: 日志记录器名称
        
    返回:
        logging.Logger: 增强的日志记录器
    """
    logger = logging.getLogger(name)
    
    # 添加智能日志记录方法
    def log_err(msg, exc=None, include_traceback=None):
        log_error(logger, msg, exc, include_traceback)
    
    def log_warn(msg, exc=None, include_traceback=None):
        log_warning(logger, msg, exc, include_traceback)
    
    # 添加便捷方法
    logger.log_error = log_err
    logger.log_warning = log_warn
    
    return logger 