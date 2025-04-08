import json
import time
import shutil
from typing import List, Optional
from sqlalchemy.orm import Session
from app.models.upload import Upload
from app.schemas.upload import UploadCreate, FileData
from app.models.task import TaskStatus
from app.schemas.task import TaskCreate
from app.services.task import TaskService
import os
from base64 import b64decode
from app.models.device import Device
from app.utils.time_utils import timestamp_to_datetime

class UploadService:
    @staticmethod
    def create_upload(db: Session, upload_data: UploadCreate, upload_dir: str) -> Upload:
        """创建或更新上传记录"""
        # 检查设备是否存在
        device = db.query(Device).filter(Device.device_name == upload_data.device_name).first()
        if not device:
            raise ValueError(f"设备 {upload_data.device_name} 不存在")

        # 检查是否存在相同device_name和time的记录
        existing_upload = db.query(Upload).filter(
            Upload.device_name == upload_data.device_name,
            Upload.time == upload_data.timestamp
        ).first()

        # 转换时间戳为格式化时间
        formatted_time = timestamp_to_datetime(upload_data.timestamp)
        # 使用格式化时间创建临时文件目录
        temp_dir = os.path.join(upload_dir, "temp", str(int(time.time())))
        os.makedirs(temp_dir, exist_ok=True)

        # 保存文件到临时目录并收集文件路径
        saved_files = []
        try:
            # 开始数据库事务
            db.begin_nested()  # 创建保存点

            for file in upload_data.files:
                # 生成临时文件路径
                temp_file_path = os.path.join(temp_dir, file.filename)
                
                try:
                    # 保存文件到临时目录
                    file_data = b64decode(file.data)
                    with open(temp_file_path, 'wb') as f:
                        f.write(file_data)
                    
                    # 显式调用垃圾回收以确保文件句柄释放
                    import gc
                    gc.collect()
                    
                    # 收集最终的相对路径（不是临时路径）
                    saved_files.append(os.path.join(upload_data.device_name, file.filename))
                except Exception as e:
                    print(f"写入临时文件失败: {str(e)}")
                    raise e

            current_time = int(time.time())
            
            if existing_upload:
                # 备份旧文件路径，以便回滚时使用
                old_files = json.loads(existing_upload.files)
                old_files_backup = old_files.copy()
                
                # 更新现有记录
                existing_upload.files = json.dumps(saved_files)
                existing_upload.title = upload_data.title
                existing_upload.content = upload_data.content
                existing_upload.updatetime = current_time
                db_upload = existing_upload
            else:
                # 创建新记录
                db_upload = Upload(
                    device_name=upload_data.device_name,
                    time=upload_data.timestamp,
                    files=json.dumps(saved_files),
                    title=upload_data.title,
                    content=upload_data.content,
                    createtime=current_time,
                    updatetime=current_time
                )
                db.add(db_upload)
                db.flush()  # 确保获取到新记录的ID

            # 创建或更新任务 - 上传成功，状态为WT
            task_data = TaskCreate(
                device_name=upload_data.device_name,
                upload_id=db_upload.id,  # 添加upload_id
                time=upload_data.timestamp,
                status="WT"
            )
            TaskService.create_or_update_task(db, task_data)

            # 如果一切正常，将文件从临时目录移动到最终目录
            final_dir = os.path.join(upload_dir, upload_data.device_name, formatted_time)
            os.makedirs(final_dir, exist_ok=True)

            # 如果是更新操作，先删除旧文件
            if existing_upload:
                for old_file in old_files:
                    old_file_path = os.path.join(upload_dir, old_file)
                    if os.path.exists(old_file_path):
                        os.remove(old_file_path)

            # 移动新文件到最终位置
            for file in upload_data.files:
                temp_file_path = os.path.join(temp_dir, file.filename)
                final_file_path = os.path.join(final_dir, file.filename)
                
                try:
                    # 复制而不是移动，以减少文件锁定问题
                    shutil.copy2(temp_file_path, final_file_path)
                except Exception as e:
                    print(f"复制文件失败 {temp_file_path} -> {final_file_path}: {str(e)}")
                    raise e

            # 提交事务
            db.commit()

            return db_upload
            
        except Exception as e:
            # 回滚数据库事务
            db.rollback()
            
            # 删除临时文件
            if os.path.exists(temp_dir):
                shutil.rmtree(temp_dir)

            # 如果是更新操作，确保恢复原有记录
            if existing_upload:
                existing_upload.files = json.dumps(old_files_backup)
                db.refresh(existing_upload)
            
            # 创建或更新任务 - 上传失败，状态为UPERR
            if 'db_upload' in locals():  # 检查是否已创建上传记录
                task_data = TaskCreate(
                    device_name=upload_data.device_name,
                    upload_id=db_upload.id,  # 添加upload_id
                    time=upload_data.timestamp,
                    status="UPERR"
                )
                TaskService.create_or_update_task(db, task_data)
            
            raise e
        finally:
            # 清理临时目录
            safe_remove_directory(temp_dir)

    @staticmethod
    def get_uploads_by_device(db: Session, device_name: str, skip: int = 0, limit: int = 100) -> List[Upload]:
        """获取设备的上传记录"""
        return db.query(Upload)\
            .filter(Upload.device_name == device_name)\
            .order_by(Upload.time.desc())\
            .offset(skip)\
            .limit(limit)\
            .all()

def safe_remove_directory(dir_path, max_retries=3, retry_delay=1):
    """安全删除目录，包含重试机制"""
    import time
    
    for attempt in range(max_retries):
        try:
            if os.path.exists(dir_path):
                shutil.rmtree(dir_path)
            return True
        except PermissionError as e:
            if attempt < max_retries - 1:
                # 强制垃圾回收
                import gc
                gc.collect()
                time.sleep(retry_delay)
            else:
                print(f"无法删除目录 {dir_path}，最大重试次数已达: {str(e)}")
                return False