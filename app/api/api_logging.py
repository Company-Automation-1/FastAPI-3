"""
API日志中间件 - 用于记录所有API请求和响应
"""
import time
import json
import logging
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response
from fastapi import FastAPI
import uuid
import asyncio
import re
import traceback
import sys

logger = logging.getLogger("api_logger")

# 定义已知API错误模式
KNOWN_API_ERROR_PATTERNS = [
    # 认证错误
    r"Could not validate credentials",
    r"Not authenticated",
    # 参数验证错误
    r"validation error",
    r"field required",
    # 资源不存在错误
    r"not found",
    # 权限错误
    r"Permission denied",
    # 文件上传错误
    r"File too large",
    # 请求错误
    r"Bad request"
]

def is_known_api_error(error):
    """检查是否为已知API错误
    
    参数:
        error: 异常对象
    
    返回:
        bool: 是否为已知错误
    """
    # 已知异常类型
    known_error_types = [
        "RequestValidationError",
        "HTTPException",
        "ValidationError",
        "PermissionError",
        "FileNotFoundError",
        "TimeoutError",
        "JSONDecodeError"
    ]
    
    # 检查错误类型
    if hasattr(error, "__class__") and hasattr(error.__class__, "__name__"):
        if error.__class__.__name__ in known_error_types:
            return True
    
    # 检查错误信息
    error_message = str(error)
    for pattern in KNOWN_API_ERROR_PATTERNS:
        if re.search(pattern, error_message, re.IGNORECASE):
            return True
            
    return False

class APILoggingMiddleware(BaseHTTPMiddleware):
    """API日志中间件，记录所有请求和响应"""
    
    async def dispatch(self, request: Request, call_next):
        """处理请求并记录日志"""
        # 生成唯一请求ID
        request_id = str(uuid.uuid4())
        
        # 记录请求开始时间
        start_time = time.time()
        
        # 记录请求信息
        client_host = request.client.host if request.client else "unknown"
        try:
            # 尝试获取请求体 - 注意这只能在特定情况下工作
            # 因为请求体是一个异步流，只能被读取一次
            # 对于小的请求体，我们可以尝试复制它以供记录
            body = await request.body()
            request_body = body.decode('utf-8')
            # 重新设置请求体，以便后续中间件和路由处理函数可以访问
            request._body = body
        except Exception:
            request_body = "(无法读取请求体或请求体为空)"
        
        # 记录请求信息
        logger.info(
            "API请求 [%s] - %s %s - 来自: %s - 参数: %s - Body: %s",
            request_id,
            request.method,
            request.url.path,
            client_host,
            dict(request.query_params),
            request_body[:1000] if len(request_body) > 1000 else request_body  # 截断过长的请求体
        )
        
        # 处理请求
        try:
            response = await call_next(request)
            
            # 计算请求处理时间
            process_time = time.time() - start_time
            
            # 记录响应信息
            logger.info(
                "API响应 [%s] - %s %s - 状态码: %d - 处理时间: %.3fs",
                request_id,
                request.method,
                request.url.path,
                response.status_code,
                process_time
            )
            
            # 添加响应头，包括请求ID和处理时间
            response.headers["X-Request-ID"] = request_id
            response.headers["X-Process-Time"] = str(process_time)
            
            return response
            
        except Exception as e:
            # 计算请求处理时间
            process_time = time.time() - start_time
            
            # 判断是否为已知错误
            known_error = is_known_api_error(e)
            
            # 记录异常信息
            if known_error:
                # 已知错误 - 只记录简要信息
                logger.error(
                    "API错误 [%s] - %s %s - 错误类型: %s - 错误: %s - 处理时间: %.3fs",
                    request_id,
                    request.method,
                    request.url.path,
                    e.__class__.__name__,
                    str(e),
                    process_time
                )
            else:
                # 未知错误 - 记录完整堆栈
                logger.error(
                    "API错误 [%s] - %s %s - 错误: %s - 处理时间: %.3fs",
                    request_id,
                    request.method,
                    request.url.path,
                    str(e),
                    process_time,
                    exc_info=True
                )
            
            # 重新抛出异常，让FastAPI的异常处理器处理
            raise

def setup_api_logging(app: FastAPI):
    """配置API日志中间件
    
    参数:
        app: FastAPI应用实例
    """
    # 添加API日志中间件
    app.add_middleware(APILoggingMiddleware)
    
    logger.info("API日志中间件已配置")
    
    return app 