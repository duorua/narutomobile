import json
from copy import deepcopy
from pathlib import Path

import pytest

from tools.repair_mumu_adb import repair_instances


def profile() -> dict:
    return {
        "InstanceName": "配置 1",
        "CurrentController": 2,
        "AdbDevice": {
            "Name": "MuMu安卓设备-MuMuPlayer v5+",
            "ScreencapMethods": 64,
            "InputMethods": 18446744073709551615,
            "Config": '{"extras":{"mumu":{"enable":true,"index":0}}}',
        },
        "TaskItems": [{"name": "任务", "option": [{"data": {"value": "保留"}}]}],
        "OtherSetting": {"enabled": False},
    }


def write_profile(root: Path, name: str, data: dict) -> Path:
    instances = root / "config" / "instances"
    instances.mkdir(parents=True, exist_ok=True)
    path = instances / name
    path.write_bytes((json.dumps(data, ensure_ascii=False, indent=2) + "\r\n").encode("utf-8-sig"))
    return path


@pytest.mark.parametrize("existing_capture", [None, "RawWithGzip", "EmulatorExtras"])
def test_repair_both_channels_and_preserve_other_settings(tmp_path, existing_capture):
    original = profile()
    if existing_capture:
        original["AdbControlScreenCapType"] = existing_capture
    path = write_profile(tmp_path, "default.json", original)
    original_bytes = path.read_bytes()

    changes = repair_instances(tmp_path)

    expected = deepcopy(original)
    expected["AdbControlScreenCapType"] = "RawWithGzip"
    expected["AdbControlInputType"] = "Maatouch"
    assert json.loads(path.read_bytes()) == expected
    assert len(changes) == 1
    repaired, backup = changes[0]
    assert repaired == path
    assert backup.read_bytes() == original_bytes
    assert backup.parent.parent == tmp_path / "config" / "backups"


def test_repeated_execution_does_not_rewrite_or_replace_backup(tmp_path):
    path = write_profile(tmp_path, "default.json", profile())
    original_bytes = path.read_bytes()
    changes = repair_instances(tmp_path)
    repaired_bytes = path.read_bytes()
    modified_at = path.stat().st_mtime_ns

    assert repair_instances(tmp_path) == []
    assert path.read_bytes() == repaired_bytes
    assert path.stat().st_mtime_ns == modified_at
    assert changes[0][1].read_bytes() == original_bytes
    assert len(list((tmp_path / "config" / "backups").iterdir())) == 1


def test_only_mumu_adb_profiles_are_changed(tmp_path):
    mumu = write_profile(tmp_path, "mumu.json", profile())
    other_adb = profile()
    other_adb["AdbDevice"]["Name"] = "Other emulator"
    other_adb["AdbDevice"]["Config"] = "{}"
    other_controller = profile()
    other_controller["CurrentController"] = 1
    untouched = [
        write_profile(tmp_path, "other_adb.json", other_adb),
        write_profile(tmp_path, "other_controller.json", other_controller),
    ]
    before = {path: path.read_bytes() for path in untouched}

    assert [path for path, _ in repair_instances(tmp_path)] == [mumu]
    assert all(path.read_bytes() == content for path, content in before.items())


def test_detect_mumu_extras_with_custom_device_name_and_repair_all_profiles(tmp_path):
    renamed = profile()
    renamed["AdbDevice"]["Name"] = "自定义名称"
    paths = [write_profile(tmp_path, name, renamed) for name in ["default.json", "second.json"]]
    assert {path for path, _ in repair_instances(tmp_path)} == set(paths)
    for path in paths:
        data = json.loads(path.read_bytes())
        assert data["AdbControlScreenCapType"] == "RawWithGzip"
        assert data["AdbControlInputType"] == "Maatouch"


@pytest.mark.parametrize("broken", [b"{invalid", b"[]", b'{"CurrentController":2,"AdbDevice":null}'])
def test_invalid_profile_aborts_before_writing_any_changes(tmp_path, broken):
    valid = write_profile(tmp_path, "a_valid.json", profile())
    before = valid.read_bytes()
    invalid = valid.with_name("z_invalid.json")
    invalid.write_bytes(broken)

    with pytest.raises(ValueError):
        repair_instances(tmp_path)

    assert valid.read_bytes() == before
    assert invalid.read_bytes() == broken
    assert not (tmp_path / "config" / "backups").exists()


def test_missing_installation_is_not_created(tmp_path):
    with pytest.raises(FileNotFoundError):
        repair_instances(tmp_path / "missing")
    assert not (tmp_path / "missing").exists()


def test_backup_failure_does_not_change_any_profile(tmp_path, monkeypatch):
    paths = [write_profile(tmp_path, name, profile()) for name in ["a.json", "b.json"]]
    originals = {path: path.read_bytes() for path in paths}
    write_bytes = Path.write_bytes

    def fail_second_backup(path, content):
        if "backups" in path.parts and path.name == "b.json":
            raise OSError("Simulated backup failure")
        return write_bytes(path, content)

    monkeypatch.setattr(Path, "write_bytes", fail_second_backup)
    with pytest.raises(OSError, match="backup failure"):
        repair_instances(tmp_path)
    assert all(path.read_bytes() == original for path, original in originals.items())
