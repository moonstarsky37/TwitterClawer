"""指令入口：uv run twitterclawer <add|full|update|repair|build> [--artist h] [--profile p]。"""

import subprocess
import sys

from . import downloader, paths
from .manifest import build_manifest, load_manifest, merge_manifests, save_manifest
from .organizer import build_episodes, load_records
from .repair import _default_fetcher, repair
from .roster import add_artist, load_roster, parse_handle
from .sitegen import write_overview, write_site

_USAGE = """\
用法：uv run twitterclawer <指令> [--artist handle] [--profile Firefox設定檔]

  add <handle|網址>  加入追蹤清單並全量下載該作家
  full               全量下載（預設清單全體；可中斷，重跑續抓）
  update             增量下載新作品＋更新網站
  repair             依 manifest 補回缺失檔案
  build              只重建 manifest 與網頁（不下載）

  --artist   只處理清單中的某一位作家
  --profile  x.com 登入不在預設 Firefox 設定檔時指定
"""

_fetch_bytes = _default_fetcher


def _build_one(artist: str) -> int:
    raw = paths.raw_dir(artist)
    mpath = paths.manifest_path(artist)
    records = load_records(raw) if raw.exists() else []
    old = load_manifest(mpath) if mpath.exists() else None

    if records:
        new = build_manifest(build_episodes(records, artist), artist)
        manifest = merge_manifests(old, new) if old else new
    elif old is not None:
        print(f"[{artist}] data 沒有 metadata，改用版控的 manifest 重建網頁。")
        manifest = old
    else:
        print(f"[{artist}] 沒有任何資料，先跑 full 下載。")
        return 1

    save_manifest(manifest, mpath)
    write_site(manifest, paths.site_path(artist))
    pages = sum(len(ep["pages"]) for ep in manifest["episodes"])
    print(f"[{artist}] 整理完成：{len(manifest['episodes'])} 話、{pages} 頁")
    return 0


def _write_overview() -> None:
    entries = []
    for artist in load_roster():
        mpath = paths.manifest_path(artist)
        if not mpath.exists():
            continue
        try:
            manifest = load_manifest(mpath)
        except ValueError as exc:  # 單一壞 manifest 不可毀掉整份總覽
            print(f"[{artist}] manifest 損毀，總覽先跳過：{exc}")
            continue
        eps = manifest["episodes"]
        entries.append(
            {
                "artist": artist,
                "episodes": len(eps),
                "pages": sum(len(ep["pages"]) for ep in eps),
                "updated": eps[0]["date"].split(" ")[0] if eps else "-",
            }
        )
    write_overview(entries, paths.INDEX_HTML)
    print(f"總覽：{paths.INDEX_HTML}")


def _targets(artist_flag: str | None) -> list[str]:
    roster = load_roster()
    if artist_flag:
        try:
            handle = parse_handle(artist_flag)
        except ValueError as exc:
            print(exc)
            return []
        if handle.casefold() not in {h.casefold() for h in roster}:
            print(f"{handle} 不在追蹤清單裡——先用 add 加入。")
            return []
        return [handle]
    if not roster:
        print("追蹤清單是空的——雙擊 add-artist.bat 或跑 "
              "uv run twitterclawer add <網址>。")
    return roster


def _download_then_build(mode: str, artist_flag: str | None, profile: str | None) -> int:
    artists = _targets(artist_flag)
    if not artists:
        return 1
    worst = 0
    for artist in artists:
        try:
            code = downloader.run_download(mode, artist, firefox_profile=profile)
            if code != 0:
                # 更新模式的 --abort 提前中止會回 0；非 0 是真的失敗
                print(f"[{artist}] gallery-dl 失敗（結束碼 {code}），請檢查上方訊息")
                worst = 1
            worst = max(worst, _build_one(artist))
        except Exception as exc:  # noqa: BLE001 — 一位作家失敗不可拖垮其他人
            print(f"[{artist}] 處理失敗：{exc}")
            worst = 1
    _write_overview()
    _suggest_commit()
    return worst


def _repair_one(artist: str) -> int:
    mpath = paths.manifest_path(artist)
    if not mpath.exists():
        print(f"[{artist}] 沒有 manifest，先跑 full。")
        return 1
    manifest = load_manifest(mpath)
    paths.raw_dir(artist).mkdir(parents=True, exist_ok=True)
    repaired, refetch_ids, failed = repair(
        manifest, paths.raw_dir(artist), fetcher=_fetch_bytes
    )
    for name in repaired:
        print(f"[{artist}] 已補回：{name}")
    for tweet_id in refetch_ids:
        print(f"[{artist}] 影片/GIF 需重抓推文 {tweet_id} …")
        subprocess.run(downloader.build_tweet_command(artist, tweet_id))
    if failed:
        print(f"[{artist}] {len(failed)} 個檔案補下載失敗（可再跑一次）")
    if not repaired and not refetch_ids and not failed:
        print(f"[{artist}] 檔案完整，無需修復。")
    return max(_build_one(artist), 1 if failed else 0)


def _repair_all(artist_flag: str | None) -> int:
    artists = _targets(artist_flag)
    if not artists:
        return 1
    worst = 0
    for artist in artists:
        try:
            worst = max(worst, _repair_one(artist))
        except Exception as exc:  # noqa: BLE001 — 一位作家失敗不可拖垮其他人
            print(f"[{artist}] 修復失敗：{exc}")
            worst = 1
    _write_overview()
    _suggest_commit()
    return worst


def _build_all(artist_flag: str | None) -> int:
    artists = _targets(artist_flag)
    if not artists:
        return 1
    worst = 0
    for artist in artists:
        try:
            worst = max(worst, _build_one(artist))
        except Exception as exc:  # noqa: BLE001 — 一位作家失敗不可拖垮其他人
            print(f"[{artist}] 重建失敗：{exc}")
            worst = 1
    _write_overview()
    _suggest_commit()
    return worst


def _add(raw: str, profile: str | None) -> int:
    handle = add_artist(raw)
    print(f"已加入追蹤清單：{handle}，開始全量下載…")
    return _download_then_build("full", handle, profile)


def _suggest_commit() -> None:
    print("建議 commit（請自行執行）：")
    print('  git add -A && git commit -m "更新追蹤資料"')


def _parse(args: list[str]) -> tuple[str | None, str | None, str | None, str | None]:
    command = args[0] if args else None
    value = None
    if command == "add" and len(args) > 1 and not args[1].startswith("--"):
        value = args[1]

    def flag(name: str) -> str | None:
        if name in args:
            i = args.index(name)
            if i + 1 < len(args):
                return args[i + 1]
        return None

    return command, value, flag("--artist"), flag("--profile")


def main(argv: list[str] | None = None) -> int:
    args = sys.argv[1:] if argv is None else argv
    command, value, artist_flag, profile = _parse(args)
    if command == "add":
        if not value:
            # .bat 端保持純 ASCII（cmd 對 UTF-8 批次檔會亂碼），提問移到這裡
            try:
                value = input("作家網址或 handle（例 https://x.com/SomeArtist）：").strip()
            except EOFError:
                value = ""
        if not value:
            print(_USAGE)
            return 2
        return _add(value, profile)
    if command in ("full", "update"):
        return _download_then_build(command, artist_flag, profile)
    if command == "repair":
        return _repair_all(artist_flag)
    if command == "build":
        return _build_all(artist_flag)
    print(_USAGE)
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
