from pathlib import Path
import zipfile
import sys


from urllib import request
from utils import get_maafw_version

sys.path.insert(0, Path(__file__).parent.__str__())
sys.path.insert(0, (Path(__file__).parent / "ci").__str__())

program_dir = Path(__file__).parent.parent

# 使用ghproxy加速下载
ghproxy = "https://gh-proxy.natsuu.top/"

# clash 的默认地址
local_proxy = "127.0.0.1:7890"


def download_with_proxy(download_url, dest_path, proxy_host, proxy_port):
    """使用本地代理下载文件"""
    proxy_url = f"{proxy_host}:{proxy_port}"
    print(f"尝试使用本地代理 {proxy_url} 进行下载...")
    try:
        # 设置代理处理器
        proxy_handler = request.ProxyHandler(
            {"http": f"http://{proxy_url}", "https": f"http://{proxy_url}"}
        )
        opener = request.build_opener(proxy_handler)

        # 创建带有User-Agent的请求
        req = request.Request(
            download_url,
            headers={
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/145.0.0.0 Safari/537.36 Edg/145.0.0.0"
            },
        )

        # 使用带代理的opener发送请求
        response = opener.open(req)

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

        return True  # 成功下载
    except Exception as e:
        print(f"本地代理下载失败: {e}")
        return False


def download_with_mirror(download_url, dest_path, mirror_base_url):
    """使用镜像站下载文件"""
    print("尝试使用镜像站下载...")
    mirror_url = mirror_base_url + download_url
    try:
        req = request.Request(
            mirror_url,
            headers={
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/145.0.0.0 Safari/537.36 Edg/145.0.0.0"
            },
        )

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

        return True  # 成功下载
    except Exception as e:
        print(f"镜像站下载失败: {e}")
        return False


def download_direct(download_url, dest_path):
    """直接下载文件"""
    print("尝试直接下载...")
    try:
        req = request.Request(
            download_url,
            headers={
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/145.0.0.0 Safari/537.36 Edg/145.0.0.0"
            },
        )

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

        return True  # 成功下载
    except Exception as e:
        print(f"直接下载失败: {e}")
        return False


def download_with_proxy_or_mirror(download_url, dest_path):
    """尝试使用本地代理下载，失败后回退到镜像站或直接下载"""
    # 首先尝试使用本地代理
    proxy_parts = local_proxy.split(":")
    if download_with_proxy(download_url, dest_path, proxy_parts[0], proxy_parts[1]):
        return True

    # 如果代理下载失败，则尝试使用镜像站
    if download_with_mirror(download_url, dest_path, ghproxy):
        return True

    # 如果镜像站也失败，则尝试直接下载
    if download_direct(download_url, dest_path):
        return True

    # 所有方式都失败
    print("所有下载方式都失败了")
    return False


def main():
    version = "v" + get_maafw_version()
    print("MaaFramework版本：" + version)

    # https://github.com/MaaXYZ/MaaFramework/releases/download/v5.1.4/MAA-win-x86_64-v5.1.4.zip

    download_url = (
        "https://github.com/MaaXYZ/MaaFramework/releases/download/"
        + version
        + f"/MAA-win-x86_64-{version}.zip"
    )

    print(f"下载URL: {download_url}")

    dest_path = f"temp/MAA-win-x86_64-{version}.zip"

    print(f"Downloading from {download_url} to {dest_path}")

    # 尝试下载，优先使用本地代理，然后是镜像站，最后是直接下载
    success = download_with_proxy_or_mirror(download_url, dest_path)

    if not success:
        print("maafw下载失败，请阅读开发文档。手动下载并解压maafw到deps文件夹下")
        sys.exit(1)

    print("Download completed.")

    print(f"Extracting {dest_path}...")
    with zipfile.ZipFile(dest_path, "r") as zip_ref:
        extract_path = program_dir / "deps"
        # 解压时跳过schema.json文件
        for member in zip_ref.infolist():
            if member.filename.endswith("schema.json"):
                print(f"跳过文件: {member.filename}")
                continue
            zip_ref.extract(member, extract_path)
        print(f"Extracted to {extract_path}.")

    Path(dest_path).unlink()  # Remove the zip file after extraction


if __name__ == "__main__":
    main()
