import os
import sys
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, Column, Integer, String, BigInteger, ForeignKey
from sqlalchemy.orm import sessionmaker, declarative_base
from sqlalchemy.pool import StaticPool

# 确保应用模块可以被导入
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app.db.session import get_db
from main import app
from app.models.task import TaskStatus

# 创建测试数据库引擎（使用内存数据库）
TEST_SQLALCHEMY_DATABASE_URL = "sqlite:///./test.db"
engine = create_engine(
    TEST_SQLALCHEMY_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# 创建测试用的Base类
TestBase = declarative_base()

# 为测试创建简化的模型类，避免从app导入可能有复合主键的模型
class TestDevice(TestBase):
    __tablename__ = "test_devices"
    id = Column(Integer, primary_key=True)
    device_id = Column(String, unique=True, index=True)
    device_name = Column(String, unique=True, index=True)
    device_path = Column(String)
    password = Column(String)

class TestUpload(TestBase):
    __tablename__ = "test_uploads"
    id = Column(Integer, primary_key=True)
    title = Column(String)
    content = Column(String)
    files = Column(String)
    upload_time = Column(BigInteger)

class TestTask(TestBase):
    __tablename__ = "test_tasks"
    id = Column(Integer, primary_key=True)
    device_name = Column(String)
    upload_id = Column(Integer, ForeignKey("test_uploads.id"))
    status = Column(String)
    time = Column(BigInteger)


@pytest.fixture(scope="session", autouse=True)
def setup_test_db():
    """在所有测试开始前设置测试数据库"""
    # 创建测试数据库表
    TestBase.metadata.create_all(bind=engine)
    yield
    # 所有测试完成后删除测试数据库文件
    if os.path.exists("./test.db"):
        os.remove("./test.db")

@pytest.fixture
def db_session():
    """每个测试提供一个数据库会话"""
    connection = engine.connect()
    transaction = connection.begin()
    session = TestingSessionLocal(bind=connection)
    
    yield session
    
    session.close()
    transaction.rollback()
    connection.close()

@pytest.fixture
def client(db_session):
    """测试客户端，重写数据库依赖"""
    def override_get_db():
        try:
            yield db_session
        finally:
            pass
    
    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as test_client:
        yield test_client
    # 测试完成后清除重写
    app.dependency_overrides.clear()

@pytest.fixture
def sample_device(db_session):
    """创建示例设备数据"""
    device = TestDevice(
        device_id="test_device_id",
        device_name="test_device",
        device_path="/storage/emulated/0/",
        password="1234"
    )
    db_session.add(device)
    db_session.commit()
    db_session.refresh(device)
    return device

@pytest.fixture
def sample_upload(db_session):
    """创建示例上传数据"""
    upload = TestUpload(
        title="测试上传",
        content="测试内容",
        files='["test_device/test.txt"]',
        upload_time=1623456789
    )
    db_session.add(upload)
    db_session.commit()
    db_session.refresh(upload)
    return upload

@pytest.fixture
def sample_task(db_session, sample_device, sample_upload):
    """创建示例任务数据"""
    task = TestTask(
        device_name=sample_device.device_name,
        upload_id=sample_upload.id,
        status=TaskStatus.WT,
        time=1623456789
    )
    db_session.add(task)
    db_session.commit()
    db_session.refresh(task)
    return task 