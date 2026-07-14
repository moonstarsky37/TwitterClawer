"""比對 manifest 與實際檔案，補回缺失的圖檔。

照片：pbs.twimg.com 網址公開可取，直接 HTTP 下載（不需 cookie）。
影片/GIF：無直接網址，回報 tweet_id 交由 gallery-dl 重抓。
"""

from pathlib import Path

import requests


def _default_fetcher(url: str) -> bytes:
    resp = requests.get(url, timeout=30)
    resp.raise_for_status()
    return resp.content


def _all_pages(manifest: dict):
    for ep in manifest["episodes"]:
        yield from ep["pages"]


def find_missing(manifest: dict, raw_dir: Path) -> list[dict]:
    return [p for p in _all_pages(manifest) if not (raw_dir / p["file"]).exists()]


def repair(
    manifest: dict, raw_dir: Path, fetcher=_default_fetcher
) -> tuple[list[str], list[int], list[str]]:
    """回傳（已補回的檔名, 需 gallery-dl 重抓的 tweet_id, 下載失敗的檔名）。

    單一網址失敗不中斷整批修復。
    """
    repaired: list[str] = []
    refetch_ids: list[int] = []
    failed: list[str] = []
    for page in find_missing(manifest, raw_dir):
        if not page["url"]:
            refetch_ids.append(page["tweet_id"])
            continue
        try:
            (raw_dir / page["file"]).write_bytes(fetcher(page["url"]))
            repaired.append(page["file"])
        except Exception as exc:  # noqa: BLE001 — 目的是繼續補其他檔
            failed.append(page["file"])
            print(f"補下載失敗 {page['file']}: {exc}")
    return repaired, refetch_ids, failed
