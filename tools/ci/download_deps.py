#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
下载Python依赖到deps目录的脚本
自动检测当前平台并下载对应架构的wheel文件
"""

import sys
import subprocess
import argparse
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")  # type: ignore


def get_platform_tag(os, arch):
    target = (os, arch)
    match target:
        case ("win", "x86_64"):
            platform_tag = "win_amd64"
        case ("win", "aarch64"):
            platform_tag = "win_arm64"
        case ("macos", "x86_64"):
            platform_tag = "macosx_13_0_x86_64"
        case ("macos", "aarch64"):
            platform_tag = "macosx_13_0_arm64"
        case ("linux", "x86_64"):
            platform_tag = "manylinux2014_x86_64"
        case ("linux", "aarch64"):
            platform_tag = "manylinux2014_aarch64"
        case _:
            print(f"不支持的操作系统或架构: {os}-{arch}")
            sys.exit(1)

    print(f"使用平台标签: {platform_tag}")
    return platform_tag


def download_dependencies(deps_dir, platform_tag):
    """下载依赖到指定目录"""
    # 创建deps目录
    deps_path = Path(deps_dir)
    deps_path.mkdir(parents=True, exist_ok=True)

    print(f"开始下载平台 {platform_tag} 的依赖到 {deps_dir}")

    # 从requirements.txt读取依赖
    requirements_file = Path("requirements.txt")
    if not requirements_file.exists():
        print("错误: requirements.txt 文件不存在")
        return False

    try:
        cmd_fallback = [
            sys.executable,
            "-m",
            "pip",
            "install",
            "-r",
            str(requirements_file),
            "--platform",
            str(platform_tag),
            "--no-deps",
            "--target",
            str(deps_path),
        ]

        print(f"执行下载命令: {' '.join(cmd_fallback)}")
        result = subprocess.run(
            cmd_fallback, check=True, capture_output=True, text=True
        )
        print(result.stdout)

        if result.stderr:
            print("警告信息:")
            print(result.stderr)

        # 列出下载的文件
        whl_files = list(deps_path.glob("*.whl"))
        print(f"\n下载的wheel文件 ({len(whl_files)} 个):")
        for whl_file in whl_files:
            print(f"  {whl_file.name}")

        print(f"依赖已经下载到目录: {deps_path}")
        return True

    except subprocess.CalledProcessError as e2:
        print(f"依赖下载失败: {e2}")
        if e2.stdout:
            print("stdout:", e2.stdout)
        if e2.stderr:
            print("stderr:", e2.stderr)
        return False


def main():
    parser = argparse.ArgumentParser(description="下载Python依赖到deps目录")
    parser.add_argument("--deps-dir", default="deps", help="依赖下载目录 (默认: deps)")
    parser.add_argument("--os", help="下载的系统")
    parser.add_argument("--arch", help="下载的架构")

    args = parser.parse_args()

    try:
        platform_tag = get_platform_tag(args.os, args.arch)

        # 下载依赖
        success = download_dependencies(args.deps_dir, platform_tag)

        if success:
            print("✅ 依赖下载成功")
            sys.exit(0)
        else:
            print("❌ 依赖下载失败")
            sys.exit(1)

    except Exception as e:
        print(f"❌ 脚本执行失败: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
