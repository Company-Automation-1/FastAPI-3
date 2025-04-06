class ADBError(Exception):
    """ADB操作基础异常类"""
    pass

class ADBConnectionError(ADBError):
    """ADB连接异常"""
    pass

class ADBCommandError(ADBError):
    """ADB命令执行异常"""
    pass

class DeviceNotFoundError(ADBError):
    """设备未找到异常"""
    pass 