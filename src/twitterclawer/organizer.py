"""把 gallery-dl 的 metadata JSON 整理成「話」（一串 thread＝一話）。"""

import json
import re
from pathlib import Path

_TCO_LINK = re.compile(r"\s*https://t\.co/\S+")


def load_records(raw_dir: Path) -> list[dict]:
    records = []
    for path in sorted(raw_dir.glob("*.json")):
        records.append(json.loads(path.read_text(encoding="utf-8")))
    return records


def _title_from(content: str, date: str) -> str:
    # 內文可能整串都是 t.co 連結，剝掉後會是空字串
    lines = _TCO_LINK.sub("", content).splitlines() if content else []
    first_line = lines[0].strip() if lines else ""
    return first_line or date.split(" ")[0]


def build_episodes(records: list[dict], artist: str) -> list[dict]:
    by_conversation: dict[str, list[dict]] = {}
    for rec in records:
        if rec.get("author", {}).get("name", "").casefold() != artist.casefold():
            continue
        key = str(rec.get("conversation_id") or rec["tweet_id"])
        by_conversation.setdefault(key, []).append(rec)

    episodes = []
    for conv_id, recs in by_conversation.items():
        recs.sort(key=lambda r: (r["date"], r["tweet_id"], r["num"]))
        first = recs[0]
        pages = [
            {
                "tweet_id": r["tweet_id"],
                "num": r["num"],
                "file": f'{r["tweet_id"]}_{r["num"]}.{r["extension"]}',
                "remote": r.get("filename", ""),
                "extension": r["extension"],
                "text": _TCO_LINK.sub("", r.get("content", "")).strip(),
                "date": r["date"],
            }
            for r in recs
        ]
        episodes.append(
            {
                "id": conv_id,
                "title": _title_from(first.get("content", ""), first["date"]),
                "date": first["date"],
                "pages": pages,
            }
        )

    episodes.sort(key=lambda ep: ep["date"], reverse=True)
    return episodes
