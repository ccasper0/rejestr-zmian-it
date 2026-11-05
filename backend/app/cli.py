"""Command line interface: ``python -m app.cli <command>``.

- ``seed`` — sample data (companies, users, roles, dictionaries, categories available in
  the companies, CI); refused with ``APP_ENV=prod``.
- ``seed-dictionaries`` — the reference dictionaries only (change categories of
  CLAUDE.md §13, CI types of §4.1); allowed in production (ADR 0011). Idempotent.
- ``create-admin --email E --name N [--generate-password]`` — the first app admin of a
  production installation (local accounts, ADR 0018 §8). The password is NEVER a command
  line argument (shell history, process list): it is read from the terminal (twice,
  hidden) or as one line from standard input; with ``--generate-password`` a random
  temporary password is generated, printed once, and must be changed at the first login.
  Audited as ``system`` (``context.source = "cli"``).
- ``verify-audit --company PREFIX | --global`` — recompute an audit hash chain
  (CLAUDE.md 6.4); the verification and its result are appended to the audit log as the
  ``system`` actor (``context.source = "cli"``). Exit code 0: chain intact; 1: chain
  broken, unknown company or error.

Runs with the application role (``DATABASE_URL``, ``app_rw``), so everything goes through
the same services, audit and database protections as the API. The transaction scope for
Row-Level Security is set explicitly and minimally (ADR 0009 §4).
"""

from __future__ import annotations

import argparse
import asyncio
import contextlib
import getpass
import re
import socket
import sys
from collections.abc import Sequence
from datetime import timedelta

from sqlalchemy.exc import SQLAlchemyError

from app.auth.passwords import hash_password
from app.config import Settings, get_settings
from app.db import Database, apply_company_scope
from app.domain.audit import Actor
from app.domain.companies import PREFIX_RE
from app.domain.passwords import MESSAGES, check_password
from app.errors import ProblemError
from app.schemas.identity import EMAIL_PATTERN
from app.services import audit
from app.services import companies as companies_service
from app.services import users as users_service
from app.services.seed import SeedReport, seed_all, seed_dictionaries

EXIT_OK = 0
EXIT_ERROR = 1
EMAIL_RE = re.compile(EMAIL_PATTERN)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="python -m app.cli", description="Rejestr zmian IT — narzędzia administracyjne"
    )
    sub = parser.add_subparsers(dest="command", required=True, metavar="COMMAND")

    sub.add_parser("seed", help="Załaduj dane przykładowe (CLAUDE.md §11.7)")
    sub.add_parser(
        "seed-dictionaries",
        help="Załaduj słowniki startowe: kategorie zmian (§13) i typy obiektów (§4.1)",
    )

    admin = sub.add_parser(
        "create-admin", help="Załóż konto administratora aplikacji (konto lokalne z hasłem)"
    )
    admin.add_argument("--email", required=True, help="Adres e-mail (login)")
    admin.add_argument("--name", required=True, help="Imię i nazwisko (wyświetlana nazwa)")
    admin.add_argument(
        "--generate-password",
        action="store_true",
        help="Wygeneruj hasło tymczasowe (wypisane raz; zmiana przy pierwszym logowaniu)",
    )

    verify = sub.add_parser("verify-audit", help="Zweryfikuj łańcuch skrótów dziennika audytu")
    target = verify.add_mutually_exclusive_group(required=True)
    target.add_argument("--company", metavar="PREFIX", help="Prefiks spółki, np. ALFA")
    target.add_argument(
        "--global",
        dest="global_chain",
        action="store_true",
        help="Łańcuch globalny (zdarzenia bez spółki)",
    )
    return parser


async def _seed() -> int:
    settings = get_settings()
    if not settings.is_dev:
        print(
            "Odmowa: dane przykładowe (użytkownicy dev-*) nie mogą być ładowane przy APP_ENV=prod.",
            file=sys.stderr,
        )
        return EXIT_ERROR
    db = Database.from_settings(settings)
    try:
        report = await seed_all(db.sessionmaker, context=_operator("seed"))
    except ProblemError as exc:
        # Data the seed cannot reconcile (e.g. edited by an admin): a message, not a traceback.
        print(f"Błąd: {exc.detail} ({exc.code}).", file=sys.stderr)
        return EXIT_ERROR
    finally:
        await db.dispose()
    return _print_report(report)


def _print_report(report: SeedReport) -> int:
    for line in report.lines:
        print(f"- {line}")
    print(f"Gotowe. Nowych elementów: {report.created}.")
    return EXIT_OK


async def _seed_dictionaries() -> int:
    """Reference data (not sample data): also with ``APP_ENV=prod``. Audited as ``system``."""
    db = Database.from_settings(get_settings())
    try:
        report = await seed_dictionaries(db.sessionmaker, context=_operator("seed-dictionaries"))
    except ProblemError as exc:
        print(f"Błąd: {exc.detail} ({exc.code}).", file=sys.stderr)
        return EXIT_ERROR
    except (OSError, SQLAlchemyError) as exc:
        print(f"Błąd: nie udało się załadować słowników ({type(exc).__name__}).", file=sys.stderr)
        return EXIT_ERROR
    finally:
        await db.dispose()
    return _print_report(report)


def _operator(command: str) -> dict[str, object]:
    """Who ran the command (informational; the audit actor is ``system``)."""
    info: dict[str, object] = {"source": "cli", "command": command}
    with contextlib.suppress(OSError, KeyError, ImportError):  # no login name available
        info["os_user"] = getpass.getuser()
    with contextlib.suppress(OSError):
        info["host"] = socket.gethostname()
    return info


async def verify_audit(settings: Settings, *, prefix: str | None) -> int:
    """Verify the chain of the company ``prefix`` (``None`` = the global chain).

    Explicit, minimal RLS scope (ADR 0009 §4): the company is looked up on the admin path
    (``companies`` is visible only there without membership), then the scope is REPLACED
    by exactly that company's chain (no admin scope, no global read) for the verification
    and its audit entry. The global chain is verified with only the global read path open.
    """
    label = "globalny"
    db = Database.from_settings(settings)
    try:
        async with db.sessionmaker() as session, session.begin():
            company_id = None
            if prefix is not None:
                normalized = prefix.strip().upper()
                if not PREFIX_RE.fullmatch(normalized):
                    print(
                        f"Błąd: nieprawidłowy prefiks spółki {prefix!r} (od 2 do 8 liter A-Z).",
                        file=sys.stderr,
                    )
                    return EXIT_ERROR
                await apply_company_scope(session, [], admin_scope=True)
                company = await companies_service.get_company_by_prefix(session, normalized)
                if company is None:
                    print(f"Błąd: nie znaleziono spółki o prefiksie {normalized}.", file=sys.stderr)
                    return EXIT_ERROR
                company_id = company.id
                label = f"spółki {company.prefix} ({company.name})"
                await apply_company_scope(session, [company_id])
            else:
                await apply_company_scope(session, [], global_audit_read=True)
            outcome = await audit.verify_and_record(
                session, company_id, actor=Actor.system(), context=_operator("verify-audit")
            )
    except (OSError, SQLAlchemyError) as exc:
        print(
            f"Błąd: weryfikacja łańcucha audytu nie powiodła się ({type(exc).__name__}).",
            file=sys.stderr,
        )
        return EXIT_ERROR
    finally:
        await db.dispose()

    verification, entry = outcome.verification, outcome.entry
    result = verification.result
    if result.ok:
        print(
            f"Łańcuch audytu {label} jest spójny: zweryfikowano {result.checked} wpisów "
            f"(głowa: seq {verification.head_seq}, hash {verification.head_hash})."
        )
    else:
        print(
            f"NARUSZENIE: łańcuch audytu {label} jest naruszony. Pierwszy błędny wpis: "
            f"seq {result.first_broken_seq} (poprawnie zweryfikowano {result.checked} "
            f"wpisów przed nim)."
        )
    if entry is None:
        print(
            "UWAGA: wyniku weryfikacji nie udało się zapisać w dzienniku audytu.", file=sys.stderr
        )
    elif outcome.recorded_in == "global":
        print(
            "Wynik zapisano w łańcuchu globalnym dziennika audytu (łańcuch spółki odrzucił "
            f"wpis): seq {entry.seq}."
        )
    else:
        print(f"Wynik zapisano w dzienniku audytu: seq {entry.seq}, hash {entry.hash}.")
    return EXIT_OK if result.ok else EXIT_ERROR


def _read_password(email: str, name: str) -> str | None:
    """The new password from the terminal (twice, hidden) or one line of stdin."""
    if sys.stdin.isatty():
        first = getpass.getpass("Hasło: ")
        second = getpass.getpass("Powtórz hasło: ")
        if first != second:
            print("Błąd: hasła się różnią.", file=sys.stderr)
            return None
        password = first
    else:
        password = sys.stdin.readline().rstrip("\r\n")
    check = check_password(password, email=email, display_name=name)
    if check.problem is not None:
        print(f"Błąd: {MESSAGES[check.problem]} ({check.problem.value}).", file=sys.stderr)
        return None
    return password


async def create_admin(
    settings: Settings, *, email: str, name: str, generate: bool, password: str | None
) -> int:
    """Create a local app admin account; audited as ``system`` in the global chain."""
    email, name = email.strip(), name.strip()
    if settings.auth_mode != "local":
        print("Odmowa: konta z hasłem są używane tylko przy AUTH_MODE=local.", file=sys.stderr)
        return EXIT_ERROR
    if not EMAIL_RE.fullmatch(email) or not name:
        print("Błąd: podaj poprawny adres e-mail i niepustą nazwę.", file=sys.stderr)
        return EXIT_ERROR
    password_hash = None if generate or password is None else hash_password(password)
    db = Database.from_settings(settings)
    try:
        async with db.sessionmaker() as session, session.begin():
            await apply_company_scope(session, [])
            account = await users_service.create_local_account(
                session,
                actor=Actor.system(),
                email=email,
                display_name=name,
                is_app_admin=True,
                password_hash=password_hash,
                context=_operator("create-admin"),
                temp_password_ttl=timedelta(hours=settings.temp_password_ttl_hours),
            )
    except ProblemError as exc:
        print(f"Błąd: {exc.detail} ({exc.code}).", file=sys.stderr)
        return EXIT_ERROR
    except (OSError, SQLAlchemyError) as exc:
        print(f"Błąd: nie udało się utworzyć konta ({type(exc).__name__}).", file=sys.stderr)
        return EXIT_ERROR
    finally:
        await db.dispose()
    print(f"Utworzono administratora {account.user.display_name} <{account.user.email}>.")
    if account.temporary_password is not None:
        print(
            "Hasło tymczasowe (pokazywane TYLKO raz, zmiana przy pierwszym logowaniu): "
            f"{account.temporary_password}"
        )
    return EXIT_OK


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if args.command == "seed":
        return asyncio.run(_seed())
    if args.command == "seed-dictionaries":
        return asyncio.run(_seed_dictionaries())
    if args.command == "create-admin":
        settings = get_settings()
        password = None
        if not args.generate_password:
            password = _read_password(args.email.strip(), args.name.strip())
            if password is None:
                return EXIT_ERROR
        return asyncio.run(
            create_admin(
                settings,
                email=args.email,
                name=args.name,
                generate=args.generate_password,
                password=password,
            )
        )
    if args.command == "verify-audit":
        return asyncio.run(verify_audit(get_settings(), prefix=args.company))
    raise AssertionError(f"unhandled command {args.command!r}")  # pragma: no cover


if __name__ == "__main__":
    raise SystemExit(main())
