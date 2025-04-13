# FastAPI 项目架构说明
```powershell
Get-ChildItem -Path . -Include __pycache__ -Recurse -Directory | Remove-Item -Recurse -Force
```
 uvicorn main:app --reload --host 0.0.0.0 --port 8848 
 python -m uvicorn main:app --reload --host 0.0.0.0 --port 8080
```bash

测试依赖
pip install pytest pytest-cov httpx

## 项目结构

```bash
app/
├── api/ # API路由层：处理HTTP请求
├── core/ # 核心配置：项目配置和设置
├── db/ # 数据库层：数据库连接和会话管理
├── models/ # 模型层：数据结构定义
├── services/ # 服务层：业务逻辑
└── utils/ # 工具层：通用功能
```

## 各层详细说明

### 1. 数据库配置与连接
#### 1.1 环境配置 (.env)
```ini
# MySQL配置
MYSQL_HOST=127.0.0.1
MYSQL_PORT=3306
MYSQL_USER=root
MYSQL_PASSWORD=root
MYSQL_DATABASE=device_manager
```

#### 1.2 配置管理 (core/config.py)
```python
class Settings(BaseSettings):
    MYSQL_HOST: str
    MYSQL_PORT: int
    MYSQL_USER: str
    MYSQL_PASSWORD: str
    MYSQL_DATABASE: str

    @property
    def MYSQL_URL(self) -> str:
        return f"mysql+pymysql://{self.MYSQL_USER}:{self.MYSQL_PASSWORD}@{self.MYSQL_HOST}:{self.MYSQL_PORT}/{self.MYSQL_DATABASE}"
```

#### 1.3 数据库连接 (db/session.py)
```python
engine = create_engine(settings.MYSQL_URL)
SessionLocal = sessionmaker(bind=engine)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
```

### 2. 数据模型定义
#### 2.1 基础模型 (db/base_class.py)
```python
@as_declarative()
class Base:
    id: Any
    __name__: str
```

#### 2.2 具体模型 (models/device.py)
```python
class Device(Base):
    __tablename__ = "pre_devices"
    device_name = Column(String(50), primary_key=True)
    device_id = Column(String(255))

# Pydantic 模型用于数据验证
class DeviceCreate(BaseModel):
    device_name: str
    device_id: str
```

### 3. 业务逻辑处理
#### 3.1 服务层 (services/device.py)
```python
class DeviceService:
    @staticmethod
    def create_device(db: Session, device: DeviceCreate) -> Device:
        db_device = Device(**device.model_dump())
        db.add(db_device)
        db.commit()
        return db_device
```

### 4. API接口定义
#### 4.1 路由处理 (api/v1/device.py)
```python
@router.post("/devices/")
def create_device(device: DeviceCreate, db: Session = Depends(get_db)):
    return DeviceService.create_device(db, device)
```

## 请求处理流程

1. **客户端发起请求**
   - 发送 HTTP 请求到特定端点
   - 携带必要的数据

2. **FastAPI 处理请求**
   - 路由匹配
   - 数据验证
   - 依赖注入（如数据库会话）

3. **服务层处理业务逻辑**
   - 调用相应的服务方法
   - 执行业务规则
   - 处理数据库操作

4. **数据库交互**
   - 通过 ORM 模型操作数据库
   - 事务管理
   - 结果返回

5. **响应返回**
   - 数据序列化
   - 返回 HTTP 响应

## 分层架构的优势

### 1. 相比简单的数据库操作（如 ThinkPHP）
- 类型安全
- 代码提示
- 更好的错误检查
- 更严格的数据验证

### 2. 代码组织优势
- 关注点分离
- 代码复用
- 易于维护
- 易于测试
- 团队协作友好

### 3. 适用场景
- 大型项目
- 企业级应用
- 需要严格类型检查的场景
- 复杂业务逻辑

## 使用示例

### 1. 定义模型
```python
class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True)
    name = Column(String)
    age = Column(Integer)
```

### 2. 数据验证
```python
class UserCreate(BaseModel):
    name: str
    age: int = Field(gt=0, lt=150)  # 年龄必须在0-150之间
```

### 3. 业务逻辑
```python
class UserService:
    @staticmethod
    def create_user(db: Session, user_data: UserCreate):
        user = User(**user_data.model_dump())
        db.add(user)
        db.commit()
        return user
```

### 4. API接口
```python
@router.post("/users/")
def create_user(user: UserCreate, db: Session = Depends(get_db)):
    return UserService.create_user(db, user)
```

## 注意事项

1. **代码组织**
   - 保持各层职责清晰
   - 避免循环导入
   - 合理使用依赖注入

2. **数据库操作**
   - 正确管理数据库会话
   - 适当使用事务
   - 注意性能优化

3. **错误处理**
   - 统一的错误处理机制
   - 合适的错误返回
   - 日志记录

4. **安全性**
   - 输入验证
   - 权限控制
   - 数据过滤