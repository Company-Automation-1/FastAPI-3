"""
简单的测试运行器，用于直接运行测试而不依赖pytest命令行
适用于无法正常使用pytest命令的环境
"""

import unittest
import sys
import os
import json
from unittest.mock import patch, MagicMock

# 修复导入路径问题
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir)
sys.path.insert(0, parent_dir)

# 导入被测试的函数
from app.utils.file import get_file_paths, get_device_file_paths
from app.utils.time_utils import timestamp_to_datetime

# 创建基于unittest的测试类，替代原来基于pytest的测试类
class SimpleFileUtilsTest(unittest.TestCase):
    """测试文件路径工具，使用unittest而非pytest"""
    
    def test_get_device_file_paths(self):
        """测试设备文件路径生成"""
        # 测试数据
        files_json = '["device1/file1.txt", "device1/file2.txt"]'
        device_name = "device1"
        device_path = "/storage/emulated/0/Pictures/"
        timestamp = 1623456789  # 对应2021年6月12日
        
        # 执行函数
        result = get_device_file_paths(files_json, device_name, device_path, timestamp)
        
        # 验证结果
        self.assertEqual(len(result), 2)
        for path in result:
            self.assertTrue(path.startswith("/storage/emulated/0/Pictures/"))
            self.assertTrue("20210612" in path)
            self.assertTrue(path.endswith(".txt"))
    
    def test_invalid_json(self):
        """测试无效的JSON输入"""
        invalid_json = '{"invalid": "not a list"}'
        
        # 测试get_device_file_paths
        result = get_device_file_paths(invalid_json, "device1", "/path/", 1623456789)
        self.assertEqual(result, [])


class SimpleTimeUtilsTest(unittest.TestCase):
    """测试时间工具，使用unittest而非pytest"""
    
    def test_timestamp_to_datetime(self):
        """测试时间戳转换为格式化时间字符串"""
        # 测试数据
        timestamp = 1623456789  # 对应2021年6月12日
        
        # 执行函数
        result = timestamp_to_datetime(timestamp)
        
        # 验证结果格式为yyyymmddhhmmss
        self.assertEqual(len(result), 14)
        self.assertTrue(result.startswith("202106"))


if __name__ == "__main__":
    # 创建测试套件
    suite = unittest.TestSuite()
    
    # 添加文件工具和时间工具测试
    suite.addTest(unittest.makeSuite(SimpleFileUtilsTest))
    suite.addTest(unittest.makeSuite(SimpleTimeUtilsTest))
    
    # 运行测试并输出结果
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    # 输出测试结果摘要
    print(f"\n测试结果摘要:")
    print(f"运行测试: {result.testsRun}")
    print(f"成功: {result.testsRun - len(result.errors) - len(result.failures)}")
    print(f"失败: {len(result.failures)}")
    print(f"错误: {len(result.errors)}")
    
    # 设置退出代码
    sys.exit(len(result.failures) + len(result.errors)) 