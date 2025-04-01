from typing import List, Optional
from sqlalchemy.orm import Session
from app.models.task import Task, TaskCreate, TaskStatus
import time

class TaskService:
    @staticmethod
    def create_or_update_task(db: Session, task: TaskCreate) -> Task:
        """创建或更新任务"""
        current_time = int(time.time())
        
        # 查找是否存在相同device_name和time的任务
        existing_task = db.query(Task).filter(
            Task.device_name == task.device_name,
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
                time=task.time,
                status=task.status,
                createtime=current_time,
                updatetime=current_time
            )
            db.add(db_task)
        
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
        return db.query(Task).filter(Task.id == task_id).first()

    @staticmethod
    def update_task_status(db: Session, task_id: int, status: TaskStatus) -> Optional[Task]:
        """更新任务状态"""
        db_task = TaskService.get_task(db, task_id)
        if not db_task:
            return None
        
        db_task.status = status.value
        db_task.updatetime = int(time.time())
        db.commit()
        db.refresh(db_task)
        return db_task 