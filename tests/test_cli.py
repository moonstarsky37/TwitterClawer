"""CLI v2（seam：main(argv)——add／全清單輪跑／--artist）。"""

import json

from twitterclawer import cli, downloader, paths

ARTIST = "TreePlanti30333"


def _fake_metadata(tweet_id=101, artist=ARTIST, content="測試話"):
    return {
        "tweet_id": tweet_id,
        "conversation_id": tweet_id,
        "date": "2026-01-01 10:00:00",
        "content": content,
        "num": 1,
        "extension": "jpg",
        "filename": "RemoteAAA",
        "author": {"name": artist},
    }


def _patch_paths(monkeypatch, tmp_path):
    monkeypatch.setattr(paths, "DATA_DIR", tmp_path / "data")
    monkeypatch.setattr(paths, "SITES_DIR", tmp_path / "sites")
    monkeypatch.setattr(paths, "INDEX_HTML", tmp_path / "index.html")
    monkeypatch.setattr(paths, "ARTISTS_JSON", tmp_path / "artists.json")


def _seed_artist(tmp_path, artist=ARTIST, tweet_id=101, content="測試話"):
    raw = tmp_path / "data" / artist / "raw"
    raw.mkdir(parents=True, exist_ok=True)
    (raw / f"{tweet_id}_1.jpg.json").write_text(
        json.dumps(_fake_metadata(tweet_id, artist, content)), encoding="utf-8"
    )
    (raw / f"{tweet_id}_1.jpg").write_bytes(b"img")
    return raw


def _seed_roster(tmp_path, artists):
    (tmp_path / "artists.json").write_text(json.dumps(artists), encoding="utf-8")


def test_unknown_command_exits_nonzero():
    assert cli.main(["banana"]) != 0


def test_add_without_arg_prompts_interactively(tmp_path, monkeypatch):
    # .bat 不能安全帶中文（cmd 亂碼），互動提問由 Python 端負責
    _patch_paths(monkeypatch, tmp_path)
    calls = []

    def fake_run(mode, artist, **kw):
        calls.append((mode, artist))
        _seed_artist(tmp_path, artist)
        return 0

    monkeypatch.setattr(downloader, "run_download", fake_run)
    monkeypatch.setattr("builtins.input", lambda prompt="": "https://x.com/TreePlanti30333")
    assert cli.main(["add"]) == 0
    assert calls == [("full", ARTIST)]


def test_add_with_empty_interactive_input_exits_nonzero(tmp_path, monkeypatch):
    _patch_paths(monkeypatch, tmp_path)
    monkeypatch.setattr("builtins.input", lambda prompt="": "")
    assert cli.main(["add"]) != 0


def test_add_registers_artist_downloads_and_builds(tmp_path, monkeypatch):
    _patch_paths(monkeypatch, tmp_path)
    calls = []

    def fake_run(mode, artist, **kw):
        calls.append((mode, artist))
        _seed_artist(tmp_path, artist)
        return 0

    monkeypatch.setattr(downloader, "run_download", fake_run)
    assert cli.main(["add", "https://x.com/TreePlanti30333"]) == 0
    assert calls == [("full", ARTIST)]
    assert json.loads((tmp_path / "artists.json").read_text(encoding="utf-8")) == [ARTIST]
    assert (tmp_path / "sites" / f"{ARTIST}.html").exists()
    assert f"sites/{ARTIST}.html" in (tmp_path / "index.html").read_text(encoding="utf-8")


def test_update_iterates_whole_roster(tmp_path, monkeypatch):
    _patch_paths(monkeypatch, tmp_path)
    _seed_roster(tmp_path, ["ArtistA", "ArtistB"])
    _seed_artist(tmp_path, "ArtistA", 201, "A話")
    _seed_artist(tmp_path, "ArtistB", 301, "B話")
    calls = []
    monkeypatch.setattr(
        downloader, "run_download", lambda mode, artist, **kw: calls.append((mode, artist)) or 0
    )
    assert cli.main(["update"]) == 0
    assert calls == [("update", "ArtistA"), ("update", "ArtistB")]
    assert (tmp_path / "sites" / "ArtistA.html").exists()
    assert (tmp_path / "sites" / "ArtistB.html").exists()
    index = (tmp_path / "index.html").read_text(encoding="utf-8")
    assert "ArtistA" in index and "ArtistB" in index


def test_artist_flag_limits_to_one(tmp_path, monkeypatch):
    _patch_paths(monkeypatch, tmp_path)
    _seed_roster(tmp_path, ["ArtistA", "ArtistB"])
    _seed_artist(tmp_path, "ArtistA", 201, "A話")
    calls = []
    monkeypatch.setattr(
        downloader, "run_download", lambda mode, artist, **kw: calls.append(artist) or 0
    )
    assert cli.main(["update", "--artist", "ArtistA"]) == 0
    assert calls == ["ArtistA"]


def test_update_with_empty_roster_hints_and_fails(tmp_path, monkeypatch, capsys):
    _patch_paths(monkeypatch, tmp_path)
    assert cli.main(["update"]) != 0
    assert "add-artist" in capsys.readouterr().out


def test_build_falls_back_to_manifest_when_raw_metadata_wiped(tmp_path, monkeypatch):
    _patch_paths(monkeypatch, tmp_path)
    _seed_roster(tmp_path, [ARTIST])
    raw = _seed_artist(tmp_path)
    assert cli.main(["build"]) == 0

    (raw / "101_1.jpg.json").unlink()
    (tmp_path / "sites" / f"{ARTIST}.html").unlink()
    assert cli.main(["build"]) == 0
    site = (tmp_path / "sites" / f"{ARTIST}.html").read_text(encoding="utf-8")
    assert "測試話" in site


def test_build_merges_with_existing_manifest_instead_of_overwriting(tmp_path, monkeypatch):
    _patch_paths(monkeypatch, tmp_path)
    _seed_roster(tmp_path, [ARTIST])
    raw = _seed_artist(tmp_path, tweet_id=101, content="測試話")
    (raw / "201_1.jpg.json").write_text(
        json.dumps({**_fake_metadata(201, content="第二話"), "date": "2026-02-01 10:00:00"}),
        encoding="utf-8",
    )
    assert cli.main(["build"]) == 0
    (raw / "201_1.jpg.json").unlink()

    assert cli.main(["build"]) == 0
    manifest = json.loads(
        (tmp_path / "data" / ARTIST / "manifest.json").read_text(encoding="utf-8")
    )
    assert {ep["title"] for ep in manifest["episodes"]} == {"測試話", "第二話"}


def test_repair_restores_missing_file_for_each_artist(tmp_path, monkeypatch):
    _patch_paths(monkeypatch, tmp_path)
    _seed_roster(tmp_path, [ARTIST])
    raw = _seed_artist(tmp_path)
    assert cli.main(["build"]) == 0
    (raw / "101_1.jpg").unlink()

    monkeypatch.setattr(cli, "_fetch_bytes", lambda url: b"restored")
    assert cli.main(["repair"]) == 0
    assert (raw / "101_1.jpg").read_bytes() == b"restored"


def test_artist_flag_rejects_traversal_and_unknown(tmp_path, monkeypatch, capsys):
    _patch_paths(monkeypatch, tmp_path)
    _seed_roster(tmp_path, ["ArtistA"])
    monkeypatch.setattr(downloader, "run_download", lambda *a, **kw: 0)
    # 穿越形輸入
    assert cli.main(["build", "--artist", "../../evil"]) != 0
    # 合法格式但不在清單
    assert cli.main(["build", "--artist", "Stranger"]) != 0
    assert "清單" in capsys.readouterr().out


def test_one_broken_artist_does_not_kill_the_rest(tmp_path, monkeypatch):
    _patch_paths(monkeypatch, tmp_path)
    _seed_roster(tmp_path, ["BadArtist", "GoodArtist"])
    _seed_artist(tmp_path, "GoodArtist", 301, "好話")
    # BadArtist 的 manifest 是壞 JSON → 不可拖垮 GoodArtist 與總覽
    bad_dir = tmp_path / "data" / "BadArtist"
    bad_dir.mkdir(parents=True)
    (bad_dir / "manifest.json").write_text("{broken", encoding="utf-8")
    monkeypatch.setattr(downloader, "run_download", lambda *a, **kw: 0)

    code = cli.main(["update"])
    assert code != 0  # 有作家失敗要反映在退出碼
    assert (tmp_path / "sites" / "GoodArtist.html").exists()
    index = (tmp_path / "index.html").read_text(encoding="utf-8")
    assert "GoodArtist" in index


def test_download_failure_reflected_in_exit_code(tmp_path, monkeypatch):
    _patch_paths(monkeypatch, tmp_path)
    _seed_roster(tmp_path, [ARTIST])
    _seed_artist(tmp_path)
    monkeypatch.setattr(downloader, "run_download", lambda *a, **kw: 4)
    assert cli.main(["full"]) != 0


def test_full_forwards_firefox_profile_flag(tmp_path, monkeypatch):
    _patch_paths(monkeypatch, tmp_path)
    _seed_roster(tmp_path, [ARTIST])
    _seed_artist(tmp_path)
    seen = {}

    def fake_run(mode, artist, firefox_profile=None, **kw):
        seen["profile"] = firefox_profile
        return 0

    monkeypatch.setattr(downloader, "run_download", fake_run)
    assert cli.main(["full", "--profile", "x88nusgc.default-release"]) == 0
    assert seen["profile"] == "x88nusgc.default-release"
