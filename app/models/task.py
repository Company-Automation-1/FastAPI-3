from sqlalchemy import Column, Integer, String, BigInteger, ForeignKey, Enum
from sqlalchemy.orm import relationship
from app.db.base_class import Base
import enum
from pydantic import BaseModel
from typing import Optional

# 1. 枚举定义
class TaskStatus(str, enum.Enum):
    UPERR = "UPERR"      # 上传失败
    WT = "WT"           # 待传输
    WTERR = "WTERR"     # 传输失败
    PENDING = "PENDING"  # 待执行
    RES = "RES"         # 执行成功
    REJ = "REJ"         # 执行失败

# 2. SQLAlchemy模型
class Task(Base):
    __tablename__ = "pre_tasks"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True, comment="任务ID")
    device_name = Column(String(50), ForeignKey("pre_devices.device_name", ondelete="CASCADE", onupdate="CASCADE"), 
                        nullable=False, comment="设备名称")
    time = Column(BigInteger, nullable=False, comment="计划执行时间戳")
    status = Column(String(10), nullable=True, comment="任务状态")  # 改为String类型
    createtime = Column(BigInteger, nullable=True, comment="创建时间")
    updatetime = Column(BigInteger, nullable=True, comment="更新时间")

    # 关联关系
    device = relationship("Device", back_populates="tasks")

    class Config:
        # 添加索引配置
        indexes = [
            ("device_name", "time")  # 复合索引
        ]

# 3. Pydantic模型
class TaskBase(BaseModel):
    device_name: str
    time: int
    status: Optional[str] = None  # 使用字符串类型

    class Config:
        use_enum_values = True

class TaskCreate(TaskBase):
    pass

class TaskInDB(TaskBase):
    id: int
    createtime: Optional[int] = None
    updatetime: Optional[int] = None

    class Config:
        from_attributes = True