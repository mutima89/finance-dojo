"""The per-user data folder, including the one-time copy from the pre-rename folder."""
import os
from pathlib import Path

from fts import paths


def _roots(monkeypatch, tmp_path):
    monkeypatch.delenv("FTS_DATA_DIR", raising=False)
    monkeypatch.setenv("APPDATA", str(tmp_path / "appdata"))
    monkeypatch.setenv("HOME", str(tmp_path / "home"))
    monkeypatch.setenv("USERPROFILE", str(tmp_path / "home"))
    if os.name == "nt":
        base = tmp_path / "appdata"
        return base / paths.LEGACY_APP_NAME, base / paths.APP_NAME
    base = tmp_path / "home"
    return base / paths.LEGACY_HOME_DIR, base / ".finance_dojo"


def test_old_progress_is_copied_to_new_folder(monkeypatch, tmp_path):
    old, new = _roots(monkeypatch, tmp_path)
    (old / "exports").mkdir(parents=True)
    (old / "progress.sqlite3").write_bytes(b"saved progress")
    (old / "exports" / "report.html").write_text("r")

    assert paths.user_data_dir() == new
    assert (new / "progress.sqlite3").read_bytes() == b"saved progress"
    assert (new / "exports" / "report.html").exists()
    assert (old / "progress.sqlite3").exists()          # original is kept


def test_existing_new_folder_is_never_overwritten(monkeypatch, tmp_path):
    old, new = _roots(monkeypatch, tmp_path)
    old.mkdir(parents=True)
    (old / "progress.sqlite3").write_bytes(b"old")
    new.mkdir(parents=True)
    (new / "progress.sqlite3").write_bytes(b"new")

    assert paths.user_data_dir() == new
    assert (new / "progress.sqlite3").read_bytes() == b"new"


def test_fresh_install_creates_empty_folder(monkeypatch, tmp_path):
    _, new = _roots(monkeypatch, tmp_path)
    assert paths.user_data_dir() == new
    assert new.is_dir() and not any(new.iterdir())


def test_override_skips_migration(monkeypatch, tmp_path):
    old, _ = _roots(monkeypatch, tmp_path)
    old.mkdir(parents=True)
    monkeypatch.setenv("FTS_DATA_DIR", str(tmp_path / "custom"))
    assert paths.user_data_dir() == Path(tmp_path / "custom")
