"""專案路徑。專案以 editable 模式安裝，__file__ 位於 src/ 之下。

v2：多作家——所有作家相關路徑都是以 handle 為參數的函式，
作家名只存在於 artists.json，不寫死在程式碼。
"""

from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]

DATA_DIR = PROJECT_ROOT / "data"
SITES_DIR = PROJECT_ROOT / "sites"
INDEX_HTML = PROJECT_ROOT / "index.html"
ARTISTS_JSON = PROJECT_ROOT / "artists.json"


def artist_dir(handle: str) -> Path:
    return DATA_DIR / handle


def raw_dir(handle: str) -> Path:
    return artist_dir(handle) / "raw"


def manifest_path(handle: str) -> Path:
    return artist_dir(handle) / "manifest.json"


def archive_db(handle: str) -> Path:
    return artist_dir(handle) / "archive.db"


def site_path(handle: str) -> Path:
    return SITES_DIR / f"{handle}.html"


def media_url(handle: str) -> str:
    return f"https://x.com/{handle}/media"
