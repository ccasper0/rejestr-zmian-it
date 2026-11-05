"""Content-based detection of attachment types (CLAUDE.md §12 Etap 8, ADR 0019 §3).

The ``Content-Type`` sent by the client is never trusted: the stored type of an
attachment is what :func:`detect_file_type` finds in the file itself, and only types on
the ``ATTACHMENT_ALLOWED_TYPES`` whitelist are accepted (415 ``attachment.type_not_allowed``).

Pure Python, no libmagic: binary formats by their signature ("magic bytes"), ZIP-based
office documents by the entries of the archive (``[Content_Types].xml`` + ``word/`` /
``xl/`` / ``ppt/``, OpenDocument ``mimetype``), text by the absence of binary control
bytes in the WHOLE file. Text subtypes (CSV, JSON, XML, e-mail) come from the file
extension, but markup that a browser would execute (HTML, SVG) is recognised by content
and reported as such whatever the extension says - so it can be refused.
"""

from __future__ import annotations

import codecs
import re
import zipfile
from pathlib import Path
from typing import BinaryIO, Final

HEAD_SIZE: Final = 8192
_CHUNK: Final = 64 * 1024

PDF: Final = "application/pdf"
PNG: Final = "image/png"
JPEG: Final = "image/jpeg"
GIF: Final = "image/gif"
WEBP: Final = "image/webp"
BMP: Final = "image/bmp"
TIFF: Final = "image/tiff"
ZIP: Final = "application/zip"
GZIP: Final = "application/gzip"
SEVEN_ZIP: Final = "application/x-7z-compressed"
DOCX: Final = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
XLSX: Final = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
PPTX: Final = "application/vnd.openxmlformats-officedocument.presentationml.presentation"
ODT: Final = "application/vnd.oasis.opendocument.text"
ODS: Final = "application/vnd.oasis.opendocument.spreadsheet"
ODP: Final = "application/vnd.oasis.opendocument.presentation"
MSG: Final = "application/vnd.ms-outlook"
OLE: Final = "application/x-ole-storage"  # legacy .doc/.xls/.ppt (OLE2 compound file)
EXE: Final = "application/x-msdownload"
ELF: Final = "application/x-executable"
TEXT: Final = "text/plain"
CSV: Final = "text/csv"
JSON: Final = "application/json"
XML: Final = "application/xml"
EML: Final = "message/rfc822"
HTML: Final = "text/html"
SVG: Final = "image/svg+xml"
UNKNOWN: Final = "application/octet-stream"

#: Every type the detector can report - the only values allowed in ATTACHMENT_ALLOWED_TYPES.
KNOWN_TYPES: Final = frozenset(
    {
        PDF, PNG, JPEG, GIF, WEBP, BMP, TIFF, ZIP, GZIP, SEVEN_ZIP, DOCX, XLSX, PPTX, ODT,
        ODS, ODP, MSG, OLE, EXE, ELF, TEXT, CSV, JSON, XML, EML, HTML, SVG, UNKNOWN,
    }
)  # fmt: skip

#: Default whitelist (``ATTACHMENT_ALLOWED_TYPES`` unset): documents, screenshots, logs,
#: exports and archives typical for change evidence. No executables, no HTML/SVG.
DEFAULT_ALLOWED_TYPES: Final = (
    PDF, PNG, JPEG, TEXT, CSV, JSON, XML, ZIP, DOCX, XLSX, ODT, ODS, MSG, EML,
)  # fmt: skip

#: Short user-facing names (Polish UI messages).
LABELS: Final[dict[str, str]] = {
    PDF: "PDF", PNG: "PNG", JPEG: "JPEG", GIF: "GIF", WEBP: "WebP", BMP: "BMP", TIFF: "TIFF",
    ZIP: "ZIP", GZIP: "GZIP", SEVEN_ZIP: "7z", DOCX: "DOCX", XLSX: "XLSX", PPTX: "PPTX",
    ODT: "ODT", ODS: "ODS", ODP: "ODP", MSG: "MSG (Outlook)", OLE: "dokument Office 97-2003",
    EXE: "program Windows", ELF: "program Linux", TEXT: "tekst", CSV: "CSV", JSON: "JSON",
    XML: "XML", EML: "EML (e-mail)", HTML: "HTML", SVG: "SVG", UNKNOWN: "nieznany",
}  # fmt: skip

_SIGNATURES: Final[tuple[tuple[bytes, str], ...]] = (
    (b"%PDF-", PDF),
    (b"\x89PNG\r\n\x1a\n", PNG),
    (b"\xff\xd8\xff", JPEG),
    (b"GIF87a", GIF),
    (b"GIF89a", GIF),
    (b"BM", BMP),
    (b"II*\x00", TIFF),
    (b"MM\x00*", TIFF),
    (b"\x1f\x8b", GZIP),
    (b"7z\xbc\xaf\x27\x1c", SEVEN_ZIP),
    (b"\xd0\xcf\x11\xe0\xa1\xb1\x1a\xe1", OLE),
    (b"MZ", EXE),
    (b"\x7fELF", ELF),
)
_ZIP_SIGNATURES: Final = (b"PK\x03\x04", b"PK\x05\x06")
_OPENDOCUMENT: Final = {ODT, ODS, ODP}

# C0 control bytes that never occur in text files (TAB, LF, VT, FF, CR and ESC do).
_BINARY_BYTES: Final = frozenset(
    set(range(0x00, 0x09)) | set(range(0x0E, 0x1B)) | set(range(0x1C, 0x20))
)
_BINARY_TABLE: Final = bytes(sorted(_BINARY_BYTES))
_BINARY_CHARS: Final = re.compile(
    "[" + "".join(re.escape(chr(b)) for b in sorted(_BINARY_BYTES)) + "]"
)

_TEXT_BY_EXTENSION: Final[dict[str, str]] = {
    "csv": CSV,
    "json": JSON,
    "xml": XML,
    "eml": EML,
    "html": HTML,
    "htm": HTML,
    "svg": SVG,
}


def label(content_type: str) -> str:
    return LABELS.get(content_type, content_type)


def _extension(filename: str | None) -> str:
    name = (filename or "").rsplit("/", 1)[-1]
    stem, dot, extension = name.rpartition(".")
    return extension.lower() if dot and stem else ""


def _zip_type(handle: BinaryIO) -> str:
    """docx/xlsx/pptx (OOXML) or odt/ods/odp (OpenDocument) by the archive entries."""
    try:
        with zipfile.ZipFile(handle) as archive:
            names = set(archive.namelist())
            if "mimetype" in names:
                declared = archive.read("mimetype")[:100].decode("ascii", "replace").strip()
                if declared in _OPENDOCUMENT:
                    return declared
            if "[Content_Types].xml" in names:
                prefixes = {name.split("/", 1)[0] for name in names if "/" in name}
                for prefix, kind in (("word", DOCX), ("xl", XLSX), ("ppt", PPTX)):
                    if prefix in prefixes:
                        return kind
    except (zipfile.BadZipFile, OSError, KeyError, ValueError, EOFError):
        # A truncated / broken archive is still "a ZIP" by its signature; it is the
        # uploader's evidence as is - never extracted on the server.
        return ZIP
    return ZIP


def _is_text(handle: BinaryIO, head: bytes) -> bool:
    """No binary control byte in the whole file (UTF-16 with a BOM decoded first)."""
    handle.seek(0)
    if head.startswith((codecs.BOM_UTF16_LE, codecs.BOM_UTF16_BE)):
        encoding = "utf-16"
        decoder = codecs.getincrementaldecoder(encoding)(errors="strict")
        try:
            while chunk := handle.read(_CHUNK):
                if _BINARY_CHARS.search(decoder.decode(chunk)):
                    return False
            decoder.decode(b"", final=True)
        except UnicodeDecodeError:
            return False
        return True
    while chunk := handle.read(_CHUNK):
        # bytes.translate(None, delete) removes the binary bytes: a shorter result = found.
        if len(chunk.translate(None, _BINARY_TABLE)) != len(chunk):
            return False
    return True


def _markup(head: bytes) -> str | None:
    """HTML / SVG (active content in a browser) regardless of the file extension."""
    for bom, encoding in (
        (codecs.BOM_UTF16_LE, "utf-16-le"),
        (codecs.BOM_UTF16_BE, "utf-16-be"),
        (codecs.BOM_UTF8, "utf-8"),
    ):
        if head.startswith(bom):
            text = head[len(bom) :].decode(encoding, "ignore")
            break
    else:
        text = head.decode("latin-1")
    sample = text.lstrip().lower()
    if sample.startswith(("<!doctype html", "<html", "<head", "<body", "<script", "<iframe")):
        return HTML
    if "<svg" in sample and (sample.startswith(("<svg", "<?xml", "<!doctype svg", "<!--"))):
        return SVG
    if "<script" in sample and sample.startswith("<"):
        return HTML
    return None


def _text_type(head: bytes, filename: str | None) -> str:
    markup = _markup(head)
    if markup is not None:
        return markup
    by_extension = _TEXT_BY_EXTENSION.get(_extension(filename))
    if by_extension is not None:
        return by_extension
    stripped = head.lstrip(codecs.BOM_UTF8).lstrip()
    if stripped.startswith(b"<?xml"):
        return XML
    return TEXT


def detect_stream(handle: BinaryIO, filename: str | None) -> str:
    """The type of the file in ``handle`` (seekable, opened in binary mode)."""
    handle.seek(0)
    head = handle.read(HEAD_SIZE)
    if not head:
        return UNKNOWN
    if head.startswith(_ZIP_SIGNATURES):
        handle.seek(0)
        return _zip_type(handle)
    if head[:4] == b"RIFF" and head[8:12] == b"WEBP":
        return WEBP
    for signature, kind in _SIGNATURES:
        if head.startswith(signature):
            if kind == OLE:
                # Outlook items and legacy Office files share the OLE2 container; the
                # extension decides between them (both are binary, never rendered).
                return MSG if _extension(filename) == "msg" else OLE
            if kind in {BMP, EXE} and _is_text(handle, head):
                # "BM..." / "MZ..." are also ordinary text openings (two-byte signatures).
                return _text_type(head, filename)
            return kind
    if _is_text(handle, head):
        return _text_type(head, filename)
    return UNKNOWN


def detect_file_type(path: Path, filename: str | None) -> str:
    """The type of the file at ``path``; ``filename`` only refines text subtypes."""
    with path.open("rb") as handle:
        return detect_stream(handle, filename)


def parse_allowed_types(values: list[str]) -> frozenset[str]:
    """Validate an ``ATTACHMENT_ALLOWED_TYPES`` list (unknown types = configuration error)."""
    normalized = {value.strip().lower() for value in values if value.strip()}
    unknown = sorted(normalized - KNOWN_TYPES)
    if unknown:
        raise ValueError(
            f"ATTACHMENT_ALLOWED_TYPES contains unsupported types: {', '.join(unknown)} "
            f"(supported: {', '.join(sorted(KNOWN_TYPES))})"
        )
    if not normalized:
        raise ValueError("ATTACHMENT_ALLOWED_TYPES must not be empty")
    return frozenset(normalized)
