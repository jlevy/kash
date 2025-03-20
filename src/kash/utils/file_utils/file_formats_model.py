from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from pathlib import Path

from kash.utils.common.url import Url, is_file_url, parse_file_url
from kash.utils.file_utils.file_ext import FileExt
from kash.utils.file_utils.file_formats import MimeType, detect_mime_type, mime_type_is_text
from kash.utils.file_utils.filename_parsing import parse_file_ext


class MediaType(Enum):
    """
    Media types. For broad categories only, to determine what processing
    is possible.
    """

    text = "text"
    image = "image"
    audio = "audio"
    video = "video"
    webpage = "webpage"
    binary = "binary"


class Format(Enum):
    """
    Format of data in a file or in an item. This is just the important formats, not an exhaustive
    list. For text items that have a body, this is the body data format. For resource items,
    it is the format of the resource (url, media, etc.).
    """

    # Formats with no body (content is in frontmatter).
    url = "url"

    # Text formats.
    plaintext = "plaintext"
    markdown = "markdown"
    md_html = "md_html"
    """`md_html` is Markdown with HTML, used for example when we structure Markdown with divs."""
    html = "html"
    """`markdown` should be simple and clean Markdown that we can use with LLMs."""
    yaml = "yaml"
    diff = "diff"
    python = "python"
    kash_script = "kash_script"
    """Our own format for kash scripts."""
    json = "json"
    csv = "csv"
    npz = "npz"
    log = "log"

    # Media formats.
    pdf = "pdf"
    docx = "docx"
    jpeg = "jpeg"
    png = "png"
    svg = "svg"
    mp3 = "mp3"
    m4a = "m4a"
    mp4 = "mp4"
    binary = "binary"
    """Catch-all format for binary files that are unrecognized."""

    @property
    def has_body(self) -> bool:
        """
        Does this format have a body, or is it stored in metadata.
        """
        return self not in [self.url]

    @property
    def is_text(self) -> bool:
        """
        Can this format be read into a string and processed by text tools?
        """
        return self in [
            self.plaintext,
            self.markdown,
            self.md_html,
            self.html,
            self.svg,
            self.yaml,
            self.diff,
            self.python,
            self.json,
            self.kash_script,
            self.csv,
            self.log,
        ]

    @property
    def is_doc(self) -> bool:
        return self in [
            self.markdown,
            self.md_html,
            self.html,
            self.pdf,
            self.docx,
        ]

    @property
    def is_image(self) -> bool:
        return self in [self.jpeg, self.png, self.svg]

    @property
    def is_audio(self) -> bool:
        return self in [self.mp3, self.m4a]

    @property
    def is_video(self) -> bool:
        return self in [self.mp4]

    @property
    def is_code(self) -> bool:
        return self in [self.python, self.kash_script, self.json, self.yaml]

    @property
    def is_data(self) -> bool:
        return self in [self.csv, self.npz]

    @property
    def is_binary(self) -> bool:
        return self.has_body and not self.is_text

    @property
    def supports_frontmatter(self) -> bool:
        """
        Is this format compatible with frontmatter format metadata?
        PDF and docx unfortunately won't work with frontmatter.
        CSV does to some degree, depending on the tool, and this is useful so we support it.
        Perhaps we could include JSON here (assuming it's JSON5), but currently we do not.
        """
        return self in [
            self.url,
            self.plaintext,
            self.markdown,
            self.md_html,
            self.html,
            self.yaml,
            self.diff,
            self.python,
            self.kash_script,
            self.csv,
            self.log,
        ]

    @property
    def media_type(self) -> MediaType:
        format_to_media_type = {
            Format.url: MediaType.webpage,
            Format.plaintext: MediaType.text,
            Format.markdown: MediaType.text,
            Format.md_html: MediaType.text,
            Format.html: MediaType.webpage,
            Format.yaml: MediaType.text,
            Format.diff: MediaType.text,
            Format.python: MediaType.text,
            Format.kash_script: MediaType.text,
            Format.json: MediaType.text,
            Format.csv: MediaType.text,
            Format.log: MediaType.text,
            Format.pdf: MediaType.text,
            Format.jpeg: MediaType.image,
            Format.png: MediaType.image,
            Format.svg: MediaType.image,
            Format.docx: MediaType.text,
            Format.mp3: MediaType.audio,
            Format.m4a: MediaType.audio,
            Format.mp4: MediaType.video,
        }
        return format_to_media_type.get(self, MediaType.binary)

    @classmethod
    def guess_by_file_ext(cls, file_ext: FileExt) -> Format | None:
        """
        Guess the format for a given file extension, if it determines the format,
        None if format is ambiguous.
        """
        ext_to_format = {
            FileExt.txt.value: Format.plaintext,
            FileExt.md.value: Format.markdown,
            FileExt.html.value: Format.html,
            FileExt.yml.value: Format.yaml,
            FileExt.diff.value: Format.diff,
            FileExt.json.value: Format.json,
            FileExt.csv.value: Format.csv,
            FileExt.npz.value: Format.npz,
            FileExt.log.value: Format.log,
            FileExt.py.value: Format.python,
            FileExt.ksh.value: Format.kash_script,
            FileExt.pdf.value: Format.pdf,
            FileExt.docx.value: Format.docx,
            FileExt.jpg.value: Format.jpeg,
            FileExt.png.value: Format.png,
            FileExt.svg.value: Format.svg,
            FileExt.mp3.value: Format.mp3,
            FileExt.m4a.value: Format.m4a,
            FileExt.mp4.value: Format.mp4,
        }
        return ext_to_format.get(file_ext.value, None)

    @property
    def file_ext(self) -> FileExt | None:
        """
        File extension to use for a given format.
        """
        format_to_file_ext = {
            Format.url: FileExt.yml,  # We save URLs as YAML resources.
            Format.markdown: FileExt.md,
            Format.md_html: FileExt.md,
            Format.html: FileExt.html,
            Format.plaintext: FileExt.txt,
            Format.yaml: FileExt.yml,
            Format.diff: FileExt.diff,
            Format.json: FileExt.json,
            Format.csv: FileExt.csv,
            Format.npz: FileExt.npz,
            Format.log: FileExt.log,
            Format.python: FileExt.py,
            Format.pdf: FileExt.pdf,
            Format.docx: FileExt.docx,
            Format.jpeg: FileExt.jpg,
            Format.png: FileExt.png,
            Format.svg: FileExt.svg,
            Format.mp3: FileExt.mp3,
            Format.m4a: FileExt.m4a,
            Format.mp4: FileExt.mp4,
        }

        return format_to_file_ext.get(self, None)

    @classmethod
    def _init_mime_type_map(cls):
        Format._mime_type_map = {
            None: Format.url,  # URLs don't have a specific MIME type
            "text/plain": Format.plaintext,
            "text/markdown": Format.markdown,
            "text/x-markdown": Format.markdown,
            "text/html": Format.html,
            "text/diff": Format.diff,
            "text/x-diff": Format.diff,
            "application/yaml": Format.yaml,
            "application/x-yaml": Format.yaml,
            "text/x-python": Format.python,
            "application/json": Format.json,
            "text/csv": Format.csv,
            "application/x-npz": Format.npz,
            "application/pdf": Format.pdf,
            "application/vnd.openxmlformats-officedocument.wordprocessingml.document": Format.docx,
            "image/jpeg": Format.jpeg,
            "image/png": Format.png,
            "image/svg+xml": Format.svg,
            "audio/mpeg": Format.mp3,
            "audio/mp3": Format.mp3,
            "audio/mp4": Format.m4a,
            "video/mp4": Format.mp4,
            "application/octet-stream": Format.binary,
        }

    @property
    def mime_type(self) -> MimeType | None:
        """
        MIME type for the format, or None if not recognized.
        """
        for mime_type, format in self._mime_type_map.items():
            if format == self and mime_type:
                return MimeType(mime_type)
        return None

    @classmethod
    def from_mime_type(cls, mime_type: MimeType | None) -> Format | None:
        """
        Format from mime type.
        """
        return cls._mime_type_map.get(mime_type)

    def __str__(self):
        return self.name


Format._init_mime_type_map()


@dataclass(frozen=True)
class FileFormatInfo:
    file_ext: FileExt | None
    """File extension, if recognized."""

    format: Format | None
    """Format, if recognized."""

    mime_type: MimeType | None
    """Raw mime type, which may include more formats than the ones above."""

    @property
    def is_text(self) -> bool:
        return bool(
            self.file_ext
            and self.file_ext.is_text
            or self.format
            and self.format.is_text
            or self.mime_type
            and (
                self.mime_type.startswith("text")
                or self.mime_type.startswith("application/yaml")
                or self.mime_type.startswith("application/json")
                or self.mime_type.startswith("application/toml")
                # .js, .jsx, .ts, .tsx are all application/javascript
                or self.mime_type.startswith("application/javascript")
                or self.mime_type.startswith("application/xml")
                or self.mime_type
                and mime_type_is_text(self.mime_type)
            )
        )

    @property
    def is_image(self) -> bool:
        return bool(
            self.file_ext
            and self.file_ext.is_image
            or self.format
            and self.format.is_image
            or self.mime_type
            and self.mime_type.startswith("image")
        )

    def as_str(self) -> str:
        if self.format and self.mime_type:
            return f"{self.format.value} ({self.mime_type})"
        elif self.format:
            return self.format.value
        elif self.mime_type:
            return self.mime_type
        else:
            return "unrecognized"

    def __str__(self) -> str:
        return self.as_str()


def _guess_format(file_ext: FileExt | None, mime_type: MimeType | None) -> Format | None:
    format = None
    if file_ext:
        format = Format.guess_by_file_ext(file_ext)
    if not format and mime_type:
        format = Format.from_mime_type(mime_type)
    return format


def guess_format_by_name(path: str | Path) -> Format | None:
    """
    Fast guess of file format by the file name only.
    """
    file_ext = parse_file_ext(path)
    return Format.guess_by_file_ext(file_ext) if file_ext else None


def file_format_info(path: str | Path) -> FileFormatInfo:
    """
    Full info on the file format path and content (file extension and file content).
    """
    path = Path(path)
    file_ext = parse_file_ext(path)
    mime_type = detect_mime_type(path)
    format = _guess_format(file_ext, mime_type)
    final_mime_type = format.mime_type if format else mime_type
    return FileFormatInfo(file_ext, format, final_mime_type)


def detect_file_format(path: str | Path) -> Format | None:
    """
    Detect best guess at file format based on file extension and file content.
    """
    return file_format_info(path).format


def detect_media_type(filename: str | Path) -> MediaType:
    """
    Get media type (text, image, video etc.) based on file content (libmagic).
    """
    fmt = detect_file_format(filename)
    media_type = fmt.media_type if fmt else MediaType.binary
    return media_type


def choose_file_ext(url_or_path: Url | Path | str) -> FileExt | None:
    """
    Pick a suffix to reflect the type of the content. Recognizes known file
    extensions, then tries libmagic, then gives up.
    """

    def file_ext_for(path: Path) -> FileExt | None:
        fmt = detect_file_format(path)
        return fmt.file_ext if fmt else None

    ext = None
    if isinstance(url_or_path, Path):
        ext = parse_file_ext(url_or_path) or file_ext_for(url_or_path)
    elif is_file_url(url_or_path):
        path = parse_file_url(url_or_path)
        if path:
            ext = parse_file_ext(path) or file_ext_for(path)
    else:
        ext = parse_file_ext(url_or_path)

    return ext
