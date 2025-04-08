from typing import Optional, List
from datetime import datetime
from sqlalchemy import Column, String, BigInteger, Integer, UniqueConstraint, Index
from sqlalchemy.orm import relationship
from app.db.base_class import Base
from app.schemas.device import DeviceBase, DeviceCreate, DeviceUpdate, DeviceInDB

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

    # 添加唯一索引
    __table_args__ = (
        UniqueConstraint('id', name='pre_devices_id'),
        UniqueConstraint('device_name', name='pre_devices_name'),
    )

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