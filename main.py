# main.py
from fastapi import FastAPI
from app.core.config import settings
from app.api.v1 import device

app = FastAPI(
    title=settings.PROJECT_NAME,
    openapi_url=f"{settings.API_V1_STR}/openapi.json"
)

# 注册路由
app.include_router(device.router, prefix=settings.API_V1_STR)

@app.get("/")
async def root():
    return {"message": "欢迎使用 FastAPI Device Manager"}