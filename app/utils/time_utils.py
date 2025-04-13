from datetime import datetime
import pytz
from app.core.config import settings
import time

def timestamp_to_datetime(timestamp: int) -> str:
    """
    将UTC时间戳转换为指定时区的yyyymmddhhmmss格式
    
    Args:
        timestamp: UTC时间戳（秒）
    
    Returns:
        str: yyyymmddhhmmss格式的时间字符串
    """
    # 检查是否配置了时区
    if hasattr(settings, 'TIMEZONE') and settings.TIMEZONE and settings.TIMEZONE.strip():
        # 如果配置了时区，使用配置的时区
        utc_time = datetime.fromtimestamp(timestamp, pytz.UTC)
        local_tz = pytz.timezone(settings.TIMEZONE)
        local_time = utc_time.astimezone(local_tz)
    else:
        # 如果没有配置时区或时区为空，使用UTC时间
        utc_time = datetime.fromtimestamp(timestamp, pytz.UTC)
        local_time = utc_time
    
    # 格式化为yyyymmddhhmmss
    return local_time.strftime("%Y%m%d%H%M%S")

def datetime_to_timestamp(date_str: str) -> int:
    """
    将yyyymmddhhmmss格式转换为UTC时间戳
    
    Args:
        date_str: yyyymmddhhmmss格式的时间字符串
    
    Returns:
        int: UTC时间戳（秒）
    """
    # 解析时间字符串
    local_time = datetime.strptime(date_str, "%Y%m%d%H%M%S")
    
    # 检查是否配置了时区
    if hasattr(settings, 'TIMEZONE') and settings.TIMEZONE and settings.TIMEZONE.strip():
        # 如果配置了时区，添加时区信息
        local_tz = pytz.timezone(settings.TIMEZONE)
        local_time = local_tz.localize(local_time)
    else:
        # 如果没有配置时区或时区为空，使用UTC时间
        local_time = pytz.UTC.localize(local_time)
    
    # 转换为UTC时间戳
    return int(local_time.timestamp())

def get_current_timestamp() -> int:
    """
    获取当前时间戳，考虑时区设置
    
    Returns:
        int: 当前时间戳（秒）
    """
    # 获取当前UTC时间戳
    current_utc = int(time.time())
    
    # 转换为本地时间字符串
    local_datetime = timestamp_to_datetime(current_utc)
    
    # 转换回时间戳，这样就会考虑时区设置
    return datetime_to_timestamp(local_datetime)

def get_current_datetime(timestamp=None) -> str:
    """
    获取指定时间戳或当前时间的格式化字符串，考虑时区设置
    
    Args:
        timestamp: 可选时间戳（秒），如果未提供则使用当前时间
    
    Returns:
        str: yyyymmddhhmmss格式的时间字符串
    """
    if timestamp is None:
        timestamp = int(time.time())
    return timestamp_to_datetime(int(timestamp))