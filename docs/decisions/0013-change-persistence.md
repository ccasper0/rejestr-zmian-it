# 0013. Persystencja zmian: tabele, numeracja, akcje, audyt, załączniki, ochrona w bazie (Etap 4, faza B)

- Status: przyjęta; punkty z §13 potwierdzone przez właściciela 2026-10-29; poprawki po recenzji Etapu 4 (2026-10-29) wprowadzone w §3, §4, §5, §6, §7, §11
- Data: 2026-10-29
- Dotyczy: CLAUDE.md §4.1, §4.2, §5, §6.3, §6.5, §7, §8, §10.1, §11.7; migracja `backend/alembic/versions/20261029_0008_changes.py`; `backend/app/models/changes.py`, `backend/app/services/{changes,numbering,comments,attachments,seed_changes}.py`, `backend/app/api/v1/changes.py`, `backend/app/permissions.py`; ADR 0007, 0008, 0011, 0012

Faza B ładuje fakty, woła domenę z ADR 0012 i zapisuje wynik razem z wpisem audytu w jednej transakcji. **Żadna reguła §4.2/§4.3 nie jest powielona w serwisach ani w SQL** — kto, kiedy i co może, rozstrzyga wyłącznie `app/domain` (decyzje właściciela z ADR 0012 §10 trafiły tylko do domeny). Baza pilnuje niezmienników przechowywania (pkt 3).

## 1. Tabele

| Tabela | Kluczowe kolumny | `app_rw` |
|---|---|---|
| `changes` | §4.1 + `approved_by_id` (kto faktycznie zatwierdził, NULL = `system`) + `consent_round` (runda zgód, pkt 5) + `version`; `UNIQUE (number)`, `UNIQUE (id, company_id)` | SELECT, INSERT, UPDATE (bez DELETE) |
| `change_items` | `change_id`, `ci_id`, migawka `ci_identifier`/`ci_name` (NULL do wdrożenia) | SELECT, INSERT, UPDATE, DELETE (usunięcie CI ze szkicu) |
| `change_ci_consents` | `change_id`, `ci_id`, `owner_user_id`, `consent_round`, `created_at` = chwila zgody; `UNIQUE (change_id, ci_id, consent_round, owner_user_id)` | SELECT, INSERT |
| `change_comments` | `author_id`, `body` (1–4000), `action` (akcja, z którą podano komentarz, albo NULL) | SELECT, INSERT |
| `attachments` | §4.1 (`sha256` hex, `storage_key` unikalny) | SELECT, INSERT |
| `number_sequences` | `company_id`, `year`, `last_value`; `UNIQUE (company_id, year)` | SELECT, INSERT, UPDATE |
| `change_categories` | + `requires_ci_owner_consent bool NOT NULL DEFAULT false` (seed: `OT = true`) | bez zmian |

- **Każda tabela podrzędna ma `company_id`** i złożony FK `(change_id, company_id) → changes (id, company_id)` oraz `(ci_id, company_id) → configuration_items (id, company_id)` (nowy `UNIQUE (id, company_id)` na `configuration_items`). Dzięki temu RLS to wszędzie ta sama bezpośrednia polityka `company_id = ANY (app_company_ids())` (bez polityk przez złączenia, które zależałyby od RLS innej tabeli), a wiersz podrzędny nie może należeć do innej spółki niż jego zmiana ani wskazywać CI innej spółki. Strażnik `tests/test_rls.py` obejmuje wszystkie sześć tabel.
- `supersedes_change_id`: złożony FK — korekta wskazuje zmianę **tej samej** spółki; ustawiany tylko przy tworzeniu (`POST`), potem niezmienny (trigger). Serwis nie wymaga, by oryginał był zamrożony (§4.2 opisuje zamiar, nie warunek; pytanie w §12).
- `approver_id` jest NULL-owalny (decyzja właściciela: standardowa zmiana zatwierdzana automatycznie nie wymaga zatwierdzającego).
- Indeksy pod filtry rejestru: `(company_id, status)`, `(company_id, created_at)`, `(company_id, implemented_at)`, `(company_id, change_type)`, `category_id`, `subcategory_id`, `assignee_id`, `approver_id`, `supersedes_change_id`, `change_items.ci_id`.
- Migracja odwracalna; `downgrade` tylko jako właściciel tabel (jak 0006/0007), usuwa dane biznesowe (historia zostaje w `audit_log`).

## 2. Numeracja `CHG-{PREFIX}-{YYYY}-{NNNN}`

- Licznik per (spółka, rok) w `number_sequences`: `INSERT … ON CONFLICT DO NOTHING`, potem `SELECT … FOR UPDATE` i `+1` — w transakcji tworzącej zmianę. Równoległe tworzenia w jednej spółce czekają na siebie; wycofana transakcja wycofuje też numer (brak luk z błędów). Test: 12 równoległych `POST` → numery 1–12.
- **Rok wg `Europe/Warsaw`**, liczony przez PostgreSQL (`AT TIME ZONE`, baza stref czasowych serwera, bez zależności od `tzdata` w Pythonie). Użytkownicy pracują w tej strefie (§11.6): zmiana z 1 stycznia 00:30 czasu lokalnego dostaje nowy rok, choć w UTC jest jeszcze 31 grudnia (test).
- `NNNN` to 4 cyfry z zerami wiodącymi; po 9999 licznik dostaje piątą cyfrę (CHECK `[0-9]{4,}`), zamiast błędu.
- Trigger: licznik startuje od 0 i rośnie dokładnie o 1 (nie da się przeskoczyć ani cofnąć numeru).
- Kolejność blokad: licznik → (INSERT zmiany: `FOR SHARE` na wierszu spółki przez `company_must_be_active`) → głowa łańcucha spółki. Archiwizacja: wiersz spółki `FOR UPDATE` → głowa globalna. Brak cyklu.

## 3. Ochrona w bazie (obrona w głąb)

Trigger `changes_guard` (`BEFORE UPDATE`):

1. `id`, `company_id`, `number`, `requested_by_id`, `supersedes_change_id`, `created_at` — niezmienne.
2. `version` rośnie **dokładnie o 1** przy każdym UPDATE — optymistycznego blokowania nie da się pominąć.
3. **Status tylko ścieżką akcji.** `status`, `approved_at`, `approved_by_id`, `implemented_at`, `verified_at`, `rejected_at`, `consent_round` zmieniają się tylko, gdy transakcja ma `app.change_action` = id tej zmiany. Ustawia to wyłącznie `services.changes.perform_action` na czas jednej akcji (i zeruje po niej). PATCH, który przypadkiem ustawiłby status, kończy się błędem bazy. Ścieżka akcji z kolei **nie może** zmieniać pól merytorycznych.
4. **Zamrożenie (poprawka po recenzji).** Od `approved` (`approved`, `implemented`, `verified`, `rolled_back`) pola merytoryczne są niezmienne — domena w `approved` też nie dopuszcza edycji, a z `approved` prowadzi tylko akcja (`implement`, `cancel`), która zmienia wyłącznie pola cyklu życia. Wyjątki odpowiadają temu, co dopuszcza domena: `verifier_id` tylko w `implemented` (przepięcie weryfikującego, który odpadł) i `approver_id` tylko dla awaryjnej `implemented` bez zatwierdzenia (przepięcie zatwierdzającego, który odpadł, decyzja właściciela 2026-10-29); kiedy dokładnie — rozstrzyga domena (`verifier_reassignable`, `approver_reassignable`). `rejected` i `cancelled` są zamknięte **w całości**: żaden UPDATE wiersza (także na ścieżce akcji) ani zmiana listy CI.

Ponadto: CHECK-i spójności (`approved` ⇒ `approved_at`, `implemented|verified|rolled_back` ⇒ `implemented_at`, `verified` ⇒ `verified_at` i `approved_at`, `rejected` ⇒ `rejected_at`), kompletności poza szkicem (`status ∉ {draft, cancelled}` ⇒ tytuł, kategoria, typ, ryzyko, opis, plan, wykonawca — bez zatwierdzającego, pkt 1), okna (`window_start < window_end`; serwis mapuje naruszenie na 422 `change.invalid_window`) i **czterech oczu** na faktycznym zatwierdzającym (`approved_by_id` ≠ zgłaszający i ≠ wykonawca; `approved_by_id` tylko przy `approved_at` i równy wskazanemu `approver_id`) — odstępstwo krytyczne z §9 nie może zostać zapisane. Zmiana zatwierdzona przez `system` ma `approved_by_id IS NULL`, więc wskazany `approver_id` (który mógł zostać podstawiony jako domyślny) nie jest przypisywany jako zatwierdzający.

`change_items_guard`: brak INSERT/DELETE CI zmiany od `approved` oraz `rejected`/`cancelled`; migawka zapisywana raz, tylko ścieżką akcji. `change_comments`, `attachments`, `change_ci_consents`: trigger `reject_modification()` odrzuca UPDATE/DELETE/TRUNCATE **także dla właściciela** (§6.3); `app_rw` ma tylko SELECT, INSERT. `changes` bez DELETE i z blokadą TRUNCATE. `company_must_be_active()` (migracja 0007) na każdym zapisie tabel zmian.

**Granica:** `app.change_action` ustawia się tak jak zakres RLS (`set_config`), więc chroni przed błędami aplikacji, nie przed atakującym wykonującym dowolny SQL jako `app_rw` (ADR 0008 §5). Funkcje triggerów bez `EXECUTE` dla `app_rw`; `app_change_action(uuid)` jest `STABLE`, nie `SECURITY DEFINER`.

## 4. Załączniki

- Plik: `STORAGE_PATH/attachments/{company_id}/{attachment_id}`. Nazwa od użytkownika **nigdy** nie jest częścią ścieżki (brak path traversal); zapisywana tylko w bazie po sanityzacji (ostatni człon ścieżki, NFC, bez znaków sterujących/formatujących, ≤ 255 znaków z zachowaniem rozszerzenia, pusta/`.`/`..` → `plik`). `resolve()` dodatkowo sprawdza, że ścieżka leży w katalogu magazynu.
- SHA-256 i rozmiar liczone podczas strumieniowego zapisu do pliku `.part` (potem `os.replace` + `fsync`); powyżej `ATTACHMENT_MAX_BYTES` (domyślnie 25 MiB, nowa zmienna w `.env.example` i docker-compose; nginx ma `client_max_body_size 25m`) → 413 `attachment.too_large`, pusty plik → 422 `attachment.empty`. Plik usuwany przy każdym błędzie przed COMMIT. Nieudany sam COMMIT może zostawić osierocony plik bez wiersza (nieszkodliwy — nigdy nie jest serwowany; sprzątanie w Etapie 8).
- MIME tylko normalizowany (`type/subtype`, bez parametrów, inaczej `application/octet-stream`); whitelista to Etap 8. Pobieranie zawsze z `Content-Disposition: attachment`, `X-Content-Type-Options: nosniff`, `Content-Security-Policy: default-src 'none'; sandbox`, `Cache-Control: private, no-store`, `X-Content-SHA256`; własny typ tylko dla bezpiecznych (`pdf`, `png`, `jpeg`, `gif`, `text/plain`, `text/csv`), resztę jako `application/octet-stream` (np. HTML nie wykona się w originie aplikacji).
- **Każde pobranie (`GET …/attachments/{aid}`) jest audytowane** (decyzja właściciela 2026-10-29): wpis `attachment` / `download` w łańcuchu spółki z `change_id`, `filename`, `size`, `sha256`, w transakcji żądania zatwierdzanej przed wysłaniem pliku — pobranie, którego nie udało się zapisać, nie jest serwowane. Nieistniejący załącznik (404) nie tworzy wpisu.
- Nowa wersja = nowy rekord (POST tego samego pliku). Załączniki i komentarze można dodawać w każdym statusie (to dowody, nie pola merytoryczne), ale nie w zarchiwizowanej spółce. Starlette buforuje upload przed handlerem (limit egzekwuje też nginx).

## 5. Zgody właścicieli CI

Tabela tylko do dopisywania; „bieżąca runda” = `consent_round` zmiany.

**Zgoda liczy się tylko od bieżącego właściciela CI (poprawka po recenzji).** Recenzja wskazała, że po przepięciu `owner_user_id` CI zgoda mogłaby pochodzić od autora/wykonawcy (ustawia siebie jako właściciela i wyraża zgodę) albo liczyłaby się zgoda dawnego właściciela. Rozwiązanie dwuwarstwowe:

1. **Blokada przepięcia właściciela:** `configuration_items.update_item` odrzuca zmianę `owner_user_id` CI, którego dotyczy zmiana w `pending_approval` albo awaryjna `implemented` bez zatwierdzenia **i której kategoria lub podkategoria wymaga zgody właściciela CI** (`requires_ci_owner_consent`; pozostałe zmiany nie zależą od właściciela, więc nie dają zbędnych 409) — 409 `ci.owner_locked_by_change` (z numerami zmian). Warunek „kategoria OR podkategoria” jest tu powtórzony w SQL (zapytanie po CI), zgodnie z regułą domeny `requires_ci_owner_consent`. Wyścig: akcja zmiany blokuje swoje CI `FOR SHARE` (po wierszu zmiany), a edycja CI blokuje wiersz `FOR UPDATE` przed sprawdzeniem — więc albo zmiana właściciela kończy się przed wysłaniem (jak zmiana w szkicu), albo czeka i widzi zmianę oczekującą (409).
2. **Liczenie zgód:** `ChangeContext.consented_ci_ids` (a więc `approve`) bierze tylko zgody bieżącej rundy, w których `owner_user_id` = **obecny** właściciel CI (złączenie z `configuration_items`). Zgoda dawnego właściciela nie liczy się, nawet gdyby właściciel zmienił się z pominięciem serwisu (test z UPDATE jako `app_rw`); nowy właściciel wyraża zgodę ponownie (stąd właściciel w kluczu unikalnym). Karta pokazuje `consents[].valid` oraz `consents[].by_requester_or_assignee` — zgoda wyrażona przez właściciela, który jest też zgłaszającym lub wykonawcą zmiany, nie jest niezależna; frontend (Etap 5) oznaczy ją dla zatwierdzającego.

Odrzucony wariant „migawka właściciela przy submit”: wymagałby zgody osoby, która mogła już odejść lub przestać być właścicielem, i nowej kolumny w `change_items`. Świadomie dopuszczone (ADR 0012 §10 pkt 4): w **szkicu** właściciel CI może się zmienić (także na autora), co widać w audycie CI, a zgoda autora/wykonawcy jest jawna — kontrolą czterech oczu jest zatwierdzenie. `return` (`outcome.clear_consents`) zwiększa `consent_round` — wcześniejsze zgody zostają jako historia, ale przestają się liczyć. Odrzucony wariant „usuwanie wierszy przy return”: tabela nie byłaby tylko do dopisywania. Kolumna `requires_ci_owner_consent` jest edytowalna przez admina (`POST/PATCH /categories`, audytowana). **Istniejące instalacje:** `seed-dictionaries` nie zmienia istniejących kategorii, więc w bazie z kategorią OT sprzed migracji admin ustawia flagę przez `PATCH /categories/{OT}`.

## 6. Audyt

| Operacja | `entity_type` / `entity_id` | `action` | `diff` / `context` |
|---|---|---|---|
| utworzenie | `change` / id | `create` | wszystkie pola (+ `number`, `status`, `requested_by_id`); `{number, status, version}` |
| PATCH | `change` / id | `update` | tylko zmienione pola (CI jako posortowana lista id); `{number, status, version}` |
| każda akcja | `change` / id | `transition` | pola cyklu życia (status, znaczniki, `consent_round`); `outcome.audit_context()` + `{number, version, comment_id?}` |
| komentarz | `change` / id | `comment` | `{number, comment_id, comment}` |
| załącznik | `attachment` / id załącznika | `attach` | `{change_id, number, filename, content_type, size, sha256}` |
| pobranie załącznika | `attachment` / id załącznika | `download` (nowa `AuditAction.DOWNLOAD`) | `{change_id, filename, size, sha256}` |

- Każda akcja `approve` zapisuje w `diff` także `approved_by_id` (faktyczny zatwierdzający).
- **`consent` i zatwierdzenie po fakcie to też `transition`** (z `from_status = to_status`, `context.action` mówi, co się stało). Tak przewidział ADR 0012 §9; nowa akcja audytu (`consent`) wymagałaby zmiany `app/domain/audit.py`, a jedna akcja dla wszystkiego, co przechodzi przez maszynę stanów, upraszcza oś czasu karty. `diff` zgody jest pusty (status się nie zmienia), zgodzone CI są w `context.consented_ci_ids`.
- **Komentarz akcji** (return/reject/rollback/cancel/consent) zapisujemy jako `change_comments` z kolumną `action` (widać go w wątku komentarzy karty) **i** w `context.comment` wpisu `transition` razem z `comment_id` — jeden wpis audytu obejmuje oba wiersze (bez osobnego wpisu `comment`).
- Auto-zatwierdzenie standardowej zmiany: jeden wpis z aktorem `system` (`actor_id NULL`), `context.auto_approved`, `reason`, `triggered_by` (kto wysłał) — zgodnie z `TransitionOutcome`.
- Ostrzeżenia domeny (`verifier.is_assignee`, `emergency.approval_late`, `implementation.outside_window`, `window.future`) trafiają do `context.warnings` i do odpowiedzi akcji (`warnings`).
- Ścieżka audytu zmiany (`GET …/audit`): wpisy `change` tej zmiany oraz `attachment` jej załączników (po `entity_id`, indeks `ix_audit_log_entity`), rosnąco po `seq`. Każdy wpis ma `hash_valid` — skrót przeliczony z zapisanej treści wpisu (`audit.entry_hash_valid`, wspólny z `verify_chain`). Ciągłość całego łańcucha nadal weryfikuje `POST /audit/verify` (auditor/admin) — pytanie w §12.
- PATCH bez faktycznej zmiany nic nie zapisuje (bez nowej wersji i bez wpisu).

## 7. API i uprawnienia

- **Zmienione decyzją właściciela 2026-11-02 (ADR 0016):** odczyty rejestru (lista, karta po id i numerze, readiness, ścieżka audytu zmiany, lista załączników, kafelki) mają nazwaną wąską ścieżkę administratora tylko do odczytu (`require_register_read`) dla `app_admin` bez roli w spółce; zapisy, akcje i pobranie pliku załącznika — bez zmian (opis poniżej). Stan sprzed decyzji:
- Wszystkie trasy zmian wymagają członkostwa w `{company_id}` (inaczej 404, także dla admina). **Brak ścieżki administracyjnej:** spójnie z ADR 0007 §4 i ADR 0009 („admin bez członkostwa nie dostaje kontekstu rejestru”), a admin nie wykonuje akcji zmian (§5, rozdział obowiązków). Admin, który nada sobie rolę (audytowane), widzi rejestr; jego `app_admin` nie daje żadnych praw w domenie (`ChangeActor.facts` odfiltrowuje tę rolę).
- Odczyt (rejestr, karta, by-number, readiness, audit, lista i pobranie załącznika, stats): `register.view`. Tworzenie, PATCH, komentarz, załącznik: `change.edit_draft` (editor, approver; `change.assign` ma ten sam zestaw ról — test). Komentować mogą więc tylko editor/approver (§5 nie daje zapisu auditorowi/viewerowi).
- `POST …/actions/{action}`: nowa zależność `require_change_action()` z mapą `CHANGE_ACTION_PERMISSIONS` w `permissions.py` (jedno źródło prawdy, `AccessRule.per_value`): `approve|reject|return` → `change.approve`, `submit|cancel|implement|verify|rollback` → `change.edit_draft`, `consent` → `register.view` (zgodę daje właściciel CI z dowolną rolą, ADR 0012 §5). Nieznana akcja → 404 `change.unknown_action`. Najpierw macierz (403 `auth.forbidden`, zapisywane jako `access_denied`), potem maszyna stanów (403 `change.forbidden_actor`, `change.four_eyes_violation`, …).
- `GET …/changes/by-number/{number}` dopisane do §8 (frontend ma w URL numer). Także `GET …/attachments` (lista). Uwaga dla Etapu 7: `GET …/changes/export.csv` trzeba zadeklarować **przed** `…/changes/{change_id}` (inaczej dopasuje się trasa z UUID).
- Wersja: `version` w treści PATCH albo `If-Match` (`"3"`, `W/"3"`, `3`); brak → 428 `change.version_required`, niezgodne → 400 `change.version_mismatch`, nieaktualna → 409 `change.version_conflict` z `current_version`. Karta i PATCH zwracają `ETag`. Akcje przyjmują tak samo `version` w treści albo `If-Match`; opcjonalnie — **poza `approve`, gdzie wersja jest wymagana (428)** (poprawka po recenzji): approver zatwierdza dokładnie tę treść, którą widział, a nie wersję zmienioną w międzyczasie (np. przepięcie okna przez innego approvera).
- Błędy domeny: `ChangeRuleError.kind` → 403/409/422, `detail` = `message_pl`, rozszerzenia `fields` i `checks`.
- Referencje: CI spoza spółki i nieistniejące dają ten sam 422 `change.ci_not_found` (nie ujawniamy istnienia). Osoby (`assignee_id`, `approver_id`, `verifier_id`) muszą być członkami spółki (dowolna rola) — nieistniejący użytkownik i nie-członek dają ten sam 422 `change.user_not_found` (poprawka po recenzji: katalog użytkowników innych spółek nie jest ujawniany). Nieznana kategoria/korygowana zmiana — 422. Kwalifikacja osób to readiness (szkic może być niekompletny).
- Domyślny zatwierdzający przy tworzeniu (gdy `approver_id` nie podano): `default_approver_id()` z domeny (override kategorii → domyślny spółki, z pominięciem zgłaszającego i wykonawcy). Karta szkicu ma `suggested_approver_id`.

## 8. Rejestr i kafelki

- Filtry z §8 oraz `approved_by` (kto faktycznie zatwierdził: id użytkownika albo `system` dla zatwierdzonych automatycznie; `approver` = wskazany zatwierdzający; inna wartość → 422 `change.invalid_filter`); okres `[period_from, period_to)` po dacie rejestracji (`created_at`) albo wdrożenia (`period_by=implemented`); `q` po numerze, tytule i zgłoszeniu (`%`/`_` dosłownie); sortowanie `sort` (`created_at`, `number`, `implemented_at`, `title`, `status`, z `-` malejąco); `limit/offset/total`. Każdy wiersz ma `deviations` z domeny.
- `GET /companies/{cid}/stats` (§10.1): `pending_approval`, `approved_not_implemented` (status `approved`), `emergency_last_30_days` (awaryjne zarejestrowane w ostatnich 30 dniach, bez anulowanych), `implemented_not_verified` (status `implemented`), oraz liczniki odstępstw liczone **funkcjami domeny** na kandydatach z SQL: `emergency_not_approved_in_24h`, `implemented_outside_window`; `by_status`.

## 9. Zegar i dane przykładowe

- Czas biznesowy (`approved_at`, `created_at`, rok numeracji, `now` readiness) to zegar bazy (`now()` transakcji); serwisy przyjmują `now` tylko dla seeda i testów. `audit_log.occurred_at` zawsze pochodzi z zegara bazy (ADR 0006 §2).
- `python -m app.cli seed` dodaje 40 zmian (ALFA 16, BETA 13, GAMMA 11) przez serwisy i maszynę stanów, we wszystkich statusach: m.in. awaryjną bez zatwierdzenia po 24 h (odstępstwo), awaryjną zatwierdzoną po terminie, ≥ 2 wdrożone bez weryfikacji, standardowe zatwierdzone przez `system`, odrzucone, wycofane, anulowane, zwrócone, komentarze. Kroki wykonują osoby wymagane przez domenę (`dev-editor`: autor/wykonawca, `dev-approver`: zatwierdzający i weryfikujący), a **czas kroków jest symulowany** (ostatnie tygodnie). Każdy wpis audytu seeda ma `context.source = "seed"` i `context.simulated_at`, więc historia przykładowa nie udaje prawdziwej pracy (rzeczywisty czas zapisu jest w `occurred_at`).
- Seed nadaje `dev-editor` rolę editor i `dev-approver` rolę approver we wszystkich trzech spółkach oraz domyślnego zatwierdzającego BETA i GAMMA (bez tego zasada czterech oczu uniemożliwia zatwierdzanie). Nadal 5 użytkowników.
- Idempotentny: zmiany tylko w spółce bez żadnej zmiany; każda zmiana w osobnym savepoincie — jeśli dane edytowane przez admina nie pozwalają jej przeprowadzić (`ProblemError`), zostaje pominięta z notatką, reszta powstaje. OT bez przykładów (CI OT nie ma właściciela).

## 10. Archiwizacja spółki

Szybka kontrola w serwisie (409 `company.archived`) + trigger `company_must_be_active()` na `changes` i tabelach podrzędnych (wyścig z archiwizacją: test deterministyczny — zapis czeka na archiwizację i dostaje 409, numer nie jest zużyty). Odczyt działa (historia); karta zarchiwizowanej spółki ma puste `allowed_actions` i `editable_fields`.

## 11. Znacznik „Łańcuch spójny” (`GET /companies/{cid}/audit/status`)

Decyzja właściciela 2026-10-29: werdykt łańcucha spółki dla każdej roli w spółce (§10.2), bez szczegółów naruszenia i **bez wpisu audytu za każde wyświetlenie**.

- **Źródło:** ostatnia **zapisana** weryfikacja łańcucha spółki (`audit` / `verify` w tym łańcuchu — z API auditora/admina, CLI albo nowego zadania workera `verify_audit_chains`, codziennie 02:30 UTC, aktor `system`, `context.source = "worker"`). Każda weryfikacja jest więc nadal audytowana (§6.4), a odczyt znacznika nie.
- **Odpowiedź:** `{status, ok, checked_at, verified_head_seq, head_seq}`; `status`:
  - `ok` — ostatnia weryfikacja przeszła, nie jest starsza niż `AUDIT_STATUS_MAX_AGE_HOURS` (domyślnie 26 h; nowa zmienna w `.env.example` i docker-compose) **i** wpisy dopisane po niej są spójne: przyrostowe sprawdzenie ogona od zweryfikowanej głowy (ciągłość `seq`, `prev_hash`, własny skrót wpisu, zgodność z `audit_chain_heads`, niezmieniony skrót zweryfikowanej głowy). Koszt jest ograniczony do wpisów od ostatniej weryfikacji (najwyżej 2000; więcej → `stale`);
  - `broken` — ostatnia weryfikacja wykryła naruszenie albo ogon jest niespójny (`ok = false`, bez `first_broken_seq`);
  - `stale` — weryfikacja za stara lub zbyt wiele nowych wpisów (`ok = null`, brak twierdzenia);
  - `unknown` — łańcuch nigdy nie był weryfikowany (`ok = null`).
  Wynik nigdy nie jest `ok` bez faktycznej weryfikacji.
- **Spójny punkt odniesienia (poprawka po ponownej recenzji):** werdykt jest liczony na stan głowy odczytanej na początku (`audit_chain_heads`); zarówno szukanie ostatniej weryfikacji, jak i odczyt ogona są ograniczone do `seq <= head_seq`. W READ COMMITTED kolejne zapytania widzą wpisy zatwierdzone w międzyczasie — bez tej granicy równoległy zapis dawał fałszywe `broken` (test deterministyczny: wpis zapisany w innej transakcji między odczytem głowy a ogona). Wpisy dopisane później ocenia następne żądanie.
- **Koszt:** bez cache — buforowany werdykt `ok` przy niezmienionej głowie ukryłby wpis sfałszowany po jego wyliczeniu. Zamiast tego limit `STATUS_TAIL_LIMIT = 2000` wpisów od ostatniej weryfikacji na żądanie (więcej → `stale`); codzienna weryfikacja workera utrzymuje krótki ogon, więc typowo sprawdzanych jest kilkadziesiąt–kilkaset wpisów.
- **Granica:** naruszenie wpisu sprzed ostatniej weryfikacji zostanie wykryte dopiero przez kolejną pełną weryfikację (najpóźniej po dobie przez workera; do tego czasu znacznik może pokazywać `ok`, a po przekroczeniu wieku — `stale`). Odrzucono weryfikację pełną na żądanie (koszt O(n) przy każdym wyświetleniu karty, blokady przy dużych łańcuchach) i wariant z zapisem do audytu (wpis za każde wyświetlenie).
- Dostęp: `register.view` przez członkostwo (bez ścieżki administracyjnej; izolacja 404, macierz RBAC). RLS: odczyt wyłącznie łańcucha spółki z zakresu transakcji.

## 12. Testy

`tests/test_api_changes.py` (przejścia przez HTTP, cztery oczy, auto-zatwierdzenie z aktorem `system`, awaryjna + 24 h, zgoda właściciela CI z nową rundą po `return`, `approved → cancelled`, wdrożenie poza oknem, przepięcie weryfikującego, zamrożenie, wersje i wyścig PATCH, wyścig numeracji, rok wg Warszawy, archiwizacja i wyścig z nią, komentarze, ścieżka audytu, kafelki), `tests/test_changes_schema.py` (uprawnienia, RLS, FK złożone, append-only także dla właściciela, ścieżka akcji, zamrożenie, wersja, liczniki, załączniki: sha256, traversal, limit, typy), macierz RBAC i izolacja dla 13 nowych tras (`tests/test_rbac_matrix.py`, `tests/isolation_cases.py`), „każdy endpoint modyfikujący tworzy wpis audytu”, seed (`tests/test_seed.py`).

## 13. Rozstrzygnięcia właściciela (2026-10-29)

1. Rok numeracji wg `Europe/Warsaw` — **potwierdzone**.
2. Komentarze dodają tylko editor/approver — **potwierdzone**.
3. Komentarze i załączniki dozwolone także w zmianach zamrożonych, nie w zarchiwizowanej spółce — **potwierdzone**.
4. `supersedes_change_id` bez wymogu zamrożenia oryginału — **potwierdzone**.
5. Znacznik „Łańcuch spójny” dla każdej roli — **przyjęte**, realizacja w §11.
6. Kafelek awaryjnych wg `created_at` (30 dni) — **potwierdzone**.
7. Pobrania załączników **audytowane** — realizacja w §4 i §6.
