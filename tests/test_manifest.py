"""manifest：產生、儲存、載入（seam：build_manifest / save_manifest / load_manifest）。"""

from twitterclawer.manifest import build_manifest, load_manifest, save_manifest


def _episode(ext="jpg", remote="GxYz123AbC"):
    return {
        "id": "100",
        "title": "第一話",
        "date": "2026-01-01 10:00:00",
        "pages": [
            {
                "tweet_id": 101,
                "num": 1,
                "file": f"101_1.{ext}",
                "remote": remote,
                "extension": ext,
                "text": "第一話",
                "date": "2026-01-01 10:00:00",
            }
        ],
    }


def test_manifest_has_artist_and_episodes():
    m = build_manifest([_episode()], "TreePlanti30333")
    assert m["artist"] == "TreePlanti30333"
    assert len(m["episodes"]) == 1


def test_photo_page_gets_orig_download_url():
    m = build_manifest([_episode(ext="jpg", remote="GxYz123AbC")], "TreePlanti30333")
    page = m["episodes"][0]["pages"][0]
    assert page["url"] == "https://pbs.twimg.com/media/GxYz123AbC?format=jpg&name=orig"


def test_video_page_has_no_direct_url():
    m = build_manifest([_episode(ext="mp4")], "TreePlanti30333")
    assert m["episodes"][0]["pages"][0]["url"] is None


def test_merge_prefers_new_episodes_but_keeps_old_only_ones():
    from twitterclawer.manifest import merge_manifests

    old = build_manifest(
        [
            {**_episode(), "id": "100", "title": "舊版標題"},
            {**_episode(), "id": "50", "title": "只存在舊 manifest 的話", "date": "2025-12-01 10:00:00"},
        ],
        "TreePlanti30333",
    )
    new = build_manifest([{**_episode(), "id": "100", "title": "新版標題"}], "TreePlanti30333")
    merged = merge_manifests(old, new)
    by_id = {ep["id"]: ep for ep in merged["episodes"]}
    assert by_id["100"]["title"] == "新版標題"
    assert by_id["50"]["title"] == "只存在舊 manifest 的話"
    # 話序維持新到舊
    assert [ep["id"] for ep in merged["episodes"]] == ["100", "50"]


def test_save_then_load_round_trips(tmp_path):
    m = build_manifest([_episode()], "TreePlanti30333")
    target = tmp_path / "manifest.json"
    save_manifest(m, target)
    assert load_manifest(target) == m
