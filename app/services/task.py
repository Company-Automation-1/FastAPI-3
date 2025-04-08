from typing import List, Optional
from sqlalchemy.orm import Session
from app.models.task import Task, TaskStatus
from app.models.upload import Upload
from app.schemas.task import TaskCreate, TaskUpdate, TaskQuery, TaskResponse
from app.core.config import settings
from app.utils.file import get_file_paths
from app.core.status_code import StatusCode
from app.utils.time_utils import timestamp_to_datetime
import time
import json
import os
from base64 import b64decode
import shutil
import logging
from app.models.device import Device

logger = logging.getLogger(__name__)

class TaskService:
    @staticmethod
    def get_tasks(db: Session, query_params: TaskQuery):
        """获取任务列表，支持条件查询和分页"""
        try:
            # 构建基础查询
            query = db.query(Task)
            
            # 添加过滤条件
            if query_params.device_name:
                query = query.filter(Task.device_name == query_params.device_name)
            if query_params.status:
                # 将状态转换为大写进行比较
                query = query.filter(Task.status == query_params.status.upper())
            if query_params.start_time:
                query = query.filter(Task.time >= query_params.start_time)
            if query_params.end_time:
                query = query.filter(Task.time <= query_params.end_time)
            if query_params.title:
                # 使用join和like进行标题模糊查询
                query = query.join(Upload).filter(Upload.title.like(f"%{query_params.title}%"))
            
            # 计算总数
            total = query.count()
            
            # 添加排序和分页
            query = query.order_by(Task.id.desc())
            skip = (query_params.page - 1) * query_params.page_size
            tasks = query.offset(skip).limit(query_params.page_size).all()
            
            # 转换为TaskResponse对象
            task_responses = []
            for task in tasks:
                task_dict = task.to_dict()
                if task.upload:
                    task_dict["title"] = task.upload.title
                    task_dict["content"] = task.upload.content
                task_responses.append(TaskResponse(**task_dict))
            
            return {
                "data": task_responses,
                "total": total,
                "page": query_params.page,
                "page_size": query_params.page_size
            }
        except Exception as e:
            logger.error(f"获取任务列表失败: {str(e)}")
            raise e

    @staticmethod
    def get_task(db: Session, task_id: int):
        """获取单个任务详情"""
        try:
            task = db.query(Task).filter(Task.id == task_id).first()
            if not task:
                raise ValueError(StatusCode.get_message(StatusCode.TASK_NOT_FOUND.value))
            # 使用关联关系获取标题和内容
            if task.upload:
                task.title = task.upload.title
                task.content = task.upload.content
            return task
        except Exception as e:
            logger.error(f"获取任务详情失败: {str(e)}")
            raise e

    @staticmethod
    def update_task(db: Session, task_id: int, task_update: TaskUpdate):
        """更新任务信息，同时更新关联的upload记录"""
        # 开始事务
        db.begin_nested()
        
        try:
            task = db.query(Task).filter(Task.id == task_id).first()
            if not task:
                raise ValueError(StatusCode.TASK_NOT_FOUND)
            
            # 获取关联的upload记录
            upload = db.query(Upload).filter(Upload.id == task.upload_id).first()
            if not upload:
                raise ValueError(StatusCode.UPLOAD_NOT_FOUND)
            
            # 如果更新设备名称，先检查设备是否存在
            if task_update.device_name is not None:
                device = db.query(Device).filter(Device.device_name == task_update.device_name).first()
                if not device:
                    raise ValueError(StatusCode.DEVICE_NOT_FOUND)
            
            # 保存旧数据，用于回滚
            old_task_data = {
                "device_name": task.device_name,
                "time": task.time,
                "status": task.status
            }
            old_upload_data = {
                "title": upload.title,
                "content": upload.content,
                "files": upload.files
            }
            
            # 使用get_file_paths方法获取旧文件的完整路径
            old_file_paths = []
            if upload.files:
                try:
                    old_file_paths = get_file_paths(upload.files, task.device_name, task.time)
                    logger.info(f"解析到的旧文件路径: {old_file_paths}")
                except Exception as e:
                    logger.error(f"解析旧文件路径失败: {str(e)}")
            
            current_time = int(time.time())
            
            # 更新任务信息
            if task_update.device_name is not None:
                # 同时更新 task 和 upload 的设备名称
                task.device_name = task_update.device_name
                upload.device_name = task_update.device_name
            if task_update.time is not None:
                task.time = task_update.time
            
            # 更新upload记录
            if task_update.title is not None:
                upload.title = task_update.title
            if task_update.content is not None:
                upload.content = task_update.content
            
            # 处理文件更新
            new_files = []
            temp_dir = None
            if task_update.files is not None and len(task_update.files) > 0:
                # 如果有新文件，将状态设置为 WT
                task.status = TaskStatus.WT
                
                # 转换时间戳为格式化时间
                formatted_time = timestamp_to_datetime(task.time)
                
                # 使用格式化时间创建临时文件目录
                temp_dir = os.path.join(settings.UPLOAD_DIR, "temp", str(int(time.time())))
                os.makedirs(temp_dir, exist_ok=True)
                
                # 保存文件到临时目录并收集文件路径
                try:
                    for file in task_update.files:
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
                            new_files.append(os.path.join(task.device_name, file.filename))
                        except Exception as e:
                            logger.error(f"写入临时文件失败: {str(e)}")
                            raise e
                    
                    # 更新upload记录的文件路径
                    upload.files = json.dumps(new_files)
                    
                    # 如果一切正常，将文件从临时目录移动到最终目录
                    final_dir = os.path.join(settings.UPLOAD_DIR, task.device_name, formatted_time)
                    os.makedirs(final_dir, exist_ok=True)
                    
                    # 移动文件到最终目录
                    for file in task_update.files:
                        src_path = os.path.join(temp_dir, file.filename)
                        dst_path = os.path.join(final_dir, file.filename)
                        if os.path.exists(src_path):
                            shutil.move(src_path, dst_path)
                    
                    # 清理临时目录
                    if os.path.exists(temp_dir):
                        shutil.rmtree(temp_dir)
                        
                except Exception as e:
                    # 如果出错，清理临时目录
                    if temp_dir and os.path.exists(temp_dir):
                        shutil.rmtree(temp_dir)
                    db.rollback()
                    raise ValueError(f"文件处理失败: {str(e)}")
            
            task.updatetime = current_time
            upload.updatetime = current_time
            
            # 提交事务
            db.commit()
            
            # 清理旧文件资源
            if old_file_paths:
                try:
                    for old_file_path in old_file_paths:
                        if os.path.exists(old_file_path):
                            os.remove(old_file_path)
                            logger.info(f"已删除旧文件: {old_file_path}")
                            
                            # 检查并删除可能变为空的目录
                            dir_path = os.path.dirname(old_file_path)
                            if os.path.exists(dir_path) and not os.listdir(dir_path):
                                os.rmdir(dir_path)
                                logger.info(f"已删除空目录: {dir_path}")
                except Exception as e:
                    logger.error(f"清理旧文件失败: {str(e)}")
            
            db.refresh(task)
            return task
        except Exception as e:
            db.rollback()
            logger.error(f"更新任务失败: {str(e)}")
            raise e

    @staticmethod
    def delete_task(db: Session, task_id: int):
        """删除任务"""
        try:
            logger.info(f"开始删除任务: {task_id}")
            task = db.query(Task).filter(Task.id == task_id).first()
            if not task:
                logger.error(f"任务不存在: {task_id}")
                raise ValueError(StatusCode.TASK_NOT_FOUND)
            
            logger.info(f"找到任务: {task_id}, upload_id: {task.upload_id}")
            
            # 使用get_file_paths方法获取要删除的文件路径
            files_to_delete = []
            if task.upload_id:
                upload = db.query(Upload).filter(Upload.id == task.upload_id).first()
                logger.info(f"查询upload记录: {task.upload_id}, 结果: {upload is not None}")
                if upload and upload.files:
                    try:
                        files_to_delete = get_file_paths(upload.files, task.device_name, task.time)
                        logger.info(f"解析到的要删除的文件路径: {files_to_delete}")
                    except Exception as e:
                        logger.error(f"解析要删除的文件路径失败: {str(e)}")
            
            # 删除关联的upload记录
            if task.upload_id:
                upload = db.query(Upload).filter(Upload.id == task.upload_id).first()
                if upload:
                    db.delete(upload)
                    logger.info(f"已执行upload删除操作: {task.upload_id}")
            
            # 删除任务
            db.delete(task)
            logger.info(f"已执行任务删除操作: {task_id}")
            
            db.commit()
            logger.info("事务提交成功")
            
            # 清理文件资源
            if files_to_delete:
                try:
                    for file_path in files_to_delete:
                        if os.path.exists(file_path):
                            os.remove(file_path)
                            logger.info(f"已删除文件: {file_path}")
                            
                            # 检查并删除可能变为空的目录
                            dir_path = os.path.dirname(file_path)
                            if os.path.exists(dir_path) and not os.listdir(dir_path):
                                os.rmdir(dir_path)
                                logger.info(f"已删除空目录: {dir_path}")
                except Exception as e:
                    logger.error(f"清理文件失败: {str(e)}")
            
            return True
        except Exception as e:
            logger.error(f"删除任务失败: {str(e)}")
            db.rollback()
            raise e

    @staticmethod
    def create_or_update_task(db: Session, task: TaskCreate) -> Task:
        """创建或更新任务"""
        current_time = int(time.time())
        
        # 查找是否存在相同device_name、upload_id和time的任务
        existing_task = db.query(Task).filter(
            Task.device_name == task.device_name,
            Task.upload_id == task.upload_id,
            Task.time == task.time
        ).first()
        
        if existing_task:
            # 更新现有任务的状态
            existing_task.status = task.status
            existing_task.updatetime = current_time
            db_task = existing_task
        else:
            # 创建新任务
            db_task = Task(
                device_name=task.device_name,
                upload_id=task.upload_id,
                time=task.time,
                status=task.status,
                createtime=current_time,
                updatetime=current_time
            )
            db.add(db_task)
        
        db.commit()
        return db_task

    @staticmethod
    def get_tasks_by_device(db: Session, device_name: str, skip: int = 0, limit: int = 100) -> List[Task]:
        """获取设备的任务列表"""
        return db.query(Task)\
            .filter(Task.device_name == device_name)\
            .order_by(Task.time.desc())\
            .offset(skip)\
            .limit(limit)\
            .all()

    @staticmethod
    def get_tasks_by_status(db: Session, status: TaskStatus) -> List[Task]:
        """获取指定状态的任务列表"""
        try:
            tasks = db.query(Task).filter(Task.status == status).all()
            logger.info(f"获取到 {len(tasks)} 个状态为 {status} 的任务")
            return tasks
        except Exception as e:
            logger.error(f"获取任务列表失败: {str(e)}")
            return []

    @staticmethod
    def update_task_status(db: Session, task_id: int, status: TaskStatus) -> Optional[Task]:
        """更新任务状态"""
        try:
            task = db.query(Task).filter(Task.id == task_id).first()
            if task:
                logger.info(f"更新任务 {task_id} 状态: {task.status} -> {status}")
                task.status = status
                task.updatetime = int(time.time())
                db.commit()
                db.refresh(task)
                logger.info(f"任务 {task_id} 状态已更新为 {status}")
                return task
            else:
                logger.error(f"找不到任务: {task_id}")
                return None
        except Exception as e:
            logger.error(f"更新任务状态失败: {str(e)}")
            return None

    @staticmethod
    def get_tasks_by_upload(db: Session, upload_id: int) -> List[Task]:
        """获取上传记录关联的任务列表"""
        return db.query(Task)\
            .filter(Task.upload_id == upload_id)\
            .order_by(Task.time.desc())\
            .all() 