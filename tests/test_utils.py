import unittest
import json
import os
import sys

# 修复导入路径问题
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir)
sys.path.insert(0, parent_dir)

from unittest.mock import patch, MagicMock
from app.utils.file import get_file_paths, get_device_file_paths
from app.utils.time_utils import timestamp_to_datetime

# 这个文件只测试纯函数，不依赖数据库

class TestFileUtils(unittest.TestCase):
    """测试文件路径工具"""
    
    @patch('os.path.exists')
    def test_get_file_paths(self, mock_exists):
        """测试本地文件路径生成"""
        # 设置模拟，假设所有文件都存在
        mock_exists.return_value = True
        
        # 测试数据
        files_json = '["device1/file1.txt", "device1/file2.txt"]'
        device_name = "device1"
        timestamp = 1623456789  # 对应2021年6月12日
        
        # 执行函数
        result = get_file_paths(files_json, device_name, timestamp)
        
        # 验证结果
        self.assertEqual(len(result), 2)
        self.assertIn("device1", result[0])
        self.assertIn("file1.txt", result[0])
        self.assertIn("20210612", result[0])
        
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
            self.assertIn("20210612", path)
            self.assertTrue(path.endswith(".txt"))
    
    def test_invalid_json(self):
        """测试无效的JSON输入"""
        invalid_json = '{"invalid": "not a list"}'
        
        # 测试get_file_paths
        result1 = get_file_paths(invalid_json, "device1", 1623456789)
        self.assertEqual(result1, [])
        
        # 测试get_device_file_paths
        result2 = get_device_file_paths(invalid_json, "device1", "/path/", 1623456789)
        self.assertEqual(result2, [])

class TestTimeUtils(unittest.TestCase):
    """测试时间工具"""
    
    def test_timestamp_to_datetime(self):
        """测试时间戳转换为格式化时间字符串"""
        # 测试数据
        timestamp = 1623456789  # 对应2021年6月12日
        
        # 执行函数
        result = timestamp_to_datetime(timestamp)
        
        # 验证结果格式为yyyymmddhhmmss
        self.assertEqual(len(result), 14)
        self.assertTrue(result.startswith("202106"))
        
    def test_invalid_timestamp(self):
        """测试无效的时间戳处理"""
        # 测试数据
        invalid_timestamp = "not_a_timestamp"
        
        # 验证异常处理
        with self.assertRaises(Exception):
            timestamp_to_datetime(invalid_timestamp)

if __name__ == "__main__":
    unittest.main() 