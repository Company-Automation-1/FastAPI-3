from typing import Optional, List
from datetime import datetime
from sqlalchemy import Column, String, BigInteger, Integer
from pydantic import BaseModel, Field
from sqlalchemy.orm import relationship
from app.db.base_class import Base

# SQLAlchemy模型
class Device(Base):
    """设备数据库模型"""
    __tablename__ = "pre_devices"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True, comment="ID")
    device_name = Column(String(50), primary_key=True, unique=True, nullable=False, index=True, comment="设备名称，唯一标识符")
    device_id = Column(String(255), nullable=False, comment="设备物理ID，如adb设备ID")
    device_path = Column(String(255), nullable=False, comment="设备存储根路径")
    password = Column(String(255), nullable=False, comment="设备密码")
    createtime = Column(BigInteger, nullable=True, comment="创建时间")
    updatetime = Column(BigInteger, nullable=True, comment="更新时间")

    # 添加与Upload和Task的关系
    uploads = relationship("Upload", back_populates="device", cascade="all, delete-orphan")
    tasks = relationship("Task", back_populates="device", cascade="all, delete-orphan")

    def to_dict(self):
        """转换为字典"""
        return {
            "device_name": self.device_name,
            "device_id": self.device_id,
            "device_path": self.device_path,
            "password": self.password,
            "createtime": self.createtime,
            "updatetime": self.updatetime
        }

# Pydantic模型
class DeviceBase(BaseModel):
    """设备基础模型"""
    device_name: str = Field(..., description="设备名称，唯一标识符")
    device_id: str = Field(..., description="设备物理ID，如adb设备ID")
    device_path: str = Field(..., description="设备存储根路径")
    password: str = Field(..., description="设备密码")

class DeviceCreate(DeviceBase):
    """创建设备的请求模型"""
    pass

class DeviceUpdate(BaseModel):
    """更新设备模型"""
    device_name: Optional[str] = Field(None, description="设备名称，唯一标识符")
    device_id: Optional[str] = Field(None, description="设备物理ID，如adb设备ID")
    device_path: Optional[str] = Field(None, description="设备存储根路径")
    password: Optional[str] = Field(None, description="设备密码")

class DeviceInDB(DeviceBase):
    """数据库中的设备模型"""
    id: int = Field(..., description="设备ID")
    createtime: Optional[int] = Field(None, description="创建时间")
    updatetime: Optional[int] = Field(None, description="更新时间")

    class Config:
        from_attributes = True  # 允许从ORM模型创建