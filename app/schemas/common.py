from typing import TypeVar, Generic, Optional
from pydantic import BaseModel
from app.core.status_code import StatusCode

T = TypeVar('T')

class ResponseModel(BaseModel, Generic[T]):
    """通用响应模型"""
    code: int = StatusCode.SUCCESS.value
    message: str = StatusCode.get_message(StatusCode.SUCCESS.value)
    data: Optional[T] = None
    total: Optional[int] = None
    page: Optional[int] = None
    page_size: Optional[int] = None 