from typing import List, Optional
from sqlalchemy import Column, Integer, String, Text, BigInteger, ForeignKey, UniqueConstraint, Index
from sqlalchemy.orm import relationship
from app.db.base_class import Base
from app.models.device import Device  # 导入Device模型
from app.schemas.upload import FileData, UploadCreate, UploadInDB  # 导入Pydantic模型

# SQLAlchemy模型
class Upload(Base):
    """上传记录数据库模型"""
    __tablename__ = "pre_uploads"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True, comment="上传记录ID")
    device_name = Column(String(50), ForeignKey("pre_devices.device_name", ondelete="CASCADE", onupdate="CASCADE"), 
                        nullable=False, index=True, comment="设备名称")
    time = Column(BigInteger, nullable=False, comment="任务时间")
    files = Column(Text, nullable=False, comment="文件路径 (json)")
    title = Column(String(200), nullable=True, comment="标题")
    content = Column(Text, nullable=True, comment="正文")
    createtime = Column(BigInteger, nullable=True, comment="创建时间")
    updatetime = Column(BigInteger, nullable=True, comment="更新时间")

    # 添加唯一索引和普通索引
    __table_args__ = (
        UniqueConstraint('id', name='pre_upload_id'),
        Index('pre_upload_device', 'device_name'),
    )

    # 定义与Device的关系
    device = relationship("Device", back_populates="uploads")
    # 添加与Task的关系
    tasks = relationship("Task", back_populates="upload", cascade="all, delete-orphan")

    def to_dict(self):
        """转换为字典"""
        return {
            "id": self.id,
            "device_name": self.device_name,
            "time": self.time,
            "files": self.files,
            "title": self.title,
            "content": self.content,
            "createtime": self.createtime,
            "updatetime": self.updatetime
        }