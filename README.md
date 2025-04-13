# 设备任务管理系统

## 系统概述

设备任务管理系统是一个基于FastAPI的后端服务，用于管理多设备的任务执行流程。系统采用分层架构设计，实现了设备管理、任务调度、文件传输和UI自动化等功能。

## 系统架构

系统采用八层分层架构设计：

1. **表现层**：API接口和HTTP请求处理
2. **业务逻辑层**：核心业务规则和处理流程
3. **应用服务层**：协调业务处理，连接业务与基础设施
4. **领域服务层**：处理特定领域的业务逻辑
5. **基础设施层**：提供通用技术服务
6. **数据访问层**：处理数据库访问
7. **工具层**：提供通用工具和辅助功能
8. **ADB层**：管理与Android设备的通信

### 架构原则

1. **单一职责原则**：每个组件只负责一项特定功能
2. **依赖倒置原则**：高层模块不依赖低层模块，两者都依赖抽象
3. **相邻层调用原则**：每层只能调用相邻的层
4. **松散耦合**：组件之间通过接口协同工作，减少直接依赖

## 目录结构

```
app/
├── api/              # API路由层
│   └── v1/           # API版本1
├── automation/       # 自动化操作实现
├── adb/              # ADB服务和通信
├── core/             # 核心配置
├── db/               # 数据库基础设施
├── models/           # 数据模型
├── schemas/          # 模式验证
├── services/         # 业务服务
│   ├── app_lifecycle.py           # 应用生命周期管理
│   ├── automation_service.py      # 自动化服务
│   ├── adb_transfer.py            # ADB传输服务
│   ├── device_operation_service.py # 设备操作服务
│   ├── task_status_manager.py     # 任务状态管理器
│   ├── task_data_provider.py      # 任务数据提供者
│   ├── task_executor.py           # 任务执行器
│   ├── pending_task_scheduler.py  # PENDING任务调度器
│   ├── wt_task_scheduler.py       # WT任务调度器
│   ├── task_dispatcher.py         # 任务分发器
│   ├── task_scanner.py            # 任务扫描器
│   └── garbage_cleanup.py         # 垃圾清理服务
└── utils/            # 工具函数
    ├── file.py                    # 文件路径处理工具
    └── time_utils.py              # 时间处理工具
```

## 依赖注入模式

系统采用依赖注入（DI）模式，确保组件之间松散耦合，提高可测试性和可维护性：

1. **构造函数注入**：通过构造函数参数传递依赖
2. **默认值模式**：允许传入自定义依赖实例，否则创建默认实例
3. **共享实例**：核心服务（如ADBService）在系统启动时创建一次，并注入到需要它的组件中

### 依赖注入示例

```python
# 初始化ADB服务（共享实例）
adb_service = ADBService()

# 注入ADB服务到设备操作服务
device_operation_service = DeviceOperationService(adb_service=adb_service)

# 注入多个依赖到ADB传输服务
adb_transfer_service = ADBTransferService(
    adb_service=adb_service,
    device_operation=device_operation_service
)
```

## 核心组件功能说明

### 1. TaskStatusManager (app/services/task_status_manager.py)

任务状态管理器，负责管理任务状态的转换并提供状态转换回调函数。

**主要方法**：
- `get_status_transition_callback()`: 返回任务状态转换回调函数
- `update_task_status()`: 更新任务状态，记录日志和状态变更时间

### 2. DeviceOperationService (app/services/device_operation_service.py)

设备基础操作服务，负责设备连接检测和屏幕解锁等基础设备操作。

**主要方法**：
- `check_device_connection(device)`: 检查设备连接状态
- `check_device_lock_status(device)`: 检查设备锁屏状态
- `check_screen_status(device)`: 检查设备屏幕状态
- `wake_screen(device)`: 唤醒设备屏幕
- `unlock_screen(device)`: 解锁设备屏幕

**依赖**：
- `ADBService`: 负责执行ADB命令

### 3. ADBTransferService (app/services/adb_transfer.py)

ADB传输服务，专注于文件传输功能。

**主要方法**：
- `execute_transfer(task, db)`: 执行文件传输任务
- `transfer_file(device, local_path, remote_path)`: 传输单个文件
- `verify_file(device, local_path, remote_path)`: 验证文件传输结果
- `transfer_all_files(device, local_files, remote_files)`: 批量传输文件

**依赖**：
- `ADBService`: 提供ADB命令执行能力
- `DeviceOperationService`: 提供设备操作功能
- `TaskDataProvider`: 获取任务相关数据

### 4. AutomationService (app/services/automation_service.py)

自动化服务，专注于UI自动化执行。

**主要方法**：
- `execute_pending_task(task, db)`: 执行处于PENDING状态的任务

**依赖**：
- `DeviceOperationService`: 提供设备操作功能
- `TaskDataProvider`: 获取任务相关数据
- `AndroidAutomation`: 执行具体的UI自动化操作

### 5. TaskExecutor (app/services/task_executor.py)

任务执行器，负责执行不同状态的任务。

**主要方法**：
- `execute_task(task, db)`: 执行任务
- `execute_wt_task(task, db)`: 执行WT状态的任务
- `execute_pending_task(task, db)`: 执行PENDING状态的任务
- `_retry_task(task, db, retry_count)`: 重试任务执行

**依赖**：
- `ADBTransferService`: 执行文件传输任务
- `AutomationService`: 执行UI自动化任务
- 状态更新回调函数：更新任务状态

### 6. TaskScanner (app/services/task_scanner.py)

任务扫描器，定期扫描待处理任务并将其分发给调度器。

**主要方法**：
- `start()`: 启动任务扫描
- `stop()`: 停止任务扫描
- `scan_tasks()`: 扫描待处理任务
- `_scan_once()`: 执行一次扫描

**依赖**：
- `TaskDispatcher`: 分发任务到对应调度器

### 7. TaskDispatcher (app/services/task_dispatcher.py)

任务分发器，将任务分发到对应的调度器。

**主要方法**：
- `register_scheduler(status, scheduler)`: 注册任务调度器
- `dispatch_task(task)`: 分发任务到对应调度器

### 8. WTTaskScheduler (app/services/wt_task_scheduler.py)

WT任务调度器，负责调度WT状态的任务，采用设备串行+任务并行的方式。

**主要方法**：
- `schedule_task(task)`: 调度任务
- `_get_device_queue(device_name)`: 获取设备队列
- `_execute_device_task(device_name, tasks)`: 执行设备上的任务

**依赖**：
- `TaskExecutor`: 执行具体任务

### 9. PendingTaskScheduler (app/services/pending_task_scheduler.py)

PENDING任务调度器，负责调度PENDING状态的任务，采用设备串行+多线程的方式。

**主要方法**：
- `schedule_task(task)`: 调度任务
- `_worker_thread()`: 工作线程函数
- `_execute_task(task)`: 执行任务
- `shutdown()`: 关闭调度器

**依赖**：
- `TaskExecutor`: 执行具体任务
- `ThreadPoolExecutor`: 提供多线程执行能力

### 10. TaskDataProvider (app/services/task_data_provider.py)

任务数据提供者，提供任务相关数据。

**主要方法**：
- `get_task_data(task, db)`: 获取任务相关数据
- `get_device(task, db)`: 获取任务关联的设备
- `get_upload(task, db)`: 获取任务关联的上传记录
- `get_file_paths(task, db)`: 获取任务关联的文件路径

**依赖**：
- `utils.file`: 文件路径处理功能

### 11. AppLifecycle (app/services/app_lifecycle.py)

应用生命周期管理，管理应用的启动和关闭过程。

**主要方法**：
- `startup()`: 应用启动时执行
- `shutdown(loop, signal)`: 应用关闭时执行

**依赖**：
- 所有核心服务组件

### 12. 文件路径工具 (app/utils/file.py)

提供文件路径处理功能，封装了本地路径和设备路径的生成逻辑。

**主要方法**：
- `get_file_paths(files_json, device_name, timestamp)`: 获取本地文件路径列表
- `get_device_file_paths(files_json, device_name, device_path, timestamp)`: 获取设备文件路径列表

## 系统调用流程

### 应用启动流程

1. `main.py` 中的 `startup_event()` 函数被触发
2. 创建共享ADB服务实例
3. 初始化基础设施服务：`DeviceOperationService`（注入ADB服务）
4. 初始化业务服务：`ADBTransferService`（注入ADB服务和设备操作服务）和 `AutomationService`（注入设备操作服务）
5. 初始化任务状态管理器：`TaskStatusManager`
6. 初始化任务执行器：`TaskExecutor`（注入业务服务和状态更新回调）
7. 初始化任务调度服务：`TaskDispatcher`、`WTTaskScheduler` 和 `PendingTaskScheduler`
8. 初始化任务扫描器：`TaskScanner`（注入任务分发器）
9. 创建应用生命周期管理器：`AppLifecycle`（注入所有核心服务）
10. 启动任务扫描器

### 任务执行流程

1. `TaskScanner` 定期扫描数据库中的待处理任务
2. `TaskDispatcher` 根据任务状态将任务分发给对应的调度器
3. 对于WT状态的任务，由 `WTTaskScheduler` 调度执行
   - 通过协程实现设备串行+任务并行
4. 对于PENDING状态的任务，由 `PendingTaskScheduler` 调度执行
   - 通过线程池实现设备串行+多线程执行
5. `TaskExecutor` 负责具体执行任务，根据任务类型调用不同的服务
   - 包含重试机制和超时控制
6. 文件传输任务由 `ADBTransferService` 执行
   - 包括文件传输和验证步骤
7. UI自动化任务由 `AutomationService` 执行
   - 通过AndroidAutomation执行具体操作
8. `DeviceOperationService` 提供设备基础操作支持
   - 检查设备连接状态
   - 管理设备屏幕（唤醒和解锁）
9. `TaskStatusManager` 管理任务状态的变更
   - 提供统一的状态更新接口

### 应用关闭流程

1. `main.py` 中的 `shutdown_event()` 函数被触发
2. 调用 `AppLifecycle.shutdown()` 方法
3. 停止任务扫描器
4. 关闭PENDING调度器的线程池
5. 关闭ADB传输服务和设备操作服务的ADB服务
6. 关闭垃圾清理服务
7. 取消所有后台任务
8. 关闭事件循环

## 技术栈

- **Web框架**: FastAPI
- **数据库**: MySQL
- **ORM工具**: SQLAlchemy
- **异步处理**: asyncio
- **并发处理**: ThreadPoolExecutor
- **任务调度**: apscheduler
- **设备通信**: adb (Android Debug Bridge)

## 开发环境

```bash
# 安装依赖
pip install -r requirements.txt

# 启动服务
uvicorn main:app --reload --host 0.0.0.0 --port 8848
```

## 测试

```bash
# 运行测试
pytest

# 带覆盖率报告的测试
pytest --cov=app
```