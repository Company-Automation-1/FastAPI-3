@echo off
title 设备任务管理系统 - 系统报告生成工具
echo 正在生成系统报告...

:: 检查Python环境
where python >nul 2>nul
if %errorlevel% neq 0 (
    echo Python未安装或未添加到PATH环境变量!
    echo 请安装Python或将其添加到PATH环境变量后重试.
    pause
    exit /b 1
)

:: 运行报告生成工具
python generate_report.py --archive

:: 检查是否成功
if %errorlevel% neq 0 (
    echo 生成报告失败!
    pause
    exit /b 1
)

echo 报告生成完成!
echo 报告已保存到logs/reports目录.
pause 