import os
from pathlib import Path
import zipfile
import sys

from urllib import request

from utils import get_maafw_version

sys.path.insert(0, Path(__file__).parent.__str__())
sys.path.insert(0, (Path(__file__).parent / "ci").__str__())

program_dir = Path(__file__).parent

# 使用ghproxy加速下载
# 如果开了代理要将这行注释掉
ghproxy = "https://gh-proxy.natsuu.top/"


def main():
    version = "v" + get_maafw_version()
    print("MaaFramework版本：" + version)

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
    if "ghproxy" not in os.environ:
        print("尝试通过ghproxy加速下载")
        print("如果你已经开启了系统代理，请将第17行注释掉")
        download_url = ghproxy + download_url
    else:
        print("尝试直接下载")

    dest_path = "MAA-win-x86_64-" + version + ".zip"

    print(f"Downloading from {download_url} to {dest_path}")
    try:
        # 创建带有User-Agent的请求
        req = request.Request(
            download_url,
            headers={
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/145.0.0.0 Safari/537.36 Edg/145.0.0.0"
            },
        )
        # 使用urlopen发送请求并保存文件，同时显示下载进度
        with request.urlopen(req) as response:
            # 获取文件大小（如果可用）
            total_size = int(response.headers.get("Content-Length", 0))
            print(f"Total size: {total_size / 1024 / 1024:.2f} MB")

            with open(dest_path, "wb") as out_file:
                downloaded = 0
                chunk_size = 8192
                while True:
                    chunk = response.read(chunk_size)
                    if not chunk:
                        break
                    out_file.write(chunk)
                    downloaded += len(chunk)
                    # 使用 \r 动态更新显示，而不是添加新行
                    if total_size > 0:
                        percent = (downloaded / total_size) * 100
                        print(
                            f"\rDownloaded: {downloaded / 1024 / 1024:.2f}/{total_size / 1024 / 1024:.2f} MB ({percent:.1f}%)",
                            end="",
                            flush=True,
                        )
                    else:
                        print(
                            f"\rDownloaded: {downloaded / 1024 / 1024:.2f} MB",
                            end="",
                            flush=True,
                        )
                print()  # 下载完成后换行
    except Exception as e:
        print(f"Download failed: {e}")
        print("maafw下载失败，请阅读开发文档。手动下载并解压maafw到deps文件夹下")
        sys.exit(1)

    print("Download completed.")

    print(f"Extracting {dest_path}...")
    with zipfile.ZipFile(dest_path, "r") as zip_ref:
        extract_path = program_dir / "deps"
        zip_ref.extractall(extract_path)
        print(f"Extracted to {extract_path}.")

    Path(dest_path).unlink()  # Remove the zip file after extraction


if __name__ == "__main__":
    main()
