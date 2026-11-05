# 0017. Eksport PDF i CSV: raporty, numeracja, RLS, audyt, worker (Etap 7)

- Status: przyjęta; punkty z §12 potwierdzone przez właściciela projektu (2026-11-03)
- Data: 2026-11-02
- Dotyczy: CLAUDE.md §4.1 (`report_exports`), §5, §6.5, §7, §8, §9, §12 (Etap 7); migracja `backend/alembic/versions/20261102_0009_report_exports.py`; `backend/app/{domain/reports.py, models/reports.py, services/reports.py, services/report_jobs.py, reports/*, api/v1/reports.py, permissions.py, worker.py}`; ADR 0006 §3/§5, ADR 0008 §4/§6, ADR 0009 §4, ADR 0012 §7, ADR 0013 §4/§7, ADR 0016

## 1. Potok (jeden dla każdego rodzaju i formatu)

1. **Dane** — `services/reports.py`: `build_register_data` (filtry rejestru `GET /companies/{cid}/changes`, odstępstwa z `app/domain/deviations.py` — bez powielania reguł, kafelki z `app/domain/reports.py`, Załącznik B, weryfikacja łańcucha) albo `build_change_card_data` (karta z `get_change_view`, oś czasu, ścieżka audytu, załączniki).
2. **`data_sha256`** = `sha256(canonical_json(dane))` — ta sama funkcja `app.domain.canonical` co łańcuch audytu (ADR 0006 §3), bez kopii.
3. **Render** wyłącznie z tych danych: `to_json_value(dane)` → Jinja2 (autoescape, `StrictUndefined`) → WeasyPrint. Szablon nie dostaje nic poza zahashowanymi danymi, numerem raportu i skrótem — PDF nie pokaże niczego, czego skrót nie obejmuje. CSV powstaje z tych samych danych.
4. **Zapis** w jednej transakcji: plik w magazynie (`STORAGE_PATH/reports/{company_id|all}/{id}.{pdf|csv}`, zapis `.part` + `fsync` + `os.replace`, jak załączniki — ADR 0013 §4), wiersz `report_exports` (`done`, `data_sha256`, `file_sha256`, `size`), wpis audytu. Błąd przed COMMIT usuwa plik.

Dane zawierają m.in. numer raportu, czas i autora wygenerowania, więc skrót jest unikalny dla raportu. Daty w danych są w UTC (format kanoniczny), w PDF/CSV wyświetlane jako `Europe/Warsaw`, `dd.MM.yyyy HH:mm` (`app/reports/labels.py`; zależność `tzdata`, bo Windows nie ma bazy stref). Etykiety i diffy jak we frontendzie (ADR 0015 §7): nazwy pól po polsku, osoby/kategorie/CI zamiast UUID, statusy, typy, ryzyko.

## 2. Zakres raportu, numeracja

- `kind = register` — jedna spółka (`company_id`) albo **raport zbiorczy** (`company_id = null`): wszystkie spółki, w których użytkownik ma rolę **auditor** (§5: „Auditor … raport zbiorczy”). Brak takiej spółki → 403. `kind = change_card` — tylko jedna spółka i `change_id` (422 `report.invalid_kind` / `report.change_required`; zmiana spoza spółki → 404 `change.not_found`).
- Raport rejestru wymaga okresu `[period_from, period_to)` (422 `report.period_required`, `report.invalid_period`); filtry jak w rejestrze (`period_by`, `status[]`, `type[]`, `category[]`, `ci[]`, `assignee`, `approver`, `approved_by` = id|`system`, `q`).
- Limit `REPORT_MAX_CHANGES` (domyślnie 5000) → 422 `report.too_large` (z `change_count`, `max_changes`), sprawdzany przy zamówieniu i ponownie przy generowaniu.
- **Numeracja:** `RAP-{PREFIX}-{YYYY}-{NNNN}` (licznik per spółka i rok wg `Europe/Warsaw`, `report_number_sequences`, `INSERT … ON CONFLICT DO NOTHING` + `SELECT … FOR UPDATE`, jak numery zmian — ADR 0013 §2). **Raport zbiorczy: `RAP-{YYYY}-{NNNN}`** (licznik z `company_id IS NULL`, `UNIQUE NULLS NOT DISTINCT`) — **odstępstwo od propozycji `RAP-ALL-…`**: prefiks spółki to dowolne 2–8 liter, więc spółka `ALL` dałaby kolizję numerów; forma bez segmentu prefiksu nigdy nie koliduje. CSV też dostaje numer (to też eksport). Równoległe eksporty jednej spółki czekają na siebie na liczniku do COMMIT (nie blokują zmian — osobna tabela).

## 3. `report_exports` i RLS

Kolumny: §4.1 + `kind`, `format` (`pdf|csv`), `change_id` (złożony FK do zmiany tej samej spółki), `scope_company_ids uuid[]` (spółki z danymi raportu; `{company_id}` dla raportu spółki), `period_from/to`, `filters jsonb`, `include_audit_trail`, `file_sha256`, `size`, `error`, `change_count`, `completed_at`. CHECK-i kształtu (`done` ⇒ skróty, plik, rozmiar; `failed` ⇒ `error`; `change_card` ⇒ zmiana i spółka; format numeru). Trigger `report_exports_guard`: wiersz jest niezmienny poza wynikiem generowania, a status przechodzi tylko `pending → done | failed` (zakończony wiersz zamrożony). `app_rw`: SELECT, INSERT, UPDATE — bez DELETE; TRUNCATE odrzuca trigger.

Polityki (nie upraszczamy — strażnik `tests/test_rls.py` je obejmuje):

| Komenda | Warunek |
|---|---|
| SELECT | `app_admin_scope()` **lub** `company_id = ANY (app_company_ids())` **lub** (`company_id IS NULL` **i** `generated_by_id = app_user_id()`) |
| INSERT, UPDATE | `company_id = ANY (app_company_ids())` **lub** (`company_id IS NULL` **i** `generated_by_id = app_user_id()` **i** `scope_company_ids <@ app_company_ids()`) |

- Wiersz zbiorczy widzi **tylko autor** i **ścieżka administracyjna**; inny audytor tej samej spółki go nie widzi (test). Zapisać go można tylko jako autor z **wszystkimi** spółkami raportu w zakresie transakcji.
- `admin_scope` daje wyłącznie odczyt (lista admina); zapis zawsze wymaga spółki w zakresie.
- `report_number_sequences`: wiersze spółki — polityka standardowa; licznik zbiorczy (`company_id IS NULL`) — każda transakcja z ustawionym `app.user_id`.

## 4. Uprawnienia (§5) i ścieżka administratora

Deklaracje w `app/permissions.py` (nowy rodzaj reguły `report`, `REPORT_KIND_PERMISSIONS`: `register → export.register`, `change_card → export.change_card`):

| Trasa | Zależność | Zachowanie |
|---|---|---|
| `POST /reports` | `require_report_order` | firma z treści: członkostwo (404 `company.not_found`), akcja rodzaju (403); zbiorczy — rola auditor (403) |
| `GET /reports` | `require_report_list` | z `company_id` (query): członkostwo (404), `export.change_card` (403); bez — spółki z prawem eksportu (brak → 403) i własne zbiorcze. Raporty rejestru tylko tam, gdzie `export.register`; edytor widzi tylko karty. Transakcja READ ONLY |
| `GET /reports/{id}`, `…/download` | `require_report` | niewidoczny (RLS: obca spółka, cudzy zbiorczy, brak) → 404 `report.not_found` bez ujawniania istnienia; widoczny bez prawa → 403 (zapisane); zbiorczy — autor z rolą auditor we **wszystkich** spółkach raportu **teraz** (utrata roli → 403) |
| `GET /companies/{cid}/changes/export.csv` | `require_company(export.register, admin_action=export.register)` | członkowie wg ról; admin — ścieżka poniżej |

Macierz: admin ✓, approver ✓, editor tylko karta, auditor ✓, viewer — (testy `tests/test_rbac_matrix.py`).

**Admin bez roli w spółce (decyzja w ramach Etapu 7, do potwierdzenia przez właściciela).** §5 daje `app_admin` ✓ dla eksportu, a eksport **zapisuje** (wiersz `report_exports`, wpis audytu w łańcuchu spółki), więc wąska ścieżka tylko do odczytu z ADR 0016 nie wystarcza. Przyjęto **jawną, nazwaną ścieżkę eksportu admina**: ten sam mechanizm co zapis inwentarza CI przez admina (ADR 0011 §1, `_admin_context(admin_scope=False)`): zakres transakcji = członkostwa admina + **ta jedna spółka**, **bez** `app.admin_scope` (spółki, członkostwa, słowniki pozostają nienaruszalne), `admin_action == action` i admin ma tę akcję w macierzy — nic nie jest omijane. Wpis audytu ma `context.admin_path = true`, aktor z rolą `app_admin`. Pobranie raportu przez admina poszerza zakres o spółki raportu (także bez `admin_scope`). Różnica wobec ADR 0016 §4 (pobranie załącznika bez ścieżki admina): tam §5 nie przewidywało zapisu admina w domenie zmian; tu §5 jawnie daje adminowi eksport. Dane w raporcie admin i tak widzi ścieżką ADR 0016. **Admin nie generuje raportu zbiorczego** (ten jest dla roli auditor) — patrz §12.

## 5. PDF: szablony, fonty, strony

- `app/reports/templates/`: `_layout.html` (CSS, `@font-face`, `@page`), `register.html`, `change_card.html`, `_audit_entry.html`. A4, marginesy 15 mm; nagłówek strony (tytuł, numer) i stopka: „Raport {numer} · sha256 danych: {data_sha256}” oraz „Strona X z Y” (`counter(page)`/`counter(pages)`).
- **Fonty:** IBM Plex Sans (Regular, Italic, Medium, SemiBold, Bold) i IBM Plex Mono (Regular, Medium), pliki WOFF „complete” z pakietów npm `@ibm/plex-sans@1.1.0` i `@ibm/plex-mono@2.5.0` (przez jsdelivr), licencja `OFL.txt`, źródła i SHA-256 w `SOURCES.txt`; sprawdzone pokrycie polskich znaków. Lokalizacja **`backend/app/reports/fonts/`** — jest w obrazie api/worker (`COPY app ./app`), wspólna z szablonami. WeasyPrint dostaje własny `URLFetcher`, który serwuje **wyłącznie** pliki z tego katalogu (`fail_on_errors=True`): brak fontu przerywa render zamiast cichego fontu systemowego, a raport nie może odczytać innego pliku ani zasobu sieciowego. W wygenerowanym PDF są osadzone tylko kroje IBM Plex (sprawdzone `pdffonts`).
- Raport rejestru — 9 sekcji §9 w kolejności: nagłówek; kafelki (liczba zmian, zatwierdzone przed wdrożeniem — `approved_at ≤ implemented_at` spośród wdrożonych, awaryjne, wdrożone bez weryfikacji); zakres i filtry; tabela (ID+status, tytuł+CI, kategoria, typ — awaryjna w czerwonej ramce, wykonawca, „Zatwierdził” = `approved_by` albo „system (automatycznie)”, wdrożenie, weryfikacja); odstępstwa w kolejności: awaryjne bez zatwierdzenia w 24 h, wdrożone bez weryfikacji, wdrożone poza oknem, wycofane, zatwierdzone przez autora — ta ostatnia w czerwonej ramce „BŁĄD KRYTYCZNY”; Załącznik A (per kategoria i per CI); Załącznik B (opcjonalny, `include_audit_trail`); weryfikacja łańcucha; pola podpisów.
- Karta zmiany: wszystkie pola, odstępstwa, osoby, okno, obiekty (z migawką), zgody właścicieli CI, oś czasu statusów (z wpisów `transition`/`create`; dla danych przykładowych także czas symulowany), załączniki z sha256, komentarze, pełna ścieżka audytu z diffami „przed → po” i skrótami (`hash_valid`).

## 6. Audyt

Każdy eksport → wpis `entity_type = report`, `action = export`, `entity_id` = raport, `context = {event, number, kind, format, status, data_sha256, file_sha256, size, change_count, period_*, filters, include_audit_trail, change_id/change_number?, chain?, admin_path?, source?}`:

- `event`: `generated` (PDF/CSV z `data_sha256`), `requested` (zamówienie w tle), `failed`, `downloaded` (każde pobranie `GET /reports/{id}/download`, zapisane **przed** wysłaniem pliku; pobranie, którego nie da się zapisać, nie jest serwowane).
- **Łańcuch:** spółki raportu. **Raport zbiorczy — wpis w łańcuchu każdej spółki raportu** (w kolejności id, ADR 0006 §7), a nie w łańcuchu globalnym: audytor nie czyta łańcucha globalnego (ADR 0008 §6), a każda spółka powinna mieć w swoim łańcuchu ślad, że jej dane wyeksportowano. Odrzucone: wpis tylko globalny (proponowany w zleceniu) — niewidoczny dla audytorów spółek.
- Łańcuch naruszony, który odrzuca dopisanie: jak w ADR 0009 §4 — `SAVEPOINT`, potem wpis w łańcuchu globalnym z `target_company_id`, `chain_append_failed`; gdy i to się nie uda, eksport się nie udaje (eksport bez wpisu jest niedopuszczalny).
- **Wynik weryfikacji łańcucha w chwili generowania** (§9 pkt 8) jest w danych raportu (więc pod `data_sha256`) i w `context.chain` wpisu `generated` (`ok, checked, first_broken_seq, head_seq, head_hash`) — sama weryfikacja jest więc audytowana (§6.4) tym wpisem, bez osobnego wpisu `audit/verify` (który odświeżałby znacznik „Łańcuch spójny” uprawnieniem eksportu). Skrót głowy łańcucha wydrukowany w PDF jest kotwicą poza bazą (ADR 0006 §5, ADR 0009 §4 „kotwice”). CSV nie weryfikuje łańcucha (nie drukuje wyniku).
- Pobranie: plik musi mieć zapisany `file_sha256` — zmieniony plik → 500 `report.file_corrupted`, brak pliku → 500 `report.file_missing`; nic nie jest wtedy wydawane ani zapisywane.

## 7. CSV (`GET /companies/{cid}/changes/export.csv`)

UTF-8 **z BOM** (Excel), separator **`;`** (separator listy w polskich ustawieniach regionalnych), CRLF, cudzysłowy tylko gdy potrzebne (RFC 4180), daty `Europe/Warsaw` `dd.MM.yyyy HH:mm`, puste pole = brak wartości. Kolumny (stała kolejność): Spółka, Numer, Tytuł, Kategoria, Podkategoria, Typ, Ryzyko, Status, Obiekty (CI), Zgłaszający, Wykonawca, Zatwierdzający (wskazany), Zatwierdził, Data zatwierdzenia, Okno od, Okno do, Data wdrożenia, Weryfikujący, Data weryfikacji, Odstępstwa, Zgłoszenie, Podstawa / wymóg, Data rejestracji. Ochrona przed wstrzyknięciem formuł (OWASP): pole zaczynające się od `= + - @ TAB CR` dostaje prefiks `'`. Filtry identyczne z listą rejestru (okres opcjonalny). Eksport jest synchroniczny, numerowany, zapisywany w magazynie (do ponownego pobrania z listy raportów) i audytowany; nagłówki `X-Report-Id`, `X-Report-Number`, `X-Data-SHA256`, `X-Content-SHA256` (wystawione w CORS). Trasa jest w routerze dołączanym **przed** routerem zmian (inaczej `…/changes/{change_id}` przechwyci `export.csv`, ADR 0013 §7).

## 8. Generowanie w tle (worker)

- Raport rejestru z liczbą zmian **> `REPORT_ASYNC_THRESHOLD`** (domyślnie 200, nowa zmienna w `.env.example` i docker-compose) → wiersz `pending`, wpis `requested`, zadanie `generate_report` w arq (`_job_id = report:{id}`), odpowiedź **202**; frontend odpytuje `GET /reports/{id}` aż `done|failed`. Mniejsze raporty i każda karta — synchronicznie (201), też z wierszem `report_exports`.
- Zadanie jest kolejkowane **przed** COMMIT transakcji żądania: niedostępny Redis → 503 `report.queue_unavailable` i wycofanie (bez osieroconego `pending`). Worker ponawia (`Retry`, do 10 prób co 2 s), dopóki wiersz nie jest widoczny.
- Worker (`services/report_jobs.py`) łączy się jako `app_rw`, w jednej transakcji: `app.user_id` = zamawiający, zakres RLS = **dokładnie spółki raportu**, wiersz `FOR UPDATE` (powtórzone zadanie → `skipped`). **Uprawnienie sprawdzane ponownie** (członkostwa z bazy, konto aktywne): utrata roli przed generowaniem → `failed` z komunikatem, bez danych. Błąd generowania → `SAVEPOINT`, wiersz `failed` + wpis `failed` w tej samej transakcji. `job_timeout` 900 s.

## 9. Testy

`tests/test_reports.py`: PDF z „zażółć gęślą jaźń” (pypdf), „Strona X z Y” na każdej stronie, `data_sha256` w stopce == `report_exports` == `audit_log` (marker `pdf`); karta zmiany (pola, ścieżka, załączniki, brak surowych UUID); 9 sekcji w kolejności, Załącznik B opcjonalny; skrót = kanoniczny skrót danych; **odstępstwa na danych seed**; wyróżnienie błędu krytycznego; CSV (BOM, `;`, CRLF, polskie znaki, strefa, formuły, filtry, audyt, ponowne pobranie); tło (202, `requested` → `generated`, `skipped`), ponowne sprawdzenie uprawnień w workerze, `Retry`; walidacje i limity; numeracja; lista wg uprawnień; ścieżka admina; podmieniony/brakujący plik; zamrożenie wiersza i brak DELETE; RLS wierszy zbiorczych. Macierz: `tests/test_rbac_matrix.py` (8 nowych kluczy, `POST /reports` w teście „każdy endpoint modyfikujący tworzy wpis audytu”). Izolacja: `tests/isolation_cases.py` (CSV, `GET /reports?company_id`, `REPORT_RESOURCE_ROUTES`, `REPORT_BODY_ROUTES`) i `tests/test_isolation_api.py` (obcy raport = brakujący, zamówienie raportu obcej spółki = nieistniejącej, zmiana B pod spółką A).

Testy z markerem `pdf` wymagają WeasyPrint z Pango (obraz Dockera, CI — kroki `apt-get` w `.github/workflows/ci.yml`, `REQUIRE_WEASYPRINT=1` zamienia pominięcie w błąd). Na hoście bez Pango (Windows) są pomijane, a testy uprawnień używają zastępczego renderera (`tests.factories.stub_pdf`).

**Dane seed** (ADR 0013 §9) — liczby sprawdzane testem: 40 zmian, 3 awaryjne, odstępstwa: awaryjne bez zatwierdzenia w 24 h — 2 (ALFA: SMBv1 bez zatwierdzenia; BETA: zatwierdzona po 30 h), wdrożone bez weryfikacji — 6 (ALFA 3, BETA 1, GAMMA 2), wycofane — 2 (ALFA, BETA), poza oknem — 0, zatwierdzone przez autora — 0. CLAUDE.md §11.7 mówi o „1 awaryjnej i 2 bez weryfikacji” — seed z Etapu 4 ma ich więcej (minimum spełnione).

## 10. API dla ekranu 5

`ReportOut`: `id, number, kind, format, status (pending|done|failed), company_id (null = zbiorczy), company {id,name,prefix}|null, companies[], change_id, change_number, period_from, period_to, filters, include_audit_trail, generated_by {id, display_name}, created_at, completed_at, change_count, data_sha256, file_sha256, size, error, download_url`. `POST /reports` → 201 (`done`) / 202 (`pending`) + `Location`; `GET /reports?company_id=&kind=&status=&limit=&offset=` → `Page[ReportOut]` (od najnowszych); `GET /reports/{id}`; `GET /reports/{id}/download` (409 `report.not_ready` / `report.failed`). Kody błędów: `report.not_found` 404, `company.not_found` 404, `change.not_found` 404, `auth.forbidden` 403, `report.period_required`/`report.invalid_period`/`report.invalid_kind`/`report.change_required`/`report.too_large`/`change.invalid_filter` 422, `report.not_ready`/`report.failed` 409, `report.queue_unavailable` 503, `report.file_missing`/`report.file_corrupted` 500.

## 11. Konfiguracja

`REPORT_ASYNC_THRESHOLD` (≥ 0, domyślnie 200), `REPORT_MAX_CHANGES` (≥ 1, domyślnie 5000). Obraz: biblioteki WeasyPrint jak dotąd, `XDG_CACHE_HOME=/tmp/cache` (cache fontconfig; `/app` nie jest zapisywalny dla `appuser`).

## 12. Decyzje właściciela (2026-11-03)

Właściciel projektu potwierdził wszystkie rozstrzygnięcia przyjęte w tym ADR:

1. **Eksport admina bez roli w spółce** — dozwolony nazwaną ścieżką eksportu (§4), z `context.admin_path=true` w audycie. §5 bez zmian.
2. **Raport zbiorczy** — tylko spółki, w których użytkownik ma rolę `auditor`; admin bez tej roli dostaje 403 (może nadać sobie rolę audytora — z wpisem w audycie).
3. **Numer raportu zbiorczego** — `RAP-{YYYY}-{NNNN}` (§2); prefiks `ALL` nie jest zastrzegany.
4. **Wpis audytu raportu zbiorczego** — w łańcuchu każdej spółki objętej raportem, nie w globalnym (§6).
5. **Pobranie raportu po utracie roli** — niedozwolone (403), bo plik zawiera dane spółki.

## 13. Frontend (Etap 7, 2026-11-03)

- **Trasy:** `/c/{PREFIKS}/reports` (raporty spółki) i `/c/all/reports` (raport zbiorczy audytora). Pseudo-prefiks `all` jak w przełączniku spółek (ADR 0002, ADR 0014 §2) — przełącznik zachowuje sekcję, więc „Wszystkie spółki (audytor)” na ekranie raportów prowadzi wprost do raportu zbiorczego. Odrzucone `/reports/all`: druga konwencja adresu spółki obok `/c/{prefix}`.
- **Widoczność wg §5 (powiela backend dla UX):** formularz raportu rejestru — admin (także bez roli: baner o eksporcie administratora, §4), approver, auditor; editor — tylko lista kart zmian (`GET /reports?company_id=…&kind=change_card`); viewer — „Brak dostępu” (bez wywołania API). `/c/all/reports` — tylko użytkownik z rolą auditor (admin bez niej: „Brak dostępu”, §12 pkt 2).
- **„Eksport PDF” w rejestrze** = przejście na ekran raportów z filtrami rejestru w query stringu (wypełniają formularz; bez okresu — bieżący kwartał). Wybrane zamiast dialogu: jeden formularz raportu, adres do udostępnienia. **„CSV”** = bezpośrednie pobranie z filtrami listy.
- **Okres:** dni kalendarzowe czasu polskiego, oba włącznie (jak `from`/`to` rejestru, ADR 0014 §5) → `period_from` = początek dnia „od”, `period_to` = początek dnia po „do” (UTC). Walidacja w UI tylko powiela `report.period_required` / `report.invalid_period`.
- **Raport zbiorczy:** filtry obiektu (CI) i wykonawcy są ukryte (identyfikatory jednej spółki); kategorie z globalnego słownika; „Zatwierdził: system” zostaje (niezależne od spółki).
- **Odpytywanie `pending`:** co 2 s, limit 15 min (= `job_timeout` workera, §8), koniec przy opuszczeniu ekranu; po limicie wiersz pokazuje „odśwież listę”. Raport zamówiony na ekranie pobiera się automatycznie po `done`.
- **Pobieranie:** dio z tokenem → `Blob`; nazwa z `Content-Disposition` (w `expose_headers`), awaryjnie `X-Report-Number`.


## 14. Poprawki po recenzji (2026-11-03)

Zmiany względem §6–§8 (pierwszeństwo przed tamtymi zdaniami, gdy się różnią):

1. **Raport nie zostaje w `pending`.** `report_jobs.run` łapie `asyncio.CancelledError`/`TimeoutError` (`job_timeout`, zamknięcie workera) oraz błędy poza punktem zapisu generowania (np. COMMIT) i oznacza wiersz `failed` (+ wpis `failed`) w **nowej** transakcji jako zamawiający, potem błąd idzie dalej. Co i tak ucieknie (utracone zadanie w Redis, awaria procesu), zamyka cron workera `report_maintenance` (co 5 min): `pending` starszy niż `job_timeout` (900 s) + ponowienia widoczności wiersza (10 × 2 s) + margines 300 s → `failed` „Przekroczono czas generowania raportu…”, wpis `failed` z `context.source = "maintenance"`, każdy w osobnej transakcji jako zamawiający; wiersz zablokowany przez trwające generowanie jest pomijany (`SKIP LOCKED`). Lista kandydatów jest czytana ścieżką `admin_scope` w transakcji READ ONLY.
2. **Pliki osierocone.** Ten sam cron usuwa pliki `STORAGE_PATH/reports/*/*` (także `.part`) bez wiersza `done` z tym `storage_key`, starsze niż próg z pkt 1 (świeższe mogą należeć do generowania przed COMMIT).
3. **Odmowa pobrania jest audytowana.** `report.file_missing` / `report.file_corrupted` → wpis `report`/`export`, `event = integrity_failed`, `code`, `expected_sha256`, `found_sha256` (`null` dla brakującego pliku), w **osobnej transakcji** (żądanie i tak kończy się 500 i wycofaniem — jak `record_access_denied`), w łańcuchach spółek raportu, z fallbackiem do globalnego (`target_company_id`). Zmienia zdanie §6 „nic nie jest wtedy … zapisywane”: plik nadal nie jest wydawany.
4. **Pobranie bez TOCTOU.** Plik jest czytany raz; te same, zweryfikowane bajty idą w odpowiedzi (`Response`, nie `FileResponse`).
5. **Dopisywanie zawsze pod `SAVEPOINT`.** Każde zdarzenie eksportu (także CSV, `requested`, `failed`, `downloaded`) najpierw próbuje łańcucha spółki w `begin_nested()`; odrzucone → łańcuch globalny z `target_company_id` i `chain_append_failed`, niezależnie od wcześniejszej weryfikacji.
6. **`admin_path`.** `context.admin_path = true` także przy `downloaded` (admin bez roli w którejś spółce raportu) i przy generowaniu/porażce w workerze (`job.admin_path`).
7. **Zakres ścieżki eksportu admina.** Zakres transakcji = **tylko** spółka docelowa (raport: spółki raportu), bez `admin_scope`, bez odczytu łańcucha globalnego, transakcja zapisywalna (`_admin_export_context`; jak `_admin_read_context`, ale bez READ ONLY). Admin **z rolą** w spółce eksportuje CSV ścieżką członka (`require_register_export`, spójnie z ADR 0016), bez `admin_path`.
8. **Ścieżka audytu.** Karta zmiany — bez limitu. Załącznik B rejestru — limit 1000 wpisów na zmianę, ale w danych (pod `data_sha256`) jest `truncated`, `omitted`, `audit_trail_limit`, `audit_trails_truncated`, a PDF pokazuje ostrzeżenie (sekcja i przy zmianie). `REPORT_DATA_FORMAT = 2`.
9. **Migracja 0009** — `downgrade` odmawia przy niepustym `report_exports`, chyba że `-x allow_audit_data_loss=yes` (jak rdzeń audytu).
10. **Worker:** `timeout` 900 s i `max_tries` 10 tylko dla `generate_report` (`arq.worker.func`); globalnych `job_timeout`/`max_tries` w `WorkerSettings` nie ma (codzienna weryfikacja łańcuchów zachowuje `timeout=900` na swoim cronie).
11. **Spójny odczyt w workerze.** Dane raportu są czytane w osobnej transakcji `REPEATABLE READ, READ ONLY` (pierwsza instrukcja transakcji, przed jakimkolwiek odczytem; `app.db.snapshot_session`) — zmiany, ścieżki audytu i weryfikacja łańcucha z jednej migawki. Wiersz raportu i wpisy audytu zapisuje dalej transakcja READ COMMITTED trzymająca blokadę wiersza: blokada głowy łańcucha (`FOR UPDATE`) w REPEATABLE READ kończyłaby się błędem serializacji przy każdym równoległym dopisaniu do łańcucha spółki w trakcie wielominutowego generowania. **Ograniczenie ścieżki synchronicznej:** raport ≤ `REPORT_ASYNC_THRESHOLD` zmian, karta i CSV są budowane w transakcji żądania (READ COMMITTED — poziomu nie da się zmienić po pierwszych zapytaniach uwierzytelnienia), więc zmiana zatwierdzona równolegle w trakcie (ułamek sekundy) może być widoczna w części zapytań. Skrót `data_sha256` zawsze odpowiada temu, co wydrukowano; ryzyko dotyczy tylko spójności między sekcjami tego samego raportu i jest akceptowane dla małych raportów.
12. **Błąd generowania synchronicznego** (inny niż 4xx) → wpis `failed` w osobnej transakcji (łańcuchy spółek raportu, fallback globalny) z `persisted = false`, `exception` i bez `number` (wiersz i numer wycofuje transakcja żądania, numer zostanie użyty ponownie); generowanie idzie pod `SAVEPOINT`, którego wycofanie zwalnia blokady głów łańcuchów przed tą transakcją. Odpowiedź: 500.
