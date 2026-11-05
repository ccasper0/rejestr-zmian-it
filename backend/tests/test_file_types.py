"""Content-based attachment type detection and the whitelist setting (ADR 0019 §3)."""

from __future__ import annotations

import codecs
import io
import zipfile
from pathlib import Path

import pytest
from pydantic import ValidationError

from app.services import file_types as ft
from tests.conftest import make_settings


def detect(data: bytes, filename: str | None = None) -> str:
    return ft.detect_stream(io.BytesIO(data), filename)


def zip_bytes(entries: dict[str, bytes | str]) -> bytes:
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w") as archive:
        for name, content in entries.items():
            archive.writestr(name, content)
    return buffer.getvalue()


@pytest.mark.parametrize(
    ("data", "filename", "expected"),
    [
        (b"%PDF-1.7\n%\xe2\xe3", "a.pdf", ft.PDF),
        (b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR", "a.png", ft.PNG),
        (b"\xff\xd8\xff\xe0\x00\x10JFIF", "a.jpg", ft.JPEG),
        (b"GIF89a\x01\x00", "a.gif", ft.GIF),
        (b"RIFF\x00\x00\x00\x00WEBPVP8 ", "a.webp", ft.WEBP),
        (b"\x1f\x8b\x08\x00", "a.tar.gz", ft.GZIP),
        (b"7z\xbc\xaf\x27\x1c\x00\x04", "a.7z", ft.SEVEN_ZIP),
        (b"\xd0\xcf\x11\xe0\xa1\xb1\x1a\xe1\x00", "mail.msg", ft.MSG),
        (b"\xd0\xcf\x11\xe0\xa1\xb1\x1a\xe1\x00", "stary.doc", ft.OLE),
        (b"MZ\x90\x00\x03\x00\x00\x00", "faktura.pdf", ft.EXE),
        (b"\x7fELF\x02\x01\x01\x00", "skrypt.txt", ft.ELF),
        (b"\x00\x01\x02\x03binary", "dane.txt", ft.UNKNOWN),
        (b"", "pusty.txt", ft.UNKNOWN),
    ],
)
def test_binary_signatures(data: bytes, filename: str, expected: str) -> None:
    assert detect(data, filename) == expected


@pytest.mark.parametrize(
    ("data", "filename", "expected"),
    [
        ("zażółć gęślą jaźń\r\n\tlinia 2\x1b[0m\n".encode(), "log.log", ft.TEXT),
        ("zażółć".encode("cp1250"), "stary.txt", ft.TEXT),  # legacy 8-bit text
        (b"a;b\n1;2\n", "lista.csv", ft.CSV),
        (b'{"a": 1}', "dane.JSON", ft.JSON),
        (b"<?xml version='1.0'?><root/>", "dane.xml", ft.XML),
        (b"<?xml version='1.0'?><root/>", "bez_rozszerzenia", ft.XML),
        (b"From: a@example.com\r\nSubject: x\r\n\r\nbody", "wiadomosc.eml", ft.EML),
        (codecs.BOM_UTF16_LE + "a;b\r\nżółw;1\r\n".encode("utf-16-le"), "excel.csv", ft.CSV),
        (b"MZ to tylko tekst", "notatka.txt", ft.TEXT),  # two-byte signature, but text
        (b"BMW - raport", "auto.txt", ft.TEXT),
    ],
)
def test_text_types(data: bytes, filename: str, expected: str) -> None:
    assert detect(data, filename) == expected


@pytest.mark.parametrize(
    "data",
    [
        b"<!DOCTYPE html><html><body>x</body></html>",
        b"  <html><script>alert(1)</script>",
        b"<script>alert(1)</script>",
        codecs.BOM_UTF8 + b"<HTML>",
    ],
)
def test_html_is_recognised_whatever_the_extension(data: bytes) -> None:
    assert detect(data, "zrzut.txt") == ft.HTML
    assert detect(data, "dane.csv") == ft.HTML


def test_svg_is_recognised() -> None:
    svg = b'<?xml version="1.0"?>\n<svg xmlns="http://www.w3.org/2000/svg"><script/></svg>'
    assert detect(svg, "rysunek.xml") == ft.SVG
    assert detect(b"<svg onload=alert(1)>", "a.txt") == ft.SVG


def test_binary_byte_late_in_the_file_makes_it_binary() -> None:
    data = b"a" * (ft.HEAD_SIZE * 20) + b"\x00"
    assert detect(data, "duzy.log") == ft.UNKNOWN


def test_invalid_utf16_is_not_text() -> None:
    assert detect(codecs.BOM_UTF16_LE + b"a\x00\x00", "x.txt") == ft.UNKNOWN
    assert detect(codecs.BOM_UTF16_LE + "a\x01".encode("utf-16-le"), "x.txt") == ft.UNKNOWN


def test_zip_based_documents() -> None:
    ooxml = {"[Content_Types].xml": "<Types/>", "_rels/.rels": "x"}
    assert detect(zip_bytes({**ooxml, "word/document.xml": "x"}), "a.zip") == ft.DOCX
    assert detect(zip_bytes({**ooxml, "xl/workbook.xml": "x"}), "a") == ft.XLSX
    assert detect(zip_bytes({**ooxml, "ppt/presentation.xml": "x"}), "a") == ft.PPTX
    assert detect(zip_bytes({"mimetype": ft.ODT, "content.xml": "x"}), "a") == ft.ODT
    assert detect(zip_bytes({"mimetype": ft.ODS}), "a") == ft.ODS
    assert detect(zip_bytes({"mimetype": "text/html"}), "a.odt") == ft.ZIP
    assert detect(zip_bytes({"logi/app.log": "x"}), "logi.docx") == ft.ZIP
    assert detect(b"PK\x03\x04broken", "a.docx") == ft.ZIP
    assert detect(b"PK\x05\x06" + b"\x00" * 18, "pusty.zip") == ft.ZIP


def test_detect_file_type_reads_the_file(tmp_path: Path) -> None:
    path = tmp_path / "plik.part"
    path.write_bytes(b"%PDF-1.4")
    assert ft.detect_file_type(path, "raport.pdf") == ft.PDF


def test_labels() -> None:
    assert ft.label(ft.DOCX) == "DOCX"
    assert ft.label("application/x-nieznany") == "application/x-nieznany"
    assert set(ft.LABELS) == ft.KNOWN_TYPES


def test_default_whitelist() -> None:
    allowed = make_settings().attachment_allowed_types
    assert allowed == frozenset(ft.DEFAULT_ALLOWED_TYPES)
    assert {ft.PDF, ft.PNG, ft.JPEG, ft.TEXT, ft.CSV, ft.DOCX, ft.XLSX, ft.ZIP} <= allowed
    assert not {ft.HTML, ft.SVG, ft.EXE, ft.ELF, ft.UNKNOWN, ft.OLE} & allowed


def test_whitelist_from_environment(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("ATTACHMENT_ALLOWED_TYPES", " application/PDF , text/plain,, ")
    settings = make_settings()
    assert settings.attachment_allowed_types == frozenset({ft.PDF, ft.TEXT})


@pytest.mark.parametrize("value", ["application/pdf,application/x-sh", "text/html;"])
def test_whitelist_rejects_unknown_types(value: str) -> None:
    with pytest.raises(ValidationError, match="ATTACHMENT_ALLOWED_TYPES"):
        make_settings(attachment_allowed_types=value)


@pytest.mark.parametrize("value", ["", " , "])
def test_empty_whitelist_variable_means_default(value: str) -> None:
    allowed = make_settings(attachment_allowed_types=value).attachment_allowed_types
    assert allowed == frozenset(ft.DEFAULT_ALLOWED_TYPES)


def test_empty_whitelist_list_is_refused() -> None:
    with pytest.raises(ValueError, match="must not be empty"):
        ft.parse_allowed_types([" "])
