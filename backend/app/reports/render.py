"""HTML (Jinja2) and PDF (WeasyPrint) rendering of the reports (CLAUDE.md §9, ADR 0017 §5).

The templates receive ONLY the report data that was hashed into ``data_sha256`` (plain
JSON, :func:`app.domain.canonical.to_json_value`) plus the report number and the hash for
the page footer - the PDF cannot show anything the hash does not cover.

Fonts: IBM Plex Sans / Mono from ``app/reports/fonts`` (OFL), loaded through
``@font-face`` - never system fonts. The URL fetcher serves only files of that directory,
so a report can never make WeasyPrint read another local file or a network resource.

WeasyPrint is imported lazily: it needs Pango/HarfBuzz at import time (present in the
Docker image and on CI; on a bare Windows host it is not), and only rendering needs it.
"""

from __future__ import annotations

import importlib
from collections.abc import Callable, Mapping
from functools import lru_cache
from pathlib import Path
from typing import Any
from urllib.parse import unquote, urlparse
from urllib.request import url2pathname

from jinja2 import Environment, FileSystemLoader, StrictUndefined, select_autoescape
from markupsafe import Markup

from app.reports import labels

REPORTS_DIR = Path(__file__).resolve().parent
TEMPLATES_DIR = REPORTS_DIR / "templates"
FONTS_DIR = REPORTS_DIR / "fonts"

PdfRenderer = Callable[[str], bytes]
"""HTML text -> PDF bytes (synchronous; callers run it in a worker thread)."""

TEMPLATES: Mapping[str, str] = {
    "register": "register.html",
    "change_card": "change_card.html",
}


class ReportRenderError(RuntimeError):
    """The PDF could not be rendered (WeasyPrint missing or failing)."""


def _dt_lines(value: Any) -> Markup:
    """Date and time on two lines (narrow table columns); escaped text + ``<br>``."""
    return Markup("<br>").join(labels.format_dt(value).split(" "))


def _short_hash(value: Any, length: int = 12) -> str:
    text = str(value or "")
    return text[:length] + "…" if len(text) > length else text


@lru_cache(maxsize=1)
def environment() -> Environment:
    env = Environment(
        loader=FileSystemLoader(str(TEMPLATES_DIR)),
        autoescape=select_autoescape(["html", "xml"], default=True),
        undefined=StrictUndefined,
        trim_blocks=True,
        lstrip_blocks=True,
    )
    env.filters.update(
        dt=labels.format_dt,
        dt_lines=_dt_lines,
        status=labels.status_label,
        change_type=labels.type_label,
        risk=labels.risk_label,
        roles=labels.roles_label,
        yes_no=labels.yes_no,
        action_noun=labels.action_noun,
        short_hash=_short_hash,
        or_dash=lambda value: value if value not in (None, "", []) else labels.EMPTY,
    )
    env.globals.update(
        DEVIATION_TITLES=labels.DEVIATION_TITLES,
        DEVIATION_SHORT=labels.DEVIATION_SHORT,
        PERIOD_BY_LABELS=labels.PERIOD_BY_LABELS,
        EMPTY=labels.EMPTY,
        SYSTEM_APPROVER=labels.SYSTEM_APPROVER,
    )
    return env


def render_html(kind: str, data: Mapping[str, Any], *, number: str, data_sha256: str) -> str:
    """The report page as HTML; ``data`` = the hashed report data (plain JSON)."""
    template = environment().get_template(TEMPLATES[kind])
    return template.render(data=data, number=number, data_sha256=data_sha256)


def allowed_font_file(url: str) -> Path:
    """The font file behind a ``file:`` URL - only files of ``FONTS_DIR`` are allowed."""
    parsed = urlparse(url)
    if parsed.scheme != "file":
        raise ReportRenderError(f"resource not allowed in a report: {parsed.scheme}:")
    resolved = Path(url2pathname(unquote(parsed.path))).resolve()
    fonts = FONTS_DIR.resolve()
    if not resolved.is_relative_to(fonts) or not resolved.is_file():
        raise ReportRenderError("resource not allowed in a report")
    return resolved


def _fetcher() -> Any:
    """A WeasyPrint URL fetcher serving only the bundled fonts; any other resource stops
    the rendering (``fail_on_errors``), so a missing font never silently falls back to a
    system font."""
    from weasyprint.urls import URLFetcher, URLFetcherResponse  # type: ignore[import-untyped]

    class FontsOnlyFetcher(URLFetcher):  # type: ignore[misc]
        def fetch(self, url: str, headers: Any = None) -> Any:
            path = allowed_font_file(url)
            return URLFetcherResponse(
                path.as_uri(), path.read_bytes(), {"Content-Type": "font/woff"}
            )

    return FontsOnlyFetcher(allowed_protocols={"file"}, fail_on_errors=True)


def weasyprint_pdf(html: str) -> bytes:
    """Render with WeasyPrint (A4, fonts from ``FONTS_DIR``; see the CSS in the templates)."""
    try:
        from weasyprint import HTML  # type: ignore[import-untyped]
        from weasyprint.text.fonts import FontConfiguration  # type: ignore[import-untyped]
    except (ImportError, OSError) as exc:  # pragma: no cover - depends on the host
        raise ReportRenderError(f"WeasyPrint is not available: {exc}") from exc
    fonts = FontConfiguration()
    document = HTML(string=html, base_url=FONTS_DIR.as_uri() + "/", url_fetcher=_fetcher())
    pdf: bytes = document.write_pdf(font_config=fonts)
    return pdf


def weasyprint_available() -> bool:
    try:
        importlib.import_module("weasyprint")
    except (ImportError, OSError):
        return False
    return True
