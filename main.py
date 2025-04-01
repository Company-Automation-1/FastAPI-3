# main.py
from fastapi import FastAPI
from app.core.config import settings
from app.api.v1 import device, upload
from fastapi.middleware.cors import CORSMiddleware

# 项目基本配置
PROJECT_NAME: str = "FastAPI Device Manager"
API_V1_STR: str = "/api/v1"
    
app = FastAPI(
    version="1.0.0",
    title=PROJECT_NAME,
    openapi_url=f"{API_V1_STR}/openapi.json",
    docs_url=f"{API_V1_STR}/docs",
    redoc_url=f"{API_V1_STR}/redoc",
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