"""RFC 9457 problem details (``application/problem+json``) — the single API error format.

Conventions (CLAUDE.md 8, 11.8):
- ``code``: stable English machine code, e.g. ``change.invalid_transition``;
- ``type``: ``urn:rejestr:problem:{code}``;
- ``detail``: Polish, user-facing message;
- ``request_id``: id of the request (also in the ``X-Request-ID`` header), for support/audit;
- extension members (e.g. ``current_version``) are allowed but never override standard ones.
"""

from __future__ import annotations

import logging
from collections.abc import Mapping
from http import HTTPStatus
from typing import Any, cast

from fastapi import FastAPI, Request
from fastapi.encoders import jsonable_encoder
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.request_context import REQUEST_ID_HEADER, request_id_from_scope

logger = logging.getLogger(__name__)

PROBLEM_JSON = "application/problem+json"
PROBLEM_TYPE_PREFIX = "urn:rejestr:problem:"

_STANDARD_MEMBERS = frozenset(
    {"type", "title", "status", "detail", "instance", "code", "request_id"}
)

_POLISH_TITLES: dict[int, str] = {
    400: "Nieprawidłowe żądanie",
    401: "Brak uwierzytelnienia",
    403: "Brak uprawnień",
    404: "Nie znaleziono",
    405: "Niedozwolona metoda",
    409: "Konflikt",
    413: "Zbyt duże żądanie",
    415: "Nieobsługiwany typ danych",
    422: "Nieprawidłowe dane",
    429: "Zbyt wiele żądań",
    500: "Błąd serwera",
    503: "Usługa niedostępna",
}

_HTTP_DEFAULTS: dict[int, tuple[str, str]] = {
    400: ("http.bad_request", "Nieprawidłowe żądanie."),
    401: ("auth.unauthenticated", "Wymagane jest zalogowanie."),
    403: ("auth.forbidden", "Brak uprawnień do wykonania tej operacji."),
    404: ("http.not_found", "Nie znaleziono zasobu."),
    405: ("http.method_not_allowed", "Metoda HTTP nie jest dozwolona dla tego zasobu."),
    406: ("http.not_acceptable", "Nieobsługiwany format odpowiedzi."),
    413: ("http.payload_too_large", "Przesłane dane są zbyt duże."),
    415: ("http.unsupported_media_type", "Nieobsługiwany typ przesłanych danych."),
    429: ("http.too_many_requests", "Zbyt wiele żądań. Spróbuj ponownie później."),
}


def _title(status: int) -> str:
    if status in _POLISH_TITLES:
        return _POLISH_TITLES[status]
    try:
        return HTTPStatus(status).phrase
    except ValueError:
        return "Błąd"


class ProblemError(Exception):
    """Raise from services/endpoints to return a problem+json response."""

    def __init__(
        self,
        *,
        status: int,
        code: str,
        detail: str,
        title: str | None = None,
        extra: Mapping[str, Any] | None = None,
        headers: Mapping[str, str] | None = None,
    ) -> None:
        super().__init__(f"{code}: {detail}")
        self.status = status
        self.code = code
        self.detail = detail
        self.title = title or _title(status)
        self.extra = dict(extra or {})
        self.headers = dict(headers or {})

    def to_body(self, instance: str | None = None) -> dict[str, Any]:
        body: dict[str, Any] = {
            k: v for k, v in jsonable_encoder(self.extra).items() if k not in _STANDARD_MEMBERS
        }
        body.update(
            type=f"{PROBLEM_TYPE_PREFIX}{self.code}",
            title=self.title,
            status=self.status,
            detail=self.detail,
            code=self.code,
        )
        if instance is not None:
            body["instance"] = instance
        return body


class ProblemResponse(JSONResponse):
    media_type = PROBLEM_JSON


def problem_response(request: Request, error: ProblemError) -> ProblemResponse:
    body = error.to_body(instance=request.url.path)
    headers = dict(error.headers)
    request_id = request_id_from_scope(request.scope)
    if request_id is not None:
        body["request_id"] = str(request_id)
        # Unhandled 500s are rendered outside RequestIdMiddleware, so set the header here too.
        headers[REQUEST_ID_HEADER] = str(request_id)
    return ProblemResponse(status_code=error.status, content=body, headers=headers or None)


async def _handle_problem(request: Request, exc: Exception) -> ProblemResponse:
    return problem_response(request, cast(ProblemError, exc))


async def _handle_http(request: Request, exc: Exception) -> ProblemResponse:
    exc = cast(StarletteHTTPException, exc)
    status = exc.status_code
    code, default_detail = _HTTP_DEFAULTS.get(status, (f"http.{status}", _title(status) + "."))
    # Keep a custom detail only if someone deliberately supplied one (not the bare HTTP phrase).
    detail = default_detail
    try:
        phrase = HTTPStatus(status).phrase
    except ValueError:
        phrase = ""
    if isinstance(exc.detail, str) and exc.detail and exc.detail != phrase:
        detail = exc.detail
    error = ProblemError(status=status, code=code, detail=detail, headers=exc.headers)
    return problem_response(request, error)


async def _handle_validation(request: Request, exc: Exception) -> ProblemResponse:
    exc = cast(RequestValidationError, exc)
    errors = [
        {"loc": list(e.get("loc", ())), "msg": e.get("msg", ""), "type": e.get("type", "")}
        for e in exc.errors()
    ]
    error = ProblemError(
        status=422,
        code="request.validation_error",
        detail="Żądanie zawiera nieprawidłowe dane.",
        extra={"errors": errors},
    )
    return problem_response(request, error)


async def _handle_unexpected(request: Request, exc: Exception) -> ProblemResponse:
    logger.exception("Unhandled exception on %s %s", request.method, request.url.path)
    error = ProblemError(
        status=500,
        code="server.internal_error",
        detail="Wystąpił nieoczekiwany błąd serwera.",
    )
    return problem_response(request, error)


def install_problem_handlers(app: FastAPI) -> None:
    app.add_exception_handler(ProblemError, _handle_problem)
    app.add_exception_handler(StarletteHTTPException, _handle_http)
    app.add_exception_handler(RequestValidationError, _handle_validation)
    app.add_exception_handler(Exception, _handle_unexpected)
