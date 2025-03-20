from __future__ import annotations

import logging
from enum import Enum

log = logging.getLogger(__name__)


class FileExt(Enum):
    """
    Recognized file type extensions for common file types.
    Currently intended to be useful for heuristics and canonicalizing common extensions,
    but not comprehensive.
    """

    txt = "txt"
    md = "md"
    html = "html"
    yml = "yml"
    diff = "diff"
    json = "json"
    csv = "csv"
    npz = "npz"
    log = "log"
    py = "py"
    sh = "sh"
    ksh = "ksh"
    xsh = "xsh"
    pdf = "pdf"
    docx = "docx"
    jpg = "jpg"
    png = "png"
    svg = "svg"
    mp3 = "mp3"
    m4a = "m4a"
    mp4 = "mp4"

    @property
    def dot_ext(self) -> str:
        return f".{self.value}"

    @property
    def is_text(self) -> bool:
        return self in [
            self.txt,
            self.md,
            self.html,
            self.yml,
            self.json,
            self.py,
            self.sh,
            self.ksh,
            self.xsh,
        ]

    @property
    def is_image(self) -> bool:
        return self in [self.jpg, self.png]

    @classmethod
    def parse(cls, ext_str: str) -> FileExt | None:
        """
        Convert a string to a FileExt enum, if possible.
        """
        ext = canonicalize_file_ext(ext_str)
        try:
            return FileExt(ext)
        except ValueError:
            return None

    def __str__(self):
        return self.name


def canonicalize_file_ext(ext: str) -> str:
    """
    Convert a file extension (with or without the dot) to canonical form (without the dot).
    """
    ext_map = {
        "htm": "html",
        "yaml": "yml",
        "jpeg": "jpg",
        "patch": "diff",
    }
    ext = ext.lower().lstrip(".")
    return ext_map.get(ext, ext)
