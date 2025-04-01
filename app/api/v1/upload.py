from typing import List
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.models.upload import UploadCreate, UploadInDB
from app.services.upload import UploadService
from app.core.config import settings

router = APIRouter()

@router.post("/upload/", response_model=UploadInDB)
def create_upload(upload: UploadCreate, db: Session = Depends(get_db)):
    """创建上传记录"""
    try:
        return UploadService.create_upload(
            db=db, 
            upload_data=upload,
            upload_dir=settings.UPLOAD_DIR
        )
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/uploads/{device_name}", response_model=List[UploadInDB])
def read_device_uploads(
    device_name: str,
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db)
):
    """获取设备的上传记录"""
    uploads = UploadService.get_uploads_by_device(
        db=db,
        device_name=device_name,
        skip=skip,
        limit=limit
    )
    return uploads
