from typing import List
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.models.device import DeviceCreate, DeviceUpdate, DeviceInDB
from app.models.common import ResponseModel
from app.services.device import DeviceService
from app.core.status_code import StatusCode

router = APIRouter()

@router.get("/devices/", response_model=ResponseModel[List[DeviceInDB]])
def read_devices(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    """获取设备列表"""
    devices = DeviceService.get_devices(db, skip=skip, limit=limit)
    return ResponseModel(data=devices)

@router.get("/devices/{device_name}", response_model=ResponseModel[DeviceInDB])
def read_device(device_name: str, db: Session = Depends(get_db)):
    """获取单个设备"""
    device = DeviceService.get_device(db, device_name)
    if device is None:
        return ResponseModel(
            code=StatusCode.DEVICE_NOT_FOUND.value,
            message=StatusCode.get_message(StatusCode.DEVICE_NOT_FOUND.value)
        )
    return ResponseModel(data=device)

@router.post("/devices/", response_model=ResponseModel[DeviceInDB])
def create_device(device: DeviceCreate, db: Session = Depends(get_db)):
    """创建设备"""
    db_device = DeviceService.get_device(db, device_name=device.device_name)
    if db_device:
        return ResponseModel(
            code=StatusCode.DEVICE_ALREADY_EXISTS.value,
            message=StatusCode.get_message(StatusCode.DEVICE_ALREADY_EXISTS.value)
        )
    device_data = DeviceService.create_device(db=db, device=device)
    return ResponseModel(
        code=StatusCode.CREATED.value,
        message=StatusCode.get_message(StatusCode.CREATED.value),
        data=device_data
    )

@router.put("/devices/{device_name}", response_model=ResponseModel[DeviceInDB])
def update_device(device_name: str, device: DeviceUpdate, db: Session = Depends(get_db)):
    """更新设备"""
    db_device = DeviceService.update_device(db, device_name, device)
    if db_device is None:
        return ResponseModel(
            code=StatusCode.DEVICE_NOT_FOUND.value,
            message=StatusCode.get_message(StatusCode.DEVICE_NOT_FOUND.value)
        )
    return ResponseModel(data=db_device)

@router.delete("/devices/{device_name}", response_model=ResponseModel)
def delete_device(device_name: str, db: Session = Depends(get_db)):
    """删除设备"""
    success = DeviceService.delete_device(db, device_name)
    if not success:
        return ResponseModel(
            code=StatusCode.DEVICE_NOT_FOUND.value,
            message=StatusCode.get_message(StatusCode.DEVICE_NOT_FOUND.value)
        )
    return ResponseModel(message="设备已删除")