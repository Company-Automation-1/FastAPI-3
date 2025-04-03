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
    try:
        devices = DeviceService.get_devices(db, skip=skip, limit=limit)
        return ResponseModel(data=devices)
    except Exception as e:
        return ResponseModel(
            code=StatusCode.SERVER_ERROR.value,
            message=str(e)
        )

@router.get("/devices/{id}", response_model=ResponseModel[DeviceInDB])
def read_device(id: str, db: Session = Depends(get_db)):
    """获取单个设备"""
    try:
        device = DeviceService.get_device(db, id)
        if device is None:
            return ResponseModel(
                code=StatusCode.DEVICE_NOT_FOUND.value,
                message=StatusCode.get_message(StatusCode.DEVICE_NOT_FOUND.value)
            )
        return ResponseModel(data=device)
    except Exception as e:
        return ResponseModel(
            code=StatusCode.SERVER_ERROR.value,
            message=str(e)
        )

@router.post("/devices/", response_model=ResponseModel[DeviceInDB])
def create_device(device: DeviceCreate, db: Session = Depends(get_db)):
    """创建设备"""
    try:
        db_device = DeviceService.get_device_by_name(db, device_name=device.device_name)
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
    except Exception as e:
        return ResponseModel(
            code=StatusCode.SERVER_ERROR.value,
            message=str(e)
        )

@router.put("/devices/{id}", response_model=ResponseModel[DeviceInDB])
def update_device(id: str, device: DeviceUpdate, db: Session = Depends(get_db)):
    """更新设备"""
    try:
        db_device = DeviceService.update_device(db, id, device)
        if db_device is None:
            return ResponseModel(
                code=StatusCode.DEVICE_NOT_FOUND.value,
                message=StatusCode.get_message(StatusCode.DEVICE_NOT_FOUND.value)
            )
        return ResponseModel(data=db_device)
    except Exception as e:
        return ResponseModel(
            code=StatusCode.SERVER_ERROR.value,
            message=str(e)
        )

@router.delete("/devices/{id}", response_model=ResponseModel)
def delete_device(id: str, db: Session = Depends(get_db)):
    """删除设备"""
    try:
        success = DeviceService.delete_device(db, id)
        if not success:
            return ResponseModel(
                code=StatusCode.DEVICE_NOT_FOUND.value,
                message=StatusCode.get_message(StatusCode.DEVICE_NOT_FOUND.value)
            )
        return ResponseModel(message="设备已删除")
    except Exception as e:
        return ResponseModel(
            code=StatusCode.SERVER_ERROR.value,
            message=str(e)
        )