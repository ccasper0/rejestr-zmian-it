# Rejestr zmian IT

[![License: Apache-2.0](https://img.shields.io/badge/License-Apache_2.0-blue.svg)](LICENSE)

> **English summary.** A web application for registering, approving,
> monitoring and auditing administrative changes in the IT infrastructure of
> several companies of a group (multi-tenant). Every operation is written to an
> append-only audit log protected by a SHA-256 hash chain and database
> triggers; companies are isolated by PostgreSQL row-level security; changes
> follow a state machine with the four-eyes principle, emergency and standard
> changes; registers and change cards export to PDF/CSV with a data hash.
> Stack: FastAPI, SQLAlchemy (async), PostgreSQL 16, arq/Redis, WeasyPrint,
> Flutter web, Docker Compose, nginx. The user interface and the documentation
> are in **Polish**; code, API and comments are in English.
>
> **Status: provided "as is".** This is a personal project, maintained in spare
> time, without warranty, support or any guaranteed response (see
> [LICENSE](LICENSE), sections 7–8). It is designed to *support* processes
> under ISO/IEC 27001:2022 (A.8.32 change management, A.8.15 logging) and the
> Polish National Cybersecurity System Act (uoKSC), but using it does **not**
> by itself make an organisation compliant or certified — that remains the
> responsibility of the organisation and its auditors.
>
> Security issues: [SECURITY.md](SECURITY.md) · Contributing:
> [CONTRIBUTING.md](CONTRIBUTING.md) · Third-party licenses:
> [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md)

Aplikacja webowa do rejestrowania, zatwierdzania, monitorowania i audytowania
zmian administracyjnych w infrastrukturze IT wielu spółek grupy kapitałowej
(ISO/IEC 27001:2022 A.8.32 / A.8.15, uoKSC).

Pełna specyfikacja, model domeny, zasady pracy i plan etapów:
**[CLAUDE.md](CLAUDE.md)** (projekt powstał z pomocą Claude Code — plik jest
jednocześnie specyfikacją i instrukcją pracy dla agentów z `.claude/agents/`;
decyzje architektoniczne: `docs/decisions/`).

> **Projekt udostępniony „tak jak jest” (as is)** — bez gwarancji i bez
> wsparcia (licencja Apache 2.0, pkt 7–8). Aplikacja wspiera procesy zgodne z
> ISO/IEC 27001:2022 i uoKSC, ale samo jej użycie nie zapewnia zgodności ani
> certyfikacji.

Wdrożenie produkcyjne (TLS, HSTS, limity żądań, kopie zapasowe i odtworzenie,
aktualizacje, logi, rotacja sekretów, lista kontrolna bezpieczeństwa):
**[docs/deployment.md](docs/deployment.md)**.

Dokumentacja dla użytkowników:

- **[docs/instrukcja-obslugi.md](docs/instrukcja-obslugi.md)** — instrukcja
  obsługi per rola (administrator, zatwierdzający, edytor, audytor,
  obserwator), FAQ i rozwiązywanie problemów,
- **[docs/funkcjonalnosci.md](docs/funkcjonalnosci.md)** — lista
  funkcjonalności z odwołaniami do ISO/IEC 27001:2022 i ADR oraz
  ograniczeniami.

## Architektura

| Usługa    | Opis                                                                 |
|-----------|----------------------------------------------------------------------|
| `db`      | PostgreSQL 16; role `app_owner` (migracje) i `app_rw` (aplikacja)     |
| `redis`   | Valkey 8 (zgodny z Redis, BSD) - kolejka zadań arq                   |
| `migrate` | jednorazowo: `alembic upgrade head` jako `app_owner`                 |
| `api`     | FastAPI/uvicorn (`backend/`), łączy się jako `app_rw`                |
| `worker`  | arq (`app.worker.WorkerSettings`) - raporty PDF w tle                |
| `web`     | nginx: build Fluttera (`frontend/`) + reverse proxy `/api/` → `api`  |
| `backup`  | opcjonalnie (profil `backup`): codzienny `pg_dump` + pliki + SHA-256 |

Konfiguracja infrastruktury: `docker-compose.yml`, `deploy/nginx/templates/`
(szablony nginx: nagłówki bezpieczeństwa, CSP, limity żądań),
`deploy/postgres/init/` (tworzenie ról przy pierwszym starcie pustej bazy),
`scripts/` (kopie zapasowe i odtworzenie, bash i PowerShell).

## Wymagania

- Docker Desktop (Windows/macOS) lub Docker Engine + Compose v2 (Linux)
- Do pracy poza kontenerami: Python 3.12+ i [uv](https://docs.astral.sh/uv/),
  Flutter (stable)

## Szybki start (Docker)

> **Uwaga:** niezmieniony `.env.example` to konfiguracja **produkcyjna**
> (`APP_ENV=prod`, `AUTH_MODE=local` — konta lokalne z hasłem, ADR 0018). W tym
> trybie API **odmawia startu**, dopóki nie ustawisz `AUTH_JWT_SECRET` (losowy,
> min. 64 znaki; instrukcja produkcyjna: [docs/deployment.md](docs/deployment.md)). Do
> uruchomienia lokalnego z użytkownikami testowymi przełącz `.env` na tryb
> deweloperski: `APP_ENV=dev`, `AUTH_MODE=dev` i losowy `DEV_AUTH_SECRET`
> (min. 32 znaki) - jak niżej.

PowerShell (Windows PowerShell 5.1 i PowerShell 7):

```powershell
Copy-Item .env.example .env
# uzupełnij hasła w .env (POSTGRES_PASSWORD, APP_OWNER_PASSWORD, APP_RW_PASSWORD
# oraz te same hasła w DATABASE_URL i MIGRATIONS_DATABASE_URL)

# tryb deweloperski + losowy klucz tokenów dev (64 znaki hex)
$b = New-Object byte[] 32
[Security.Cryptography.RandomNumberGenerator]::Create().GetBytes($b)
$secret = ($b | ForEach-Object { $_.ToString('x2') }) -join ''
Add-Content .env "`nAPP_ENV=dev`nAUTH_MODE=dev`nDEV_AUTH_SECRET=$secret"

docker compose up --build
```

bash:

```bash
cp .env.example .env
# uzupełnij hasła w .env (jak wyżej)

# tryb deweloperski + losowy klucz tokenów dev (64 znaki hex)
printf '\nAPP_ENV=dev\nAUTH_MODE=dev\nDEV_AUTH_SECRET=%s\n' "$(openssl rand -hex 32)" >> .env

docker compose up --build
```

Dopisane na końcu `.env` wartości nadpisują wcześniejsze `APP_ENV=prod`,
`AUTH_MODE=local` i puste `DEV_AUTH_SECRET=` (wygrywa ostatnie przypisanie).
Możesz też po prostu zmienić te trzy linie ręcznie. Tak samo działa job
`docker-compose` w CI.

Adresy:

- aplikacja: <http://localhost:8080>
- API przez nginx: <http://localhost:8080/api/v1/health>
- API bezpośrednio (tylko z tego komputera, port na `127.0.0.1`):
  <http://localhost:8000/api/v1/health> (dokumentacja OpenAPI:
  <http://localhost:8000/api/v1/docs> - tylko przy `APP_ENV=dev`, poza nim 404)
- PostgreSQL: `127.0.0.1:5432`, Redis: `127.0.0.1:6379` (tylko localhost)

Sprawdzenie stanu:

```powershell
docker compose ps                                   # kolumna STATUS: (healthy)
Invoke-RestMethod http://localhost:8080/api/v1/health
```

### Dane przykładowe i token deweloperski

Wgranie danych przykładowych (spółki ALFA/BETA/GAMMA, użytkownicy `dev-admin`,
`dev-editor`, `dev-approver`, `dev-auditor`, `dev-viewer` z rolami, słowniki
kategorii i typów obiektów, kategorie dostępne w spółkach, ok. 30 obiektów CI;
komendę można powtarzać - istniejące elementy są pomijane):

```powershell
docker compose exec api python -m app.cli seed
```

Same słowniki startowe (kategorie zmian z CLAUDE.md §13 i typy obiektów CI) -
dane referencyjne, komenda dozwolona także w produkcji (`APP_ENV=prod`):

```powershell
docker compose exec api python -m app.cli seed-dictionaries
```

Weryfikacja łańcucha skrótów dziennika audytu (CLAUDE.md §6.4; kod wyjścia 0 =
spójny, 1 = naruszony lub błąd; wynik weryfikacji sam trafia do dziennika):

```powershell
docker compose exec api python -m app.cli verify-audit --company ALFA
docker compose exec api python -m app.cli verify-audit --global
```

Token deweloperski (tylko `AUTH_MODE=dev`) i wywołanie `GET /api/v1/me`
przez nginx - PowerShell:

```powershell
$tok = (Invoke-RestMethod -Method Post http://localhost:8080/api/v1/auth/dev/token `
  -ContentType 'application/json' -Body '{"external_id":"dev-editor"}').access_token
Invoke-RestMethod http://localhost:8080/api/v1/me -Headers @{ Authorization = "Bearer $tok" }
```

bash:

```bash
tok=$(curl -fsS -X POST http://localhost:8080/api/v1/auth/dev/token \
  -H 'Content-Type: application/json' -d '{"external_id":"dev-editor"}' | jq -r .access_token)
curl -fsS -H "Authorization: Bearer $tok" http://localhost:8080/api/v1/me
```

Bez nagłówka `Authorization` `GET /api/v1/me` zwraca `401`.

### Tryb uwierzytelniania

| Zmienna           | Produkcja (`.env.example`)          | Lokalnie (dev)                 |
|-------------------|-------------------------------------|--------------------------------|
| `APP_ENV`         | `prod`                              | `dev`                          |
| `AUTH_MODE`       | `local` (konta lokalne z hasłem)    | `dev`                          |
| `AUTH_JWT_SECRET` | **wymagane**, min. 64 znaki, losowe (bez niego API nie wstaje) | nieużywane |
| `DEV_AUTH_SECRET` | puste (nieużywane)                  | **wymagane**, min. 32 znaki, losowe |

Kombinacja `APP_ENV=prod` + `AUTH_MODE=dev` jest odrzucana przy starcie API.
Gdy zmienne nie są ustawione, compose przyjmuje bezpieczne wartości
produkcyjne (`prod` / `local`). Zmiana `DEV_AUTH_SECRET` unieważnia wydane
tokeny dev.

### Sieć i adres IP klienta

Usługi działają w sieci `172.28.0.0/16` (stała podsieć w `docker-compose.yml`).
nginx (`web`) ma stały adres `172.28.0.10` i jako jedyny może przekazywać
nagłówki `X-Forwarded-For`/`X-Forwarded-Proto` (`FORWARDED_ALLOW_IPS`).
nginx **zastępuje** nagłówek `X-Forwarded-For` adresem klienta, więc klient nie
może podrobić IP zapisywanego w dzienniku audytu. Jeśli podsieć koliduje
z siecią lokalną, zmień razem: `subnet`, `ip_range`, `gateway`, adres `web`
i `FORWARDED_ALLOW_IPS`.

Po aktualizacji istniejącego stosu do tej definicji sieci uruchom raz
`docker compose up -d --force-recreate` - inaczej kontenery, których compose
nie odtworzył (np. `db`), tracą aliasy DNS (`db`, `redis`) w nowej sieci.

Uwaga: przy Docker Desktop (Windows/macOS) ruch z przeglądarki przechodzi
przez NAT maszyny wirtualnej Dockera, więc nginx i API widzą adres bramy
(`172.28.0.1`) zamiast prawdziwego IP klienta — w dzienniku audytu i w limitach
żądań. Tego nie da się obejść konfiguracją aplikacji. W produkcji (Linux)
prawdziwe IP wymaga wyłączenia `userland-proxy` w Dockerze albo proxy TLS przed
nginx wskazanego w `NGINX_TRUSTED_PROXIES` (moduł `realip`) — patrz
[docs/deployment.md](docs/deployment.md) §5 i §8.

### Role bazy danych

Skrypt `deploy/postgres/init/10-roles.sh` uruchamia się **tylko przy pierwszym
starcie z pustym wolumenem** `db-data`. Zmiana haseł w `.env` po inicjalizacji
wymaga `ALTER ROLE ... PASSWORD ...` albo usunięcia wolumenu
(`docker compose down -v` - **kasuje dane**).

## Praca lokalna (bez Dockera dla kodu)

Baza i Redis w kontenerach, kod uruchamiany lokalnie:

```powershell
docker compose up -d db redis
```

W `.env`/zmiennych środowiskowych zamień hosty `db` i `redis` na `localhost`
(oba porty są wystawione wyłącznie na `127.0.0.1`).

Komendy backendu i frontendu: [CLAUDE.md, sekcja 14](CLAUDE.md#14-komendy).

## CI

`.github/workflows/ci.yml`:

- **backend** (macierz Python 3.12 i 3.13): `ruff check`, `ruff format --check`,
  `mypy app`, `pytest` (testy bazodanowe na PostgreSQL 16 przez testcontainers;
  bez `APP_ENV`/`AUTH_MODE` w środowisku - testy budują własne ustawienia),
- **frontend**: `flutter pub get`, `build_runner`, `flutter analyze`,
  `flutter test`, `flutter build web`,
- **docker-compose**: `docker compose config`, `docker compose up -d --build
  --wait` z `.env.example` przełączonym na `APP_ENV=dev`, `AUTH_MODE=dev`
  i losowy `DEV_AUTH_SECRET` (cache BuildKit w GitHub Actions, override
  `deploy/ci/docker-compose.ci.yml`), testy dymne: health przez nginx (8080)
  i bezpośrednio (8000), deep link SPA `/c/ALFA/changes`, odrzucenie
  podrobionego `X-Forwarded-For`, `seed`, `GET /api/v1/me` bez tokenu → 401,
  token dev (`dev-editor`) przez nginx i `GET /api/v1/me` → 200, nagłówki
  bezpieczeństwa (CSP, nosniff, …) i lokalny CanvasKit, odrzucenie pliku
  wykonywalnego jako załącznika (415), logi JSON z `request_id`, limit żądań
  logowania (429 problem+json); logi przy porażce, na końcu `down -v`.

## Bezpieczeństwo

- Żadnych sekretów w repozytorium - tylko `.env` (ignorowany przez git).
- nginx: CSP bez zewnętrznych źródeł (CanvasKit serwowany lokalnie),
  `X-Content-Type-Options`, `Referrer-Policy`, `Permissions-Policy`,
  `X-Frame-Options`, COOP/CORP, HSTS po włączeniu TLS (`NGINX_HSTS`), limity
  żądań (429 `request.rate_limited`).
- Załączniki: limit rozmiaru (`ATTACHMENT_MAX_BYTES`) i whitelist typów
  rozpoznawanych z zawartości pliku (`ATTACHMENT_ALLOWED_TYPES`, 415
  `attachment.type_not_allowed`).
- Logi api/worker w JSON (`LOG_FORMAT`), z `request_id` jak w dzienniku audytu,
  z maskowaniem haseł i tokenów.
- Kopie zapasowe: `scripts/backup.sh|ps1`, odtworzenie z weryfikacją łańcuchów
  audytu: `scripts/restore.sh|ps1`.
- Szczegóły: [ADR 0019](docs/decisions/0019-hardening.md),
  [docs/deployment.md](docs/deployment.md).
- Zgłaszanie podatności (prywatnie, nie w publicznych issues): [SECURITY.md](SECURITY.md).

## Licencja

[Apache License 2.0](LICENSE) — zob. też [NOTICE](NOTICE) i
[THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md) (licencje zależności, fonty
IBM Plex na licencji SIL OFL 1.1). Zgłaszanie podatności:
[SECURITY.md](SECURITY.md); wkład w projekt: [CONTRIBUTING.md](CONTRIBUTING.md).
