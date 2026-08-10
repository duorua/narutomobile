import json
from base64 import b64decode
from datetime import datetime
from pathlib import Path

# 获取当前main.py路径并设置上级目录为工作目录
current_file_path = Path(__file__).resolve()  # 当前脚本的绝对路径
current_script_dir = current_file_path.parent  # 包含此脚本的目录
project_root_dir = current_script_dir.parent.parent  # 假定的项目根目录

interface_file_name = "interface.json"
interface_path = project_root_dir / "interface.json"
assets_interface_path = project_root_dir / "assets" / interface_file_name
is_debug = assets_interface_path.exists()
interface_path = assets_interface_path if is_debug else interface_path

_dev_resource_base = project_root_dir / "assets" / "resource" / "base"
_prod_resource_base = project_root_dir / "resource" / "base"
resource_base = _dev_resource_base if is_debug else _prod_resource_base


def get_format_timestamp():
    now = datetime.now()
    date = now.strftime("%Y.%m.%d")
    time = now.strftime("%H.%M.%S")
    milliseconds = f"{now.microsecond // 1000:03d}"

    return f"{date}-{time}.{milliseconds}"


bdc = lambda s: b64decode(s).decode("utf-8")  # noqa: E731
jL = json.load
jD = json.dump
root = Path(__file__).resolve().parent.parent.parent

is_debug = any(root.glob("MFAAvalonia*"))
logo = (root / "docs" / "imgs" / "logo.png").absolute()
