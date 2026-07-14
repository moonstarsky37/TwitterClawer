"""追蹤清單（seam：parse_handle / load_roster / add_artist）。"""

import pytest

from twitterclawer.roster import add_artist, load_roster, parse_handle


@pytest.mark.parametrize(
    "raw",
    [
        "TreePlanti30333",
        "@TreePlanti30333",
        "https://x.com/TreePlanti30333",
        "https://x.com/TreePlanti30333/",
        "https://x.com/TreePlanti30333/media",
        "https://twitter.com/TreePlanti30333?s=20",
        "x.com/TreePlanti30333",
    ],
)
def test_parse_handle_accepts_common_forms(raw):
    assert parse_handle(raw) == "TreePlanti30333"


@pytest.mark.parametrize(
    "raw",
    [
        "",
        "https://x.com/",
        "@",
        "x.com",
        # 安全：handle 會拼進 data/<handle>/ 路徑，穿越形輸入必須擋
        "../../etc",
        "https://x.com/../secret",
        "a/b",
        "back\\slash",
        "..",
        # X 保留路徑與 Windows 裝置名
        "home",
        "https://x.com/messages",
        "CON",
        "nul",
        "COM1",
    ],
)
def test_parse_handle_rejects_garbage_and_traversal(raw):
    with pytest.raises(ValueError):
        parse_handle(raw)


def test_load_roster_rejects_non_list_json(tmp_path):
    bad = tmp_path / "artists.json"
    bad.write_text('{"artist": "abc"}', encoding="utf-8")
    with pytest.raises(ValueError):
        load_roster(bad)


def test_empty_roster_loads_as_empty_list(tmp_path):
    assert load_roster(tmp_path / "artists.json") == []


def test_add_then_load_round_trips(tmp_path):
    target = tmp_path / "artists.json"
    add_artist("https://x.com/TreePlanti30333", target)
    assert load_roster(target) == ["TreePlanti30333"]


def test_add_same_artist_twice_no_duplicate(tmp_path):
    target = tmp_path / "artists.json"
    add_artist("TreePlanti30333", target)
    add_artist("@treeplanti30333", target)  # 大小寫視為同一人
    assert load_roster(target) == ["TreePlanti30333"]


def test_add_preserves_existing_order_appends_new(tmp_path):
    target = tmp_path / "artists.json"
    add_artist("ArtistA", target)
    add_artist("ArtistB", target)
    assert load_roster(target) == ["ArtistA", "ArtistB"]
