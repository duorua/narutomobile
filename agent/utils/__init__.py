import json
from pathlib import Path
from base64 import b64decode
from datetime import datetime


def get_format_timestamp():
    now = datetime.now()
    date = now.strftime("%Y.%m.%d")
    time = now.strftime("%H.%M.%S")
    milliseconds = f"{now.microsecond // 1000:03d}"

    return f"{date}-{time}.{milliseconds}"


bdc = lambda s: b64decode(s).decode("utf-8")  # noqa: E731
jL = json.load
jD = json.dump
root = Path(__file__).resolve().parent.parent.parent
