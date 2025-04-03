from sqlalchemy import Column, Integer, String, BigInteger,ForeignKey
from sqlalchemy.orm import relationship
from app.db.base_class import Base
import enum
from pydantic import BaseModel, Field
from typing import Optional

# 定义任务状态枚举
class TaskStatus(str, enum.Enum):
    UPERR = "UPERR"      # 上传失败
    WT = "WT"           # 待传输
    WTERR = "WTERR"     # 传输失败
    PENDING = "PENDING"  # 待执行
    RES = "RES"         # 执行成功
    REJ = "REJ"         # 执行失败

# SQLAlchemy模型
class Task(Base):
    __tablename__ = "pre_tasks"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True, comment="任务ID")
    upload_id = Column(Integer, ForeignKey("pre_uploads.id", ondelete="CASCADE", onupdate="CASCADE"), 
                    nullable=False, index=True, comment="上传记录外键")
    device_name = Column(String(50), ForeignKey("pre_devices.device_name", ondelete="CASCADE", onupdate="CASCADE"), 
                        nullable=False, index=True, comment="设备名称")
    time = Column(BigInteger, nullable=False, comment="计划执行时间戳")
    status = Column(String(10), nullable=True, comment="任务状态")
    createtime = Column(BigInteger, nullable=True, comment="创建时间")
    updatetime = Column(BigInteger, nullable=True, comment="更新时间")

    # 关联关系
    device = relationship("Device", back_populates="tasks")
    upload = relationship("Upload", back_populates="tasks")

    class Config:
        # 添加索引配置
        indexes = [
            ("device_name", "time")  # 复合索引
        ]

# Pydantic模型
class TaskBase(BaseModel):
    """任务基础模型"""
    upload_id: int = Field(..., description="上传记录ID")
    device_name: str = Field(..., description="设备名称")
    time: int = Field(..., description="计划执行时间戳")
    status: Optional[str] = Field(None, description="任务状态")

class TaskCreate(TaskBase):
    """创建任务的请求模型"""
    pass

class TaskInDB(TaskBase):
    """数据库中的任务模型"""
    id: int = Field(..., description="任务ID")
    createtime: Optional[int] = Field(None, description="创建时间")
    updatetime: Optional[int] = Field(None, description="更新时间")

    class Config:
        from_attributes = True