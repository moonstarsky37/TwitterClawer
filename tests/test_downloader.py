"""下載器包裝：gallery-dl 指令組裝（seam：build_command / build_tweet_command / run_download）。"""

import sys

from twitterclawer import paths
from twitterclawer.downloader import build_command, build_tweet_command, run_download

ARTIST = "TreePlanti30333"


def _joined(cmd: list[str]) -> str:
    return " ".join(cmd)


def test_full_mode_uses_gallery_dl_module_with_media_url_last():
    cmd = build_command("full", ARTIST)
    assert cmd[0] == sys.executable
    assert cmd[1:3] == ["-m", "gallery_dl"]
    assert cmd[-1] == "https://x.com/TreePlanti30333/media"


def test_full_mode_reads_firefox_cookies_readonly():
    cmd = build_command("full", ARTIST)
    i = cmd.index("--cookies-from-browser")
    assert cmd[i + 1] == "firefox"


def test_firefox_profile_override():
    cmd = build_command("full", ARTIST, firefox_profile="x88nusgc.default-release")
    i = cmd.index("--cookies-from-browser")
    assert cmd[i + 1] == "firefox:x88nusgc.default-release"


def test_full_mode_downloads_into_artist_raw_dir_with_tweet_id_filenames():
    cmd = build_command("full", ARTIST)
    i = cmd.index("-D")
    assert cmd[i + 1] == str(paths.raw_dir(ARTIST))
    j = cmd.index("-f")
    assert cmd[j + 1] == "{tweet_id}_{num}.{extension}"


def test_each_artist_gets_own_archive_db():
    cmd = build_command("full", ARTIST)
    assert "--write-metadata" in cmd
    i = cmd.index("--download-archive")
    assert cmd[i + 1] == str(paths.archive_db(ARTIST))
    other = build_command("full", "OtherArtist")
    j = other.index("--download-archive")
    assert other[j + 1] != cmd[i + 1]


def test_full_mode_requests_orig_size_and_sleeps():
    joined = _joined(build_command("full", ARTIST))
    assert 'size=["orig", "large", "medium"]' in joined
    assert "--sleep-request" in joined


def test_full_mode_has_no_abort_early_stop():
    assert "--abort" not in build_command("full", ARTIST)


def test_update_mode_aborts_after_consecutive_skips():
    cmd = build_command("update", ARTIST)
    i = cmd.index("--abort")
    assert cmd[i + 1] == "30"


def test_unknown_mode_rejected():
    import pytest

    with pytest.raises(ValueError):
        build_command("banana", ARTIST)


def test_tweet_refetch_command_targets_status_url_without_archive():
    cmd = build_tweet_command(ARTIST, 1234567890)
    assert cmd[-1] == "https://x.com/TreePlanti30333/status/1234567890"
    assert "--download-archive" not in cmd  # 不跳過已記錄的檔案，才能補回
    assert "--write-metadata" in cmd


def test_run_download_invokes_runner_and_returns_exit_code():
    calls = {}

    def fake_runner(cmd):
        calls["cmd"] = cmd

        class R:
            returncode = 0

        return R()

    code = run_download("update", ARTIST, runner=fake_runner)
    assert code == 0
    # 獨立驗證關鍵事實，不與 build_command 循環比對
    assert calls["cmd"][-1] == "https://x.com/TreePlanti30333/media"
    assert "--abort" in calls["cmd"]
