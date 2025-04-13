from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.core.config import settings
import logging
from app.db.db_logging import setup_db_logging

# 配置数据库日志
db_logger = setup_db_logging(is_debug=settings.DEBUG if hasattr(settings, 'DEBUG') else False)

# 使用同步引擎
engine = create_engine(
    settings.MYSQL_URL,
    pool_pre_ping=True
)

# 创建同步会话工厂
SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine
)

# 依赖项
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def close_db_connection():
    """关闭数据库连接池"""
    db_logger.info("关闭数据库连接池")
    engine.dispose() 