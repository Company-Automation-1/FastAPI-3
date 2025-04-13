# 设备任务管理系统 测试说明

## 测试架构

本项目提供了两种测试方法：

1. **标准 pytest 测试**: 完整的测试框架，适用于正常的开发环境
2. **基本 unittest 测试**: 简化的测试，适用于环境有问题的情况

### 测试架构原则

1. 测试数据库使用SQLite内存数据库，确保测试的快速执行和隔离性
2. 使用模拟(Mock)对象隔离外部依赖，如ADB服务和设备通信
3. 按功能模块组织测试文件，清晰区分测试范围
4. 使用fixture提供常用测试数据和对象，减少重复代码

## 测试文件结构

```
tests/
├── conftest.py              # pytest配置和fixture
├── test_utils.py            # 工具类测试
├── test_services.py         # 服务层测试
├── test_api.py              # API接口测试  
├── test_core_services.py    # 核心服务测试
├── test_simple_models.py    # 简化的模型测试（使用unittest）
└── README.md                # 测试说明文档

项目根目录:
├── run_all_tests.py         # 主测试运行脚本（使用unittest）
└── run_tests.bat            # Windows批处理运行脚本
```

## 运行测试

### 方法1: 使用 pytest (推荐方式，但可能会有复合主键问题)

```bash
# 安装测试依赖
pip install pytest pytest-asyncio pytest-cov httpx

# 运行所有测试
pytest

# 运行特定测试文件
pytest tests/test_utils.py

# 运行特定测试类或方法
pytest tests/test_services.py::TestTaskStatusManager
```

### 方法2: 使用 unittest (简化版，避免环境问题)

```bash
# Windows
run_tests.bat

# Linux/Mac
python run_all_tests.py
```

或直接运行特定的测试文件:

```bash
python tests/test_utils.py
python tests/test_simple_models.py
```

## 主要测试内容

1. **工具类测试 (test_utils.py)**
   - 文件路径处理测试
   - 时间工具测试

2. **服务层测试 (test_services.py)**
   - TaskStatusManager 测试
   - TaskDataProvider 测试
   - DeviceOperationService 测试

3. **API测试 (test_api.py)**
   - 设备API测试
   - 任务API测试

4. **核心服务测试 (test_core_services.py)**
   - TaskExecutor 测试
   - TaskDispatcher 测试
   - WTTaskScheduler 和 PendingTaskScheduler 测试

5. **简化模型测试 (test_simple_models.py)**
   - 使用内存数据库的基本CRUD测试

## 测试数据

测试数据通过两种方式提供：

1. **pytest fixture** (conftest.py)：为pytest测试提供数据
2. **unittest setUp** (test_simple_models.py)：为unittest测试提供数据

## 如何编写新测试

### 使用 pytest:

```python
import pytest

@pytest.mark.asyncio
async def test_device_connection(self, device_service, sample_device):
    # 准备: 设置必要的预期条件
    device_service.adb_service.connection._execute_command.return_value = f"{sample_device.device_id}\tdevice"
    
    # 执行: 调用被测试的函数
    result = await device_service.check_device_connection(sample_device)
    
    # 验证: 检查函数的行为和输出
    assert result is True
    device_service.adb_service.connection._execute_command.assert_called_once()
```

### 使用 unittest:

```python
import unittest
from unittest.mock import patch, MagicMock

class TestExample(unittest.TestCase):
    def test_example_function(self):
        # 准备
        test_input = "test"
        
        # 执行
        result = example_function(test_input)
        
        # 验证
        self.assertEqual(result, "expected output")

if __name__ == "__main__":
    unittest.main()
```

## 已知问题与解决方案

1. **SQLite复合主键问题**：SQLite不支持复合主键的自动递增
   - 解决方案：使用简化的测试模型，避免复合主键

2. **pytest依赖问题**：某些环境下安装或运行pytest可能有问题
   - 解决方案：使用标准库unittest作为替代

3. **测试文件路径问题**：Windows环境下可能有路径解析问题
   - 解决方案：使用`os.path.join`和`os.path.abspath`处理路径 