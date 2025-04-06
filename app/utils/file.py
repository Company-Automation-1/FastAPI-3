import os
import json
import logging
from typing import List
from app.core.config import settings
from app.utils.time_utils import timestamp_to_datetime

logger = logging.getLogger(__name__)

def get_file_paths(files_json: str, device_name: str, timestamp: int) -> List[str]:
    """
    解析文件JSON字符串，获取完整的文件路径列表
    
    Args:
        files_json: JSON格式的文件路径列表字符串，如'["deviceA/file1.txt"]'
        device_name: 设备名称
        timestamp: 时间戳
        
    Returns:
        List[str]: 完整文件路径列表
    """
    try:
        # 解析JSON字符串为Python列表
        relative_paths = json.loads(files_json)
        if not isinstance(relative_paths, list):
            logger.error(f"文件列表格式错误，应为数组: {relative_paths}")
            return []
        
        # 将时间戳转换为格式化时间字符串 (yyyymmddhhmmss)
        time_folder = timestamp_to_datetime(timestamp)
        
        # 构建完整路径
        full_paths = []
        for rel_path in relative_paths:
            # rel_path的格式是"设备名/文件名"，提取文件名
            filename = os.path.basename(rel_path)
            
            # 构建完整路径: UPLOAD_DIR/设备名/格式化时间/文件名
            full_path = os.path.join(settings.UPLOAD_DIR, device_name, time_folder, filename)
            
            # 检查文件是否存在
            if os.path.exists(full_path):
                full_paths.append(full_path)
                logger.debug(f"找到文件: {full_path}")
            else:
                logger.warning(f"文件不存在: {full_path}")
        
        logger.info(f"找到 {len(full_paths)}/{len(relative_paths)} 个有效文件")
        return full_paths
        
    except json.JSONDecodeError as e:
        logger.error(f"解析文件列表JSON失败: {str(e)}")
        return []
    except Exception as e:
        logger.error(f"获取文件路径时出错: {str(e)}")
        return []

def get_device_file_paths(files_json: str, device_name: str, device_path: str, timestamp: int) -> List[str]:
    """
    为设备生成文件路径列表，结合设备存储路径和时间戳
    
    Args:
        files_json: JSON格式的文件路径列表字符串，如'["deviceA/file1.txt"]'
        device_name: 设备名称
        device_path: 设备存储路径，如'/storage/emulated/0/Pictures/'
        timestamp: 时间戳
        
    Returns:
        List[str]: 设备上的完整文件路径列表
    """
    try:
        # 解析JSON字符串为Python列表
        relative_paths = json.loads(files_json)
        if not isinstance(relative_paths, list):
            logger.error(f"文件列表格式错误，应为数组: {relative_paths}")
            return []
        
        # 将时间戳转换为完整的格式化时间字符串 (yyyymmddhhmmss)
        time_folder = timestamp_to_datetime(timestamp)
        
        # 构建设备上的完整路径
        device_full_paths = []
        for rel_path in relative_paths:
            # rel_path的格式是"设备名/文件名"，提取文件名
            filename = os.path.basename(rel_path)
            
            # 如果设备路径不以斜杠结尾，则添加斜杠
            if device_path and not device_path.endswith('/'):
                device_path += '/'
                
            # 构建设备上的完整路径: 设备存储路径/完整时间文件夹/文件名
            device_full_path = f"{device_path}{time_folder}/{filename}"
            
            # 标准化路径，使用正斜杠，去除多余斜杠
            device_full_path = device_full_path.replace('\\', '/').replace('//', '/')
            
            device_full_paths.append(device_full_path)
            logger.debug(f"设备文件路径: {device_full_path}")
        
        logger.info(f"生成了 {len(device_full_paths)} 个设备文件路径")
        return device_full_paths
        
    except json.JSONDecodeError as e:
        logger.error(f"解析文件列表JSON失败: {str(e)}")
        return []
    except Exception as e:
        logger.error(f"获取设备文件路径时出错: {str(e)}")
        return [] 