#!/usr/bin/env bash
# 自定义键位 - macOS / Linux 启动脚本

# 切到脚本所在目录，保证脚本里的相对路径正确
cd "$(dirname "$0")" || exit 1

echo "=============================================="
echo "        除非你清楚maafw图像处理的逻辑"
echo "     否则使用MFAToolsPlus获取按键位置及测试"
echo "     sh文件还未测试,如有问题请反馈"
echo "=============================================="
echo

# 优先用项目自带的 python，其次用系统的 python3
if [ -x "./python/bin/python3" ]; then
    PY="./python/bin/python3"
elif [ -x "./python/bin/python" ]; then
    PY="./python/bin/python"
elif command -v python3 >/dev/null 2>&1; then
    PY="python3"
else
    echo "[错误] 找不到 python3"
    echo "请确认 python 目录与本脚本在同一层，或已安装 python3"
    echo
    exit 1
fi

"$PY" change_Keybindings.py