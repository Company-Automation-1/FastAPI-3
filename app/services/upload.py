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
from app.utils.time_utils import get_current_timestamp, get_current_datetime

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

        # 确保上传目录存在
        if not os.path.exists(upload_dir):
            os.makedirs(upload_dir, mode=0o755, exist_ok=True)
            
        # 确保临时目录存在
        temp_base_dir = os.path.join(upload_dir, "temp")
        if not os.path.exists(temp_base_dir):
            os.makedirs(temp_base_dir, mode=0o755, exist_ok=True)
            
        # 使用格式化时间创建临时文件目录，添加随机数避免并发冲突
        import random
        current_time = get_current_timestamp()
        temp_dir = os.path.join(temp_base_dir, f"{current_time}_{random.randint(1000, 9999)}")
        os.makedirs(temp_dir, mode=0o755, exist_ok=True)
        print(f"创建临时目录: {temp_dir}")

        # 保存文件到临时目录并收集文件路径
        saved_files = []
        temp_files = []  # 记录所有创建的临时文件
        try:
            # 开始数据库事务
            db.begin_nested()  # 创建保存点

            # 先保存所有文件到临时目录
            for file in upload_data.files:
                # 生成临时文件路径
                temp_file_path = os.path.join(temp_dir, file.filename)
                temp_files.append(temp_file_path)  # 记录临时文件路径
                
                try:
                    # 保存文件到临时目录
                    file_data = b64decode(file.data)
                    with open(temp_file_path, 'wb') as f:
                        f.write(file_data)
                    
                    # 设置文件权限
                    os.chmod(temp_file_path, 0o644)
                    
                    # 显式调用垃圾回收以确保文件句柄释放
                    import gc
                    gc.collect()
                    
                    # 收集最终的相对路径（不是临时路径）
                    saved_files.append(os.path.join(upload_data.device_name, file.filename))
                    print(f"文件已保存到临时目录: {temp_file_path}")
                    
                    # 添加短暂延迟，避免文件系统压力
                    time.sleep(0.1)
                except Exception as e:
                    print(f"写入临时文件失败: {str(e)}")
                    # 清理已创建的临时文件
                    for temp_file in temp_files:
                        try:
                            if os.path.exists(temp_file):
                                os.remove(temp_file)
                        except Exception as cleanup_error:
                            print(f"清理临时文件失败: {str(cleanup_error)}")
                    raise e

            # 添加延迟，确保所有文件都已写入磁盘
            time.sleep(0.8)

            current_time = get_current_timestamp()
            
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
            final_dir = os.path.join(upload_dir, upload_data.device_name, get_current_datetime(upload_data.timestamp))
            os.makedirs(final_dir, mode=0o755, exist_ok=True)
            print(f"创建最终目录: {final_dir}")

            # 如果是更新操作，先删除旧文件
            if existing_upload:
                for old_file in old_files:
                    old_file_path = os.path.join(upload_dir, old_file)
                    if os.path.exists(old_file_path):
                        try:
                            os.remove(old_file_path)
                            print(f"删除旧文件: {old_file_path}")
                        except Exception as e:
                            print(f"删除旧文件失败: {str(e)}")

            # 移动新文件到最终位置
            for file in upload_data.files:
                temp_file_path = os.path.join(temp_dir, file.filename)
                final_file_path = os.path.join(final_dir, file.filename)
                
                # 检查临时文件是否存在
                if not os.path.exists(temp_file_path):
                    print(f"临时文件不存在: {temp_file_path}")
                    # 尝试重新创建临时文件
                    try:
                        file_data = next((f.data for f in upload_data.files if f.filename == file.filename), None)
                        if file_data:
                            file_data = b64decode(file_data)
                            with open(temp_file_path, 'wb') as f:
                                f.write(file_data)
                            os.chmod(temp_file_path, 0o644)
                            print(f"重新创建临时文件: {temp_file_path}")
                        else:
                            raise ValueError(f"找不到文件数据: {file.filename}")
                    except Exception as e:
                        print(f"重新创建临时文件失败: {str(e)}")
                        raise e
                
                try:
                    # 复制而不是移动，以减少文件锁定问题
                    shutil.copy2(temp_file_path, final_file_path)
                    # 设置目标文件权限
                    os.chmod(final_file_path, 0o644)
                    print(f"文件已复制到最终位置: {final_file_path}")
                    
                    # 添加短暂延迟，避免文件系统压力
                    time.sleep(0.2)
                except Exception as e:
                    print(f"复制文件失败 {temp_file_path} -> {final_file_path}: {str(e)}")
                    raise e

            # 提交事务
            db.commit()
            print("数据库事务已提交")

            return db_upload
            
        except Exception as e:
            # 回滚数据库事务
            db.rollback()
            print(f"数据库事务已回滚: {str(e)}")
            
            # 删除临时文件
            for temp_file in temp_files:
                try:
                    if os.path.exists(temp_file):
                        os.remove(temp_file)
                        print(f"删除临时文件: {temp_file}")
                except Exception as cleanup_error:
                    print(f"删除临时文件失败: {str(cleanup_error)}")

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
            # 添加延迟，确保所有文件操作完成
            time.sleep(0.8)
            
            # 清理临时目录 - 使用安全删除函数
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
                # 先尝试删除目录中的所有文件
                for root, dirs, files in os.walk(dir_path, topdown=False):
                    for name in files:
                        file_path = os.path.join(root, name)
                        try:
                            os.remove(file_path)
                            print(f"删除文件: {file_path}")
                        except Exception as e:
                            print(f"删除文件失败: {str(e)}")
                    for name in dirs:
                        dir_path = os.path.join(root, name)
                        try:
                            os.rmdir(dir_path)
                            print(f"删除目录: {dir_path}")
                        except Exception as e:
                            print(f"删除目录失败: {str(e)}")
                
                # 最后删除根目录
                os.rmdir(dir_path)
                print(f"删除根目录: {dir_path}")
            return True
        except PermissionError as e:
            if attempt < max_retries - 1:
                # 强制垃圾回收
                import gc
                gc.collect()
                time.sleep(retry_delay)
                print(f"删除目录失败，重试 {attempt+1}/{max_retries}: {str(e)}")
            else:
                print(f"无法删除目录 {dir_path}，最大重试次数已达: {str(e)}")
                return False
        except Exception as e:
            print(f"删除目录时出错: {str(e)}")
            return False