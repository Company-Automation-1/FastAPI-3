# main.py
from fastapi import FastAPI
from app.core.config import settings
from app.api.v1 import device, upload
from fastapi.middleware.cors import CORSMiddleware

# 项目基本配置
PROJECT_NAME: str = "FastAPI Device Manager"
API_V1_STR: str = "/api/v1"

# 添加状态码说明到描述中
API_DESCRIPTION = """
# FastAPI Device Manager API

## 状态码说明

### 成功状态码
- 200: 操作成功
- 201: 创建成功
- 202: 请求已接受

### 客户端错误状态码
- 400: 请求参数错误
- 401: 未授权
- 403: 禁止访问
- 404: 资源不存在
- 405: 方法不允许
- 409: 资源冲突

### 服务器错误状态码
- 500: 服务器内部错误
- 503: 服务不可用

### 业务状态码

#### 设备相关 (1000-1999)
- 1001: 设备不存在
- 1002: 设备已存在
- 1003: 设备连接失败
- 1004: 设备离线

#### 上传相关 (2000-2999)
- 2001: 上传失败
- 2002: 文件不存在
- 2003: 文件过大

#### 任务相关 (3000-3999)
- 3001: 任务不存在
- 3002: 任务已存在
- 3003: 任务执行失败

#### ADB相关 (4000-4999)
- 4001: ADB连接错误
- 4002: ADB命令执行错误
- 4003: ADB设备未找到
- 4004: ADB权限不足
"""
    
app = FastAPI(
    version="1.0.0",
    title=PROJECT_NAME,
    openapi_url=f"{API_V1_STR}/openapi.json",
    docs_url=f"{API_V1_STR}/docs",
    redoc_url=f"{API_V1_STR}/redoc",
    # description="FastAPI Device Manager API"
    description=API_DESCRIPTION
)

# 配置CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 在生产环境中应该设置具体的域名
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 注册路由
app.include_router(device.router, prefix=API_V1_STR)
app.include_router(upload.router, prefix=API_V1_STR)

@app.get("/")
async def root():
    return {"message": "欢迎使用 FastAPI Device Manager"}

# 启动服务器（仅在直接运行时）
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)