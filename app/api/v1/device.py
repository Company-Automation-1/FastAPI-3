from typing import List
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.models.device import DeviceCreate, DeviceUpdate, DeviceInDB
from app.services.device import DeviceService

router = APIRouter()

@router.get("/devices/", response_model=List[DeviceInDB])
def read_devices(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    """获取设备列表"""
    devices = DeviceService.get_devices(db, skip=skip, limit=limit)
    return devices

@router.get("/devices/{device_name}", response_model=DeviceInDB)
def read_device(device_name: str, db: Session = Depends(get_db)):
    """获取单个设备"""
    device = DeviceService.get_device(db, device_name)
    if device is None:
        raise HTTPException(status_code=404, detail="设备不存在")
    return device

@router.post("/devices/", response_model=DeviceInDB)
def create_device(device: DeviceCreate, db: Session = Depends(get_db)):
    """创建设备"""
    db_device = DeviceService.get_device(db, device_name=device.device_name)
    if db_device:
        raise HTTPException(status_code=400, detail="设备名称已存在")
    return DeviceService.create_device(db=db, device=device)

@router.put("/devices/{device_name}", response_model=DeviceInDB)
def update_device(device_name: str, device: DeviceUpdate, db: Session = Depends(get_db)):
    """更新设备"""
    db_device = DeviceService.update_device(db, device_name, device)
    if db_device is None:
        raise HTTPException(status_code=404, detail="设备不存在")
    return db_device

@router.delete("/devices/{device_name}")
def delete_device(device_name: str, db: Session = Depends(get_db)):
    """删除设备"""
    success = DeviceService.delete_device(db, device_name)
    if not success:
        raise HTTPException(status_code=404, detail="设备不存在")
    return {"message": "设备已删除"}