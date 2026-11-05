# 0016. Podgląd rejestru zmian przez administratora bez roli w spółce (tylko odczyt)

- Status: przyjęta — decyzja właściciela projektu 2026-11-02, wariant „a”
- Data: 2026-11-02
- Dotyczy: CLAUDE.md §5, §7, §8; `backend/app/permissions.py` (`require_register_read`, `require_company(..., admin_read_only=True)`, `_admin_read_context`, `AccessRule.admin_read_only`), `backend/app/auth/principal.py` (`CompanyContext.read_only`), `backend/app/api/v1/changes.py`, `backend/app/schemas/changes.py` (`ChangeOut.access`); zmienia ADR 0013 §7 i rozstrzyga rozbieżność opisaną w ADR 0015 §1/§11 pkt 3; uzupełnia ADR 0007 §4

## 1. Problem

Macierz §5 daje `app_admin` ✓ w wierszu „Podgląd rejestru, kart, ścieżki audytu”, ale API zmian (ADR 0013 §7) wymagało członkostwa — admin bez roli dostawał 404. Właściciel wybrał wariant „a”: wąska ścieżka **tylko do odczytu**, analogiczna do dziennika audytu spółki (ADR 0015 §7). Odrzucony wariant „b”: zmiana §5 na „✓ tylko z rolą w spółce”.

## 2. Zakres

Admin **bez roli** w spółce `{cid}` czyta (200):

| Endpoint | Uwagi |
|---|---|
| `GET /companies/{cid}/changes` | wszystkie filtry, sortowanie, paginacja jak dla członka |
| `GET /companies/{cid}/changes/by-number/{number}` | karta |
| `GET /companies/{cid}/changes/{id}` | karta: `access = "admin_read_only"`, `allowed_actions = []`, `editable_fields = []` |
| `GET /companies/{cid}/changes/{id}/readiness` | |
| `GET /companies/{cid}/changes/{id}/audit` | ścieżka audytu zmiany z `hash_valid` |
| `GET /companies/{cid}/changes/{id}/attachments` | lista metadanych z `sha256` |
| `GET /companies/{cid}/stats` | kafelki rejestru |
| `GET /companies/{cid}/audit/status` | już wcześniej (ADR 0015 §7) |

Bez zmian (admin bez roli: **404 `company.not_found` + `access_denied`** w łańcuchu globalnym z `target_company_id`): `POST/PATCH` zmian, wszystkie `POST …/actions/{action}` (także `consent`), komentarze, dodanie załącznika i **pobranie pliku załącznika** (§4). Inwentarz CI ma własną ścieżkę admina (ADR 0011) — nie zmieniany.

Odczyt nie tworzy wpisu audytu (jak dla członków, ADR 0013 §11), poza pobraniem pliku.

## 3. Mechanizm (jawny, nazwany)

- `permissions.require_register_read()` = `require_company(Action.REGISTER_VIEW, admin_action=Action.REGISTER_VIEW, admin_read_only=True)`. `app_admin` ma `register.view` w macierzy §5, więc ścieżka niczego nie omija; `_check_admin_action` to sprawdza przy deklaracji trasy. Deklaracja trafia do `AccessRule(admin_action=register.view, admin_read_only=True)` — testy (`test_declared_actions`, `test_change_routes_admin_path_only_read_only_reads`, `tests/isolation_cases.py`) sprawdzają, że dokładnie te 7 tras zmian ma tę ścieżkę, a zapisy, akcje i pobranie pliku — żadnej.
- Ścieżka wąska (`_admin_read_context`, jak w ADR 0015 §7): zakres RLS **zastąpiony** jedną spółką (`app.company_ids = '{cid}'`, bez członkostw admina), `app.admin_scope = off`, `app.audit_global_read = off`, `SET TRANSACTION READ ONLY` przed pierwszym odczytem danych spółki. Każdy zapis w tej transakcji odrzuca PostgreSQL („read-only transaction”) niezależnie od polityk RLS. `CompanyContext.read_only = True` → karta bez akcji i pól edytowalnych.
- **Admin z rolą w spółce** nie wchodzi na ścieżkę administracyjną: `require_company(..., admin_read_only=True)` wybiera `_member_context` i decydują role członkostwa (jak dotąd; `ChangeActor.facts` odfiltrowuje `app_admin`). Ta reguła dotyczy wszystkich tras z `admin_read_only`, także `GET /companies/{cid}/audit/status` (wynik dla admina z rolą bez zmian — 200).
- Audytor (i każdy inny użytkownik) bez członkostwa: 404 jak dotąd. Nieistniejąca spółka: 404 także dla admina.
- Spółka zarchiwizowana: odczyt działa jak dla członków (200, karta bez akcji); zapisy admina bez roli — 404 (brak członkostwa), członków — 409 `company.archived`.

## 4. Pobranie pliku załącznika — bez ścieżki admina

Każde pobranie zapisuje wpis audytu w łańcuchu spółki (§6.5), czego transakcja READ ONLY nie pozwala zrobić. Rozważone: pobranie w transakcji zapisującej z zakresem poszerzonym o spółkę (`_admin_context`) — wymagałoby to ścieżki zapisu dla admina w domenie zmian, której §5 nie przewiduje (rozdział obowiązków), oraz wpisu w łańcuchu spółki, w której admin nie ma roli. Przyjęto rekomendację: admin bez roli widzi metadane i `sha256` (wystarczające do weryfikacji integralności pliku przekazanego inną drogą), treść pobiera dopiero po nadaniu sobie roli (audytowane `role_grant`).

## 5. Macierz w UI

`GET /permissions/matrix` pokazuje wiersz `register.view` z notą: „Administrator bez roli w spółce — tylko odczyt: bez akcji, edycji, komentarzy i pobierania plików załączników (widzi ich listę z sha256).” Zestaw ról w macierzy się nie zmienia (admin miał ✓ od początku).

## 6. Testy

`tests/test_api_admin_register_read.py` (odczyty, karta `admin_read_only`, transakcja READ ONLY i zakres jednej spółki, 404 + `access_denied` dla wszystkich zapisów i pobrania, admin z rolą editor/viewer, audytor bez roli, spółka zarchiwizowana), `tests/test_rbac_matrix.py` (`REGISTER_READ`), `tests/isolation_cases.py` (`admin_path=True` dla 7 tras odczytu), `tests/test_permissions.py`.
