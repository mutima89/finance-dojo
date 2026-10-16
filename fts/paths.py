"""File locations that work both from source and inside a PyInstaller .exe."""
from __future__ import annotations

import os
import shutil
import sys
from pathlib import Path

APP_NAME = "Finance_Dojo"
# Folder names used before the app was renamed; progress found there is copied over once.
LEGACY_APP_NAME = "Finance_Commercial_Training"
LEGACY_HOME_DIR = ".finance_commercial_training"


def resource_root() -> Path:
    """Folder holding bundled read-only files (datasets, workbooks, docs)."""
    if getattr(sys, "frozen", False) and hasattr(sys, "_MEIPASS"):
        return Path(sys._MEIPASS)
    return Path(__file__).resolve().parents[1]


def datasets_dir() -> Path:
    return resource_root() / "datasets"


def workbooks_dir() -> Path:
    return resource_root() / "workbooks"


def docs_dir() -> Path:
    return resource_root() / "docs"


def user_data_dir() -> Path:
    """Writable per-user folder for the progress database and exports.

    Windows: %APPDATA%/Finance_Dojo
    Other:   ~/.finance_dojo
    Override with the FTS_DATA_DIR environment variable (used by tests).
    """
    override = os.environ.get("FTS_DATA_DIR")
    if override:
        p = Path(override)
    elif os.name == "nt" and os.environ.get("APPDATA"):
        p = Path(os.environ["APPDATA"]) / APP_NAME
        _adopt_legacy(Path(os.environ["APPDATA"]) / LEGACY_APP_NAME, p)
    else:
        p = Path.home() / ".finance_dojo"
        _adopt_legacy(Path.home() / LEGACY_HOME_DIR, p)
    p.mkdir(parents=True, exist_ok=True)
    return p


def _adopt_legacy(old: Path, new: Path) -> None:
    """Copy progress from the pre-rename folder the first time the new one is needed.

    The old folder is left in place, so nothing is lost if the copy is interrupted.
    """
    if new.exists() or not old.is_dir():
        return
    try:
        shutil.copytree(old, new)
    except OSError:
        shutil.rmtree(new, ignore_errors=True)


def exports_dir() -> Path:
    p = user_data_dir() / "exports"
    p.mkdir(parents=True, exist_ok=True)
    return p
