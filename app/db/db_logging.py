"""
数据库操作日志记录器 - 用于跟踪SQL语句执行
"""
import logging
import time
from sqlalchemy import event
from sqlalchemy.engine import Engine
import uuid
import re

logger = logging.getLogger("db_logger")

# 定义已知错误模式
KNOWN_ERROR_PATTERNS = [
    # MySQL连接错误
    r"Can't connect to MySQL server on '[\w\.:]+'\s+\(\[WinError 10061\]",
    # 表不存在错误
    r"Table '[\w\.]+' doesn't exist",
    # 字段不存在错误
    r"Unknown column '[\w]+' in",
    # 超时错误
    r"Lost connection to MySQL server",
    # 认证错误
    r"Access denied for user"
]

def is_known_error(error_message):
    """检查是否为已知错误类型
    
    参数:
        error_message: 错误信息字符串
    
    返回:
        bool: 是否为已知错误
    """
    if not error_message:
        return False
        
    for pattern in KNOWN_ERROR_PATTERNS:
        if re.search(pattern, error_message):
            return True
            
    return False

def setup_db_logging(is_debug=False):
    """设置数据库操作日志记录
    
    参数:
        is_debug: 是否启用调试模式，如果为True，将记录所有SQL语句
    """
    # 记录数据库引擎启动
    logger.info("数据库日志记录器已启动")
    
    # 为所有数据库引擎添加事件监听器
    @event.listens_for(Engine, "before_cursor_execute")
    def before_cursor_execute(conn, cursor, statement, parameters, context, executemany):
        # 添加开始时间到连接信息中
        conn.info.setdefault('query_start_time', []).append(time.time())
        # 生成查询ID
        query_id = str(uuid.uuid4())[:8]
        conn.info.setdefault('query_id', []).append(query_id)
        
        # 在调试模式下记录完整SQL语句
        if is_debug:
            # 记录SQL语句和参数
            logger.debug(
                "SQL执行 [%s] - 语句: %s - 参数: %s",
                query_id,
                statement,
                parameters
            )

    @event.listens_for(Engine, "after_cursor_execute")
    def after_cursor_execute(conn, cursor, statement, parameters, context, executemany):
        # 计算执行时间
        total = time.time() - conn.info['query_start_time'].pop()
        # 获取查询ID
        query_id = conn.info['query_id'].pop()
        
        # 记录SQL执行统计
        if total > 0.5:  # 仅记录执行时间超过0.5秒的查询
            logger.warning(
                "SQL执行较慢 [%s] - 耗时: %.3fs - 语句: %s",
                query_id,
                total,
                statement[:100] + "..." if len(statement) > 100 else statement
            )
        elif not is_debug:  # 非调试模式下，只记录基本信息
            logger.info(
                "SQL执行 [%s] - 耗时: %.3fs - 语句类型: %s",
                query_id,
                total,
                statement.split()[0] if statement else "未知"
            )
    
    # 记录数据库异常
    @event.listens_for(Engine, "handle_error")
    def handle_error(context):
        error_message = str(context.original_exception)
        
        if is_known_error(error_message):
            # 已知错误类型 - 只记录简要信息，不记录堆栈
            logger.error(
                "SQL错误 - 语句类型: %s - 错误: %s",
                context.statement.split()[0] if context.statement else "未知",
                error_message.split('\n')[0]  # 只取第一行
            )
        else:
            # 未知错误类型 - 记录完整信息和堆栈
            logger.error(
                "SQL错误 - 语句: %s - 参数: %s - 错误: %s",
                context.statement,
                context.parameters,
                error_message,
                exc_info=True
            )

    return logger 