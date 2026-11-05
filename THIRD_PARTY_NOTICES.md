# Third-party notices

Rejestr zmian IT is licensed under the [Apache License 2.0](LICENSE). It uses
the third-party components listed below. Each component is the property of its
respective authors and is distributed under its own license; the license texts
are included in the packages themselves (PyPI, pub.dev, container images).

Versions are the ones locked at the time of writing (`backend/uv.lock`,
`frontend/pubspec.lock`); check the lock files for the current state.

## Bundled in this repository

| Component | License | Where |
|---|---|---|
| IBM Plex Sans, IBM Plex Mono (© IBM Corp.) | SIL Open Font License 1.1 | `backend/app/reports/fonts/`, `frontend/assets/fonts/` (`OFL.txt` next to the files) |

## Backend (Python, runtime)

| Package | License |
|---|---|
| FastAPI | MIT |
| Starlette | BSD-3-Clause |
| Uvicorn | BSD-3-Clause |
| Pydantic, pydantic-core, pydantic-settings | MIT |
| SQLAlchemy | MIT |
| asyncpg | Apache-2.0 |
| Alembic | MIT |
| arq | MIT |
| redis-py | MIT |
| Jinja2, MarkupSafe | BSD-3-Clause |
| python-multipart | Apache-2.0 |
| PyJWT | MIT |
| argon2-cffi | MIT |
| tzdata | Apache-2.0 |
| WeasyPrint (extra `reports`) | BSD-3-Clause |

Development-only tools (pytest, pytest-asyncio, pytest-cov, httpx,
testcontainers, ruff, mypy, pypdf) are not part of the runtime image.

## Frontend (Flutter / Dart)

| Package | License |
|---|---|
| Flutter SDK (incl. CanvasKit served from the image) | BSD-3-Clause |
| dio | MIT |
| riverpod, flutter_riverpod | MIT |
| freezed_annotation | MIT |
| go_router | BSD-3-Clause |
| intl | BSD-3-Clause |
| json_annotation | BSD-3-Clause |
| cupertino_icons | MIT |
| timezone | BSD-2-Clause |
| data_table_2 | BSD-3-Clause |
| web | BSD-3-Clause |

Code generators (build_runner, freezed, json_serializable) and lints are
development-only.

## Container images and tools (not distributed with this repository)

| Component | License |
|---|---|
| PostgreSQL (`postgres:16-alpine`) | PostgreSQL License |
| Valkey (`valkey/valkey:8-alpine`, Redis-compatible job queue) | BSD-3-Clause |
| nginx | BSD-2-Clause |
| Python (`python:3.13-slim`) | PSF License |
| age (backup encryption, optional) | BSD-3-Clause |

The job queue (arq) uses Valkey instead of Redis 7.4+, whose server is
source-available (RSALv2/SSPLv1); any Redis-protocol server works via
`REDIS_URL`.
