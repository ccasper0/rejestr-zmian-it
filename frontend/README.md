# Rejestr zmian IT — frontend

Aplikacja Flutter, target wyłącznie **web** (Riverpod, go_router, dio, freezed, data_table_2). Specyfikacja: `../CLAUDE.md`; decyzje frontendu: `../docs/decisions/0014-frontend-stage-5.md`, logowanie kontami lokalnymi: `../docs/decisions/0020-frontend-local-login.md` (kontrakt API: ADR 0018, kody błędów infrastruktury: ADR 0019).

## Wymagania

- Flutter 3.47.5 / Dart 3.13.4 (ADR 0003)
- Działające API (`backend/`) — lokalnie domyślnie `http://localhost:8000`: w trybie `AUTH_MODE=dev` z danymi przykładowymi (`python -m app.cli seed`) albo `AUTH_MODE=local` (konta z hasłem, ADR 0018)

## Uruchomienie lokalne z logowaniem deweloperskim

1. Backend w trybie dev (patrz `../README.md`, „Szybki start”): w `.env` `APP_ENV=dev`, `AUTH_MODE=dev`, losowy `DEV_AUTH_SECRET`, potem

   ```bash
   docker compose up -d --build
   docker compose exec api python -m app.cli seed
   ```

2. Frontend:

   ```bash
   cd frontend
   flutter pub get
   dart run build_runner build   # po zmianie modeli freezed/json
   flutter run -d chrome --web-port=5000 --dart-define=API_URL=http://localhost:8000
   ```

   Port 5000 jest na liście `CORS_ORIGINS` w `.env.example` (API na innym originie niż `flutter run` wymaga CORS). Inny port = dopisz go do `CORS_ORIGINS` i zrestartuj `api`.

3. Otwórz <http://localhost:5000>. Ekran logowania pokaże użytkowników testowych z `GET /auth/dev/users` (np. „Ewa Edytorska” — editor, „Jan Zatwierdzający” — approver, „Alicja Audytorka” — auditor). Wylogowanie: ikona obok nazwy użytkownika w panelu.

Zamiast `flutter run` można użyć gotowego obrazu: `docker compose up -d --build web` → <http://localhost:8080> (nginx, ten sam origin co API, bez CORS).

## Logowanie kontami lokalnymi (`AUTH_MODE=local`)

Domyślny i produkcyjny tryb backendu (ADR 0018). Pierwszego administratora zakłada się w API: `docker compose exec api python -m app.cli create-admin --email … --name …` (hasło z terminala albo `--generate-password`). Kolejne konta zakłada administrator w aplikacji: „Użytkownicy i role” → „Nowy użytkownik”.

- **Logowanie** (`/login`): e-mail i hasło, Enter wysyła, pokaż/ukryj hasło. Każda porażka daje ten sam komunikat (nieznany e-mail, złe hasło, konto zablokowane lub nieaktywne). Po 429 (`auth.too_many_attempts` z API albo `request.rate_limited` z nginx) przycisk jest zablokowany na czas z `Retry-After` (z odliczaniem).
- **Hasło tymczasowe** (nowe konto, reset przez administratora): po zalogowaniu każdy adres przekierowuje do `/account/password` — dopóki hasło nie zostanie zmienione, działa tylko zmiana hasła i „Wyloguj” (tak samo po 403 `auth.password_change_required` z dowolnego endpointu).
- **Zmiana hasła z własnej woli:** menu konta (⋮ obok nazwy na dole panelu nawigacji) → „Zmień hasło”. Po zmianie wszystkie sesje użytkownika są zamknięte, a karta dostaje nową parę tokenów.
- **Wylogowanie:** menu konta → „Wyloguj” (`POST /auth/logout`, potem czyszczenie `sessionStorage`).

### Tryb logowania

| `--dart-define` | Zachowanie |
|---|---|
| brak `AUTH_MODE` (zalecane) | aplikacja pyta API: `GET /auth/dev/users` istnieje → logowanie deweloperskie; 404 → e-mail i hasło (konta lokalne) |
| `AUTH_MODE=dev` | zawsze logowanie deweloperskie |
| `AUTH_MODE=local` | zawsze e-mail i hasło |

### Sesja i tokeny

- Tokeny są w pamięci i w `sessionStorage` karty (klucz `rejestr.auth`): przeładowanie nie wylogowuje, zamknięcie karty — tak; każda karta ma osobną sesję (ADR 0014 §1).
- Konta lokalne: token dostępu (domyślnie 15 min) jest odświeżany `POST /auth/refresh` **przed** wygaśnięciem (przy pierwszym żądaniu na minutę przed końcem) albo po 401 `auth.invalid_token` (jedno odświeżenie i jedno powtórzenie żądania). Odświeżanie jest **single-flight** w karcie: równoległe żądania czekają na jedno odświeżenie — dwa odświeżenia tym samym jednorazowym tokenem backend uznaje za kradzież i zamyka sesję.
- Koniec sesji → `/login` z komunikatem: nieudane odświeżenie (401 `auth.invalid_refresh_token`), 401 `auth.session_expired` (wylogowanie gdzie indziej, zmiana/reset hasła, limit 12 h), 403 `auth.user_inactive` (dezaktywacja). Tryb dev: każde 401 kończy sesję (bez odświeżania).
- Komunikaty dla całej aplikacji (pasek u dołu ekranu): 429 `request.rate_limited` z czasem z `Retry-After`, 503 `api.unavailable`. Przy pracy na innym originie niż API (`flutter run` na :5000) przeglądarka nie udostępnia nagłówka `Retry-After` (brak w `expose_headers` CORS API) — wtedy komunikat mówi „Odczekaj chwilę”, a formularz logowania blokuje się na 30 s.

### `API_URL`

`API_URL` to **origin API bez `/api`** — klient sam dokleja `/api/v1` (ADR 0001).

| `--dart-define` | Bazowy URL klienta |
|---|---|
| brak `API_URL` | `http://localhost:8000/api/v1` |
| `API_URL=http://localhost:8000` | `http://localhost:8000/api/v1` |
| `API_URL=` (pusty) | `/api/v1` — ten sam origin (nginx proxuje `/api/` do API) |

## Build produkcyjny (Docker / nginx)

```bash
flutter build web --release --csp --no-web-resources-cdn --dart-define=API_URL=
```

`--csp` (bez `eval`/`new Function`) i `--no-web-resources-cdn` (CanvasKit z tego samego originu) są wymagane przez CSP nginx (ADR 0019 §2); `frontend/Dockerfile` buduje z tymi flagami. Nie dodawaj zależności, które ładują skrypty, fonty lub style z zewnętrznych CDN albo potrzebują `eval`.

Aplikacja używa ścieżek bez `#` (`/c/ALFA/changes`), więc serwer musi kierować nieznane ścieżki do `index.html`.

## Jakość

```bash
flutter analyze
flutter test
dart format --set-exit-if-changed lib test
```

Testy widgetów mockują API adapterem dio (`test/helpers.dart`, `FakeApi`) — nie potrzebują backendu. Logowanie kontami lokalnymi: `test/core/auth_interceptor_test.dart` (Bearer, single-flight refresh — równoległe 401 → jedno odświeżenie, kody sesji, 429/503), `test/features/login_test.dart`, `change_password_test.dart`, `admin_accounts_test.dart`, `service_errors_test.dart` (413/415 przy załącznikach, komunikaty 429/503).

## Ekrany i adresy

| Adres | Ekran |
|---|---|
| `/login` | logowanie (`?from=` — powrót po zalogowaniu) |
| `/account/password` | zmiana własnego hasła (konta lokalne); wymuszona przy haśle tymczasowym (`?from=` — powrót po zmianie) |
| `/c/{PREFIKS}/changes` | rejestr zmian; filtry w query stringu (`q`, `status`, `type`, `category`, `ci`, `assignee`, `approved_by`, `from`, `to`, `period_by`, `sort`, `page`); admin bez roli w spółce — tylko odczyt (ADR 0016) |
| `/c/{PREFIKS}/changes/new` | tworzy szkic z numerem i przechodzi do edycji (admin bez roli: „Brak dostępu”) |
| `/c/{PREFIKS}/changes/{NUMER}` | karta zmiany; admin bez roli — „Podgląd administratora — tylko odczyt”: bez akcji, edycji, komentarzy, dodawania i pobierania załączników (nazwa, rozmiar, sha256) |
| `/c/{PREFIKS}/changes/{NUMER}/edit` | formularz (autozapis co 30 s; admin bez roli: „Brak dostępu”) |
| `/c/all/changes` | widok audytora „Wszystkie spółki” (lista spółek z przejściem do ich rejestrów i do raportu zbiorczego) |
| `/c/{PREFIKS}/reports` | raporty i eksport (ADR 0017 §13): formularz raportu rejestru PDF (approver, auditor, admin — także bez roli) i lista raportów spółki; editor — tylko lista kart zmian; viewer — „Brak dostępu”. Query string jak w rejestrze (`from`, `to`, `period_by`, `status`, `type`, `category`, `ci`, `assignee`, `approved_by`, `q`) tylko wypełnia formularz — tak działa „Eksport PDF” w rejestrze |
| `/c/all/reports` | raport zbiorczy audytora (`company_id = null`: wszystkie spółki, w których ma rolę auditor); bez filtrów obiektu i wykonawcy (dotyczą jednej spółki) |
| `/c/{PREFIKS}/ci` | obiekty (CI) spółki; filtry `q`, `type`, `status` (`active`/`inactive`), `page` |
| `/c/{PREFIKS}/audit` | dziennik audytu spółki (audytor spółki; admin — każdej spółki, także bez roli); filtry `entity`, `action`, `actor`, `from`, `to`, `page` |
| `/admin/companies` | spółki: tabela, panel „Nowa spółka” i edycja (kategorie, członkowie i role, weryfikacja łańcucha, archiwizacja) |
| `/admin/categories`, `/admin/ci-types` | słowniki; filtr `status` (`active`/`inactive`) |
| `/admin/permissions` | macierz uprawnień (tylko odczyt, z `GET /permissions/matrix`) |
| `/admin/users`, `/admin/users/{id}` | katalog użytkowników (`q`, `page`) ze stanem kont (hasło ustawione, wymaga zmiany hasła, zablokowane do …, nieaktywne) i „Nowy użytkownik”; karta: konto (zmiana nazwy, reset hasła, dezaktywacja/aktywacja, uprawnienia administratora — z potwierdzeniem; hasło tymczasowe pokazywane jednorazowo z przyciskiem „Kopiuj”) i role we wszystkich spółkach |
| `/admin/audit` | dziennik audytu — łańcuch globalny (admin) |

Daty w UI: `dd.MM.yyyy HH:mm`, strefa `Europe/Warsaw` (pakiet `timezone`).

## Struktura

- `lib/app/` — aplikacja, routing z przekierowaniem logowania, strona startowa
- `lib/core/` — konfiguracja, klient API (`api_client.dart`: Bearer, odświeżanie tokenów, kody sesji), błędy API po polsku (`api_error.dart`, `Retry-After`, typy załączników), komunikaty dla całej aplikacji (`service_notice.dart`), sesja (`/me`), logowanie i tokeny (`auth/`), czas (`time.dart`), pliki w przeglądarce (`files/`), tokeny wizualne (`theme.dart`)
- `lib/features/changes/` — `data/` (modele, API, filtry rejestru), `presentation/` (rejestr, karta, formularz, akcje, kontrola przed wysłaniem)
- `lib/features/auth/` — logowanie (dev i konta lokalne), zmiana hasła
- `lib/features/admin/` — `data/` (modele, API, walidacja UX), `presentation/` (spółki, słowniki, macierz, użytkownicy i role) — ADR 0015
- `lib/features/ci/`, `lib/features/audit/` — inwentarz CI i dziennik audytu (filtry w URL, weryfikacja łańcucha)
- `lib/widgets/` — wspólne: `AppShell`, `CompanySwitcher`, `CompanyGate`, `StatusPill`, `AuditTimeline`, `ApiHealthIndicator`
- `assets/fonts/` — IBM Plex Sans / Mono (SIL OFL 1.1, `OFL.txt`)

## Scenariusz akceptacyjny Etapu 5

Kryterium §12 (Etap 5): przejście zmiany od szkicu do weryfikacji. Wymaga stosu w trybie dev z danymi przykładowymi (`docker compose down -v && docker compose up -d --build && docker compose exec api python -m app.cli seed`).

### Przez API (wykonane 2026-10-30)

`python -X utf8 tool/e2e_api_scenario.py` (domyślnie `http://localhost:8000/api/v1`). Przebieg na lokalnym stosie, zmiana **CHG-ALFA-2026-0017**:

| Krok | Kto | Wynik |
|---|---|---|
| 1. `POST /companies/{ALFA}/changes` | Ewa (editor) | 201, szkic z numerem, `version` 1 |
| 2. `PATCH` z `version` 1 (tytuł, kategoria FW, CI, ryzyko wysokie, osoby, okno, podstawa) | Ewa | 200, `version` 2; readiness: brak `rollback_plan.required_high_risk` |
| 2a. `PATCH` z nieaktualną `version` 1 | Ewa | 409 `change.version_conflict`, `current_version` 2 |
| 3a. `submit` bez planu wycofania | Ewa | 422 `change.not_ready` z checkami |
| 3. `PATCH` planu wycofania, `submit` | Ewa | `draft → pending_approval` |
| 3b. `approve` przez autorkę | Ewa | 403 `auth.forbidden` (editor nie ma `change.approve`) |
| 4. `approve` z `version` karty | Jan (approver) | `→ approved`, `approved_by` = Jan; `allowed_actions` Jana: `return, approve, reject` |
| 5. `implement` | Ewa (wykonawca) | `→ implemented`, ostrzeżenie `implementation.outside_window` (okno za 2 dni) |
| 6. `verify` | Jan (weryfikujący) | `→ verified` |
| 7. `GET …/audit` | Ewa | 7 wpisów (`create`, 2× `update`, `transition` submit/approve/implement/verify), wszystkie `hash_valid` |

Karta tej zmiany pokazuje odstępstwo „wdrożona poza zatwierdzonym oknem” (ADR 0012 §7).

### W przeglądarce (http://localhost:8080 albo `flutter run` na :5000)

1. Zaloguj się jako **Ewa Edytorska** → rejestr Alfy → „Nowa zmiana”: szkic dostaje numer, otwiera się formularz.
2. Uzupełnij: tytuł, kategorię „Firewall / sieć”, obiekt (wyszukiwarka CI), typ „Normalna”, ryzyko „Wysokie” — od razu widać błąd „Plan wycofania jest wymagany przy wysokim ryzyku” i wymóg okna; „Wyślij do zatwierdzenia” jest nieaktywne.
3. Uzupełnij plan wdrożenia i wycofania, wykonawcę (Ewa), zatwierdzającego (Jan — podpowiedź domyślnego), weryfikującego (Jan), okno od/do w przyszłości (czas polski), podstawę/wymóg. „Zapisz szkic” (albo odczekaj 30 s — autozapis) → panel „Kontrola przed wysłaniem”: „Gotowa do wysłania”. Opcjonalnie dodaj załącznik.
4. Wyjście z niezapisanymi zmianami (np. „Dziennik audytu” w panelu): formularz najpierw zapisuje; przeładowanie strony z niezapisanymi zmianami pokazuje ostrzeżenie przeglądarki.
5. „Wyślij do zatwierdzenia” → status „Do zatwierdzenia”.
6. Wyloguj (ikona w panelu) → **Jan Zatwierdzający** → „Do zatwierdzenia” (licznik) → karta: tylko „Zatwierdź”, „Zwróć do poprawy”, „Odrzuć” (+ „Edytuj” okna i zatwierdzającego) → „Zatwierdź”.
   - Konflikt wersji: w dwóch kartach przeglądarki (osobne logowanie — `sessionStorage` jest per karta) otwórz edycję tej samej zmiany, zapisz zmianę w jednej, potem w drugiej → baner konfliktu z różnicami i wyborem „Zapisz moje na nowej wersji” / „Odrzuć moje zmiany”.
7. **Ewa** → karta → „Oznacz jako wdrożoną”.
8. **Jan** → „Potwierdź weryfikację” → „Zweryfikowana”: pasek etapów, ścieżka audytu z diffami „przed → po”, kolumna „Zatwierdził” w rejestrze.
9. Dodatkowo: Alicja (audytor) — brak przycisków akcji, „Wszystkie spółki (audytor)”; Piotr (viewer) — brak „Nowa zmiana”; filtry rejestru przeżywają przeładowanie; okno < 900 px — panel jako szuflada; spreparowany adres `/c/ALFA/changes/..%2F..%2Fstats` — „Nie znaleziono strony”.

## Scenariusz akceptacyjny Etapu 6

### Przez API (wykonane 2026-10-30)

`python -X utf8 tool/e2e_admin_scenario.py` — admin tworzy spółkę **DELTA**, ustawia kategorie i role, editor DELTA dodaje obiekt. Spółki nie da się usunąć, więc DELTA zostaje w lokalnej bazie (ponowne uruchomienie tylko powtarza kontrole).

| Krok | Kto | Wynik |
|---|---|---|
| 1. `POST /companies` z prefiksem `DE1` | Adam (admin) | 422 `company.invalid_data` |
| 2. `POST /companies` DELTA, NIP `526-025-09-95`, domyślny zatwierdzający Jan | Adam | 201, NIP znormalizowany `5260250995` |
| 2a. nazwa „delta SP. Z O.O.” / `PATCH` prefiksu / `POST` jako editor | Adam / Ewa | 409 `company.name_taken` / 422 `company.prefix_immutable` / 403 |
| 3. `PUT …/categories` z zatwierdzającym FW = Jan | Adam | 422 `company_category.approver_not_eligible` (Jan nie ma jeszcze roli) |
| 4. `PUT …/categories` ACC, FW, SRV | Adam | 200 |
| 5. `PUT …/members/{id}`: Ewa `[editor]`, Jan `[approver]`, Alicja `[auditor]` | Adam | 200 ×3 |
| 6. `PUT …/categories` z FW → Jan | Adam | 200 |
| 7. `POST /companies/{DELTA}/ci` FW-DELTA-01, właściciel Jan | Ewa (editor DELTA) | 201; duplikat `fw-delta-01` — 409 `ci.identifier_taken`; Piotr — 404; Alicja — 403 |
| 8. `GET /companies` | Adam | DELTA: `active_ci` 1, `editors` 1, `approvers` 1, `auditors` 1 |
| 9. `GET /audit?company_id=DELTA`, `POST /audit/verify` | Alicja | 6 wpisów (`company_category:update`, 3× `membership:role_grant`, `company_category:update`, `ci:create`); łańcuch spójny |
| 10. `GET /audit?entity_type=company&action=create` | Adam | wpis utworzenia DELTA w łańcuchu globalnym |

### W przeglądarce (http://localhost:8080)

1. **Adam Administrator** → „Spółki i słowniki”: tabela z DELTA (Obiekty 1, Edytorzy 1, Zatwierdzający 1). Kliknij Alfę → panel edycji: prefiks zablokowany, sekcje „Kategorie dostępne w spółce” (zatwierdzający kategorii tylko spośród zatwierdzających Alfy), „Członkowie i role”, „Zweryfikuj łańcuch”.
2. „Nowa spółka”: wpisz prefiks `ep1` → wielkie litery i błąd inline; `EPSILON` → podgląd `CHG-EPSILON-2026-0001`; NIP `5260250994` → błąd sumy kontrolnej. Kliknij inną zakładkę z niezapisanym formularzem → pytanie o odrzucenie zmian. (Nie zapisuj, jeśli nie chcesz kolejnej spółki w bazie.)
3. Zakładka „Kategorie zmian”: drzewo, filtr „Nieaktywne” w adresie; „Dodaj podkategorię” przy FW → „Wymaga zatwierdzenia” zaznaczone i zablokowane z wyjaśnieniem. „Typy obiektów (CI)”, „Role i uprawnienia” (macierz tylko do odczytu).
4. „Użytkownicy i role” → wyszukaj „Ewa” → karta: role w ALFA, BETA, GAMMA, DELTA → „Zmień role” w DELTA (checkboxy, zapis pełnego zestawu). Na własnej karcie admina „Nadaj rolę w spółce” → ostrzeżenie o nadaniu roli sobie („Anuluj”, jeśli nie chcesz zmieniać swoich ról).
5. Wyloguj → **Ewa Edytorska** → przełącznik spółki: DELTA → „Obiekty (CI)”: FW-DELTA-01, filtry w adresie, „Nowy obiekt”; edycja → „Obiekt aktywny” (dezaktywacja).
6. **Alicja Audytorka** → DELTA → „Dziennik audytu”: wpisy z diffami ról i kategorii, filtry w adresie, „Zweryfikuj łańcuch” → „Łańcuch spółki spójny”. Ewa w „Dziennik audytu” widzi „Brak dostępu”.
7. **Adam** → przełącznik spółki: wszystkie spółki (bez roli — „(administrator)”); DELTA → „Rejestr zmian”: rejestr i karty z banerem „Podgląd administratora — tylko odczyt” (bez „Nowa zmiana”, akcji, komentarzy i pobierania załączników; w panelu brak „Do zatwierdzenia”; ADR 0016), `/c/DELTA/changes/new` → „Brak dostępu”; „Obiekty (CI)” i „Dziennik audytu” działają. Potem `/admin/audit`: łańcuch globalny (utworzenie DELTA, logowania). Okno < 900 px: panel jako szuflada, ekrany bez przepełnień.

### Fikstury kontraktu

`test/contract/api_contract_test.dart` parsuje modelami Dart rzeczywiste odpowiedzi API zapisane w `test/fixtures/api/`. Odświeżenie po zmianie API (po jednym przebiegu `tool/e2e_api_scenario.py`; skrypt dopisuje do lokalnej bazy jeden załącznik i jeden anulowany szkic):

```bash
python -X utf8 tool/dump_api_fixtures.py
python -X utf8 tool/dump_admin_fixtures.py   # Etap 6: jedna weryfikacja łańcucha ALFA
python -X utf8 tool/dump_report_fixtures.py  # Etap 7: raport rejestru ALFA i karta zmiany
flutter test test/contract
```

Fikstury raportów (`report_*.json`, `reports_page.json`, `problem_report_too_large.json`) przygotowano ręcznie według `backend/app/schemas/reports.py` i `app/errors.py` — lokalny stos działał wtedy na kodzie sprzed Etapu 7. `report_pending.json` i `problem_report_too_large.json` zostają ręczne (dane seed nie przekraczają progów `REPORT_ASYNC_THRESHOLD` / `REPORT_MAX_CHANGES`).

## Eksport (Etap 7)

- **Rejestr:** „Eksport PDF” przechodzi do `/c/{PREFIKS}/reports` z bieżącymi filtrami (bez sortowania i strony); „CSV” pobiera `GET …/changes/export.csv` z tymi samymi filtrami co lista. Oba przyciski tylko przy prawie `export.register` (approver, auditor, admin).
- **Karta zmiany:** „Karta PDF” = `POST /reports` (`change_card`) i pobranie po `done` (przy `pending` odpytywanie). Dla editora, approvera, auditora i admina (także na ścieżce tylko do odczytu, ADR 0017 §12); viewer — brak przycisku.
- **Pobieranie:** pliki zawsze przez klienta API z nagłówkiem `Authorization` (nigdy goły link do `download_url`), bajty → `Blob` → `<a download>`. Nazwa pliku z `Content-Disposition` (wystawiony w CORS), awaryjnie z `X-Report-Number`.
- **Raport w tle (202 `pending`):** odpytywanie `GET /reports/{id}` co 2 s, najdłużej 15 min (`job_timeout` workera); opuszczenie ekranu kończy odpytywanie; raport zamówiony na ekranie pobiera się sam po `done`.
