from typing import List, Optional
from pydantic import BaseModel, Field
from sqlalchemy import Column, Integer, String, Text, BigInteger, ForeignKey
from sqlalchemy.orm import relationship
from app.db.base_class import Base
from app.models.device import Device  # 导入Device模型

# SQLAlchemy模型
class Upload(Base):
    """上传记录数据库模型"""
    __tablename__ = "pre_uploads"

    id = Column(Integer, primary_key=True, autoincrement=True, comment="上传记录ID")
    device_name = Column(String(50), ForeignKey('pre_devices.device_name', ondelete='CASCADE', onupdate='CASCADE'), 
                        nullable=False, index=True, comment="设备名称")
    time = Column(BigInteger, nullable=False, comment="任务时间")
    files = Column(Text, nullable=False, comment="文件路径 (json)")
    title = Column(String(200), comment="标题")
    content = Column(Text, comment="正文")
    createtime = Column(BigInteger, comment="创建时间")
    updatetime = Column(BigInteger, comment="更新时间")

    # 定义与Device的关系
    device = relationship("Device", back_populates="uploads")

# Pydantic模型
class FileData(BaseModel):
    """文件数据模型"""
    filename: str = Field(..., description="文件名")
    data: str = Field(..., description="文件数据")

class UploadCreate(BaseModel):
    """创建上传记录模型"""
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