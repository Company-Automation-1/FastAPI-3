from pydantic import BaseModel, Field
from typing import Optional, List
from app.models.task import TaskStatus
from app.models.upload import FileData

class TaskBase(BaseModel):
    """任务基础模型"""
    upload_id: int = Field(..., description="上传记录ID")
    device_name: str = Field(..., description="设备名称")
    time: int = Field(..., description="计划执行时间戳")
    status: Optional[str] = Field(None, description="任务状态")

class TaskCreate(TaskBase):
    """创建任务的请求模型"""
    pass

class TaskUpdate(BaseModel):
    """更新任务的请求模型"""
    # 任务相关字段
    device_name: Optional[str] = Field(None, description="设备名称")
    time: Optional[int] = Field(None, description="计划执行时间戳")
    
    # upload表相关字段
    title: Optional[str] = Field(None, description="标题")
    content: Optional[str] = Field(None, description="正文")
    files: Optional[List[FileData]] = Field(None, description="文件列表")

class TaskInDB(TaskBase):
    """数据库中的任务模型"""
    id: int = Field(..., description="任务ID")
    createtime: Optional[int] = Field(None, description="创建时间")
    updatetime: Optional[int] = Field(None, description="更新时间")
    title: Optional[str] = Field(None, description="标题")
    content: Optional[str] = Field(None, description="正文")

    class Config:
        from_attributes = True 