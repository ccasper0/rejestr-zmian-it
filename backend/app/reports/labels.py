"""Polish labels and formatting for the reports (PDF, CSV) - presentation only.

Mirrors the labels of the frontend (``frontend/lib/features/changes/presentation/
labels.dart``, ADR 0015 §7): field names, statuses, types, roles; dates in
``Europe/Warsaw`` as ``dd.MM.yyyy HH:mm`` (CLAUDE.md §11.6).
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any
from zoneinfo import ZoneInfo

WARSAW = ZoneInfo("Europe/Warsaw")
DATE_TIME_FORMAT = "%d.%m.%Y %H:%M"
EMPTY = "—"
SYSTEM_APPROVER = "system (automatycznie)"

STATUS_LABELS: dict[str, str] = {
    "draft": "Szkic",
    "pending_approval": "Do zatwierdzenia",
    "approved": "Zatwierdzona",
    "implemented": "Wdrożona",
    "verified": "Zweryfikowana",
    "rejected": "Odrzucona",
    "rolled_back": "Wycofana",
    "cancelled": "Anulowana",
}

TYPE_LABELS: dict[str, str] = {
    "standard": "Standardowa",
    "normal": "Normalna",
    "emergency": "Awaryjna",
}

RISK_LABELS: dict[str, str] = {"low": "Niskie", "medium": "Średnie", "high": "Wysokie"}

ROLE_LABELS: dict[str, str] = {
    "app_admin": "administrator",
    "approver": "zatwierdzający",
    "editor": "edytor",
    "auditor": "audytor",
    "viewer": "przeglądający",
}

FIELD_LABELS: dict[str, str] = {
    "title": "Tytuł",
    "category_id": "Kategoria",
    "subcategory_id": "Podkategoria",
    "change_type": "Typ zmiany",
    "risk": "Ryzyko",
    "description": "Opis i uzasadnienie",
    "implementation_plan": "Plan wdrożenia",
    "rollback_plan": "Plan wycofania",
    "impact": "Wpływ",
    "requirement_ref": "Podstawa / wymóg",
    "ticket_ref": "Zgłoszenie",
    "assignee_id": "Wykonawca",
    "approver_id": "Zatwierdzający",
    "verifier_id": "Weryfikujący",
    "window_start": "Okno od",
    "window_end": "Okno do",
    "ci_ids": "Obiekty (CI)",
    "status": "Status",
    "number": "Numer",
    "requested_by_id": "Zgłaszający",
    "approved_at": "Zatwierdzono",
    "approved_by_id": "Zatwierdził",
    "implemented_at": "Wdrożono",
    "verified_at": "Zweryfikowano",
    "rejected_at": "Odrzucono",
    "consent_round": "Runda zgód",
    "supersedes_change_id": "Korekta zmiany",
    "version": "Wersja",
}

USER_FIELDS = frozenset(
    {"assignee_id", "approver_id", "verifier_id", "requested_by_id", "approved_by_id"}
)
CATEGORY_FIELDS = frozenset({"category_id", "subcategory_id"})
DATETIME_FIELDS = frozenset(
    {"window_start", "window_end", "approved_at", "implemented_at", "verified_at", "rejected_at"}
)

DEVIATION_TITLES: dict[str, str] = {
    "emergency_not_approved_in_24h": "Zmiany awaryjne bez zatwierdzenia w ciągu 24 h",
    "implemented_not_verified": "Zmiany wdrożone bez weryfikacji",
    "implemented_outside_window": "Zmiany wdrożone poza zatwierdzonym oknem serwisowym",
    "rolled_back": "Zmiany wycofane",
    "approved_by_requester_or_assignee": (
        "Zmiany zatwierdzone przez zgłaszającego lub wykonawcę (błąd krytyczny)"
    ),
}

DEVIATION_SHORT: dict[str, str] = {
    "emergency_not_approved_in_24h": "awaryjna bez zatwierdzenia w 24 h",
    "implemented_not_verified": "bez weryfikacji",
    "implemented_outside_window": "poza oknem serwisowym",
    "rolled_back": "wycofana",
    "approved_by_requester_or_assignee": "zatwierdzona przez autora (BŁĄD KRYTYCZNY)",
}

TRANSITION_PHRASES: dict[str, str] = {
    "submit": "wysłał(a) do zatwierdzenia",
    "return": "zwrócił(a) do poprawy",
    "approve": "zatwierdził(a)",
    "reject": "odrzucił(a)",
    "implement": "oznaczył(a) jako wdrożoną",
    "verify": "potwierdził(a) weryfikację",
    "rollback": "wycofał(a)",
    "cancel": "anulował(a)",
    "consent": "wyraził(a) zgodę właściciela CI",
}

ACTION_NOUNS: dict[str, str] = {
    "submit": "wysłanie",
    "return": "zwrot do poprawy",
    "approve": "zatwierdzenie",
    "reject": "odrzucenie",
    "implement": "wdrożenie",
    "verify": "weryfikacja",
    "rollback": "wycofanie",
    "cancel": "anulowanie",
    "consent": "zgoda właściciela CI",
}

PERIOD_BY_LABELS: dict[str, str] = {
    "created": "data rejestracji zmiany",
    "implemented": "data wdrożenia zmiany",
}


def parse_datetime(value: Any) -> datetime | None:
    """A datetime or its canonical ISO text (``...Z``) as an aware datetime."""
    if value is None or value == "":
        return None
    if isinstance(value, datetime):
        result = value
    else:
        result = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    if result.tzinfo is None:
        result = result.replace(tzinfo=UTC)
    return result


def format_dt(value: Any) -> str:
    """``dd.MM.yyyy HH:mm`` in Europe/Warsaw; ``—`` for no value."""
    parsed = parse_datetime(value)
    if parsed is None:
        return EMPTY
    return parsed.astimezone(WARSAW).strftime(DATE_TIME_FORMAT)


def status_label(value: Any) -> str:
    return STATUS_LABELS.get(str(value), str(value)) if value else EMPTY


def type_label(value: Any) -> str:
    return TYPE_LABELS.get(str(value), str(value)) if value else EMPTY


def risk_label(value: Any) -> str:
    return RISK_LABELS.get(str(value), str(value)) if value else EMPTY


def roles_label(roles: Any) -> str:
    if not roles:
        return ""
    return ", ".join(ROLE_LABELS.get(str(r), str(r)) for r in roles)


def field_label(field: str) -> str:
    return FIELD_LABELS.get(field, field)


def action_phrase(entity_type: str, action: str, context: dict[str, Any]) -> str:
    """Polish phrase of an audit entry of a change trail ("zatwierdził(a)")."""
    if action == "transition":
        name = str(context.get("action") or "")
        if name == "submit" and context.get("auto_approved"):
            return "zatwierdził automatycznie (zmiana standardowa)"
        if name == "approve" and context.get("from_status") == context.get("to_status"):
            return "zatwierdził(a) po fakcie"
        return TRANSITION_PHRASES.get(name, "zmienił(a) status")
    filename = context.get("filename")
    phrases = {
        "create": "utworzył(a) zmianę",
        "update": "zmienił(a) dane zmiany",
        "comment": "dodał(a) komentarz",
        "attach": f"dodał(a) załącznik {filename}" if filename else "dodał(a) załącznik",
        "download": f"pobrał(a) załącznik {filename}" if filename else "pobrał(a) załącznik",
        "export": "wyeksportował(a) raport",
    }
    return phrases.get(action, action)


def action_noun(value: Any) -> str:
    return ACTION_NOUNS.get(str(value), str(value)) if value else EMPTY


def yes_no(value: Any) -> str:
    return "tak" if value else "nie"
