@echo off
setlocal

echo 设备任务管理系统单元测试
echo =================================

rem 添加颜色支持
set GREEN=92
set RED=91
set DEFAULT=0

rem 检查Python环境
where python >nul 2>nul
if %ERRORLEVEL% neq 0 (
    call :colorEcho %RED% "错误: 未找到Python. 请确保Python已安装并添加到PATH."
    exit /b 1
)

rem 运行测试
echo.
echo 运行所有单元测试...
echo.
python run_all_tests.py
set RESULT=%ERRORLEVEL%

if %RESULT% equ 0 (
    call :colorEcho %GREEN% "所有测试通过!"
) else (
    call :colorEcho %RED% "测试未通过. 请查看上面的错误信息."
)

exit /b %RESULT%

:colorEcho
echo [%~1m%~2[%DEFAULT%m
exit /b 