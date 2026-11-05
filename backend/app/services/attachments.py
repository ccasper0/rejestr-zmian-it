"""Attachments of a change (CLAUDE.md 4.1, 6.5; ADR 0013 §4).

- Files live in ``STORAGE_PATH`` under ``attachments/{company_id}/{attachment_id}``: the
  user's file name is never part of a path (no path traversal), it is only stored
  (sanitized) in the database and sent back in ``Content-Disposition``.
- SHA-256 and size are computed while the upload is streamed to a temporary file; above
  ``ATTACHMENT_MAX_BYTES`` the upload is refused (413) and the file removed.
- Rows are append-only (``app_rw``: SELECT, INSERT; trigger against UPDATE / DELETE): a
  new version of a file is a new attachment. The audit entry (``entity_type =
  attachment``, ``action = attach``) carries the change, file name, size and sha256.
- If the transaction fails after the file was written, the file is removed; a failure of
  the final COMMIT may leave an orphan file without a row (harmless: never served).
- The stored type is DETECTED from the file content (``app.services.file_types``), never
  taken from the client's ``Content-Type``; a type outside ``ATTACHMENT_ALLOWED_TYPES``
  is refused with 415 ``attachment.type_not_allowed`` and the file removed (ADR 0019 §3).
"""

from __future__ import annotations

import asyncio
import hashlib
import os
import re
import unicodedata
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import BinaryIO
from uuid import UUID, uuid4

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.audit import AuditAction, EntityType
from app.domain.companies import CompanyStatus
from app.errors import ProblemError
from app.models import Attachment, Change, Company
from app.services import audit, file_types
from app.services.changes import ChangeActor, company_archived, db_now, flush_guarded, not_found

CHUNK_SIZE = 64 * 1024
FILENAME_MAX_LENGTH = 255
DEFAULT_FILENAME = "plik"
DEFAULT_CONTENT_TYPE = "application/octet-stream"
_MIME_PART = r"[a-z0-9][a-z0-9!#$&^_.+-]{0,126}"
_CONTENT_TYPE_RE = re.compile(rf"^{_MIME_PART}/{_MIME_PART}$")

Reader = Callable[[int], Awaitable[bytes]]


def sanitize_filename(name: str | None) -> str:
    """The last path component, without control/format characters, at most 255 chars."""
    base = (name or "").replace("\\", "/").rsplit("/", 1)[-1]
    base = unicodedata.normalize("NFC", base)
    base = "".join(ch for ch in base if unicodedata.category(ch)[0] not in {"C", "Z"} or ch == " ")
    base = base.strip()
    if base in {"", ".", ".."}:
        return DEFAULT_FILENAME
    if len(base) > FILENAME_MAX_LENGTH:
        stem, dot, extension = base.rpartition(".")
        if dot and 0 < len(extension) <= 16 and stem:
            base = stem[: FILENAME_MAX_LENGTH - len(extension) - 1] + "." + extension
        else:
            base = base[:FILENAME_MAX_LENGTH]
    return base


def normalize_content_type(value: str | None) -> str:
    """``type/subtype`` in lower case without parameters, else ``application/octet-stream``."""
    if not value:
        return DEFAULT_CONTENT_TYPE
    main = value.split(";", 1)[0].strip().lower()
    return main if _CONTENT_TYPE_RE.fullmatch(main) else DEFAULT_CONTENT_TYPE


def storage_key(company_id: UUID, attachment_id: UUID) -> str:
    return f"attachments/{company_id}/{attachment_id}"


def resolve(storage_root: Path, key: str) -> Path:
    """The file of ``key`` inside ``storage_root`` (never outside it)."""
    root = storage_root.resolve()
    path = (root / key).resolve()
    if not path.is_relative_to(root):  # pragma: no cover - keys are generated, never input
        raise ValueError("storage key outside the storage root")
    return path


def too_large(max_bytes: int) -> ProblemError:
    return ProblemError(
        status=413,
        code="attachment.too_large",
        detail=f"Załącznik jest zbyt duży (maksymalnie {max_bytes} bajtów).",
        extra={"max_bytes": max_bytes},
    )


def type_not_allowed(detected: str, allowed: frozenset[str]) -> ProblemError:
    names = ", ".join(sorted({file_types.label(t) for t in allowed}))
    return ProblemError(
        status=415,
        code="attachment.type_not_allowed",
        detail=(
            f"Niedozwolony typ pliku ({file_types.label(detected)}). "
            f"Dozwolone typy załączników: {names}."
        ),
        extra={"detected_type": detected, "allowed_types": sorted(allowed)},
    )


def attachment_not_found() -> ProblemError:
    return ProblemError(
        status=404, code="attachment.not_found", detail="Nie znaleziono załącznika."
    )


@dataclass(frozen=True, slots=True)
class _Written:
    size: int
    sha256: str


def _open(path: Path) -> BinaryIO:
    path.parent.mkdir(parents=True, exist_ok=True)
    return path.open("xb")


async def _write(reader: Reader, path: Path, max_bytes: int) -> _Written:
    digest = hashlib.sha256()
    size = 0
    handle = await asyncio.to_thread(_open, path)
    try:
        while chunk := await reader(CHUNK_SIZE):
            size += len(chunk)
            if size > max_bytes:
                raise too_large(max_bytes)
            digest.update(chunk)
            await asyncio.to_thread(handle.write, chunk)
        await asyncio.to_thread(handle.flush)
        await asyncio.to_thread(os.fsync, handle.fileno())
    finally:
        await asyncio.to_thread(handle.close)
    return _Written(size=size, sha256=digest.hexdigest())


def _remove(path: Path) -> None:
    path.unlink(missing_ok=True)


async def _change(session: AsyncSession, company_id: UUID, change_id: UUID) -> Change:
    change = (
        await session.execute(
            select(Change).where(Change.company_id == company_id, Change.id == change_id)
        )
    ).scalar_one_or_none()
    if change is None:
        raise not_found()
    return change


async def add_attachment(
    session: AsyncSession,
    *,
    actor: ChangeActor,
    company: Company,
    change_id: UUID,
    filename: str | None,
    content_type: str | None,
    reader: Reader,
    storage_root: Path,
    max_bytes: int,
    allowed_types: frozenset[str] | None = None,
    now: datetime | None = None,
) -> Attachment:
    """Store the uploaded file and its row; the audit entry is in the company chain."""
    if company.status == CompanyStatus.ARCHIVED:
        raise company_archived()
    change = await _change(session, company.id, change_id)
    attachment_id = uuid4()
    key = storage_key(company.id, attachment_id)
    final = resolve(storage_root, key)
    partial = final.with_name(final.name + ".part")
    written = False
    try:
        result = await _write(reader, partial, max_bytes)
        if result.size == 0:
            raise ProblemError(
                status=422,
                code="attachment.empty",
                detail="Przesłany plik jest pusty.",
                extra={"fields": ["file"]},
            )
        allowed = (
            allowed_types
            if allowed_types is not None
            else frozenset(file_types.DEFAULT_ALLOWED_TYPES)
        )
        detected = await asyncio.to_thread(file_types.detect_file_type, partial, filename)
        if detected not in allowed:
            raise type_not_allowed(detected, allowed)
        await asyncio.to_thread(os.replace, partial, final)
        written = True
        clock = now or await db_now(session)
        attachment = Attachment(
            id=attachment_id,
            company_id=company.id,
            change_id=change.id,
            filename=sanitize_filename(filename),
            content_type=detected,
            size=result.size,
            sha256=result.sha256,
            storage_key=key,
            uploaded_by_id=actor.user_id,
            created_at=clock,
            updated_at=clock,
        )
        session.add(attachment)
        await flush_guarded(session)
        await audit.record(
            session,
            company_id=company.id,
            actor=actor.audit,
            entity_type=EntityType.ATTACHMENT,
            entity_id=attachment.id,
            action=AuditAction.ATTACH,
            context={
                "change_id": change.id,
                "number": change.number,
                "filename": attachment.filename,
                "content_type": attachment.content_type,
                "declared_content_type": normalize_content_type(content_type),
                "size": attachment.size,
                "sha256": attachment.sha256,
            },
        )
    except BaseException:
        await asyncio.to_thread(_remove, partial)
        if written:
            await asyncio.to_thread(_remove, final)
        raise
    return attachment


async def list_attachments(
    session: AsyncSession, company_id: UUID, change_id: UUID
) -> list[Attachment]:
    await _change(session, company_id, change_id)
    rows = await session.execute(
        select(Attachment)
        .where(Attachment.company_id == company_id, Attachment.change_id == change_id)
        .order_by(Attachment.created_at, Attachment.id)
    )
    return list(rows.scalars().all())


async def get_attachment(
    session: AsyncSession, company_id: UUID, change_id: UUID, attachment_id: UUID
) -> Attachment:
    await _change(session, company_id, change_id)
    attachment = (
        await session.execute(
            select(Attachment).where(
                Attachment.company_id == company_id,
                Attachment.change_id == change_id,
                Attachment.id == attachment_id,
            )
        )
    ).scalar_one_or_none()
    if attachment is None:
        raise attachment_not_found()
    return attachment


async def record_download(
    session: AsyncSession, *, actor: ChangeActor, attachment: Attachment
) -> None:
    """Every download is in the company chain (owner decision 2026-10-29, ADR 0013 §4).

    Written in the request transaction, committed BEFORE the file is sent: a download
    that could not be recorded is not served."""
    await audit.record(
        session,
        company_id=attachment.company_id,
        actor=actor.audit,
        entity_type=EntityType.ATTACHMENT,
        entity_id=attachment.id,
        action=AuditAction.DOWNLOAD,
        context={
            "change_id": attachment.change_id,
            "filename": attachment.filename,
            "size": attachment.size,
            "sha256": attachment.sha256,
        },
    )
