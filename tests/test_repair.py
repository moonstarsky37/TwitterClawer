"""修復器（seam：find_missing / repair）。"""

from twitterclawer.repair import find_missing, repair


def _manifest():
    return {
        "artist": "TreePlanti30333",
        "episodes": [
            {
                "id": "100",
                "title": "第一話",
                "date": "2026-01-01 10:00:00",
                "pages": [
                    {
                        "tweet_id": 101,
                        "num": 1,
                        "file": "101_1.jpg",
                        "url": "https://pbs.twimg.com/media/AAA?format=jpg&name=orig",
                        "text": "",
                        "date": "2026-01-01 10:00:00",
                    },
                    {
                        "tweet_id": 102,
                        "num": 1,
                        "file": "102_1.jpg",
                        "url": "https://pbs.twimg.com/media/BBB?format=jpg&name=orig",
                        "text": "",
                        "date": "2026-01-02 10:00:00",
                    },
                    {
                        "tweet_id": 103,
                        "num": 1,
                        "file": "103_1.mp4",
                        "url": None,
                        "text": "",
                        "date": "2026-01-03 10:00:00",
                    },
                ],
            }
        ],
    }


def test_find_missing_lists_only_absent_files(tmp_path):
    (tmp_path / "101_1.jpg").write_bytes(b"ok")
    missing = find_missing(_manifest(), tmp_path)
    assert [p["file"] for p in missing] == ["102_1.jpg", "103_1.mp4"]


def test_repair_downloads_missing_photos_via_url(tmp_path):
    (tmp_path / "101_1.jpg").write_bytes(b"ok")
    fetched = []

    def fake_fetcher(url):
        fetched.append(url)
        return b"image-bytes"

    repaired, refetch_ids, failed = repair(_manifest(), tmp_path, fetcher=fake_fetcher)
    assert repaired == ["102_1.jpg"]
    assert failed == []
    assert fetched == ["https://pbs.twimg.com/media/BBB?format=jpg&name=orig"]
    assert (tmp_path / "102_1.jpg").read_bytes() == b"image-bytes"


def test_repair_reports_pages_without_url_for_refetch(tmp_path):
    (tmp_path / "101_1.jpg").write_bytes(b"ok")
    (tmp_path / "102_1.jpg").write_bytes(b"ok")
    repaired, refetch_ids, failed = repair(_manifest(), tmp_path, fetcher=lambda u: b"x")
    assert repaired == []
    assert refetch_ids == [103]
    assert failed == []


def test_repair_continues_past_failed_downloads(tmp_path):
    # 一個網址 404 不可中斷整批修復
    (tmp_path / "103_1.mp4").write_bytes(b"ok")

    def flaky_fetcher(url):
        if "AAA" in url:
            raise RuntimeError("404")
        return b"image-bytes"

    repaired, refetch_ids, failed = repair(_manifest(), tmp_path, fetcher=flaky_fetcher)
    assert repaired == ["102_1.jpg"]
    assert failed == ["101_1.jpg"]
    assert (tmp_path / "102_1.jpg").read_bytes() == b"image-bytes"


def test_repair_with_nothing_missing_is_noop(tmp_path):
    for name in ("101_1.jpg", "102_1.jpg", "103_1.mp4"):
        (tmp_path / name).write_bytes(b"ok")
    repaired, refetch_ids, failed = repair(
        _manifest(), tmp_path, fetcher=lambda u: (_ for _ in ()).throw(AssertionError)
    )
    assert repaired == []
    assert refetch_ids == []
    assert failed == []
