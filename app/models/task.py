from typing import Optional
from datetime import datetime
import enum
from sqlalchemy import Column, Integer, String, BigInteger, ForeignKey, Enum, UniqueConstraint, Index
from sqlalchemy.orm import relationship
from app.db.base_class import Base

# 定义任务状态枚举
class TaskStatus(str, enum.Enum):
    UPERR = "uperr"      # 上传失败
    WT = "wt"           # 待传输
    WTERR = "wterr"     # 传输失败
    PENDING = "pending"  # 待执行
    RES = "res"         # 执行成功
    REJ = "rej"         # 执行失败

# SQLAlchemy模型
class Task(Base):
    """任务数据库模型"""
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

    # 添加唯一索引和普通索引
    __table_args__ = (
        UniqueConstraint('id', name='pre_tasks_id'),
        Index('pre_tasks_device', 'device_name'),
        Index('pre_upload_id', 'upload_id'),
    )

    # 关联关系
    device = relationship("Device", back_populates="tasks")
    upload = relationship("Upload", back_populates="tasks")

    def __repr__(self):
        return f"<Task(id={self.id}, device_name={self.device_name}, status={self.status})>"

    def to_dict(self):
        """转换为字典"""
        return {
            "id": self.id,
            "upload_id": self.upload_id,
            "device_name": self.device_name,
            "time": self.time,
            "status": self.status,
            "createtime": self.createtime,
            "updatetime": self.updatetime
        }