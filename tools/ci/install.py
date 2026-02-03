import platform
from pathlib import Path
import os
import shutil
import sys

import jsonc

from configure import configure_ocr_model  # type: ignore
from utils import working_dir  # type: ignore

install_path = working_dir / Path("install")

sys.stdout.reconfigure(encoding="utf-8")  # type: ignore


def get_dotnet_platform_tag(os_name, arch) -> str:
    """自动检测当前平台并返回对应的dotnet平台标签"""
    if os_name == "win" and arch == "x86_64":
        platform_tag = "win-x64"
    elif os_name == "win" and arch == "aarch64":
        platform_tag = "win-arm64"
    elif os_name == "macos" and arch == "x86_64":
        platform_tag = "osx-x64"
    elif os_name == "macos" and arch == "aarch64":
        platform_tag = "osx-arm64"
    elif os_name == "linux" and arch == "x86_64":
        platform_tag = "linux-x64"
    elif os_name == "linux" and arch == "aarch64":
        platform_tag = "linux-arm64"
    else:
        print(f"Unsupported OS or architecture: {os_name}-{arch}")
        print("available parameters:")
        print("version: e.g., v1.0.0")
        print("os: [win, macos, linux, android]")
        print("arch: [aarch64, x86_64]")
        sys.exit(1)

    return platform_tag


def install_maafw(os_name, arch):
    if not (working_dir / "deps" / "bin").exists():
        print('Please download the MaaFramework to "deps" first.')
        print('请先下载 MaaFramework 到 "deps"。')
        sys.exit(1)

    shutil.copytree(
        working_dir / "deps" / "bin",
        install_path / "runtimes" / get_dotnet_platform_tag(os_name, arch) / "native",
        ignore=shutil.ignore_patterns(
            "*MaaDbgControlUnit*",
            "*MaaThriftControlUnit*",
            "*MaaRpc*",
            "*MaaHttp*",
            "plugins",
            "*.node",
            "*MaaPiCli*",
        ),
        dirs_exist_ok=True,
    )


def install_resource(version):
    configure_ocr_model()

    def merge_pipeline_files():
        pipeline_files = Path(
            working_dir / "assets" / "resource" / "base" / "pipeline"
        ).glob("*.json")
        pipeline_merged = {}
        for pipeline_file in pipeline_files:
            with open(pipeline_file, "r", encoding="utf-8") as f:
                pipeline_data = jsonc.load(f)
                pipeline_merged.update(pipeline_data)
            os.remove(pipeline_file)

        with open(
            working_dir / "assets" / "resource" / "base" / "pipeline" / "merged.json",
            "w",
            encoding="utf-8",
        ) as f:
            jsonc.dump(pipeline_merged, f, ensure_ascii=False, indent=4)

    if Path(".vscode").exists() or Path(".venv").exists() or Path(".nicegui").exists():
        print("开发环境安装，跳过资源合并")
    else:
        merge_pipeline_files()

    shutil.copytree(
        working_dir / "assets" / "resource",
        install_path / "resource",
        dirs_exist_ok=True,
    )

    shutil.copy2(
        working_dir / "assets" / "interface.json",
        install_path,
    )

    with open(install_path / "interface.json", "r", encoding="utf-8") as f:
        interface = jsonc.load(f)

    interface["version"] = version
    if "beta" in version:
        interface["welcome"] = "你正在使用的是公测版，这不是一个稳定版本！"
    if "ci" in version:
        interface["welcome"] = "欢迎使用内部测试版本，包含最不稳定但是最新的功能。"

    with open(install_path / "interface.json", "w", encoding="utf-8") as f:
        jsonc.dump(interface, f, ensure_ascii=False, indent=4)


def install_chores():
    for file in ["README.md", "LICENSE", "requirements.txt", "CONTACT"]:
        shutil.copy2(
            working_dir / file,
            install_path,
        )

    shutil.copytree(
        working_dir / "docs",
        install_path / "docs",
        dirs_exist_ok=True,
        ignore=shutil.ignore_patterns("*.yaml"),
    )

    shutil.copy2(
        working_dir / "docs" / "imgs" / "logo.ico",
        install_path / "resource" / "logo.ico",
    )

    if platform.system() == "Linux":
        shutil.copy2(
            working_dir / "tools" / "deploy_python_env_linux.sh",
            install_path / "deploy_python_env_linux.sh",
        )

    shutil.copy2(
        working_dir / "tools" / "get_cli.sh",
        install_path / "get_cli.sh",
    )
    shutil.copy2(
        working_dir / "tools" / "get_cli.bat",
        install_path / "get_cli.bat",
    )


def install_agent(os_name):
    shutil.copytree(
        working_dir / "agent",
        install_path / "agent",
        dirs_exist_ok=True,
    )

    with open(install_path / "interface.json", "r", encoding="utf-8") as f:
        interface = jsonc.load(f)

    if os_name == "win":
        interface["agent"]["child_exec"] = r"python/python.exe"
    elif os_name == "macos":
        interface["agent"]["child_exec"] = r"python/bin/python3"
    elif os_name == "linux":
        interface["agent"]["child_exec"] = r".venv/bin/python3"
    else:
        print(f"Unsupported OS: {os_name}")
        sys.exit(1)

    interface["agent"]["child_args"] = ["-u", r"agent/main.py"]

    with open(install_path / "interface.json", "w", encoding="utf-8") as f:
        jsonc.dump(interface, f, ensure_ascii=False, indent=4)


if __name__ == "__main__":
    if sys.argv.__len__() < 4:
        print("Usage: python install.py <version> <os> <arch>")
        print("Example: python install.py v1.0.0 win x86_64")
        sys.exit(1)

    # the first parameter is self name
    version = len(sys.argv) > 1 and sys.argv[1] or "v0.0.1"
    os_name = sys.argv[2]
    arch = sys.argv[3]

    install_maafw(os_name, arch)
    install_resource(version)
    install_chores()
    install_agent(os_name)

    print(f"Install to {install_path} successfully.")
