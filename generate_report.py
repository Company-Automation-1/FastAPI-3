#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
系统报告生成工具 - 命令行入口
"""
import argparse
import sys
import os
import logging

# 添加项目根目录到Python路径
current_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.append(current_dir)

from app.core.logger import setup_logger
from app.utils.log_generator import LogGenerator

def main():
    """主函数"""
    parser = argparse.ArgumentParser(description="设备任务管理系统 - 日志报告生成工具")
    parser.add_argument("--output", "-o", help="报告输出目录", default="logs/reports")
    parser.add_argument("--days", "-d", type=int, help="收集最近几天的错误日志", default=7)
    parser.add_argument("--archive", "-a", action="store_true", help="是否归档旧日志")
    parser.add_argument("--keep", "-k", type=int, help="归档时保留最近几天的日志", default=30)
    
    args = parser.parse_args()
    
    # 设置日志系统
    setup_logger()
    
    # 创建日志生成器
    generator = LogGenerator(output_dir=args.output)
    
    # 生成系统报告
    print("正在生成系统报告...")
    report_path = generator.generate_report()
    
    if report_path:
        print(f"系统报告已生成: {report_path}")
    else:
        print("生成系统报告失败")
        return 1
    
    # 如果需要归档旧日志
    if args.archive:
        print(f"正在归档超过{args.keep}天的旧日志...")
        if generator.archive_logs(days_to_keep=args.keep):
            print("日志归档完成")
        else:
            print("日志归档失败")
    
    return 0

if __name__ == "__main__":
    sys.exit(main()) 