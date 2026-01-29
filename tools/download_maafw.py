from pathlib import Path
import zipfile
import sys

from urllib import request

from utils import get_maafw_version

sys.path.insert(0, Path(__file__).parent.__str__())
sys.path.insert(0, (Path(__file__).parent / "ci").__str__())

ghproxy = "https://gh-proxy.natsuu.top/"


def main():
    version = "v" + get_maafw_version()
    # https://github.com/MaaXYZ/MaaFramework/releases/download/v5.1.4/MAA-win-x86_64-v5.1.4.zip

    download_url = (
        "https://github.com/MaaXYZ/MaaFramework/releases/download/"
        + version
        + "/MAA-"
        + "win-x86_64"
        + "-"
        + version
        + ".zip"
    )
    download_url = ghproxy + download_url
    dest_path = "MAA-win-x86_64-" + version + ".zip"

    print(f"Downloading from {download_url} to {dest_path}")
    request.urlretrieve(download_url, dest_path)

    print("Download completed.")

    print(f"Extracting {dest_path}...")
    with zipfile.ZipFile(dest_path, "r") as zip_ref:
        extract_path = Path("deps")
        zip_ref.extractall(extract_path)
        print(f"Extracted to {extract_path}.")

    Path(dest_path).unlink()  # Remove the zip file after extraction


if __name__ == "__main__":
    main()
