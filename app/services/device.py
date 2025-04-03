from typing import List, Optional
from sqlalchemy.orm import Session
from app.models.device import Device, DeviceCreate, DeviceUpdate
import time

class DeviceService:
    @staticmethod
    def get_device_by_name(db: Session, device_name: str) -> Optional[Device]:
        """通过name获取单个设备"""
        return db.query(Device).filter(Device.device_name == device_name).first()

    @staticmethod
    def get_device(db: Session, id: int) -> Optional[Device]:
        """获取单个设备"""
        return db.query(Device).filter(Device.id == id).first()

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
        try:
            db.commit()
            db.refresh(db_device)
            return db_device
        except Exception as e:
            db.rollback()
            raise e

    @staticmethod
    def update_device(db: Session, id: str, device: DeviceUpdate) -> Optional[Device]:
        """更新设备"""
        db_device = DeviceService.get_device(db, id)

        if not db_device:
            return None
        
        update_data = device.model_dump(exclude_unset=True)
        if update_data:
            update_data["updatetime"] = int(time.time())
            for key, value in update_data.items():
                setattr(db_device, key, value)
            
            try:
                db.commit()
                db.refresh(db_device)
            except Exception as e:
                db.rollback()
                raise e
        return db_device

    @staticmethod
    def delete_device(db: Session, id: str) -> bool:
        """删除设备"""
        db_device = DeviceService.get_device(db, id)
        if not db_device:
            return False
        
        try:
            db.delete(db_device)
            db.commit()
            return True
        except Exception as e:
            db.rollback()
            raise e