from typing import List, Optional
from sqlalchemy.orm import Session
from app.models.task import Task, TaskCreate, TaskStatus
import time
import logging

logger = logging.getLogger(__name__)

class TaskService:
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
    def get_task(db: Session, task_id: int) -> Optional[Task]:
        """获取单个任务"""
        try:
            task = db.query(Task).filter(Task.id == task_id).first()
            if not task:
                logger.error(f"找不到任务: {task_id}")
            return task
        except Exception as e:
            logger.error(f"获取任务失败: {str(e)}")
            return None

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