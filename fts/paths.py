"""File locations that work both from source and inside a PyInstaller .exe."""
from __future__ import annotations

import os
import sys
from pathlib import Path

APP_NAME = "Finance_Commercial_Training"


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

    Windows: %APPDATA%/Finance_Commercial_Training
    Other:   ~/.finance_commercial_training
    Override with the FTS_DATA_DIR environment variable (used by tests).
    """
    override = os.environ.get("FTS_DATA_DIR")
    if override:
        p = Path(override)
    elif os.name == "nt" and os.environ.get("APPDATA"):
        p = Path(os.environ["APPDATA"]) / APP_NAME
    else:
        p = Path.home() / ".finance_commercial_training"
    p.mkdir(parents=True, exist_ok=True)
    return p


def exports_dir() -> Path:
    p = user_data_dir() / "exports"
    p.mkdir(parents=True, exist_ok=True)
    return p
