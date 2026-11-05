@echo off
chcp 65001 >nul 2>&1

rem 切到 bat 所在目录，保证脚本里的相对路径正确
cd /d "%~dp0"

echo ==============================================
echo         除非你清楚maafw图像处理的逻辑
echo      否则使用MFAToolsPlus获取按键位置及测试
echo ==============================================
echo.

if not exist "python\python.exe" (
    echo [错误] 找不到 python\python.exe
    echo        请确认 python 目录与 bat 在同一层。
    echo.
    pause
    exit /b 1
)

python\python.exe change_Keybindings.py