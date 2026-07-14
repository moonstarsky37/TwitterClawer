"""整理器：gallery-dl metadata → 話（seam：load_records / build_episodes）。"""

import json

from twitterclawer.organizer import build_episodes, load_records


def _rec(tweet_id, conversation_id, date, content, num=1, ext="jpg", author="TreePlanti30333", remote="AbCdEf"):
    """gallery-dl twitter extractor 的 metadata JSON 最小子集。"""
    return {
        "tweet_id": tweet_id,
        "conversation_id": conversation_id,
        "date": date,
        "content": content,
        "num": num,
        "extension": ext,
        "filename": remote,
        "author": {"name": author},
    }


def test_same_conversation_merges_into_one_episode_pages_in_order():
    records = [
        _rec(103, 100, "2026-01-03 10:00:00", "第三頁", num=1),
        _rec(101, 100, "2026-01-01 10:00:00", "新連載開始！", num=1),
        _rec(101, 100, "2026-01-01 10:00:00", "新連載開始！", num=2),
        _rec(102, 100, "2026-01-02 10:00:00", "第二頁", num=1),
    ]
    episodes = build_episodes(records, "TreePlanti30333")
    assert len(episodes) == 1
    ep = episodes[0]
    assert ep["id"] == "100"
    assert [(p["tweet_id"], p["num"]) for p in ep["pages"]] == [
        (101, 1),
        (101, 2),
        (102, 1),
        (103, 1),
    ]
    assert [p["file"] for p in ep["pages"]] == [
        "101_1.jpg",
        "101_2.jpg",
        "102_1.jpg",
        "103_1.jpg",
    ]


def test_episodes_sorted_newest_first_by_first_tweet_date():
    records = [
        _rec(201, 201, "2026-02-01 09:00:00", "舊短篇"),
        _rec(301, 301, "2026-03-01 09:00:00", "新短篇"),
    ]
    episodes = build_episodes(records, "TreePlanti30333")
    assert [ep["id"] for ep in episodes] == ["301", "201"]
    assert episodes[0]["date"] == "2026-03-01 09:00:00"


def test_title_is_first_line_without_tco_links():
    records = [
        _rec(401, 401, "2026-04-01 09:00:00", "第五話：出發 https://t.co/abc123\n續文在下面")
    ]
    (ep,) = build_episodes(records, "TreePlanti30333")
    assert ep["title"] == "第五話：出發"


def test_title_falls_back_to_date_when_content_is_only_tco_links():
    # gallery-dl 只剝掉最後一個 t.co，內文可能只剩連結 → 不可 crash
    records = [_rec(411, 411, "2026-04-11 09:00:00", "https://t.co/only1 https://t.co/only2")]
    (ep,) = build_episodes(records, "TreePlanti30333")
    assert ep["title"] == "2026-04-11"


def test_author_match_is_case_insensitive():
    records = [_rec(421, 421, "2026-04-21 09:00:00", "大小寫", author="treeplanti30333")]
    episodes = build_episodes(records, "TreePlanti30333")
    assert len(episodes) == 1


def test_title_falls_back_to_date_when_no_text():
    records = [_rec(501, 501, "2026-05-01 09:00:00", "")]
    (ep,) = build_episodes(records, "TreePlanti30333")
    assert ep["title"] == "2026-05-01"


def test_other_authors_records_are_excluded():
    records = [
        _rec(601, 601, "2026-06-01 09:00:00", "本人的圖"),
        _rec(602, 601, "2026-06-01 10:00:00", "別人的圖", author="SomeoneElse"),
    ]
    (ep,) = build_episodes(records, "TreePlanti30333")
    assert [p["tweet_id"] for p in ep["pages"]] == [601]


def test_page_keeps_text_and_date():
    records = [_rec(701, 701, "2026-07-01 09:00:00", "單頁圖 https://t.co/xyz")]
    (ep,) = build_episodes(records, "TreePlanti30333")
    page = ep["pages"][0]
    assert page["text"] == "單頁圖"
    assert page["date"] == "2026-07-01 09:00:00"


def test_load_records_reads_json_files_from_raw_dir(tmp_path):
    rec = _rec(801, 801, "2026-08-01 09:00:00", "讀檔測試")
    (tmp_path / "801_1.jpg.json").write_text(json.dumps(rec), encoding="utf-8")
    (tmp_path / "801_1.jpg").write_bytes(b"fake")  # 圖檔本體不該被當 metadata 讀
    records = load_records(tmp_path)
    assert records == [rec]
