"""Shared text types reject NUL and other control characters (422, never a 500)."""

from __future__ import annotations

from typing import Any

import pytest
from pydantic import BaseModel, ValidationError

from app.schemas.common import CONTROL_CHARACTERS_MESSAGE, SafeLine, SafeStr
from app.schemas.identity import CompanyCreate, CompanyUpdate, DevTokenIn


class _Model(BaseModel):
    line: SafeLine | None = None
    text: SafeStr | None = None


@pytest.mark.parametrize(
    "value",
    ["Zla\x00Spolka", "a\x01b", "bell\x07", "esc\x1b[0m", "\x0bvt", "\x0cff", "del\x7f", "c1\x85"],
)
@pytest.mark.parametrize("field", ["line", "text"])
def test_control_characters_rejected(field: str, value: str) -> None:
    with pytest.raises(ValidationError) as info:
        _Model(**{field: value})
    error = info.value.errors()[0]
    assert error["type"] == "string_control_characters"
    assert error["msg"] == CONTROL_CHARACTERS_MESSAGE


@pytest.mark.parametrize("value", ["a\nb", "a\rb", "a\r\nb"])
def test_single_line_rejects_line_breaks(value: str) -> None:
    with pytest.raises(ValidationError):
        _Model(line=value)
    assert _Model(text=value).text == value  # multi-line text keeps them


def test_tab_and_polish_text_allowed() -> None:
    value = "Zażółć\tgęślą jaźń — „cytat” €"
    assert _Model(line=value, text=value).line == value


@pytest.mark.parametrize(
    ("schema", "data"),
    [
        (CompanyCreate, {"name": "Zla\x00Spolka", "prefix": "ZLA"}),
        (CompanyCreate, {"name": "Dobra", "prefix": "Z\x00A"}),
        (CompanyCreate, {"name": "Dobra", "prefix": "ZLA", "tax_id": "526\x00"}),
        (CompanyCreate, {"name": "Dwie\nlinie", "prefix": "ZLA"}),
        (CompanyUpdate, {"name": "Zla\x00Spolka"}),
        (CompanyUpdate, {"tax_id": "\x00"}),
        (CompanyUpdate, {"prefix": "\x00"}),
        (DevTokenIn, {"external_id": "dev\x00admin"}),
    ],
)
def test_input_schemas_use_safe_text(schema: type[BaseModel], data: dict[str, Any]) -> None:
    with pytest.raises(ValidationError) as info:
        schema.model_validate(data)
    assert info.value.errors()[0]["msg"] == CONTROL_CHARACTERS_MESSAGE
