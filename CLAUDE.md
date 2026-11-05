# CLAUDE.md — Rejestr zmian administracyjnych IT

Ten plik jest specyfikacją i instrukcją pracy dla Claude Code. Czytaj go w całości przed każdą sesją. Jeśli coś w kodzie jest sprzeczne z tym plikiem — ten plik wygrywa, chyba że właściciel projektu zdecyduje inaczej (wtedy zaktualizuj ten plik w tym samym commicie).

---

## 1. Cel produktu

Aplikacja webowa do **rejestrowania, zatwierdzania, monitorowania i audytowania zmian administracyjnych w infrastrukturze IT** wielu spółek (grupa kapitałowa; dział IT obsługuje wiele podmiotów).

Najważniejsze wymagania (w kolejności priorytetu):

1. **Audytowalność** — każda operacja na danych jest zapisana w niemodyfikowalnym dzienniku z łańcuchem skrótów SHA-256; da się udowodnić, że historia nie została zmieniona.
2. **Izolacja spółek (multi-tenancy)** — użytkownik widzi wyłącznie dane spółek, do których ma rolę. Administrator aplikacji dodaje/archiwizuje spółki.
3. **Poprawna klasyfikacja** — każda zmiana ma kategorię, typ, ryzyko, obiekty (CI), których dotyczy, oraz przypisane osoby (wykonawca, zatwierdzający, weryfikujący).
4. **Eksport PDF** raportu audytowego (rejestr za okres + odstępstwa) i karty pojedynczej zmiany (z pełną ścieżką audytu).
5. Zgodność procesu z ISO/IEC 27001:2022 (A.8.32 zarządzanie zmianami, A.8.15 logowanie) oraz wymaganiami ustawy o KSC dla spółek objętych ustawą.

Język interfejsu: **polski**. Język kodu, nazw w bazie, API i komentarzy: **angielski**.

---

## 2. Stos technologiczny

**Backend**
- Python 3.12+, FastAPI, Pydantic v2, SQLAlchemy 2.x (async, `asyncpg`), Alembic
- PostgreSQL 16
- WeasyPrint + Jinja2 (PDF)
- arq (lub Celery) + Redis — generowanie dużych raportów w tle
- pytest, pytest-asyncio, httpx, testcontainers (Postgres w testach)
- ruff (lint + format), mypy (strict dla `app/domain` i `app/services`)

**Frontend**
- Flutter (stable) — target **web**
- Riverpod (stan), go_router (routing), dio (HTTP), freezed + json_serializable (modele)
- data_table_2 lub pluto_grid (duże tabele)
- `flutter analyze` bez ostrzeżeń, testy widgetów dla formularza zmiany

**Infrastruktura**
- Docker Compose: `api`, `worker`, `db`, `redis`, `web` (nginx serwujący build Fluttera + reverse proxy do API)
- Uwierzytelnianie: **konta lokalne z hasłem** (`AUTH_MODE=local`; decyzja właściciela 2026-11-03 — bez Entra ID/OIDC, ADR 0018): hasła argon2id, polityka haseł, blokada po nieudanych próbach, konta zakłada i resetuje `app_admin`, wymuszona zmiana hasła tymczasowego; API wydaje i weryfikuje własne tokeny JWT. W trybie dev: lokalny provider z użytkownikami testowymi (`AUTH_MODE=dev`), **nigdy** aktywny w produkcji.

---

## 3. Struktura repozytorium

```
/
├── CLAUDE.md
├── docker-compose.yml
├── .env.example                # bez sekretów; wszystkie zmienne opisane
├── backend/
│   ├── pyproject.toml
│   ├── alembic/
│   ├── app/
│   │   ├── main.py
│   │   ├── config.py           # pydantic-settings
│   │   ├── db.py               # engine, session, ustawianie app.company_id dla RLS
│   │   ├── auth/               # konta lokalne (hasła), dev-auth, current_user
│   │   ├── domain/             # enumy, maszyna stanów, reguły walidacji (czysty Python, bez I/O)
│   │   ├── models/             # SQLAlchemy
│   │   ├── schemas/            # Pydantic (request/response)
│   │   ├── services/           # logika: changes, audit, numbering, reports
│   │   ├── api/v1/             # routery
│   │   ├── permissions.py      # RBAC — jedno źródło prawdy
│   │   └── reports/templates/  # Jinja2 HTML + CSS do PDF
│   └── tests/
└── frontend/
    ├── pubspec.yaml
    └── lib/
        ├── main.dart
        ├── app/router.dart
        ├── core/               # api client, auth, theme, tokens
        ├── features/
        │   ├── changes/        # rejestr, karta zmiany, formularz
        │   ├── admin/          # spółki, słowniki, role
        │   ├── reports/
        │   └── audit/
        └── widgets/            # wspólne: StatusPill, AuditTimeline, CompanySwitcher
```

---

## 4. Model domeny

### 4.1 Tabele

Wszystkie tabele mają `id UUID PK`, `created_at timestamptz`, `updated_at timestamptz`. Tabele należące do spółki mają `company_id UUID NOT NULL FK`.

**companies**
- `name` (unikalna), `tax_id` (NIP, nullable), `prefix` (2–8 znaków A–Z, unikalny, **niezmienny po utworzeniu**), `status` (`active` | `archived`), `is_ksc_entity` bool, `default_approver_id` FK users nullable
- Spółki się nie usuwa — tylko archiwizuje.

**users**
- `external_id` (stały identyfikator podmiotu w tokenie — `sub`, unikalny; `local:<uuid>` dla kont lokalnych, `dev-*` dla użytkowników seeda; ADR 0018), `email` (login konta lokalnego — unikalny bez względu na wielkość liter), `display_name`, `is_app_admin` bool, `is_active` bool
- Hasło w osobnej tabeli **user_credentials** (ADR 0018): `user_id` (unikalny), `password_hash` (argon2id — nigdy w API ani w audycie), `password_changed_at`, `must_change_password`, `temp_password_expires_at` (termin hasła tymczasowego — ustawiony dokładnie wtedy, gdy `must_change_password`; `TEMP_PASSWORD_TTL_HOURS`), `failed_attempts`, `locked_until`; brak wiersza = konto bez hasła (użytkownicy dev). Użytkowników się nie usuwa — tylko dezaktywuje.
- **auth_sessions** (`user_id`, `expires_at`, `refreshed_at`, `revoked_at`, `revoke_reason`) i **auth_refresh_tokens** (`session_id`, `token_hash` = SHA-256, `expires_at`, `rotated_at`) — sesje kont lokalnych; tokeny odświeżania jednorazowe (rotacja, wykrywanie ponownego użycia).

**company_memberships** — role per spółka
- `user_id`, `company_id`, `role` (`editor` | `approver` | `auditor` | `viewer`), unikalne (`user_id`, `company_id`, `role`) — użytkownik może mieć kilka ról w jednej spółce.

**change_categories** — słownik globalny (edytuje admin aplikacji)
- `code`, `name`, `parent_id` (podkategorie, 2 poziomy), `requires_approval` bool, `requires_ci_owner_consent` bool (zgoda właściciela CI, np. OT — ADR 0012 §5), `default_risk`, `is_active`; flagi podkategorii tylko zaostrzają (ADR 0011 §3)

**company_categories** — które kategorie są dostępne w spółce
- `company_id`, `category_id`, `approver_override_id` nullable (domyślny zatwierdzający dla kategorii w tej spółce)

**ci_types** — słownik globalny: `server`, `vm`, `network_device`, `firewall`, `account`, `group`, `application`, `ot_system`, `other` (+ możliwość dodania przez admina)

**configuration_items** (CI, inwentarz obiektów) — per spółka
- `company_id`, `ci_type_id`, `identifier` (np. `FW-01`, unikalny w spółce), `name`, `description`, `owner_user_id` nullable, `is_active`

**changes** — per spółka
- `company_id`, `number` (np. `CHG-ALFA-2026-0142`, unikalny), `title`
- `category_id`, `subcategory_id` nullable
- `change_type` (`standard` | `normal` | `emergency`)
- `risk` (`low` | `medium` | `high`)
- `status` (patrz 4.2)
- `description`, `implementation_plan`, `rollback_plan`, `impact`
- `requirement_ref` (np. „ISO 27001 A.8.32”, nullable; wymagane gdy `company.is_ksc_entity`)
- `ticket_ref` nullable
- `requested_by_id`, `assignee_id` (wykonawca), `approver_id`, `verifier_id` nullable
- `window_start`, `window_end` (timestamptz, nullable)
- `implemented_at`, `verified_at`, `approved_at`, `rejected_at` (nullable); `approved_by_id` nullable — kto faktycznie zatwierdził (NULL przy `approved_at` = `system`, ADR 0012 §4)
- `supersedes_change_id` nullable — korekta zamrożonej zmiany to NOWA zmiana wskazująca na oryginał
- `version` int — optymistyczne blokowanie (`If-Match` / pole w body)

**change_items** — M:N zmiana ↔ CI: `change_id`, `ci_id`

**change_comments**: `change_id`, `author_id`, `body` (komentarze też tylko dopisywane)

**attachments**: `change_id`, `filename`, `content_type`, `size`, `sha256`, `storage_key`, `uploaded_by_id`. Pliki w storage (lokalny wolumen / S3-compatible). Załączników się nie nadpisuje — nowa wersja = nowy rekord.

**number_sequences**: `company_id`, `year`, `last_value` — numeracja w transakcji z `SELECT … FOR UPDATE`. Format: `CHG-{PREFIX}-{YYYY}-{NNNN}` (4 cyfry, zero-padded, reset co rok).

**audit_log** — patrz sekcja 6.

**report_exports**: `company_id` nullable (raport wielospółkowy dla audytora), `number` (`RAP-{PREFIX}-{YYYY}-{NNNN}`; raport wielospółkowy `RAP-{YYYY}-{NNNN}` — ADR 0017 §2), `kind` (`register` | `change_card`), `format` (`pdf` | `csv`), `change_id`, `scope_company_ids`, `period_from/to`, `filters` jsonb, `include_audit_trail`, `generated_by_id`, `data_sha256`, `file_sha256`, `storage_key`, `status` (`pending` | `done` | `failed`), `error`. Wiersz wielospółkowy widzi tylko autor i ścieżka administracyjna (RLS, ADR 0017 §3).

### 4.2 Maszyna stanów zmiany

Statusy: `draft` → `pending_approval` → `approved` → `implemented` → `verified`
oraz końcowe/boczne: `rejected`, `rolled_back`, `cancelled`.

| Przejście | Kto | Warunki |
|---|---|---|
| `draft → pending_approval` | editor (autor lub wykonawca) | walidacja kompletności (4.3) |
| `pending_approval → draft` (zwrot do poprawy) | approver | wymagany komentarz |
| `pending_approval → approved` | approver | **approver ≠ requested_by i ≠ assignee** (zasada czterech oczu); ponowna walidacja 4.3 — każdy błąd blokuje, poza oknem, które już się zaczęło (wtedy ostrzeżenie w audycie) |
| `pending_approval → rejected` | approver | wymagany komentarz |
| `approved → implemented` | assignee | ustawia `implemented_at`; wdrożenie poza zatwierdzonym oknem dozwolone z ostrzeżeniem w audycie i odstępstwem |
| `implemented → verified` | verifier — wskazany `verifier_id`; gdy nie wskazano: editor lub approver spółki (≠ assignee, jeśli to możliwe — w spółce z 1 osobą dopuszczalne z ostrzeżeniem w audycie) | |
| `implemented → rolled_back` | assignee lub approver | wymagany komentarz |
| `draft → cancelled` | autor (z rolą editor lub approver) | |
| `approved → cancelled` | autor lub approver | wymagany komentarz |
| **standard**: `draft → approved` automatycznie przy wysłaniu | system | tylko gdy kategoria (i podkategoria) `requires_approval = false` i nie wymaga zgody właściciela CI; zatwierdzający nie jest wtedy wymagany; audyt zapisuje aktora `system` |
| **emergency**: `draft → implemented` | editor/approver będący zgłaszającym lub wykonawcą | następnie wymagane `approve` po fakcie w ciągu 24 h; zmiana bez zatwierdzenia po 24 h jest flagowana jako odstępstwo |
| zgoda właściciela CI (`consent`, status bez zmian) | właściciel CI zmiany | tylko gdy kategoria/podkategoria `requires_ci_owner_consent`; w `pending_approval` (oraz w `implemented` dla awaryjnej przed zatwierdzeniem po fakcie); `approve` wymaga zgody dla każdego CI zmiany (ADR 0012 §5) |

Zasady:
- Przejścia realizuje **wyłącznie** backend (`app/domain/state_machine.py`) przez endpoint akcji. Frontend nie ustawia `status` bezpośrednio.
- Od statusu `implemented` w górę rekord zmiany jest **zamrożony** (żadnej edycji pól merytorycznych); zamrożone są też statusy końcowe `rejected` i `cancelled`, a w `approved` pól się nie edytuje. Korekta = nowa zmiana z `supersedes_change_id` (w UI: „Utwórz korektę” na karcie, ADR 0021).
- Edycja pól dozwolona tylko w `draft` (editor) oraz w `pending_approval` przez approvera spółki, który nie jest zgłaszającym ani wykonawcą (tylko pola `approver_id`, `window_*`; ADR 0012 §6). Komentarze to osobna funkcja — dopisuje je editor lub approver w każdym statusie.
- Wyjątek od zamrożenia: w `implemented` approver może przepiąć `verifier_id`, jeśli wskazany weryfikujący nie może już weryfikować (nieaktywny lub bez roli) — z wpisem w audycie (ADR 0012 §6).
- Analogicznie dla awaryjnej wdrożonej bez zatwierdzenia: gdy wskazany `approver_id` nie jest już aktywnym approverem, inny approver spółki (≠ zgłaszający, ≠ wykonawca) może przepiąć `approver_id` (z wpisem w audycie) i zatwierdzić po fakcie; odstępstwo 24 h pozostaje, jeśli termin minął (ADR 0012 §6, decyzja właściciela 2026-10-29).
- `approver_id` to zatwierdzający **wskazany**; kto faktycznie zatwierdził, zapisuje `approved_by_id` (ustawiane wyłącznie akcją `approve`; NULL przy `approved_at` = `system`, automatyczne zatwierdzenie zmiany standardowej). Rejestr i raporty w kolumnie „Zatwierdził” pokazują `approved_by` albo „system (automatycznie)” (ADR 0012 §4).
- Szczegóły rozstrzygnięć (wskazany zatwierdzający, akcja `implement` dla awaryjnej, zgoda właściciela CI, ostrzeżenie weryfikacji, kody błędów): ADR 0012.

### 4.3 Walidacja przed wysłaniem do zatwierdzenia

- tytuł, kategoria, co najmniej jeden CI, typ, ryzyko, opis, plan wdrożenia, wykonawca, zatwierdzający (nie jest wymagany dla zmiany standardowej zatwierdzanej automatycznie; jeśli jest wskazany — obowiązują cztery oczy)
- `risk = high` → wymagany `rollback_plan` i okno serwisowe
- `window_start < window_end` i `window_start` w przyszłości (nie dotyczy emergency)
- `company.is_ksc_entity` → wymagany `requirement_ref` i `verifier_id`
- CI muszą należeć do tej samej spółki co zmiana
- Domyślny zatwierdzający: `company_categories.approver_override_id` → `companies.default_approver_id`

Te same reguły zwracaj z endpointu `GET /changes/{id}/readiness` (lista checków z flagą ok/błąd) — frontend pokazuje je w panelu „Kontrola przed wysłaniem”.

---

## 5. Uprawnienia (RBAC)

Jedno źródło prawdy: `app/permissions.py`. Każdy endpoint deklaruje wymaganą akcję; testy sprawdzają całą macierz.

| Akcja | app_admin | approver | editor | auditor | viewer |
|---|---|---|---|---|---|
| Zarządzanie spółkami (dodaj, edytuj, archiwizuj) | ✓ | — | — | — | — |
| Słowniki globalne (kategorie, typy CI) | ✓ | — | — | — | — |
| Przypisywanie ról w spółce | ✓ | — | — | — | — |
| Konta użytkowników (zakładanie, reset hasła, dezaktywacja) | ✓ | — | — | — | — |
| Inwentarz CI spółki (CRUD, bez usuwania — dezaktywacja) | ✓ | ✓ | ✓ | — | — |
| Tworzenie / edycja zmian w `draft` | — | ✓ | ✓ | — | — |
| Przypisywanie kategorii, CI, wykonawcy, zatwierdzającego | — | ✓ | ✓ | — | — |
| Zatwierdzanie / odrzucanie | — | ✓ (nie własnych) | — | — | — |
| Podgląd rejestru, kart, ścieżki audytu | ✓ | ✓ | ✓ | ✓ | ✓ |
| Eksport PDF/CSV | ✓ | ✓ | tylko karta zmiany | ✓ | — |
| Weryfikacja łańcucha audytu | ✓ | — | — | ✓ | — |
| Przegląd całego dziennika audytu (`GET /audit`) | ✓ | — | — | ✓ | — |

- `app_admin` **nie** jest automatycznie editorem/approverem w spółkach (rozdział obowiązków). Może sobie nadać rolę, ale to też trafia do audytu.
- Dziennik audytu (ADR 0009, ADR 0015 §7): łańcuch **globalny** czyta i weryfikuje wyłącznie `app_admin`. Audytor czyta i weryfikuje łańcuchy tylko **swoich** spółek (tych, w których ma rolę). `app_admin` weryfikuje łańcuch **każdej** spółki (jawna ścieżka administracyjna, zwracany jest tylko wynik) i czyta wpisy łańcucha **każdej** spółki także bez roli w niej — wąską ścieżką tylko do odczytu (zakres RLS = ta jedna spółka, transakcja READ ONLY).
- Podgląd rejestru (decyzja właściciela 2026-11-02, ADR 0016): `app_admin` **bez roli** w spółce czyta jej rejestr zmian, karty (z `allowed_actions = []`, `editable_fields = []`, `access = "admin_read_only"`), `readiness`, ścieżkę audytu zmiany, listę załączników (metadane z sha256) i kafelki — tą samą wąską ścieżką tylko do odczytu. Nie wykonuje akcji, nie edytuje, nie komentuje, nie dodaje i **nie pobiera** plików załączników (404 + `access_denied`). Admin **z rolą** w spółce działa wyłącznie według tej roli.
- Ścieżką administracyjną także **bez roli** w spółce `app_admin` eksportuje raporty PDF/CSV spółki (ADR 0017), prowadzi jej inwentarz CI (zgodnie z macierzą powyżej) oraz przegląda i weryfikuje jej łańcuch audytu (ADR 0015 §7).
- Auditor może mieć rolę w wielu spółkach i generować raport zbiorczy „Wszystkie spółki (audytor)”.

---

## 6. Dziennik audytu (krytyczne — nie upraszczaj)

### 6.1 Tabela `audit_log`

```
id              bigserial PK
company_id      uuid NULL         -- NULL dla zdarzeń globalnych (słowniki, spółki)
seq             bigint NOT NULL   -- kolejny numer w łańcuchu danej spółki (lub globalnym)
occurred_at     timestamptz NOT NULL (UTC, ustawiane przez serwer)
actor_id        uuid NULL         -- NULL = 'system'
actor_display   text NOT NULL     -- zamrożona nazwa w chwili zdarzenia
actor_roles     text[] NOT NULL
ip_address      inet NULL
user_agent      text NULL
request_id      uuid NOT NULL
entity_type     text NOT NULL     -- 'change','ci','company','membership','category','ci_type','company_category','attachment','report','auth',...
entity_id       uuid NULL
action          text NOT NULL     -- 'create','update','transition','attach','export','login','role_grant',...
diff            jsonb NOT NULL    -- {"field": {"before": ..., "after": ...}} lub {} 
context         jsonb NOT NULL    -- np. {"from_status":"draft","to_status":"pending_approval","comment":"..."}
prev_hash       char(64) NOT NULL
hash            char(64) NOT NULL
UNIQUE NULLS NOT DISTINCT (company_id, seq)   -- łańcuch globalny (NULL) też ma unikalne seq (ADR 0006)
```

### 6.2 Łańcuch skrótów

- Osobny łańcuch na każdą spółkę + jeden łańcuch globalny (`company_id IS NULL`).
- Pierwszy wpis łańcucha: `prev_hash = '0' * 64`.
- `hash = sha256(prev_hash + canonical_json(payload))`, gdzie `payload` = wszystkie pola poza `id`, `hash`; `canonical_json` = JSON z posortowanymi kluczami, bez spacji, UTF-8, daty w ISO 8601 UTC z `Z`.
- Dopisywanie: w tej samej transakcji co zmiana danych biznesowych. Głowa łańcucha blokowana przez `SELECT … FOR UPDATE` na tabeli `audit_chain_heads (company_id, last_seq, last_hash)` — żeby równoległe żądania nie rozwidliły łańcucha.
- Zapis audytu jest **częścią serwisu**, nie middleware — każda funkcja serwisu, która modyfikuje dane, wywołuje `audit.record(...)`. Brak wpisu audytu = błąd (test sprawdza, że każdy endpoint modyfikujący tworzy co najmniej jeden wpis).

### 6.3 Ochrona na poziomie bazy

- Aplikacja łączy się rolą `app_rw`, która ma na `audit_log` wyłącznie `INSERT, SELECT`.
- Trigger `BEFORE UPDATE OR DELETE ON audit_log` → `RAISE EXCEPTION`.
- Migracje uruchamia osobna rola `app_owner` (nieużywana przez działającą aplikację).
- To samo (tylko INSERT/SELECT) dla `change_comments` i `attachments`.

### 6.4 Weryfikacja

- `POST /api/v1/audit/verify?company_id=…` — przelicza łańcuch, zwraca `{ok, checked, first_broken_seq}` (oraz zweryfikowaną głowę i wpis audytu weryfikacji). Bez `company_id` — łańcuch globalny (tylko `app_admin`).
- Wynik weryfikacji (i sama weryfikacja) też trafia do audytu — do weryfikowanego łańcucha; gdy naruszony łańcuch spółki odrzuca dopisanie, do łańcucha globalnego (ADR 0009).
- Komenda CLI: `python -m app.cli verify-audit --company ALFA` lub `--global` (aktor `system`, kod wyjścia 0 = spójny, 1 = naruszony lub błąd).

### 6.5 Co logujemy

Każde utworzenie/edycję/przejście statusu zmiany, CI, spółki, kategorii, członkostwa; dodanie załącznika (z sha256); komentarz; eksport (z numerem raportu i `data_sha256`); logowanie i nieudane logowanie; zdarzenia kont lokalnych (ADR 0018): wylogowanie, odświeżenie i zakończenie sesji (`token_refresh`, `session_revoke`), blokadę konta (`lockout`), zmianę i reset hasła (`password_change`, `password_reset` — bez haseł i skrótów); odmowę dostępu (403) do zasobu innej spółki.

Definicje (ADR 0010): „logowanie” = pierwsze żądanie z danym tokenem (raz na token, także przy wielu procesach API); nieudane logowania są liczone w oknach czasowych per źródło — wpisy przy 1., 2., 4., 8.… próbie i dokładne podsumowanie po zamknięciu okna (żadna próba nie znika, zalew nie zalewa dziennika); odmowy dostępu (każde 403 oraz 404 dla spółki bez członkostwa) — w łańcuchu globalnym z `context.target_company_id`.

---

## 7. Izolacja spółek

1. Warstwa aplikacji: zależność FastAPI `get_company_context(company_id)` sprawdza członkostwo i zwraca kontekst; każde zapytanie w serwisach filtruje po `company_id`.
2. Warstwa bazy: **Row-Level Security** na wszystkich tabelach z `company_id`. Na początku transakcji `SET LOCAL app.company_ids = '{…}'` (lista spółek użytkownika); polityka `USING (company_id = ANY (current_setting('app.company_ids')::uuid[]))`. Admin aplikacji dla operacji na słownikach/spółkach używa osobnej, jawnej ścieżki.
3. Testy: dla każdego endpointu z `company_id` test, że użytkownik spółki A dostaje 404 (nie 403 — nie ujawniamy istnienia) dla zasobu spółki B.

---

## 8. API (v1)

Prefiks `/api/v1`. JSON, błędy w formacie RFC 9457 (`application/problem+json`). Paginacja kursorowa lub `limit/offset` z `total`. Daty w ISO 8601 UTC.

```
GET    /me                                   # profil + członkostwa i role
GET    /companies                            # spółki dostępne dla użytkownika (+ liczniki: CI, role — ADR 0015)
POST   /companies                            # admin
PATCH  /companies/{id}                       # admin (prefix niezmienny)
POST   /companies/{id}/archive               # admin
GET    /companies/{id}/members
PUT    /companies/{id}/members/{user_id}     # admin — ustaw role
GET    /users                                # admin — katalog użytkowników do przypisywania ról (?q=&limit=&offset=); stan hasła, nigdy skrót
GET    /users/{id}                           # admin — użytkownik z rolami we wszystkich spółkach (ADR 0015)
POST   /users                                # admin — konto lokalne {email, display_name, is_app_admin?}; hasło tymczasowe zwracane JEDNORAZOWO, ważne TEMP_PASSWORD_TTL_HOURS (domyślnie 7 dni; ADR 0018)
POST   /users/{id}/reset-password            # admin — nowe hasło tymczasowe (jednorazowo, nowy termin TEMP_PASSWORD_TTL_HOURS), odblokowanie, koniec wszystkich sesji
PATCH  /users/{id}                           # admin — display_name, is_active (dezaktywacja kończy sesje), is_app_admin; nie siebie, nie ostatniego admina
GET    /permissions/matrix                   # macierz uprawnień z app/permissions.py (tylko odczyt, ADR 0015)
GET    /categories        POST/PATCH         # słownik globalny, 2 poziomy (zapis: admin; ?active=&parent_id=&top_level=)
GET    /companies/{id}/categories  PUT       # dostępne kategorie główne + override zatwierdzającego (PUT: admin, pełna lista)
GET    /ci-types          POST/PATCH         # słownik globalny typów CI (zapis: admin; ?active=)
GET    /companies/{cid}/ci                   # ?q=&type=&active=&limit=&offset=
POST   /companies/{cid}/ci   GET/PATCH /companies/{cid}/ci/{id}   # bez DELETE — dezaktywacja przez is_active=false (ADR 0011)

GET    /companies/{cid}/changes              # filtry: period_from, period_to, period_by (created|implemented), status[], type[], category[], ci[], assignee, approver (wskazany), approved_by (faktyczny: id albo system), q; sort; limit/offset/total
POST   /companies/{cid}/changes              # tworzy draft, nadaje numer
GET    /companies/{cid}/changes/by-number/{number}   # karta po numerze (URL /c/:prefix/changes/:number, ADR 0013)
GET    /companies/{cid}/changes/{id}         # karta z allowed_actions, editable_fields, access (member|admin_read_only, ADR 0016), version (też ETag); supersedes_number, superseded_by — ADR 0021
PATCH  /companies/{cid}/changes/{id}         # tylko w dozwolonych statusach; wymaga version (pole lub If-Match), 409 change.version_conflict
GET    /companies/{cid}/changes/{id}/readiness
POST   /companies/{cid}/changes/{id}/actions/{action}   # submit|return|approve|reject|implement|verify|rollback|cancel|consent  body: {comment?, version?} lub If-Match; approve wymaga wersji (428)
GET    /companies/{cid}/changes/{id}/audit   # ścieżka audytu tej zmiany (i jej załączników), od najstarszych
POST   /companies/{cid}/changes/{id}/comments
GET    /companies/{cid}/changes/{id}/attachments        # lista załączników
POST   /companies/{cid}/changes/{id}/attachments        # multipart (pole file), limit ATTACHMENT_MAX_BYTES (413 attachment.too_large); typ rozpoznawany z zawartości, spoza ATTACHMENT_ALLOWED_TYPES → 415 attachment.type_not_allowed (ADR 0019 §3)
GET    /companies/{cid}/changes/{id}/attachments/{aid}  # pobranie pliku (zawsze jako attachment); każde pobranie trafia do audytu
GET    /companies/{cid}/stats                # liczniki do kafelków rejestru
GET    /companies/{cid}/audit/status         # werdykt łańcucha audytu spółki dla znacznika „Łańcuch spójny” (każda rola; ok|stale|broken|unknown, ADR 0013 §11)

POST   /reports                              # {company_id|null, period_from, period_to, filters, kind: 'register'|'change_card', change_id?, include_audit_trail}; 201 done / 202 pending (ADR 0017)
GET    /reports                              # lista do ekranu 5 (?company_id=&kind=&status=&limit=&offset=) — tylko raporty, które użytkownik może eksportować
GET    /reports/{id}                         # status
GET    /reports/{id}/download                # PDF lub CSV (każde pobranie w audycie)
GET    /companies/{cid}/changes/export.csv   # filtry jak lista zmian; UTF-8 z BOM, separator ';' (ADR 0017 §7)

POST   /auth/login                           # tylko AUTH_MODE=local, publiczny: {email, password} → token dostępu + refresh token (ADR 0018); poprawne, ale wygasłe hasło tymczasowe → 401 auth.temporary_password_expired
POST   /auth/refresh                         # tylko AUTH_MODE=local, publiczny: {refresh_token} → nowa para (rotacja; ponowne użycie odwołuje sesję)
POST   /auth/logout                          # tylko AUTH_MODE=local: kończy sesję tokenu (204)
POST   /auth/password                        # tylko AUTH_MODE=local: {current_password, new_password} → nowa para tokenów; kończy wszystkie sesje
                                             # przy must_change_password dozwolone tylko: /me, /auth/password, /auth/logout (reszta 403 auth.password_change_required)
GET    /auth/dev/users  POST /auth/dev/token # tylko AUTH_MODE=dev (poza nim 404) — logowanie deweloperskie

POST   /audit/verify                         # ?company_id= (brak = łańcuch globalny, tylko admin)
GET    /audit                                # przegląd jednego łańcucha (auditor/admin): ?company_id= (brak = globalny), entity_type, entity_id, action, actor_id, occurred_from, occurred_to, limit/offset
```

Błędy generowane przez reverse proxy (nginx) mają ten sam format problem+json (ADR 0019): `429 request.rate_limited` (limity żądań per IP, ostrzejsze dla `/auth/login`, `/auth/password`, `/auth/refresh`), `413 attachment.too_large` (ciało żądania), `503 api.unavailable`. Ten sam `request_id` (UUID) jest w nagłówku `X-Request-ID`, logach nginx i API oraz w `audit_log.request_id`.

---

## 9. Eksport PDF

- Generowanie po stronie serwera: Jinja2 → HTML → WeasyPrint. Fonty osadzone (IBM Plex Sans, IBM Plex Mono — licencja OFL, pliki w repo w `reports/fonts/`), pełne polskie znaki.
- A4, marginesy 15 mm, nagłówek/stopka przez CSS `@page` (numer strony „Strona X z Y”, numer raportu, skrót danych).
- **Raport rejestru** (sekcje):
  1. Nagłówek: tytuł, spółka (lub „wszystkie spółki”), okres, nr raportu, data i autor wygenerowania
  2. Kafelki: liczba zmian, zatwierdzone przed wdrożeniem, awaryjne, bez weryfikacji
  3. Zakres i zastosowane filtry
  4. Tabela rejestru: ID, tytuł, kategoria, typ, wykonawca, zatwierdzający, data wdrożenia, weryfikacja
  5. Odstępstwa: awaryjne bez zatwierdzenia w 24 h, wdrożone bez weryfikacji, wdrożone poza zatwierdzonym oknem serwisowym (ADR 0012), wycofane, zatwierdzone przez autora (nie powinno wystąpić — jeśli jest, to błąd krytyczny)
  6. Załącznik A: zestawienie per kategoria i per CI
  7. Załącznik B (opcjonalny, checkbox): pełna ścieżka audytu każdej zmiany
  8. Wynik weryfikacji łańcucha audytu w chwili generowania
  9. Pola podpisów: „Sporządził”, „Zatwierdził (właściciel procesu)”
- **Karta zmiany**: wszystkie pola, obiekty, osoby, oś czasu statusów, pełny audit trail z diffami, lista załączników z sha256.
- `data_sha256` = sha256 z kanonicznego JSON danych, z których zbudowano raport — drukowane w stopce i zapisywane w `report_exports` + `audit_log`.
- Raporty > 200 zmian — w tle (worker), frontend odpytuje status. Próg: `REPORT_ASYNC_THRESHOLD`.
- Fonty: `backend/app/reports/fonts/` (WOFF, OFL). Eksport (także CSV i każde pobranie) → wpis `report`/`export` w łańcuchu każdej spółki raportu; raport zbiorczy audytora obejmuje spółki z rolą auditor. Szczegóły i decyzje: ADR 0017.
- Test: wygenerowanie PDF z danymi zawierającymi „zażółć gęślą jaźń” i sprawdzenie tekstu (pypdf).

---

## 10. Frontend — ekrany

Makiety istnieją w projekcie Design (5 ekranów). Odwzoruj układ i treść; poniżej opis, bo nie masz do nich dostępu.

**Wspólny układ**: lewy panel nawigacji (ciemny, `#161A1F`, ~232 px) z: logo „Rejestr zmian IT”, przełącznikiem spółki (dropdown; opcja „Wszystkie spółki (audytor)” dla audytora), linkami: Rejestr zmian, Do zatwierdzenia (licznik), Obiekty (CI), Raporty i eksport, Dziennik audytu; sekcja Administracja (tylko admin): Spółki i słowniki, Użytkownicy i role; na dole awatar, nazwa i rola. Na wąskim ekranie panel zwija się w górny pasek/drawer. Wybrana spółka jest w URL (`/c/{prefix}/...`). Bez sesji każdy adres prowadzi do `/login` (w trybie dev: wybór użytkownika testowego; ADR 0014).

1. **Rejestr zmian** (`/c/:prefix/changes`): nagłówek z nazwą spółki, przyciski „Eksport PDF”, „CSV”, „Nowa zmiana”. 4 kafelki: Do zatwierdzenia, Zatwierdzone niewdrożone, Awaryjne (30 dni), Wdrożone bez weryfikacji. Pasek: wyszukiwarka + filtry (Okres, Kategoria, Obiekt, Status, Typ). Tabela: ID (mono, link), Zmiana, Kategoria, Obiekt (CI), Typ (awaryjna wyróżniona czerwoną ramką), Status (pigułka), Wykonawca, Zatwierdził, Wdrożenie. Stopka: licznik i sortowanie.
2. **Karta zmiany** (`/c/:prefix/changes/:number`): breadcrumb, pigułka statusu, typ i ryzyko, tytuł; przyciski zależne od uprawnień i statusu (Edytuj, Karta PDF, Odrzuć, Zatwierdź itd. — pokazuj tylko dozwolone akcje, które zwraca API w polu `allowed_actions`). Pasek etapów (Szkic → Do zatwierdzenia → Zatwierdzona → Wdrożona → Zweryfikowana). Lewa kolumna: Opis zmiany (siatka 2 kol.: co i dlaczego, zgłoszenie, plan wdrożenia, plan wycofania, wpływ, załączniki) + **Ścieżka audytu** (wpisy: znacznik czasu + IP w mono, kto (rola) — akcja, diff „przed → po” w ramce z przekreśloną czerwoną wartością i zieloną nową, skrót sha256; w nagłówku zielony znacznik „Łańcuch spójny”). Prawa kolumna: Klasyfikacja (spółka, kategoria, typ, zgłaszający, wykonawca, zatwierdzający, okno, weryfikacja, podstawa/wymóg) + Obiekty, których dotyczy (chipy mono).
3. **Nowa zmiana / edycja** (`/c/:prefix/changes/new` tworzy szkic i przechodzi do `/c/:prefix/changes/:number/edit`): numer nadany od razu (draft). Sekcje: 1) Czego dotyczy — tytuł, kategoria + podkategoria, multi-select CI z wyszukiwaniem (chipy, możliwość dodania CI w locie); 2) Typ i ryzyko — 3 karty radio (Standardowa / Normalna / Awaryjna z opisem), ryzyko Niskie/Średnie/Wysokie; 3) Opis i plan — opis i uzasadnienie, plan wdrożenia, plan wycofania (wymagany przy wysokim ryzyku — walidacja inline), wpływ; 4) Osoby, termin, dowody — wykonawca, zatwierdzający (podpowiedź domyślnego), weryfikujący, okno od/do, zgłoszenie, podstawa/wymóg, strefa załączników. Prawy panel „Kontrola przed wysłaniem” — lista checków z `/readiness`. Przyciski: Anuluj, Zapisz szkic, Wyślij do zatwierdzenia (nieaktywny, dopóki są błędy). Autosave szkicu co 30 s.
4. **Administracja** (`/admin/...`): zakładki Spółki | Kategorie zmian | Typy obiektów (CI) | Role i uprawnienia. Spółki: tabela (Spółka, Prefiks ID, Obiekty, Edytorzy, Zatwierdzający, Status) + panel „Nowa spółka” (nazwa, prefiks z podglądem przykładowego ID, NIP, domyślny zatwierdzający, checkboxy kategorii dostępnych w spółce z regułą zatwierdzania, checkbox „Podmiot objęty uoKSC”). Macierz uprawnień tylko do odczytu (z sekcji 5).
5. **Raport PDF**: ekran z formularzem parametrów (spółka/wszystkie, okres, filtry, czy dołączyć załącznik B) + lista wygenerowanych raportów (nr, okres, kto, kiedy, sha256, pobierz).

**Tokeny wizualne** (`core/theme.dart`):
- tło `#F4F5F7`, powierzchnia `#FFFFFF`, obramowanie `#DDE1E6`, tekst `#161A1F`, tekst drugorzędny `#5A6270`, akcent `#1D4ED8`
- statusy (tło/tekst): szkic `#ECEEF1/#3D4450`, do zatwierdzenia `#FDF0D5/#7A4B00`, zatwierdzona `#DCE7FD/#1E3A8A`, wdrożona `#E2F0FB/#0B4A6F`, zweryfikowana `#DDF3E4/#14532D`, odrzucona/wycofana `#FBE1E1/#8A1C1C`
- font: IBM Plex Sans; identyfikatory, daty, skróty: IBM Plex Mono
- promień 8–10 px, cele dotykowe ≥ 44 px, kontrast tekstu ≥ 4.5:1

---

## 11. Zasady pracy dla Claude Code

1. **Pracuj etapami (sekcja 12).** Po każdym etapie: testy zielone, `ruff`, `mypy`, `flutter analyze` bez błędów, krótkie podsumowanie co zrobiono i co dalej. Zatrzymaj się i poczekaj na akceptację przed kolejnym etapem.
2. Najpierw testy dla: maszyny stanów, macierzy uprawnień, łańcucha audytu, izolacji spółek. Te moduły muszą mieć pokrycie ≥ 90%.
3. Nie upraszczaj audytu ani RLS „na później”. Jeśli coś blokuje — zapytaj.
4. Migracje tylko przez Alembic, nigdy `create_all` poza testami. Każda migracja odwracalna, jeśli to możliwe (z wyjątkiem triggerów ochronnych audytu — ich `downgrade` też musi istnieć, ale tylko dla roli `app_owner`).
5. Żadnych sekretów w repo. Konfiguracja przez zmienne środowiskowe, wszystkie opisane w `.env.example`.
6. Czasy w bazie zawsze UTC; w UI strefa `Europe/Warsaw`, format `dd.MM.yyyy HH:mm`.
7. Dane przykładowe (`python -m app.cli seed`): 3 spółki (Alfa, Beta, Gamma), 5 użytkowników z różnymi rolami, słownik kategorii z sekcji 13, ~30 CI, ~40 zmian w różnych statusach, w tym 1 awaryjna i 2 bez weryfikacji.
8. Komunikaty błędów dla użytkownika po polsku; kody błędów w API po angielsku (`change.invalid_transition`, `change.four_eyes_violation`, …).
9. Commity małe, w konwencji Conventional Commits.
10. Jeśli specyfikacja jest niejasna lub sprzeczna — zapytaj zamiast zgadywać. Decyzje zapisuj w `docs/decisions/NNNN-*.md` (ADR).

---

## 12. Plan etapów i kryteria akceptacji

**Etap 0 — Szkielet**
- Docker Compose (api, db, redis, worker, web), `backend` i `frontend` uruchamiają się, healthcheck `/api/v1/health`, CI (lint + testy) w GitHub Actions.
- ✔ `docker compose up` → działa pusty Flutter z layoutem nawigacji i ping do API.

**Etap 1 — Rdzeń audytu, auth, spółki, role** (kolejność zmieniona — ADR 0005)
- Najpierw rdzeń audytu: `audit_log`, `audit_chain_heads`, `audit.record()`, triggery ochronne, uprawnienia roli `app_rw` — tak, by każdy endpoint zapisujący od początku tworzył wpis audytu.
- Następnie: uwierzytelnianie (pierwotnie OIDC — zastąpione kontami lokalnymi w Etapie 8, ADR 0018) + tryb dev, `users`, `companies`, `company_memberships`, `/me`, CRUD spółek dla admina, RLS.
- ✔ Testy izolacji (A nie widzi B), test archiwizacji, prefiks niezmienny.

**Etap 2 — Dziennik audytu (dokończenie)**
- Weryfikacja łańcucha (API + CLI), przegląd dziennika `GET /audit`, logowanie zdarzeń auth i odmów dostępu; rdzeń powstał w Etapie 1.
- ✔ Test: ręczny UPDATE w bazie rolą `app_rw` się nie udaje; zmodyfikowany wpis (rolą owner) jest wykrywany przez `verify`; 50 równoległych zapisów nie rozwidla łańcucha.

**Etap 3 — Słowniki i inwentarz CI**
- Kategorie (2 poziomy), kategorie per spółka, typy CI, CRUD CI, wszystko audytowane.

**Etap 4 — Zmiany: model, numeracja, maszyna stanów**
- `changes`, `change_items`, numeracja, `readiness`, akcje, zamrażanie, `allowed_actions` w odpowiedzi, komentarze, załączniki z sha256, optymistyczne blokowanie.
- ✔ Testy wszystkich przejść z tabeli 4.2 (dozwolone i niedozwolone), zasada czterech oczu, emergency + flaga po 24 h, standard auto-approve.

**Etap 5 — Frontend: rejestr, karta, formularz**
- Ekrany 1–3 z sekcji 10, przełącznik spółki, filtry w URL, oś audytu.
- ✔ Testy widgetów formularza (walidacja wysokiego ryzyka), ręczny scenariusz end-to-end od szkicu do weryfikacji.

**Etap 6 — Administracja (frontend)**
- Ekran 4, zarządzanie rolami.

**Etap 7 — Eksport PDF i CSV**
- Szablony, worker, `report_exports`, ekran 5, karta zmiany w PDF.
- ✔ PDF z polskimi znakami, numer strony, `data_sha256` w stopce zgodny z zapisem w audycie, odstępstwa poprawnie wyliczone na danych seed.

**Etap 8 — Utwardzenie**
- Logowanie kontami lokalnymi z hasłem (ADR 0018) — backend i frontend (logowanie, zmiana hasła, zakładanie kont i reset hasła przez admina), wszystko audytowane.
- Dokumentacja: README wdrożeniowe, **instrukcja obsługi** dla użytkowników (po polsku, per rola) oraz **lista funkcjonalności** aplikacji.
- Rate limiting, nagłówki bezpieczeństwa (CSP, HSTS), limity rozmiaru załączników i whitelist typów MIME, logi aplikacyjne JSON, backup bazy (skrypt + instrukcja), README wdrożeniowe.

---

## 13. Słownik startowy kategorii (seed)

| Kod | Kategoria | Podkategorie | Wymaga zatwierdzenia |
|---|---|---|---|
| ACC | Konta i uprawnienia | nadanie, odebranie, zmiana grupy, konto serwisowe | nie (standard) — poza kontami uprzywilejowanymi |
| NET | Sieć | VLAN/routing, firmware urządzeń, Wi-Fi | tak |
| FW | Firewall / sieć | reguły dostępu, NAT, VPN | tak |
| SRV | Serwery / wirtualizacja | nowy serwer/VM, zasoby, migracja, wyłączenie | tak |
| PATCH | Aktualizacje i łatki | system operacyjny, aplikacje, krytyczne | tak |
| BKP | Kopie zapasowe | harmonogram, retencja, odtworzenie testowe | tak |
| GPO | Polityki domenowe | GPO, polityki haseł, MDM | tak |
| APP | Aplikacje biznesowe | konfiguracja, wersja, integracje | tak |
| SEC | Bezpieczeństwo | EDR/AV, SIEM, certyfikaty | tak |
| OT | Systemy OT / przemysłowe | konfiguracja, aktualizacja | tak + zgoda właściciela CI |

---

## 14. Komendy

```bash
# całość
docker compose up --build

# backend
cd backend
uv sync                      # lub pip install -e ".[dev]"
alembic upgrade head
python -m app.cli seed-dictionaries   # słowniki startowe (§13, typy CI) — także w produkcji
python -m app.cli seed                # dane przykładowe (tylko dev; zawiera słowniki)
python -m app.cli create-admin --email admin@example.com --name "Imię Nazwisko"   # pierwszy admin (AUTH_MODE=local); hasło z terminala/STDIN albo --generate-password
pytest -q
ruff check . && ruff format --check . && mypy app

# frontend
cd frontend
flutter pub get
dart run build_runner build
flutter analyze
flutter test
flutter run -d chrome --web-port=5000 --dart-define=API_URL=http://localhost:8000   # port 5000 jest w CORS_ORIGINS
```

---

## 15. Definition of Done (każda funkcja)

- [ ] Endpoint ma deklarowane uprawnienie i test macierzy uprawnień
- [ ] Każda modyfikacja danych tworzy wpis audytu (test)
- [ ] Zapytania filtrują po spółce + działa RLS (test izolacji)
- [ ] Walidacja po stronie backendu (frontend tylko powiela dla UX)
- [ ] Komunikaty po polsku w UI
- [ ] Lint, typy, testy zielone
- [ ] Zaktualizowany ten plik, jeśli zmieniła się specyfikacja
