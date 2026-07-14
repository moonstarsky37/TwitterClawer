"""章節目錄 manifest：閱讀網站的資料來源＋修復依據（進版控）。"""

import json
from pathlib import Path

_PHOTO_EXTENSIONS = {"jpg", "jpeg", "png", "webp"}


def _download_url(page: dict) -> str | None:
    """照片可由 pbs.twimg.com 直接補下載；影片/GIF 走 gallery-dl 重抓。"""
    if page["extension"].lower() in _PHOTO_EXTENSIONS and page.get("remote"):
        return (
            f'https://pbs.twimg.com/media/{page["remote"]}'
            f'?format={page["extension"]}&name=orig'
        )
    return None


def build_manifest(episodes: list[dict], artist: str) -> dict:
    out_episodes = []
    for ep in episodes:
        out_pages = [{**page, "url": _download_url(page)} for page in ep["pages"]]
        out_episodes.append({**ep, "pages": out_pages})
    return {"artist": artist, "episodes": out_episodes}


def merge_manifests(old: dict, new: dict) -> dict:
    """新資料優先，但舊 manifest 獨有的話與頁保留（sidecar 遺失時不掉資料）。"""
    old_eps = {ep["id"]: ep for ep in old["episodes"]}
    merged: dict[str, dict] = {}
    for ep_id, old_ep in old_eps.items():
        merged[ep_id] = old_ep
    for new_ep in new["episodes"]:
        old_ep = old_eps.get(new_ep["id"])
        if old_ep is None:
            merged[new_ep["id"]] = new_ep
            continue
        pages = {(p["tweet_id"], p["num"]): p for p in old_ep["pages"]}
        pages.update({(p["tweet_id"], p["num"]): p for p in new_ep["pages"]})
        ordered = sorted(pages.values(), key=lambda p: (p["date"], p["tweet_id"], p["num"]))
        merged[new_ep["id"]] = {**new_ep, "pages": ordered}
    episodes = sorted(merged.values(), key=lambda ep: ep["date"], reverse=True)
    return {**new, "episodes": episodes}


def save_manifest(manifest: dict, target: Path) -> None:
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(
        json.dumps(manifest, ensure_ascii=False, indent=1), encoding="utf-8"
    )


def load_manifest(source: Path) -> dict:
    return json.loads(source.read_text(encoding="utf-8"))
