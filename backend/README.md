# Backend — Rejestr zmian administracyjnych IT

FastAPI + SQLAlchemy (async) + Alembic + arq. Specyfikacja: `../CLAUDE.md`.

```bash
uv sync --all-extras          # extra "reports" = WeasyPrint (wymaga Pango/GTK w runtime)
uv run uvicorn app.main:app --reload
uv run pytest -q              # testy z markerem `db` wymagają działającego Dockera
uv run ruff check . && uv run ruff format --check . && uv run mypy app
uv run python -m app.cli --help
uv run python -m app.cli seed-dictionaries   # słowniki startowe (także prod)
uv run python -m app.cli seed                # dane przykładowe (tylko APP_ENV=dev)
uv run python -m app.cli verify-audit --company ALFA   # lub --global; kod 0 = spójny, 1 = naruszony/błąd
uv run arq app.worker.WorkerSettings
```

Na Windows WeasyPrint instaluje się, ale jego import wymaga bibliotek GTK/Pango
(https://doc.courtbouillon.org/weasyprint/stable/first_steps.html#windows).
Pełne środowisko (PDF) jest w obrazie Docker.

## Testy z bazą danych

Testy z markerem `db` uruchamiają PostgreSQL 16 (testcontainers) z tym samym
bootstrapem co produkcja: katalog `deploy/postgres/init` (role `app_owner`/`app_rw`
z `roles.psql`) jest montowany jako `/docker-entrypoint-initdb.d`, następnie
`alembic upgrade head` działa jako `app_owner`. Kod aplikacji jest testowany jako
`app_rw` (bez `BYPASSRLS`, nie właściciel tabel), więc RLS i uprawnienia do
`audit_log` działają jak w produkcji. Fixture: `db_urls`, `rw_engine`, `owner_engine`
w `tests/conftest.py`.
