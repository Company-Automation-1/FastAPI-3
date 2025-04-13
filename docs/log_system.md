# 日志系统说明

## 日志系统概述

本系统采用分层的日志记录方案，提供了全面的日志收集、存储和分析功能。日志系统具有以下特点：

1. **按日期分割日志文件**：每天生成独立的日志文件，便于管理和查询
2. **多级别日志记录**：支持INFO、WARNING、ERROR等不同级别的日志
3. **独立错误日志**：所有ERROR级别以上的日志会额外记录到专门的错误日志文件中
4. **日志归档功能**：支持自动归档旧日志，减少存储空间占用
5. **系统报告生成**：提供全面的系统报告生成功能，包括系统信息、任务统计等

## 日志文件结构

日志文件保存在项目根目录的`logs`文件夹下，具体结构如下：

```
logs/
├── app_20250413.log            # 应用日志（包含所有级别）
├── error_20250413.log          # 错误日志（仅ERROR及以上级别）
├── runtime_reports/            # 运行报告目录
│   └── runtime_report_20250413_123456.log  # 运行报告文件（自动生成）
├── reports/                    # 系统报告目录
│   └── system_report_20250413_123456.log   # 系统报告文件（手动生成）
└── archive/                    # 归档日志目录
    ├── app_20250313.log        # 归档的应用日志
    └── error_20250313.log      # 归档的错误日志
```

## 日志级别说明

本系统使用以下日志级别：

- **DEBUG**：调试信息，详细的开发诊断
- **INFO**：一般信息，确认程序正常运行
- **WARNING**：警告信息，表明有潜在问题
- **ERROR**：错误信息，表明某些功能无法正常工作
- **CRITICAL**：严重错误，表明程序可能无法继续运行

## 智能错误日志处理

系统实现了智能错误日志处理机制，可以根据错误类型自动调整日志的详细程度：

1. **已知错误处理**：对于常见的错误（如数据库连接失败、文件不存在等），仅记录简要错误信息，不记录详细堆栈，减少日志冗余
2. **未知错误处理**：对于未知或不常见的错误，记录完整堆栈信息，便于详细排查
3. **错误模式识别**：系统维护常见错误模式列表，能够自动识别大多数常见错误
4. **日志信息优化**：自动截断过长的错误信息，移除不必要的背景链接

### 常见错误类型

系统可识别的常见错误类型包括：

- 数据库连接错误（`Can't connect to MySQL server`, `Connection refused`等）
- 文件操作错误（`No such file or directory`, `Permission denied`等）
- 网络错误（`Connection reset by peer`, `Connection timed out`等）
- 设备错误（`Device not found`, `Device disconnected`等）
- 认证错误（`Access denied`, `Not authenticated`等）
- 参数验证错误（`Validation error`, `Field required`等）

### 使用智能日志工具

开发者可以使用`app.utils.log_utils`模块中提供的工具函数进行智能日志记录：

```python
from app.utils.log_utils import get_logger

# 获取增强的日志记录器
logger = get_logger(__name__)

try:
    # 可能抛出异常的代码
    result = some_function()
except Exception as e:
    # 智能日志记录 - 会自动判断是否需要记录堆栈
    logger.log_error("执行操作时出错", e)
    
    # 也可以强制指定是否包含堆栈
    # logger.log_error("执行操作时出错", e, include_traceback=True)
```

## 运行报告系统

系统在启动时会自动创建并持续记录完整的运行报告，无需手动干预。运行报告包括以下内容：

1. **系统启动信息**：记录系统环境、配置和资源情况
2. **API请求和响应**：记录所有API调用的详细信息，包括请求参数、状态码和处理时间
3. **数据库操作**：记录SQL查询执行情况，特别是较慢的查询
4. **系统状态监控**：每5分钟自动记录CPU、内存、磁盘使用情况
5. **任务系统状态**：记录各种状态的任务数量和今日任务总数
6. **未捕获异常**：记录所有未被代码捕获的异常

### 运行报告的位置

运行报告自动保存在`logs/runtime_reports/`目录中，文件名格式为`runtime_report_YYYYMMDD_HHMMSS.log`，其中包含了报告的创建时间。每次应用启动都会创建一个新的运行报告文件。

### 运行报告与手动系统报告的区别

1. **运行报告**：
   - 自动创建和记录，无需手动操作
   - 持续记录系统运行的所有关键信息
   - 包含API请求、数据库操作等实时数据
   - 适合长期监控和问题排查

2. **手动系统报告**：
   - 需要手动触发生成
   - 提供当前时间点的系统快照
   - 包含更多统计数据和汇总信息
   - 适合定期审查和系统分析

## 如何使用日志系统

### 在代码中记录日志

```python
import logging

# 获取类或模块的日志记录器
logger = logging.getLogger(__name__)

# 记录不同级别的日志
logger.debug("调试信息")
logger.info("一般信息")
logger.warning("警告信息")
logger.error("错误信息")
logger.critical("严重错误")

# 记录异常信息
try:
    # 可能会抛出异常的代码
    result = 1 / 0
except Exception as e:
    logger.exception("发生异常：%s", str(e))  # 会自动记录堆栈跟踪
```

### 生成系统报告

系统提供了命令行工具来生成系统报告，有两种使用方式：

#### 方式1：使用批处理文件（推荐）

```bash
# Windows
generate_report.bat

# Linux/Mac
./generate_report.sh
```

#### 方式2：直接运行Python脚本

```bash
# 基本用法
python generate_report.py

# 指定输出目录
python generate_report.py --output logs/custom_reports

# 收集最近14天的错误日志
python generate_report.py --days 14

# 同时归档旧日志
python generate_report.py --archive

# 归档时保留最近60天的日志
python generate_report.py --archive --keep 60
```

## 系统报告内容

系统报告包含以下信息：

1. **系统信息**：操作系统、Python版本、CPU、内存、磁盘使用情况等
2. **应用配置**：主要的应用配置项（排除敏感信息）
3. **ADB设备**：当前连接的ADB设备列表
4. **任务统计**：任务状态分布、今日任务数、最近失败任务等
5. **错误日志**：最近的错误日志摘要

## 日志归档功能

系统支持自动归档旧日志，以减少主日志目录中的文件数量：

```bash
# 使用默认设置归档（保留最近30天日志）
python generate_report.py --archive

# 自定义保留天数
python generate_report.py --archive --keep 60
```

## 故障排查

如果日志系统无法正常工作，请检查：

1. `logs`目录是否存在且有写入权限
2. Python环境中是否安装了所需依赖（特别是psutil库）
3. 系统时钟是否正确（影响日志文件名生成）
4. 磁盘空间是否充足

## 最佳实践

1. 定期生成系统报告并归档旧日志（可设置为每周自动任务）
2. 适当调整日志级别，生产环境建议使用INFO级别
3. 核心功能或关键操作应该有明确的日志记录
4. 敏感信息（密码、令牌等）不应直接记录在日志中 