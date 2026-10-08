"""Parsing Google Drive share links."""

import re

# Drive ids are base64-ish strings, usually 28-44 chars long
_FILE_RES = (
    re.compile(r"/d/([\w-]{20,})"),        # /file/d/<id>/view, /document/d/<id>/edit
    re.compile(r"[?&]id=([\w-]{20,})"),    # open?id=<id>, uc?id=<id>
)
_FOLDER_RE = re.compile(r"/folders/([\w-]{20,})")


def folder_id(url):
    """Return folder id for a folder link, otherwise None."""
    m = _FOLDER_RE.search(url or "")
    return m.group(1) if m else None


def file_id(url):
    """Return file id for a file link, otherwise None."""
    if not url or folder_id(url):
        return None
    for rx in _FILE_RES:
        m = rx.search(url)
        if m:
            return m.group(1)
    return None
