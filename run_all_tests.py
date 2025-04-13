"""
主测试运行脚本，运行所有单元测试
这是一个替代pytest的简单方法，适用于环境有问题的情况
"""

import unittest
import sys
import os
import time

# 修复导入路径问题
current_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, current_dir)

# 确保首先使用此路径设置加载测试模块
try:
    from tests.test_utils import TestFileUtils, TestTimeUtils
    from tests.test_simple_models import SimpleModelTest
except ModuleNotFoundError:
    # 如果上面的导入失败，则尝试直接导入
    # 这种情况可能发生在不同的环境下
    sys.path.append(os.path.join(current_dir, 'tests'))
    from test_utils import TestFileUtils, TestTimeUtils
    from test_simple_models import SimpleModelTest

def run_tests():
    """运行所有测试并输出结果"""
    print("="*80)
    print(f"开始运行测试: {time.strftime('%Y-%m-%d %H:%M:%S')}")
    print("="*80)
    
    # 创建测试套件
    suite = unittest.TestSuite()
    
    # 添加工具测试
    suite.addTest(unittest.makeSuite(TestFileUtils))
    suite.addTest(unittest.makeSuite(TestTimeUtils))
    
    # 添加模型测试
    suite.addTest(unittest.makeSuite(SimpleModelTest))
    
    # 运行测试
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    # 输出测试结果摘要
    print("\n" + "="*40)
    print("测试结果摘要:")
    print(f"运行测试: {result.testsRun}")
    print(f"成功: {result.testsRun - len(result.errors) - len(result.failures)}")
    print(f"失败: {len(result.failures)}")
    print(f"错误: {len(result.errors)}")
    print("="*40)
    
    # 详细输出失败和错误
    if result.failures:
        print("\n失败的测试:")
        for test, error in result.failures:
            print(f"- {test}")
            print(f"  {error}")
    
    if result.errors:
        print("\n出错的测试:")
        for test, error in result.errors:
            print(f"- {test}")
            print(f"  {error}")
    
    # 返回测试结果状态码（成功为0，失败非0）
    return len(result.failures) + len(result.errors)

if __name__ == "__main__":
    sys.exit(run_tests()) 