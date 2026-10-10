#!/usr/bin/env python3
"""Build the Android APK using the same steps as the GitHub Actions workflows."""

from __future__ import annotations

import argparse
import os
import subprocess
import sys
from collections.abc import Sequence
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
APP_DIR = REPO / "Android" / "MaaFwApp"
MAAFW_TAG = "v5.13.0"
ABIS = ("arm64-v8a", "x86_64")


def run(command: Sequence[str], *, cwd: Path = REPO) -> None:
    print(f"\n==> {' '.join(str(item) for item in command)}", flush=True)
    subprocess.run(command, cwd=cwd, check=True)


def ensure_submodule() -> None:
    required = (
        APP_DIR / "settings.gradle.kts",
        APP_DIR / "gradlew.bat" if sys.platform == "win32" else APP_DIR / "gradlew",
        APP_DIR / "scripts" / "setup_maa_framework.py",
    )
    if all(path.exists() for path in required):
        return

    print("\n==> Initializing Android/MaaFwApp submodule", flush=True)
    run(("git", "submodule", "update", "--init", "--", "Android/MaaFwApp"))


def find_android_sdk() -> Path | None:
    env_sdk = os.environ.get("ANDROID_HOME") or os.environ.get("ANDROID_SDK_ROOT")
    if env_sdk:
        return Path(env_sdk)

    if sys.platform == "win32":
        local_app_data = os.environ.get("LOCALAPPDATA")
        if local_app_data:
            return Path(local_app_data) / "Android" / "Sdk"
    elif home := os.environ.get("HOME"):
        return Path(home) / "Android" / "Sdk"
    return None


def properties_escape(value: str) -> str:
    return value.replace("\\", "\\\\").replace(":", "\\:")


def properties_unescape(value: str) -> str:
    result: list[str] = []
    escaped = False
    for char in value:
        if escaped:
            result.append(char)
            escaped = False
        elif char == "\\":
            escaped = True
        else:
            result.append(char)
    return "".join(result)


def write_local_properties(abi: str | None, *, release: bool = False) -> None:
    path = APP_DIR / "local.properties"
    key = "build.releaseAbi" if release else "build.debugAbi"
    properties: dict[str, str] = {}
    if path.exists():
        for line in path.read_text(encoding="utf-8").splitlines():
            key_, separator, value = line.partition("=")
            if separator and not line.lstrip().startswith("#"):
                properties[key_.strip()] = properties_unescape(value)

    if not properties.get("sdk.dir"):
        sdk = find_android_sdk()
        if sdk is None:
            raise SystemExit(
                "Android SDK was not found. Set ANDROID_HOME or ANDROID_SDK_ROOT, "
                "or add sdk.dir to Android/MaaFwApp/local.properties."
            )
        properties["sdk.dir"] = str(sdk)

    properties["pi.profile"] = "../profile.yaml"
    if abi is None:
        properties.pop("build.debugAbi", None)
        properties.pop("build.releaseAbi", None)
    else:
        properties[key] = abi

    lines = [f"{k}={properties_escape(v)}" for k, v in properties.items()]
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def prepare_inputs(variant: str, abis: Sequence[str], skip_setup: bool) -> None:
    if skip_setup:
        return

    run((sys.executable, str(REPO / "tools" / "prepare_android_pi.py")))

    setup_args = [
        sys.executable,
        str(APP_DIR / "scripts" / "setup_maa_framework.py"),
        "--tag",
        MAAFW_TAG,
        "--abi",
        abis[0],
    ]
    if len(abis) > 1:
        setup_args.extend(["--abi", abis[1]])
    run(setup_args)

    bundle_args = [
        sys.executable,
        str(APP_DIR / "scripts" / "build_agent_bundle.py"),
        "--out",
        str(REPO / "Android" / "agent-dist"),
        "--requirements",
        str(REPO / "requirements.txt"),
        "--exclude",
        "pillow",
        "--exclude",
        "opencv-python",
        "--exclude",
        "win32-setctime",
        "--exclude",
        "colorama",
        "--exclude",
        "jeepney",
        "--require",
        "pillow==11.0.0",
        "--extra-index-url",
        "https://chaquo.com/pypi-13.1/",
    ]
    for abi in abis:
        bundle_args.extend(["--abi", abi])
    run(bundle_args)


def run_gradle(variant: str, clean: bool) -> list[Path]:
    wrapper = APP_DIR / "gradlew.bat" if sys.platform == "win32" else APP_DIR / "gradlew"
    command: list[str]
    if sys.platform == "win32":
        command = [str(wrapper)]
    else:
        command = ["sh", str(wrapper)]

    command.append("--no-daemon")
    if clean:
        command.append(":app:clean")
    command.append(f":app:assemble{variant.capitalize()}")
    run(command, cwd=APP_DIR)

    apk_dir = APP_DIR / "app" / "build" / "outputs" / "apk" / variant
    apks = sorted(apk_dir.glob("*.apk"))
    if not apks:
        raise SystemExit(f"No APK was generated under {apk_dir}")
    return apks


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("variant", nargs="?", choices=("debug", "release"), default="debug")
    parser.add_argument("--abi", choices=(*ABIS, "all"), help="Default is arm64-v8a for debug and all for release")
    parser.add_argument(
        "--skip-setup",
        action="store_true",
        help="Skip PI, native library, and agent runtime preparation",
    )
    parser.add_argument("--clean", action="store_true", help="Run the Gradle clean task before assembling")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    if args.abi == "all":
        abis = ABIS
    else:
        abis = (args.abi,) if args.abi else ("arm64-v8a",) if args.variant == "debug" else ABIS

    if args.variant == "debug" and len(abis) > 1:
        raise SystemExit("The debug APK supports one ABI per build. Pass --abi arm64-v8a or --abi x86_64.")

    ensure_submodule()
    if args.variant == "debug":
        write_local_properties(abis[0])
    else:
        write_local_properties(abis[0] if len(abis) == 1 else None, release=True)
    prepare_inputs(args.variant, abis, args.skip_setup)
    apks = run_gradle(args.variant, args.clean)

    print("\nAPK generated:")
    for apk in apks:
        print(f"  {apk}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
