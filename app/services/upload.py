import json
import time
from typing import List, Optional
from sqlalchemy.orm import Session
from app.models.upload import Upload, UploadCreate, FileData
import os
from base64 import b64decode
from app.models.device import Device
from app.utils.time_utils import timestamp_to_datetime

class UploadService:
    @staticmethod
    def create_upload(db: Session, upload_data: UploadCreate, upload_dir: str) -> Upload:
        """创建上传记录"""
        # 检查设备是否存在
        device = db.query(Device).filter(Device.device_name == upload_data.device_name).first()
        if not device:
            raise ValueError(f"设备 {upload_data.device_name} 不存在")

        print(upload_data.timestamp)

        # 转换时间戳为格式化时间
        formatted_time = timestamp_to_datetime(upload_data.timestamp)
        print(formatted_time)
        print("""=============================================""")
        # 使用格式化时间创建文件目录
        device_dir = os.path.join(upload_dir, upload_data.device_name, formatted_time)
        os.makedirs(device_dir, exist_ok=True)

        # 保存文件并收集文件路径
        saved_files = []
        for file in upload_data.files:
            # 生成文件路径
            file_path = os.path.join(device_dir, file.filename)
            
            # 保存文件
            file_data = b64decode(file.data)
            with open(file_path, 'wb') as f:
                f.write(file_data)
            
            # 收集相对路径
            saved_files.append(os.path.join(upload_data.device_name, file.filename))

        # 创建数据库记录
        current_time = int(time.time())
        db_upload = Upload(
            device_name=upload_data.device_name,
            time=upload_data.timestamp,  # 保存原始时间戳
            files=json.dumps(saved_files),
            title=upload_data.title,
            content=upload_data.content,
            createtime=current_time,
            updatetime=current_time
        )

        db.add(db_upload)
        db.commit()
        db.refresh(db_upload)
        return db_upload

    @staticmethod
    def get_uploads_by_device(db: Session, device_name: str, skip: int = 0, limit: int = 100) -> List[Upload]:
        """获取设备的上传记录"""
        return db.query(Upload)\
            .filter(Upload.device_name == device_name)\
            .order_by(Upload.time.desc())\
            .offset(skip)\
            .limit(limit)\
            .all()