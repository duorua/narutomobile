#!/usr/bin/env python3
"""Bypass the MuMu SDK crash in MFAAvalonia 2.16.2 / MaaFramework 5.13.0.

Close MFAAvalonia before running. Backups contain the exact original profiles;
restore them by copying them over config/instances with MFAAvalonia closed.
"""

import argparse
import codecs
import json
from datetime import datetime
from pathlib import Path
from uuid import uuid4

OVERRIDES = {"AdbControlScreenCapType": "RawWithGzip", "AdbControlInputType": "Maatouch"}


def repair_instances(install_dir: Path) -> list[tuple[Path, Path]]:
    """Validate all profiles, back up originals, then update only MuMu ADB profiles."""
    instances = install_dir / "config" / "instances"
    if not instances.is_dir():
        raise FileNotFoundError(f"MFA instance directory not found: {instances}")

    planned: list[tuple[Path, bytes, bytes]] = []
    for path in sorted(instances.glob("*.json")):
        original = path.read_bytes()
        data = json.loads(original)
        if not isinstance(data, dict):
            raise ValueError(f"Profile must be a JSON object: {path}")
        if data.get("CurrentController") != 2:
            continue
        device = data.get("AdbDevice")
        if not isinstance(device, dict):
            raise ValueError(f"ADB profile has no device object: {path}")
        config = device.get("Config") or {}
        if isinstance(config, str):
            config = json.loads(config)
        if not isinstance(config, dict):
            raise ValueError(f"ADB device config must be an object: {path}")
        extras = config.get("extras", {})
        is_mumu = "mumu" in str(device.get("Name", "")).casefold() or (isinstance(extras, dict) and "mumu" in extras)
        if not is_mumu or all(data.get(key) == value for key, value in OVERRIDES.items()):
            continue
        data.update(OVERRIDES)
        newline = "\r\n" if b"\r\n" in original else "\n"
        content = (json.dumps(data, ensure_ascii=False, indent=2) + "\n").replace("\n", newline)
        encoding = "utf-8-sig" if original.startswith(codecs.BOM_UTF8) else "utf-8"
        planned.append((path, original, content.encode(encoding)))

    if not planned:
        return []
    stamp = datetime.now().astimezone().strftime("%Y%m%d-%H%M%S-%f")
    backup_dir = install_dir / "config" / "backups" / f"mumu-adb-{stamp}-{uuid4().hex[:8]}"
    backup_dir.mkdir(parents=True)
    changes = []
    # Back up every original before changing the first profile.
    for path, original, _ in planned:
        backup = backup_dir / path.name
        backup.write_bytes(original)
        changes.append((path, backup))
    for path, original, content in planned:
        if path.read_bytes() != original:
            raise RuntimeError(f"Profile changed during repair; close MFAAvalonia and retry: {path}")
        staged = path.with_name(f"{path.name}.{uuid4().hex}.tmp")
        with staged.open("xb") as output:
            output.write(content)
        staged.replace(path)
    return changes


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("install_dir", type=Path, help="MFA installation directory (close MFAAvalonia first)")
    args = parser.parse_args()
    changes = repair_instances(args.install_dir)
    for path, backup in changes:
        print(f"Repaired: {path}\nBackup:   {backup}")
    if not changes:
        print("No MuMu ADB profiles need changes.")


if __name__ == "__main__":
    main()
