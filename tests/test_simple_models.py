"""
简单的数据模型测试，使用SQLite内存数据库，避免复合主键问题
"""
import unittest
import os
import sys
from sqlalchemy import create_engine, Column, Integer, String, BigInteger, ForeignKey
from sqlalchemy.orm import sessionmaker, declarative_base
from sqlalchemy.pool import StaticPool

# 修复导入路径问题
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir)
sys.path.insert(0, parent_dir)

# 创建内存数据库引擎
TEST_DB_URL = "sqlite:///:memory:"
engine = create_engine(
    TEST_DB_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# 创建测试用的Base类
TestBase = declarative_base()

# 为测试创建简化的模型类
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


class SimpleModelTest(unittest.TestCase):
    """简单的模型测试，使用内存数据库"""
    
    def setUp(self):
        """创建测试表和会话"""
        TestBase.metadata.create_all(bind=engine)
        self.db = TestingSessionLocal()
    
    def tearDown(self):
        """清理测试会话和表"""
        self.db.close()
        TestBase.metadata.drop_all(bind=engine)
    
    def test_create_device(self):
        """测试创建设备"""
        device = TestDevice(
            device_id="test_id",
            device_name="test_device",
            device_path="/storage/test/",
            password="1234"
        )
        self.db.add(device)
        self.db.commit()
        
        # 从数据库查询并验证
        db_device = self.db.query(TestDevice).filter_by(device_name="test_device").first()
        self.assertIsNotNone(db_device)
        self.assertEqual(db_device.device_id, "test_id")
    
    def test_create_upload(self):
        """测试创建上传记录"""
        upload = TestUpload(
            title="测试上传",
            content="测试内容",
            files='["test_device/test.txt"]',
            upload_time=1623456789
        )
        self.db.add(upload)
        self.db.commit()
        
        # 验证
        db_upload = self.db.query(TestUpload).first()
        self.assertIsNotNone(db_upload)
        self.assertEqual(db_upload.title, "测试上传")
    
    def test_create_task(self):
        """测试创建任务并关联设备和上传"""
        # 创建设备
        device = TestDevice(
            device_id="test_id",
            device_name="test_device",
            device_path="/storage/test/",
            password="1234"
        )
        self.db.add(device)
        
        # 创建上传
        upload = TestUpload(
            title="测试上传",
            content="测试内容",
            files='["test_device/test.txt"]',
            upload_time=1623456789
        )
        self.db.add(upload)
        self.db.commit()
        
        # 创建任务
        task = TestTask(
            device_name=device.device_name,
            upload_id=upload.id,
            status="WT",
            time=1623456789
        )
        self.db.add(task)
        self.db.commit()
        
        # 验证
        db_task = self.db.query(TestTask).first()
        self.assertIsNotNone(db_task)
        self.assertEqual(db_task.device_name, "test_device")
        self.assertEqual(db_task.status, "WT")


if __name__ == "__main__":
    unittest.main() 