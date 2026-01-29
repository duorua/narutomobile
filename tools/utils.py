from pathlib import Path


def get_maafw_version():
    self_path = Path(__file__)
    requirements_path = self_path.parent.parent / "requirements.txt"

    with open(requirements_path, "r") as f:
        for line in f:
            if "maafw" in line:
                return line.split("==")[1].strip()

    raise ValueError(f"MaaFramework not found in {requirements_path}")
