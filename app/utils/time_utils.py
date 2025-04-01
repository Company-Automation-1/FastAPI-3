from datetime import datetime
import pytz
from app.core.config import settings

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