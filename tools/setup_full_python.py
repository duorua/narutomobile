from pathlib import Path
import argparse
from zipfile import ZipFile
from urllib import request
from tqdm import tqdm

default_version = "3.12.9"
default_arch = "amd64"
default_tmp_dir = "tmp"
default_install_path = "install"
default_is_embed = False


def get_args():
    parser = argparse.ArgumentParser(description="Download Python embeddable package.")
    parser.add_argument("--version", default=default_version, help="Python version")
    parser.add_argument(
        "--arch", default=default_arch, help="Architecture (amd64 or win32)"
    )
    parser.add_argument(
        "--tmp_dir", default=default_tmp_dir, help="Temporary directory"
    )
    parser.add_argument(
        "--install_path", default=default_install_path, help="Install directory"
    )
    parser.add_argument(
        "--is_embed",
        type=bool,
        default=default_is_embed,
        help="Download embeddable package",
    )
    return parser.parse_args()


def download_file(url, dest_path, chunk_size=8192):
    with request.urlopen(url) as response, open(dest_path, "wb") as out_file:
        # 获取文件大小（如果可用）
        total_size = int(response.headers.get("Content-Length", 0))

        # 创建进度条
        with tqdm(
            total=total_size, unit="B", unit_scale=True, desc="Downloading"
        ) as pbar:
            downloaded = 0
            while True:
                chunk = response.read(chunk_size)
                if not chunk:
                    break
                out_file.write(chunk)
                downloaded += len(chunk)
                pbar.update(len(chunk))


def main():
    args = get_args()
    tmp_path = Path(args.tmp_dir)
    install_path = Path(args.install_path)
    version = args.version
    arch = args.arch
    is_embed = args.is_embed

    if is_embed:
        python_embed_zip_path = tmp_path / f"python-{version}-embed-{arch}.zip"
        python_embed_url = f"https://mirrors.huaweicloud.com/python/{version}/python-{version}-embed-{arch}.zip"
    else:
        python_embed_zip_path = tmp_path / f"python-{version}-{arch}.zip"
        python_embed_url = f"https://mirrors.huaweicloud.com/python/{version}/python-{version}-{arch}.zip"

    if not python_embed_zip_path.exists():
        print(f"Downloading Python embed zip from {python_embed_url}...")
        download_file(python_embed_url, python_embed_zip_path)
        print("Download completed.")
    else:
        print("Python embed zip already exists.")

    with ZipFile(python_embed_zip_path, "r") as zip_ref:
        zip_ref.extractall(install_path / "python")


if __name__ == "__main__":
    main()
