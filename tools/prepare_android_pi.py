#!/usr/bin/env python3
"""把仓库里的 assets + agent 合成 MaaFwApp 能 sync 的一份 PI 根。

interface.json 在 assets/，agent 在仓库根。Gradle 的 include 只能相对 assets 目录，
所以先摊到 Android/pi-root/：根上是 interface.json，旁边是 agent/。
"""

from __future__ import annotations

import shutil
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
DEST = REPO / "Android" / "pi-root"
IGNORE = shutil.ignore_patterns("__pycache__", "*.pyc", ".git")


def copy_tree(src: Path, dest: Path) -> None:
    if dest.exists():
        shutil.rmtree(dest)
    shutil.copytree(src, dest, ignore=IGNORE)


def main() -> int:
    assets = REPO / "assets"
    android_assets = assets / "android"

    if not (android_assets / "interface.json").is_file():
        print(f"missing {android_assets / 'interface.json'}", file=sys.stderr)
        return 1

    sys.path.insert(0, str(REPO / "tools" / "ci"))
    from configure import configure_ocr_model  # pyright: ignore[reportMissingImports]

    configure_ocr_model()

    if DEST.exists():
        shutil.rmtree(DEST)
    DEST.mkdir(parents=True)

    for child in assets.iterdir():
        if child.name == "android":
            continue
        target = DEST / child.name
        if child.is_dir():
            copy_tree(child, target)
        else:
            shutil.copy2(child, target)

    shutil.copy2(android_assets / "interface.json", DEST / "interface.json")

    copy_tree(REPO / "agent", DEST / "agent")

    for name in ("LICENSE", "CONTACT", "DISCLAIMER.md"):
        src = REPO / name
        if src.is_file():
            shutil.copy2(src, DEST / name)

    logo_ico = REPO / "docs" / "imgs" / "logo.ico"
    if logo_ico.is_file():
        (DEST / "resource").mkdir(exist_ok=True)
        shutil.copy2(logo_ico, DEST / "resource" / "logo.ico")

    logo_png = REPO / "docs" / "imgs" / "logo.png"
    if logo_png.is_file():
        dest_logo = DEST / "docs" / "imgs"
        dest_logo.mkdir(parents=True, exist_ok=True)
        shutil.copy2(logo_png, dest_logo / "logo.png")

    files = sum(1 for p in DEST.rglob("*") if p.is_file())
    print(f"{files} files -> {DEST}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
