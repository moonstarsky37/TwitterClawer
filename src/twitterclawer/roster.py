"""追蹤清單：artists.json（進版控）。"""

import json
import re
from pathlib import Path

from . import paths

# x.com / twitter.com 網址、@handle、裸 handle 皆可。
# handle 會拼進 data/<handle>/ 路徑：白名單字元擋掉路徑穿越。
_HANDLE = re.compile(r"^[A-Za-z0-9_]{1,15}$")

# X 的保留路徑 + Windows 裝置名（data/CON/ 會建立失敗）
_RESERVED = {
    "home", "i", "explore", "messages", "notifications", "settings",
    "search", "compose", "intent", "login", "logout", "about",
    "con", "prn", "aux", "nul",
    *(f"com{n}" for n in range(1, 10)),
    *(f"lpt{n}" for n in range(1, 10)),
}


def parse_handle(raw: str) -> str:
    s = raw.strip()
    s = re.sub(r"^https?://", "", s)
    if s.startswith(("x.com/", "twitter.com/", "www.x.com/", "www.twitter.com/")):
        s = s.split("/", 1)[1]
        s = s.split("/", 1)[0]
    s = s.split("?", 1)[0].lstrip("@").strip()
    if not _HANDLE.match(s) or s.casefold() in _RESERVED:
        raise ValueError(f"無法解析作家 handle：{raw!r}")
    return s


def load_roster(source: Path | None = None) -> list[str]:
    source = source or paths.ARTISTS_JSON
    if not source.exists():
        return []
    data = json.loads(source.read_text(encoding="utf-8"))
    if not isinstance(data, list) or not all(isinstance(h, str) for h in data):
        raise ValueError(f"{source} 格式錯誤：應為 handle 字串陣列")
    return data


def add_artist(raw: str, target: Path | None = None) -> str:
    target = target or paths.ARTISTS_JSON
    handle = parse_handle(raw)
    roster = load_roster(target)
    if handle.casefold() not in {h.casefold() for h in roster}:
        roster.append(handle)
        target.write_text(
            json.dumps(roster, ensure_ascii=False, indent=1), encoding="utf-8"
        )
    return handle
