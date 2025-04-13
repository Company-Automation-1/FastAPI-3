#!/bin/bash
# 设备任务管理系统 - 系统报告生成工具 (Linux/Mac版)

echo "正在生成系统报告..."

# 检查Python环境
if ! command -v python &> /dev/null; then
    echo "错误: Python未安装或未添加到PATH环境变量!"
    echo "请安装Python或将其添加到PATH环境变量后重试."
    exit 1
fi

# 添加执行权限（如果需要）
chmod +x generate_report.py 2>/dev/null

# 运行报告生成工具
python generate_report.py --archive

# 检查是否成功
if [ $? -ne 0 ]; then
    echo "生成报告失败!"
    exit 1
fi

echo "报告生成完成!"
echo "报告已保存到logs/reports目录." 