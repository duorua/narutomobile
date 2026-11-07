#!/usr/bin/env python3
"""
下载Python依赖的脚本
"""

import argparse
import os
import re
import subprocess
import sys
import tempfile
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")  # type: ignore


# 默认排除的包
# --exclude 会在此基础上追加
DEFAULT_EXCLUDES: list[str] = [
    # 测试
    "pytest",
    "iniconfig",
    "pluggy",
    "pygments",
    "packaging",
    # 类型检查
    "pyright",
    "nodeenv",
    "typing-extensions",
    # 格式化
    "ruff",
    # 安装工具
    "pip",
]


def canonicalize_name(name: str) -> str:
    """PEP 503 包名规范化:Foo_Bar.Baz -> foo-bar-baz(全小写)"""
    return re.sub(r"[-_.]+", "-", name).lower()


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


def filter_requirements(req_path: Path, excludes: set[str]) -> tuple[str, list[str]]:
    """
    读取 requirements.txt,过滤掉 exclude 中的包。
    不支持 -r 引用
    """
    if not req_path.exists():
        raise FileNotFoundError(f"{req_path} 不存在")

    lines = req_path.read_text(encoding="utf-8").splitlines(keepends=True)
    out: list[str] = []
    removed: list[str] = []
    skip_hash_continuation = False

    for line in lines:
        stripped = line.strip()

        # 上一行被排除后,紧随其后的 --hash 续行一并跳过
        if skip_hash_continuation and stripped.startswith("--hash"):
            continue
        skip_hash_continuation = False

        # 空行、注释、pip 保留
        if not stripped or stripped.startswith("#") or stripped.startswith("-"):
            out.append(line)
            continue

        m = re.match(r"^\s*([A-Za-z0-9][A-Za-z0-9._-]*)", line)
        if not m:
            out.append(line)
            continue

        name = canonicalize_name(m.group(1))
        if name in excludes:
            removed.append(name)
            print(f"排除依赖: {name}  ({stripped[:100]})")
            # 如果这一行是以反斜杠续行,后续 --hash 行要跳过
            skip_hash_continuation = stripped.endswith("\\")
            continue

        out.append(line)

    return "".join(out), removed


def download_dependencies(deps_dir, platform_tag, excludes: set[str]):
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
        filtered, removed = filter_requirements(requirements_file, excludes)
        print(f"过滤后共排除 {len(removed)} 个包: {removed or '无'}")

        # 写临时 requirements 文件
        fd, temp_req = tempfile.mkstemp(suffix=".txt", prefix="requirements-filtered-")
        try:
            # 使用 --platform 可以指定下载特定平台的包
            # 但是必须附带 --no-deps,而且无法自动解析依赖
            # 所以本项目使用 uv 进行依赖管理并自动生成 requirements.txt
            # uv pip compile --output-file=requirements.txt pyproject.toml
            with os.fdopen(fd, "w", encoding="utf-8") as f:
                f.write(filtered)

            cmd_fallback = [
                sys.executable,
                "-m",
                "pip",
                "install",
                "-r",
                temp_req,
                "--platform",
                str(platform_tag),
                "--no-deps",
                "--target",
                str(deps_path),
            ]

            print(f"执行下载命令: {' '.join(cmd_fallback)}")
            result = subprocess.run(cmd_fallback, check=True, capture_output=True, text=True)
            print(result.stdout)

            if result.stderr:
                print("警告信息:")
                print(result.stderr)
        finally:
            try:
                os.unlink(temp_req)
            except OSError:
                pass

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
    except FileNotFoundError as e:
        print(f"错误: {e}")
        return False


def main():
    parser = argparse.ArgumentParser(description="下载Python依赖到deps目录")
    parser.add_argument("--deps-dir", default="deps", help="依赖下载目录 (默认: deps)")
    parser.add_argument("--os", help="下载的系统")
    parser.add_argument("--arch", help="下载的架构")
    parser.add_argument(
        "--exclude",
        action="append",
        default=[],
        help="要排除的包名,可多次指定,也可用逗号分隔,例如 --exclude torch,torchvision",
    )
    parser.add_argument(
        "--no-default-excludes",
        action="store_true",
        help="不使用脚本内 DEFAULT_EXCLUDES 默认排除列表",
    )

    args = parser.parse_args()

    # 展开 --exclude 的逗号分隔
    cli_excludes: list[str] = []
    for item in args.exclude:
        cli_excludes.extend(x.strip() for x in item.split(",") if x.strip())

    base_excludes = [] if args.no_default_excludes else list(DEFAULT_EXCLUDES)
    all_excludes = {canonicalize_name(x) for x in base_excludes + cli_excludes}

    try:
        platform_tag = get_platform_tag(args.os, args.arch)
        success = download_dependencies(args.deps_dir, platform_tag, all_excludes)

        if success:
            print("依赖下载成功")
            sys.exit(0)
        else:
            print("依赖下载失败")
            sys.exit(1)

    except Exception as e:
        print(f"脚本执行失败: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
