from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
from app.db.session import get_db
from app.models.task import Task, TaskStatus
from app.models.upload import Upload
from app.schemas.upload import FileData
from app.schemas.task import TaskCreate, TaskInDB, TaskUpdate
from app.services.upload import UploadService
from app.services.task import TaskService
from app.core.config import settings
from app.utils.file import get_file_paths
from app.schemas.common import ResponseModel
from app.core.status_code import StatusCode
import time
import json
import os
from base64 import b64decode
from app.utils.time_utils import timestamp_to_datetime
import shutil
from sqlalchemy.exc import SQLAlchemyError
import logging

logger = logging.getLogger(__name__)

router = APIRouter()

@router.get("/tasks/", response_model=ResponseModel[List[TaskInDB]])
async def get_tasks(
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db)
):
    """
    获取任务列表
    """
    try:
        tasks = TaskService.get_tasks(db, skip, limit)
        return ResponseModel(data=tasks)
    except Exception as e:
        return ResponseModel(
            code=StatusCode.SERVER_ERROR.value,
            message=str(e)
        )

@router.get("/tasks/{task_id}", response_model=ResponseModel[TaskInDB])
async def get_task(
    task_id: int,
    db: Session = Depends(get_db)
):
    """
    获取单个任务详情
    """
    try:
        task = TaskService.get_task(db, task_id)
        return ResponseModel(data=task)
    except ValueError as e:
        return ResponseModel(
            code=StatusCode.TASK_NOT_FOUND.value,
            message=str(e)
        )
    except Exception as e:
        return ResponseModel(
            code=StatusCode.SERVER_ERROR.value,
            message=str(e)
        )

@router.put("/tasks/{task_id}", response_model=ResponseModel[TaskInDB])
async def update_task(
    task_id: int,
    task_update: TaskUpdate,
    db: Session = Depends(get_db)
):
    """
    更新任务信息，同时更新关联的upload记录
    """
    try:
        task = TaskService.update_task(db, task_id, task_update)
        return ResponseModel(data=task)
    except ValueError as e:
        error_code = int(str(e))
        return ResponseModel(
            code=error_code,
            message=StatusCode.get_message(error_code)
        )
    except SQLAlchemyError as e:
        return ResponseModel(
            code=StatusCode.INTERNAL_ERROR,
            message=str(e)
        )
    except Exception as e:
        return ResponseModel(
            code=StatusCode.INTERNAL_ERROR,
            message=str(e)
        )

@router.delete("/tasks/{task_id}", response_model=ResponseModel)
async def delete_task(
    task_id: int,
    db: Session = Depends(get_db)
):
    """
    删除任务
    """
    try:
        TaskService.delete_task(db, task_id)
        return ResponseModel(message="任务已删除")
    except ValueError as e:
        return ResponseModel(
            code=StatusCode.TASK_NOT_FOUND.value,
            message=str(e)
        )
    except Exception as e:
        return ResponseModel(
            code=StatusCode.SERVER_ERROR.value,
            message=str(e)
        ) 