from typing import List, Optional
from sqlalchemy.orm import Session
from app.models.device import Device, DeviceCreate, DeviceUpdate
import time

class DeviceService:
    @staticmethod
    def get_device(db: Session, device_name: str) -> Optional[Device]:
        """获取单个设备"""
        return db.query(Device).filter(Device.device_name == device_name).first()

    @staticmethod
    def get_devices(db: Session, skip: int = 0, limit: int = 100) -> List[Device]:
        """获取设备列表"""
        return db.query(Device).offset(skip).limit(limit).all()

    @staticmethod
    def create_device(db: Session, device: DeviceCreate) -> Device:
        """创建设备"""
        current_time = int(time.time())
        db_device = Device(
            **device.model_dump(),
            createtime=current_time,
            updatetime=current_time
        )
        db.add(db_device)
        db.commit()
        db.refresh(db_device)
        return db_device

    @staticmethod
    def update_device(db: Session, device_name: str, device: DeviceUpdate) -> Optional[Device]:
        """更新设备"""
        db_device = DeviceService.get_device(db, device_name)
        if not db_device:
            return None
        
        update_data = device.model_dump(exclude_unset=True)
        if update_data:
            update_data["updatetime"] = int(time.time())
            for key, value in update_data.items():
                setattr(db_device, key, value)
            
            db.commit()
            db.refresh(db_device)
        return db_device

    @staticmethod
    def delete_device(db: Session, device_name: str) -> bool:
        """删除设备"""
        db_device = DeviceService.get_device(db, device_name)
        if not db_device:
            return False
        
        db.delete(db_device)
        db.commit()
        return True