"""
简单的测试脚本，验证导入路径是否正确设置
"""
import os
import sys

# 打印当前的Python路径
print("当前Python路径:")
for path in sys.path:
    print(f" - {path}")

# 修复导入路径问题
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir)
sys.path.insert(0, parent_dir)

# 验证路径设置
print("\n添加路径后的Python路径:")
for path in sys.path:
    print(f" - {path}")

# 尝试导入app模块
try:
    import app
    print("\n成功导入app模块!")
    print(f"app模块路径: {app.__file__}")
except ImportError as e:
    print(f"\n导入app模块失败: {e}")
    
# 检查app目录是否存在
app_dir = os.path.join(parent_dir, 'app')
if os.path.exists(app_dir):
    print(f"\napp目录存在: {app_dir}")
    
    # 列出app目录中的文件和子目录
    print("\napp目录内容:")
    for item in os.listdir(app_dir):
        item_path = os.path.join(app_dir, item)
        if os.path.isdir(item_path):
            print(f" - [dir] {item}")
        else:
            print(f" - [file] {item}")
else:
    print(f"\napp目录不存在: {app_dir}")

if __name__ == "__main__":
    print("测试完成") 