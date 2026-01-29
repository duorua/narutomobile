@echo off
chcp 65001 >nul
setlocal enabledelayedexpansion

echo ============================================
echo Python 虚拟环境安装脚本
echo ============================================
echo.

cd /d "%~dp0\.."
echo 当前目录: %cd%
echo.
echo [1/4] 检查 Python 是否安装...
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo [错误] 未找到 Python，请先安装 Python 3.8+
    echo 下载地址: https://www.python.org/downloads/
    pause
    exit /b 1
)

for /f "tokens=2" %%i in ('python --version 2^>^&1') do set PYTHON_VERSION=%%i
echo [成功] 检测到 Python %PYTHON_VERSION%
echo.

if not exist "requirements.txt" (
    echo [错误] 未找到 requirements.txt 文件
    pause
    exit /b 1
)

echo [2/4] 检查虚拟环境...
if exist ".venv\Scripts\activate.bat" (
    echo [信息] 虚拟环境已存在，跳过创建
) else (
    echo [信息] 创建虚拟环境...
    python -m venv .venv
    if %errorlevel% neq 0 (
        echo [错误] 创建虚拟环境失败
        pause
        exit /b 1
    )
    echo [成功] 虚拟环境创建完成
)
echo.

echo [3/4] 激活虚拟环境
call .venv\Scripts\activate.bat
if %errorlevel% neq 0 (
    echo [错误] 激活虚拟环境失败
    pause
    exit /b 1
)
echo [成功] 虚拟环境已激活
echo.

echo [信息] 升级 pip...
python -m pip install --upgrade pip -q
echo.

echo [4/4] 安装 Python 依赖包...
python -m pip install -r requirements.txt
if %errorlevel% neq 0 (
    echo [错误] 安装依赖包失败
    pause
    exit /b 1
)
echo.

echo ============================================
echo [完成] 所有依赖安装成功！
echo ============================================
echo.
echo 提示: 运行项目前请先激活虚拟环境:
echo   .venv\Scripts\activate
echo.

pause
