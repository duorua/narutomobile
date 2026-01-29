# -*- coding: utf-8 -*-

# M9A
# https://github.com/MAA1999/M9A
# AGPL-3.0 License

import os
import sys
import json
from pathlib import Path

# utf-8
sys.stdout.reconfigure(encoding="utf-8")  # type: ignore

# 获取当前main.py路径并设置上级目录为工作目录
current_file_path = Path(__file__).resolve()  # 当前脚本的绝对路径
current_script_dir = current_file_path.parent  # 包含此脚本的目录
project_root_dir = current_script_dir.parent  # 假定的项目根目录

# 更改CWD到项目根目录
if Path.cwd() != project_root_dir:
    os.chdir(project_root_dir)
print(f"set cwd: {Path.cwd()}")

# 将脚本自身的目录添加到sys.path，以便导入utils、maa等模块
if current_script_dir.__str__() not in sys.path:
    sys.path.insert(0, current_script_dir.__str__())

from utils.logger import logger  # type: ignore

VENV_NAME = ".venv"  # 虚拟环境目录的名称
VENV_DIR = Path(project_root_dir) / VENV_NAME


### 配置相关 ###
def read_interface_version(interface_file_name="./interface.json") -> str:
    interface_path = Path(project_root_dir) / interface_file_name
    assets_interface_path = Path(project_root_dir) / "assets" / interface_file_name

    target_path = None
    if interface_path.exists():
        target_path = interface_path
    elif assets_interface_path.exists():
        return "DEBUG"

    if target_path is None:
        logger.warning("未找到interface.json")
        return "unknown"

    try:
        with open(target_path, "r", encoding="utf-8") as f:
            interface_data = json.load(f)
            return interface_data.get("version", "unknown")
    except Exception:
        logger.exception(f"读取interface.json版本失败，文件路径：{target_path}")
        return "unknown"


### 核心业务 ###
def agent(is_dev_mode=False):
    try:
        if is_dev_mode:
            from utils.logger import change_console_level  # type: ignore

            change_console_level("DEBUG")
            logger.info("开发模式：日志等级已设置为DEBUG")

        try:
            from maa.agent.agent_server import AgentServer
            from maa.toolkit import Toolkit

            import custom  # type: ignore
        except ImportError as e:
            logger.error(e)
            logger.error("Failed to import modules")
            logger.error("Please try to run dependency deployment script first")
            logger.error("导入模块失败！")
            logger.error("请先尝试运行依赖部署脚本")
            return

        Toolkit.init_option("./")

        if len(sys.argv) < 2:
            logger.error("缺少必要的 socket_id 参数")
            return

        socket_id = sys.argv[-1]
        logger.info(f"socket_id: {socket_id}")

        AgentServer.start_up(socket_id)
        logger.info("AgentServer启动")
        AgentServer.join()
        AgentServer.shut_down()
        logger.info("AgentServer关闭")
    except ImportError as e:
        logger.error(f"导入模块失败: {e}")
        logger.error("考虑重新配置环境")
        sys.exit(1)
    except Exception as e:
        logger.exception("agent运行过程中发生异常")
        raise


### 程序入口 ###


def main():
    current_version = read_interface_version()
    is_dev_mode = current_version == "DEBUG"

    if is_dev_mode:
        os.chdir(Path("./assets"))
        logger.info(f"set cwd: {os.getcwd()}")

    agent(is_dev_mode=is_dev_mode)


if __name__ == "__main__":
    main()
