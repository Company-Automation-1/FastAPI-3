# 这个文件使tests目录成为一个Python包
# 允许pytest正确发现和导入测试文件

import os
import sys

# 确保应用模块可以被导入
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))) 