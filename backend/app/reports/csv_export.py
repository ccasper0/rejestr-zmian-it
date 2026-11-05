"""CSV export of the change register (CLAUDE.md §8, ADR 0017 §7).

Format chosen for Microsoft Excel with Polish regional settings:

- UTF-8 with BOM (``EF BB BF``) - otherwise Excel reads the file as Windows-1250;
- separator ``;`` (the list separator of the Polish locale; ``,`` is the decimal comma);
- CRLF line endings, fields quoted only when needed (RFC 4180, ``csv.QUOTE_MINIMAL``);
- dates in Europe/Warsaw as ``dd.MM.yyyy HH:mm``; empty value = empty field;
- one header row, one row per change, columns below (fixed order);
- formula injection: a text field starting with ``=``, ``+``, ``-``, ``@``, TAB or CR is
  prefixed with an apostrophe, so Excel never evaluates user text as a formula (OWASP).

Built only from the report data hashed into ``data_sha256``.
"""

from __future__ import annotations

import csv
import io
from collections.abc import Callable, Mapping
from typing import Any

from app.reports import labels

BOM = "﻿"
SEPARATOR = ";"
_FORMULA_START = ("=", "+", "-", "@", "\t", "\r")


def _text(value: Any) -> str:
    if value is None:
        return ""
    result = str(value)
    if result.startswith(_FORMULA_START):
        return "'" + result
    return result


def _dt(value: Any) -> str:
    return "" if value is None else labels.format_dt(value)


def _join(values: Any) -> str:
    return _text(", ".join(str(v) for v in values or []))


Column = tuple[str, Callable[[Mapping[str, Any]], str]]

COLUMNS: tuple[Column, ...] = (
    ("Spółka", lambda r: _text(r["company_prefix"])),
    ("Numer", lambda r: _text(r["number"])),
    ("Tytuł", lambda r: _text(r["title"])),
    ("Kategoria", lambda r: _text(r["category"])),
    ("Podkategoria", lambda r: _text(r["subcategory"])),
    ("Typ", lambda r: labels.type_label(r["change_type"]) if r["change_type"] else ""),
    ("Ryzyko", lambda r: labels.risk_label(r["risk"]) if r["risk"] else ""),
    ("Status", lambda r: labels.status_label(r["status"])),
    ("Obiekty (CI)", lambda r: _join(r["ci"])),
    ("Zgłaszający", lambda r: _text(r["requested_by"])),
    ("Wykonawca", lambda r: _text(r["assignee"])),
    ("Zatwierdzający (wskazany)", lambda r: _text(r["approver"])),
    ("Zatwierdził", lambda r: _text(r["approved_by"])),
    ("Data zatwierdzenia", lambda r: _dt(r["approved_at"])),
    ("Okno od", lambda r: _dt(r["window_start"])),
    ("Okno do", lambda r: _dt(r["window_end"])),
    ("Data wdrożenia", lambda r: _dt(r["implemented_at"])),
    ("Weryfikujący", lambda r: _text(r["verifier"])),
    ("Data weryfikacji", lambda r: _dt(r["verified_at"])),
    ("Odstępstwa", lambda r: _join(labels.DEVIATION_SHORT.get(k, k) for k in r["deviations"])),
    ("Zgłoszenie", lambda r: _text(r["ticket_ref"])),
    ("Podstawa / wymóg", lambda r: _text(r["requirement_ref"])),
    ("Data rejestracji", lambda r: _dt(r["created_at"])),
)

HEADER = tuple(name for name, _ in COLUMNS)


def register_csv(data: Mapping[str, Any]) -> bytes:
    """The register report data (``kind = register``) as CSV bytes (UTF-8 with BOM)."""
    buffer = io.StringIO(newline="")
    writer = csv.writer(
        buffer, delimiter=SEPARATOR, quoting=csv.QUOTE_MINIMAL, lineterminator="\r\n"
    )
    writer.writerow(HEADER)
    for row in data["changes"]:
        writer.writerow([render(row) for _, render in COLUMNS])
    return (BOM + buffer.getvalue()).encode("utf-8")
