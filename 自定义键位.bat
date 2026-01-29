@echo off
chcp 65001 >nul 2>&1  :: 解决中文乱码问题
echo ==============================================
echo          正在启动键位替换工具...
echo          Python解释器路径：python\python.exe
echo ==============================================
echo.

:: 调用指定的python.exe运行脚本（脚本名要和你的py文件一致）
python\python.exe change_Keybindings.py

echo.
echo ==============================================
echo          程序已退出，按任意键关闭窗口...
echo ==============================================
pause >nul
