import os
import platform
from zipfile import ZipFile
import json
import sys
from pathlib import Path
import argparse
import shutil
import subprocess
import urllib.request as request


sys.path.insert(0, Path(__file__).parent.__str__())
sys.path.insert(0, (Path(__file__).parent / "ci").__str__())

from ci.install import (
    install_maafw,
    install_resource,
    install_agent,
)
from ci.setup_embed_python import PYTHON_VERSION_TARGET
from setup_full_python import download_file

DEFAULT_MFA_VERSION = "v2.5.7-beta.2"
GHPROXY_URL = "https://gh-proxy.natsuu.top/"

parser = argparse.ArgumentParser(
    description="Install MaaFramework to install directory"
)
parser.add_argument(
    "--install_dir", type=str, default="install", help="Install directory"
)
parser.add_argument(
    "--arch", type=str, default="amd64", help="Architecture (amd64 or win32)"
)
parser.add_argument(
    "--pre-release", type=bool, default=False, help="Install pre-release version"
)
parser.add_argument(
    "--ghproxy",
    type=bool,
    default=True,
    help="Use ghproxy to download from github",
)
parser.add_argument("--install-python", type=bool, default=True, help="Install Python")
parser.add_argument("--clean", type=bool, default=False, help="Clean install directory")
parser.add_argument(
    "--mfa_version",
    type=str,
    default=DEFAULT_MFA_VERSION,
    help="MFA version to install",
)

args = parser.parse_args()

TEMP_DIR = Path("temp")

# clean install directory
if args.clean:
    print(f"开始清理目录：{args.install_dir}")
    if Path(args.install_dir).exists():
        shutil.rmtree(args.install_dir)


# setup python environment
def setup_python():
    print(f"开始设置Python环境")
    TEMP_DIR.mkdir(exist_ok=True)

    print(f"下载python并解压...")
    cmd = [
        "python",
        "tools/setup_full_python.py",
        "--tmp_dir",
        TEMP_DIR,
    ]

    try:
        subprocess.run(cmd, check=True)
    except (subprocess.CalledProcessError, OSError) as e:
        print(f"Failed to install Python: {e}")
        sys.exit(1)

    # install Python dependents
    print("开始安装python依赖")
    cmd = [
        "python",
        "-m",
        "pip",
        "install",
        "-r",
        "./requirements.txt",
        "-t",
        "install/python/Lib/",
    ]

    try:
        subprocess.run(cmd, check=True)
    except (subprocess.CalledProcessError, OSError) as e:
        print(f"Failed to install Python: {e}")
        sys.exit(1)


# install MFA
def download_mfa_release(version, archive_name, cache_path):
    print(f"开始下载：{archive_name}")
    url = f"https://github.com/SweetSmellFox/MFAAvalonia/releases/download/{version}/{archive_name}"
    if args.ghproxy:
        url = GHPROXY_URL + url

    print(f"Downloading from {url}...")
    download_file(url, cache_path)


# modified from download_deps.py of M9A
def detect_dotnet_platform_tag():
    """自动检测当前平台并返回对应的dotnet平台标签"""

    os_type = platform.system()
    os_arch = platform.machine()

    print(f"检测到操作系统: {os_type}, 架构: {os_arch}")

    if os_type == "Windows":

        # 在Windows ARM64环境中，platform.machine()可能错误返回AMD64
        # 我们需要检查处理器标识符来确定真实架构
        processor_identifier = os.environ.get("PROCESSOR_IDENTIFIER", "")

        # 检查是否为ARM64处理器
        if "ARMv8" in processor_identifier or "ARM64" in processor_identifier:
            print(f"检测到ARM64处理器: {processor_identifier}")
            os_arch = "ARM64"

        # 映射platform.machine()到dotnet的平台标签
        arch_mapping = {
            "AMD64": "win-x64",
            "x86_64": "win-x64",
            "ARM64": "win-arm64",
            "aarch64": "win-arm64",
        }

        platform_tag = arch_mapping.get(os_arch, f"win-{os_arch.lower()}")

    elif os_type == "Darwin":  # macOS
        # 映射platform.machine()到dotnet的平台标签
        arch_mapping = {
            "x86_64": "osx-x64",
            "arm64": "osx-arm64",
            "aarch64": "osx-arm64",
        }

        platform_tag = arch_mapping.get(os_arch, f"osx-{os_arch.lower()}")

    elif os_type == "Linux":
        # 映射platform.machine()到dotnet的平台标签
        arch_mapping = {
            "x86_64": "linux-x64",
            "aarch64": "linux-arm64",
            "arm64": "linux-arm64",
        }

        platform_tag = arch_mapping.get(os_arch, f"linux-{os_arch.lower()}")

    else:
        raise ValueError(f"不支持的操作系统: {os_type}")

    print(f"使用平台标签: {platform_tag}")
    return platform_tag


def install_mfa():
    arch = detect_dotnet_platform_tag()

    if args.mfa_version:
        version = args.mfa_version
    else:
        print("尝试获取MFA版本信息")
        RELEASE_API = "https://api.github.com/repos/SweetSmellFox/MFAAvalonia/releases"
        response = request.urlopen(RELEASE_API)
        if response.status != 200:
            if response.status == 403:
                print("Rate limit exceeded")
                print(
                    "Please check the proxy settings or use tag argument to install specific version"
                )
                sys.exit(1)
            print(f"Failed to get release info: {response.status}")
            sys.exit(1)

        release_info = json.loads(response.read())
        if args.pre_release:
            pass
        else:
            release_info = [
                release for release in release_info if not release["prerelease"]
            ]

        release_info = release_info[0]
        version = release_info["tag_name"]

    archive_name = f"MFAAvalonia-{version}-{arch}.zip"
    cache_path = TEMP_DIR / archive_name
    if not cache_path.exists():
        download_mfa_release(version, archive_name, cache_path)
    else:
        print(f"MFAAvalonia-{version}-{arch}.zip already exists.")
        size = cache_path.stat().st_size
        MB = 1024 * 1024
        if size < 50 * MB:
            print(f"文件大小为：{size / 1024 / 1024}MB")
            print("文件大小小于50MB，可能下载不完整，重新下载...")
            cache_path.unlink()
            download_mfa_release(version, archive_name, cache_path)
            size = cache_path.stat().st_size
            MB = 1024 * 1024
            if size < 50 * MB:
                print(f"文件大小为：{size / 1024 / 1024}MB")
                print("文件大小仍然小于50MB，下载失败，退出安装")
                sys.exit(1)

    with ZipFile(cache_path, "r") as zip_ref:
        zip_ref.extractall(args.install_dir)


def main():
    os_name = platform.system().lower()
    arch = platform.machine().lower()
    os_mapping = {
        "windows": "win",
        "darwin": "macos",
        "linux": "linux",
    }
    os_name = os_mapping.get(os_name, os_name)
    arch_mapping = {
        "amd64": "x86_64",
        "x86_64": "x86_64",
        "aarch64": "aarch64",
        "arm64": "aarch64",
    }
    arch = arch_mapping.get(arch, arch)

    print("开始本地构建流程")
    print("设置Python环境...")
    setup_python()
    print("MFAA环境")
    install_mfa()
    print("安装MaaFramework...")
    install_maafw(os_name, arch)
    print("安装资源文件...")
    install_resource("v0.0.0")
    print("安装Agent...")
    install_agent(os_name)
    print("本地测试包已于install文件夹内安装完成!")


if __name__ == "__main__":
    main()
