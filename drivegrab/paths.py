"""Helpers for turning Drive titles into safe local paths."""

import re
from pathlib import Path

_DRIVE_SUFFIX = re.compile(r"\s*-\s*Google\s*(Drive|Диск|Drive'ı)?\s*$", re.IGNORECASE)
_BAD_CHARS = re.compile(r'[\\/:*?"<>|\x00-\x1f]')


def safe_name(name, fallback="untitled"):
    """Strip the ' - Google Drive' tail and characters Windows won't accept."""
    name = _DRIVE_SUFFIX.sub("", name or "").strip()
    name = _BAD_CHARS.sub("_", name).rstrip(" .")
    return name or fallback


def as_pdf(name):
    return name if name.lower().endswith(".pdf") else name + ".pdf"


def unique_path(folder, name):
    """folder/name, or folder/name (1), (2)... if it already exists."""
    folder = Path(folder)
    p = folder / name
    stem, suffix = Path(name).stem, Path(name).suffix
    n = 1
    while p.exists():
        p = folder / f"{stem} ({n}){suffix}"
        n += 1
    return p
