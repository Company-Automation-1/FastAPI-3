from typing import List, Optional
from pydantic import BaseModel, Field

class FileData(BaseModel):
    """文件数据模型"""
    filename: str = Field(..., description="文件名")
    data: str = Field(..., description="文件数据")

class UploadCreate(BaseModel):
    """创建上传记录的请求模型"""
    device_name: str = Field(..., description="设备名称")
    timestamp: int = Field(..., description="时间戳")
    title: Optional[str]  = Field(None, description="标题")
    content: Optional[str]  = Field(None, description="正文")
    files: List[FileData] = Field(..., description="文件列表")

class UploadInDB(BaseModel):
    """数据库中的上传记录模型"""
    id: int = Field(..., description="上传记录ID")
    device_name: str = Field(..., description="设备名称")
    time: int = Field(..., description="任务时间")
    files: str = Field(..., description="文件路径 (json)")
    title: Optional[str] = Field(None, description="标题")
    content: Optional[str] = Field(None, description="正文")
    createtime: Optional[int] = Field(None, description="创建时间")
    updatetime: Optional[int] = Field(None, description="更新时间")

    class Config:
        from_attributes = True 