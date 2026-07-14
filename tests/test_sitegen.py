"""網站產生器（seam：render_site / write_site / render_overview / write_overview）。"""

from twitterclawer.sitegen import (
    render_overview,
    render_site,
    write_overview,
    write_site,
)


def _manifest(text="第一話開始"):
    return {
        "artist": "TreePlanti30333",
        "episodes": [
            {
                "id": "100",
                "title": "第一話：出發",
                "date": "2026-01-01 10:00:00",
                "pages": [
                    {
                        "tweet_id": 101,
                        "num": 1,
                        "file": "101_1.jpg",
                        "remote": "GxYz",
                        "extension": "jpg",
                        "text": text,
                        "date": "2026-01-01 10:00:00",
                        "url": "https://pbs.twimg.com/media/GxYz?format=jpg&name=orig",
                    }
                ],
            }
        ],
    }


def test_site_embeds_manifest_data():
    html = render_site(_manifest())
    assert "第一話：出發" in html
    assert "101_1.jpg" in html


def test_artist_page_references_its_own_data_dir_relatively():
    # 專頁位於 sites/<handle>.html，圖檔在 ../data/<handle>/raw/
    html = render_site(_manifest())
    assert '"../data/" + encodeURIComponent(DATA.artist) + "/raw/"' in html


def test_site_is_self_contained_single_file():
    html = render_site(_manifest())
    assert "<script src=" not in html
    assert 'rel="stylesheet"' not in html


def test_embedded_json_cannot_break_out_of_script_tag():
    html = render_site(_manifest(text='惡意</script><script>alert(1)'))
    assert "</script><script>alert(1)" not in html


def test_first_pages_load_eagerly_rest_lazily():
    # 圖片標籤由前端 JS 生成，伺服端只能驗證邏輯存在；
    # 實際渲染由 headless 截圖驗證（見 CLAUDE.md 如何驗證）
    html = render_site(_manifest())
    assert "EAGER_COUNT = 3" in html
    assert "idx < EAGER_COUNT" in html
    assert 'loading=\\"lazy\\"' in html or 'loading="lazy"' in html


def test_artist_name_is_escaped_in_page_title():
    m = _manifest()
    m["artist"] = "<img onerror=x>"
    html = render_site(m)
    assert "<title><img onerror=x>" not in html


def test_write_site_writes_html(tmp_path):
    target = tmp_path / "TreePlanti30333.html"
    write_site(_manifest(), target)
    assert "第一話：出發" in target.read_text(encoding="utf-8")


def test_overview_lists_artists_with_links_and_stats():
    html = render_overview(
        [
            {"artist": "TreePlanti30333", "episodes": 344, "pages": 926, "updated": "2026-07-14"},
            {"artist": "OtherArtist", "episodes": 12, "pages": 40, "updated": "2026-07-10"},
        ]
    )
    assert 'href="sites/TreePlanti30333.html"' in html
    assert "344" in html and "926" in html and "2026-07-14" in html
    assert 'href="sites/OtherArtist.html"' in html


def test_overview_escapes_artist_names():
    html = render_overview(
        [{"artist": '<img onerror=x>', "episodes": 1, "pages": 1, "updated": "2026-01-01"}]
    )
    assert "<img onerror=x>" not in html


def test_write_overview_writes_index(tmp_path):
    target = tmp_path / "index.html"
    write_overview(
        [{"artist": "A_1", "episodes": 1, "pages": 2, "updated": "2026-01-01"}], target
    )
    assert "A_1" in target.read_text(encoding="utf-8")
