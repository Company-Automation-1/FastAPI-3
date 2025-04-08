from typing import Optional
from pydantic import BaseModel, Field

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