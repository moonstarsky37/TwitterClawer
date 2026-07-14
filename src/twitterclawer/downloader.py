"""gallery-dl 指令組裝與執行。

只透過 --cookies-from-browser 唯讀 Firefox 的 session cookie，
不接觸密碼檔（logins.json / key4.db）。
"""

import subprocess
import sys

from . import paths

# 更新模式：連續 N 個檔案已在 archive 中即停止翻頁（作品由新到舊列出）
UPDATE_ABORT_AFTER = 30

FILENAME_FORMAT = "{tweet_id}_{num}.{extension}"


def _common_args(artist: str, browser: str) -> list[str]:
    return [
        "--cookies-from-browser",
        browser,
        "--write-metadata",
        "-D",
        str(paths.raw_dir(artist)),
        "-f",
        FILENAME_FORMAT,
        # 圖片解析度：優先 orig 原始檔，缺少時退回 large/medium
        "-o",
        'size=["orig", "large", "medium"]',
    ]


def build_command(
    mode: str, artist: str, firefox_profile: str | None = None
) -> list[str]:
    if mode not in ("full", "update"):
        raise ValueError(f"unknown mode: {mode!r}")

    browser = "firefox" if firefox_profile is None else f"firefox:{firefox_profile}"
    cmd = [sys.executable, "-m", "gallery_dl"]
    cmd += _common_args(artist, browser)
    cmd += [
        "--download-archive",
        str(paths.archive_db(artist)),
        # 保守速率，降低觸發 X 限速的機率
        "--sleep-request",
        "1.0-2.0",
    ]
    if mode == "update":
        cmd += ["--abort", str(UPDATE_ABORT_AFTER)]
    cmd.append(paths.media_url(artist))
    return cmd


def build_tweet_command(artist: str, tweet_id: int) -> list[str]:
    """修復用：重抓單一推文的媒體。不掛 archive，否則已記錄的檔案會被跳過。"""
    cmd = [sys.executable, "-m", "gallery_dl"]
    cmd += _common_args(artist, "firefox")
    cmd.append(f"https://x.com/{artist}/status/{tweet_id}")
    return cmd


def run_download(
    mode: str,
    artist: str,
    firefox_profile: str | None = None,
    runner=subprocess.run,
) -> int:
    paths.raw_dir(artist).mkdir(parents=True, exist_ok=True)
    cmd = build_command(mode, artist, firefox_profile=firefox_profile)
    return runner(cmd).returncode
