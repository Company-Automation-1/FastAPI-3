from enum import Enum

class StatusCode(Enum):
    """状态码枚举"""
    # 成功状态码
    SUCCESS = 200
    CREATED = 201
    ACCEPTED = 202
    
    # 客户端错误状态码
    BAD_REQUEST = 400
    UNAUTHORIZED = 401
    FORBIDDEN = 403
    NOT_FOUND = 404
    METHOD_NOT_ALLOWED = 405
    CONFLICT = 409
    
    # 服务器错误状态码
    INTERNAL_ERROR = 500
    SERVICE_UNAVAILABLE = 503
    
    # 业务状态码 (1000-9999)
    DEVICE_NOT_FOUND = 1001
    DEVICE_ALREADY_EXISTS = 1002
    DEVICE_CONNECTION_FAILED = 1003
    DEVICE_OFFLINE = 1004
    
    UPLOAD_FAILED = 2001
    FILE_NOT_FOUND = 2002
    FILE_TOO_LARGE = 2003
    
    TASK_NOT_FOUND = 3001
    TASK_ALREADY_EXISTS = 3002
    TASK_EXECUTION_FAILED = 3003
    
    # ADB相关错误码
    ADB_CONNECTION_ERROR = 4001
    ADB_COMMAND_ERROR = 4002
    ADB_DEVICE_NOT_FOUND = 4003
    ADB_PERMISSION_DENIED = 4004
    
    VALIDATION_ERROR = 422
    
    UPLOAD_NOT_FOUND = 4001
    FILE_PROCESS_ERROR = 5001
    
    @classmethod
    def get_message(cls, code: int) -> str:
        """获取状态码对应的消息"""
        messages = {
            # 成功状态码
            200: "操作成功",
            201: "创建成功",
            202: "请求已接受",
            
            # 客户端错误状态码
            400: "请求参数错误",
            401: "未授权",
            403: "禁止访问",
            404: "资源不存在",
            405: "方法不允许",
            409: "资源冲突",
            
            # 服务器错误状态码
            500: "服务器内部错误",
            503: "服务不可用",
            
            # 业务状态码
            1001: "设备不存在",
            1002: "设备已存在",
            1003: "设备连接失败",
            1004: "设备离线",
            
            2001: "上传失败",
            2002: "文件不存在",
            2003: "文件过大",
            
            3001: "任务不存在",
            3002: "任务已存在",
            3003: "任务执行失败",
            
            # ADB相关错误码
            4001: "ADB连接错误",
            4002: "ADB命令执行错误",
            4003: "ADB设备未找到",
            4004: "ADB权限不足",
            
            422: "数据验证错误",
            
            StatusCode.UPLOAD_NOT_FOUND: "上传记录不存在",
            StatusCode.FILE_PROCESS_ERROR: "文件处理失败"
        }
        return messages.get(code, "未知错误") 