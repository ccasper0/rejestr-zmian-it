# 0012. Maszyna stanów zmiany, readiness, zgoda właściciela CI i odstępstwa (Etap 4, faza A)

- Status: przyjęta; punkty z §10 rozstrzygnięte przez właściciela 2026-10-29
- Data: 2026-10-29
- Dotyczy: CLAUDE.md §4.1, §4.2, §4.3, §5, §8, §9 (odstępstwa); `backend/app/domain/{changes,readiness,state_machine,deviations,roles}.py`, `backend/app/permissions.py`; ADR 0007, ADR 0011 §3, §5, §9

Faza A Etapu 4 to wyłącznie czysta logika domenowa (bez I/O, `mypy --strict`). Faza B (modele, migracje, numeracja, serwisy, API, komentarze, załączniki, seed) ładuje dane, woła domenę i zapisuje wynik razem z audytem.

## 1. Moduły i podział odpowiedzialności

| Moduł | Zawartość |
|---|---|
| `app/domain/roles.py` | `Role`, `MEMBERSHIP_ROLES` — przeniesione z `app/permissions.py` (re-eksport), bo domena nie może importować FastAPI. Macierz akcji zostaje w `permissions.py`. |
| `app/domain/changes.py` | enumy `ChangeStatus`, `ChangeType`, `ChangeAction`, `ChangeField`, `Risk` (z `dictionaries`); fakty wejściowe `ChangeData`, `ActorFacts`, `ChangeContext` (+ `CompanyFacts`, `CategoryFacts`, `CIFacts`, `MemberFacts`); `Check`/`CheckLevel`; `ChangeRuleError` z `ChangeErrorCode` i `ErrorKind`. |
| `app/domain/readiness.py` | `readiness()` — jedyna implementacja reguł §4.3; `approval_readiness()` (ten sam raport z oknem, które się zaczęło, jako ostrzeżeniem); `is_auto_approved()`, `default_approver_id()`, `effective_requires_approval()`, `requires_ci_owner_consent()`, `verifier_may_be_assignee()`; grupy `approver_checks()`, `window_checks()`, `verifier_checks()` używane też przy edycji. |
| `app/domain/state_machine.py` | deklaratywna tabela `TRANSITIONS`, `check_access()`, `allowed_actions()`, `execute()` → `TransitionOutcome`, `editable_fields()`, `check_edit()`, `verifier_reassignable()`, `approver_reassignable()`. |
| `app/domain/deviations.py` | `deviations()`, `emergency_approval_overdue()`, `emergency_approval_deadline()`, `implemented_outside_window()`, `approved_by_requester_or_assignee()`. |

Czas zawsze jako parametr `now` (aware, UTC); naiwne daty to `ValueError` (błąd programisty). Role aktora to role **w spółce zmiany** (`company_memberships`); `app_admin` nie daje żadnych praw do zmian (§5, ADR 0007), więc admin bez członkostwa ma puste `allowed_actions` i `editable_fields`.

## 2. Przejścia (tabela §4.2)

| Akcja | Ze statusu → do | Kto (`ActorRule`) | Warunki / skutki |
|---|---|---|---|
| `submit` | `draft → pending_approval` | autor (`requested_by`) lub wykonawca, z rolą editor/approver | readiness bez błędów (`change.not_ready` + lista checków) |
| `submit` (standard) | `draft → approved` | aktor audytu `system` | `change_type = standard` i efektywnie **nie** wymaga zatwierdzenia (kategoria OR podkategoria, ADR 0011 §3) **ani zgody właściciela CI** (`is_auto_approved`); zatwierdzający nie jest wtedy wymagany; `approved_at = now`; `context`: `auto_approved`, `reason`, `triggered_by` (kto wysłał) |
| `return` | `pending_approval → draft` | wskazany zatwierdzający | komentarz wymagany; zgody właścicieli CI są kasowane (`clear_consents`) |
| `approve` | `pending_approval → approved` | wskazany zatwierdzający, cztery oczy | `approval_readiness` bez błędów (pkt 3); zgody właścicieli CI, jeśli wymagane; `approved_at = now` |
| `reject` | `pending_approval → rejected` | wskazany zatwierdzający, cztery oczy | komentarz wymagany; `rejected_at = now` |
| `implement` | `approved → implemented` | wykonawca (editor/approver) | `implemented_at = now`; `snapshot_ci`; poza oknem (pkt 7) — dozwolone z ostrzeżeniem `implementation.outside_window` |
| `cancel` | `approved → cancelled` | autor (editor/approver) lub wskazany zatwierdzający | komentarz wymagany |
| `implement` (awaryjna) | `draft → implemented` | autor lub wykonawca (editor/approver) | tylko `emergency`; readiness bez błędów (okno może być w przeszłości); `implemented_at = now`; `approval_due_at = now + 24 h` w `context` |
| `approve` (po fakcie) | `implemented → implemented` | wskazany zatwierdzający, cztery oczy | tylko `emergency` z `approved_at IS NULL`; `approved_at = now`; po terminie dozwolone, ale z ostrzeżeniem `emergency.approval_late` (odstępstwo pozostaje) |
| `verify` | `implemented → verified` | weryfikujący (pkt 4) | wymaga `approved_at` (awaryjna przed zatwierdzeniem po fakcie: `change.approval_missing`); `verified_at = now` |
| `rollback` | `implemented → rolled_back` | wykonawca (editor/approver) lub wskazany zatwierdzający | komentarz wymagany |
| `cancel` | `draft → cancelled` | autor (editor/approver) | komentarz opcjonalny |
| `consent` | status bez zmian | właściciel CI zmiany (dowolna rola w spółce) | pkt 5 |

- **Awaryjna: `implement`, nie `submit`.** `submit` znaczy „wyślij do zatwierdzenia”, a tu zmiana jest wdrażana bez zatwierdzenia. Awaryjna może też przejść zwykłą ścieżką (`submit` → `approve` → `implement`), jeśli czas na to pozwala.
- **Standard z kategorią wymagającą zatwierdzenia** idzie zwykłą ścieżką do `pending_approval` (bez błędu). `normal` i `emergency` nigdy nie są zatwierdzane automatycznie.
- **`approve` w `pending_approval` ponownie sprawdza readiness** (`approval_readiness`), bo zmiana mogła się zestarzeć od wysłania (CI zdezaktywowane, wykonawca bez roli, kategoria wyłączona w spółce). Blokuje (`change.not_ready`) **każdy** błąd readiness z pkt 3 **poza** `window.future`: okno, które już się zaczęło, daje ostrzeżenie (`level = warning`, kod `window.future`) zapisywane w `context.warnings`. `window.order`, `window.required_high_risk` i `window.complete` nadal blokują. Zatwierdzenie po fakcie zmiany awaryjnej readiness nie sprawdza — zmiana jest już wdrożona i zamrożona.
- `rollback` nie ma znacznika czasu (§4.1 nie definiuje `rolled_back_at`; czas jest w audycie).

## 3. Readiness (§4.3)

`readiness(change, ctx, now=...)` zwraca `ReadinessReport(checks)`; każdy check: `{code, ok, level, message_pl, field}` (`Check.as_dict()`), `level ∈ ok|warning|error`, `ok = level != error`. Zwracane są tylko checki, które dotyczą zmiany (np. plan wycofania tylko przy `high`), w stałej kolejności. `message_pl` opisuje warunek twierdząco („Tytuł zmiany jest podany.”), więc czyta się poprawnie przy ✓ i ✗.

| Kod | Warunek |
|---|---|
| `title.required`, `change_type.required`, `risk.required`, `description.required`, `implementation_plan.required` | pola wypełnione (tekst po `strip`) |
| `category.required`, `category.available` | kategoria główna, aktywna, dostępna w spółce (`company_categories`) |
| `subcategory.valid` | jeśli podana: aktywna i należy do kategorii |
| `ci.required`, `ci.same_company`, `ci.active` | ≥ 1 CI; każde z tej spółki (brak w `ctx.cis` = obca spółka/nieistniejące, RLS) i aktywne |
| `ci.owner_consent_possible` | gdy wymagana zgoda: każde CI ma właściciela, który jest aktywnym członkiem spółki |
| `rollback_plan.required_high_risk`, `window.required_high_risk` | `risk = high` |
| `window.complete` | poniżej `high`: okno albo pełne, albo puste |
| `window.order`, `window.future` | `start < end`; `start > now` (ściśle) — nie dla `emergency` |
| `assignee.required`, `assignee.eligible` | wykonawca: aktywny członek z rolą editor lub approver |
| `approver.required`, `approver.eligible`, `approver.four_eyes` | zatwierdzający: aktywny członek z rolą approver; ≠ zgłaszający i ≠ wykonawca. Dla zmiany zatwierdzanej automatycznie (`is_auto_approved`) bez zatwierdzającego zwracany jest tylko `approver.required` z `ok` („nie jest wymagany”); wskazany zatwierdzający nadal podlega `eligible` i `four_eyes` |
| `requirement_ref.required_ksc`, `verifier.required_ksc` | `company.is_ksc_entity` |
| `verifier.eligible` | jeśli podany: aktywny członek z rolą editor lub approver |
| `verifier.not_assignee` | weryfikujący = wykonawca: błąd, a gdy w spółce nie ma innej osoby mogącej weryfikować — `warning` |

`default_approver_id(category_override_id, company_default_approver_id, excluded=...)`: override kategorii → domyślny spółki, z pominięciem kandydatów z `excluded` (serwis podaje zgłaszającego i wykonawcę). Kwalifikację (rola `approver`) raportuje readiness — zamyka punkt z ADR 0007 §7 i ADR 0011 §4.

## 4. Aktorzy

- **Zatwierdza wskazany `approver_id`** (wariant bezpieczniejszy): `approve`/`reject`/`return` wymagają roli `approver` **i** bycia wskazanym. Kolejność błędów: brak roli → `change.forbidden_actor`; aktor jest zgłaszającym lub wykonawcą → `change.four_eyes_violation`; nie jest wskazany → `change.forbidden_actor`. Zastępstwo: w `pending_approval` **każdy** approver spółki, który mógłby zatwierdzić (≠ zgłaszający, ≠ wykonawca), może zmienić `approver_id` (także na siebie) — z walidacją `approver_checks` i wpisem w audycie.
- **Kto faktycznie zatwierdził: `approved_by_id` (poprawka po recenzji Etapu 4, 2026-10-29).** Pierwotnie przyjęto, że `approver_id` zatwierdzonej zmiany jest faktycznym zatwierdzającym. To nieprawda dla zmiany standardowej zatwierdzonej automatycznie: `approver_id` wskazuje człowieka (np. domyślnego zatwierdzającego), a zatwierdził `system` — rejestr i PDF przypisałyby zatwierdzenie osobie, która go nie wykonała. Dlatego `approve` (oba warianty) ustawia w `outcome.updates` `approved_by_id = aktor`, a auto-zatwierdzenie go nie ustawia (NULL przy `approved_at` = `system`). `ChangeData.approved_by_id`; odstępstwo „zatwierdzone przez autora” liczone z `approved_by_id`. W bazie: kolumna zmieniana tylko ścieżką akcji, CHECK `approved_by_id = approver_id` (zatwierdza wskazany) i cztery oczy na `approved_by_id` (ADR 0013 §3). Domyślny zatwierdzający jest nadal podstawiany przy tworzeniu także dla zmian, które mogą zostać zatwierdzone automatycznie: kategoria w szkicu może się jeszcze zmienić, a `approver_id` jest tylko wskazaniem — rozstrzyga `approved_by`.
- **Autor = `requested_by_id`, niezmienny** (ustawiany przy tworzeniu na twórcę, brak w `ChangeField`). Gdyby dało się go edytować, approver mógłby założyć zmianę „za kogoś” i ją zatwierdzić.
- „editor” z tabeli §4.2 = rola z `change.edit_draft` (editor **lub** approver), zgodnie z macierzą §5. Testy pilnują `WRITER_ROLES == PERMISSIONS[change.edit_draft]` i `APPROVER_ROLES == PERMISSIONS[change.approve]`.
- **Weryfikacja:** aktor z rolą editor/approver; jeśli `verifier_id` jest ustawiony — tylko on, w przeciwnym razie dowolny editor/approver. Wykonawca może weryfikować tylko, gdy w spółce nie ma innego aktywnego członka z rolą editor/approver (`verifier_may_be_assignee`, dane: `ctx.members` = wszyscy członkowie spółki). Wtedy `outcome.warnings` zawiera `verifier.is_assignee`, a `audit_context()["warnings"]` trafia do `audit_log.context`. W innym przypadku `change.verifier_is_assignee`. Ponieważ zmiana standardowa zatwierdzana automatycznie nie wymaga zatwierdzającego, w spółce, której jedynym aktywnym editorem/approverem jest wykonawca, wyjątek rzeczywiście zachodzi: `submit` (auto-approve, `system`) → `implement` → `verify` przez tę samą osobę z ostrzeżeniem (test `test_one_person_company_standard_change_end_to_end`). Członkowie z rolą viewer/auditor nie liczą się jako możliwi weryfikujący.

## 5. Zgoda właściciela CI (OT; ADR 0011 §9 pkt 6)

- Flaga słownikowa `change_categories.requires_ci_owner_consent` (kategoria OR podkategoria — tylko zaostrza). Faza B dodaje kolumnę (domyślnie `false`, seed: `OT = true`).
- Nowa akcja **`consent`** (status bez zmian): wykonuje właściciel (`configuration_items.owner_user_id`) co najmniej jednego CI zmiany, z dowolną rolą w spółce (właściciel to osoba merytoryczna, ADR 0011 §5). Jedna akcja = zgoda na wszystkie jego CI tej zmiany jeszcze bez zgody (`outcome.consented_ci_ids`). Ponowna zgoda: `change.invalid_transition`; nie-właściciel: `change.forbidden_actor`; kategoria bez wymogu: `change.invalid_transition`.
- Dozwolona w `pending_approval` oraz w `implemented` dla awaryjnej przed zatwierdzeniem po fakcie. `approve` (oba warianty) wymaga zgody dla **każdego** CI zmiany, inaczej `change.ci_owner_consent_missing` (z identyfikatorami CI).
- `return` kasuje zgody (`clear_consents`) — szkic może zmienić zakres. Zmiana z wymogiem zgody nigdy nie jest zatwierdzana automatycznie.
- Readiness sprawdza tylko, czy zgoda jest **możliwa** (`ci.owner_consent_possible`).
- Faza B: proponowana tabela tylko do dopisywania `change_ci_consents (change_id, ci_id, owner_user_id, consented_at)` z polityką RLS spółki; „bieżąca runda” = zgody nowsze niż ostatni `return` (albo usuwanie wierszy przy `return`, jeśli tabela nie będzie append-only — do decyzji w fazie B). `ChangeContext.consented_ci_ids` = CI ze zgodą w bieżącej rundzie.

## 6. Edycja i zamrożenie

- `editable_fields(change, actor, ctx)`: `draft` — wszystkie `ChangeField` dla roli editor/approver (dowolny taki członek spółki, nie tylko autor — macierz §5); `pending_approval` — `approver_id`, `window_start`, `window_end` dla approvera, który nie jest zgłaszającym ani wykonawcą; `implemented` — wyłącznie `verifier_id`, w wyjątku poniżej; pozostałe statusy — nic.
- **Weryfikujący, który odpadł (potwierdzone przez właściciela 2026-10-29):** w `implemented`, gdy wskazany `verifier_id` nie jest już aktywnym członkiem z rolą editor/approver (`verifier_reassignable`), approver spółki, który nie jest zgłaszającym ani wykonawcą, może zmienić **tylko** `verifier_id` (na innego kwalifikującego się albo na pusty — wtedy weryfikuje dowolny editor/approver; w spółce KSC pusty jest niedozwolony). Nowa wartość przechodzi `verifier_checks` (`change.invalid_edit`), zmiana trafia do audytu jak każdy PATCH. Gdy wskazany weryfikujący może weryfikować, każda próba to `change.frozen` — approver nie może „wybierać” weryfikującego po wdrożeniu.
- **Zatwierdzający awaryjnej, który odpadł (decyzja właściciela 2026-10-29):** awaryjna w `implemented` bez zatwierdzenia (`approved_at IS NULL`), której wskazany `approver_id` nie jest już aktywnym członkiem z rolą `approver` (`approver_reassignable`): approver spółki, który nie jest zgłaszającym ani wykonawcą, może zmienić **tylko** `approver_id` (razem z ewentualnym przepięciem weryfikującego — `IMPLEMENTED_EDITABLE = {verifier_id, approver_id}`, dozwolone pola wylicza `_reassignable_fields`). Nowa wartość przechodzi `approver_checks` (`change.invalid_edit`), wpis w audycie jak każdy PATCH; potem nowy zatwierdzający zatwierdza po fakcie. Odstępstwo 24 h pozostaje, jeśli termin minął. Gdy wskazany zatwierdzający może zatwierdzić — `change.frozen`. W bazie trigger zwalnia `approver_id` tylko dla awaryjnej `implemented` bez zatwierdzenia (ADR 0013 §3).
- `check_edit(current, proposed, actor, ctx, now=...)` zwraca zbiór faktycznie zmienionych pól (pusty = nic do zapisu, brak wpisu audytu). Kolejność: `company.archived` → (wyjątek weryfikującego) → `change.frozen` (`implemented`, `verified`, `rolled_back` oraz terminalne `rejected`, `cancelled`; komunikat wskazuje korektę nową zmianą z `supersedes_change_id`) → `approved`: `change.field_not_editable` → brak roli: `change.forbidden_actor` → pole spoza listy: `change.field_not_editable` (`fields`) → w `pending_approval` walidacja `approver_checks`/`window_checks` nowej wartości: `change.invalid_edit` (`checks`). Szkic może być niekompletny.
- Próba zmiany atrybutu spoza `ChangeField` (`status`, znaczniki czasu, `requested_by_id`, `company_id`) to `ValueError` — błąd serwisu, nie użytkownika.
- Komentarz nie jest polem zmiany (osobny endpoint, tylko dopisywanie).
- **Migawka CI** (ADR 0011 §9 pkt 5): `outcome.snapshot_ci = True` przy wejściu w `implemented`; faza B zapisuje wtedy `identifier` i `name` CI w `change_items`.

## 7. Odstępstwa

- `emergency_not_approved_in_24h`: awaryjna z `implemented_at`; bez zatwierdzenia i `now > implemented_at + 24 h`, albo `approved_at > implemented_at + 24 h`. Zatwierdzenie dokładnie po 24 h jest w terminie.
- `implemented_outside_window` (2026-10-29): zmiana inna niż awaryjna z pełnym oknem, wdrożona przed `window_start` albo po `window_end` (granice włącznie = w oknie). Ta sama funkcja `implemented_outside_window(change_type, implemented_at, window_start, window_end)` daje ostrzeżenie `implementation.outside_window` przy `implement` (z `implemented_at = now`). Do raportu §9 (sekcja 5) dochodzi więc ta kategoria odstępstw.
- `implemented_not_verified`: status `implemented`.
- `rolled_back`: status `rolled_back`.
- `approved_by_requester_or_assignee` (krytyczne): `approved_at` ustawione i `approved_by_id ∈ {requested_by_id, assignee_id}` (faktyczny zatwierdzający, pkt 4). Zmiana zatwierdzona automatycznie (`approved_by_id IS NULL`, `system`) nie jest tu liczona, nawet gdy wskazany `approver_id` byłby autorem.
- `DeviationSubject` (bez okna; wystarcza `emergency_approval_overdue`) i `WindowedDeviationSubject` (+ `window_start`, `window_end`; wymagany przez `deviations()`) to protokoły tylko do odczytu — można podać wiersz ORM albo `ChangeData`.

## 8. Błędy

`ChangeRuleError(code, message_pl, fields=(), checks=())`; `code.kind` → HTTP w serwisie: `forbidden` 403, `conflict` 409, `validation` 422. `detail` = `message_pl`, `fields`/`checks` jako rozszerzenia problem+json.

| Kod | Rodzaj | Kiedy |
|---|---|---|
| `change.invalid_transition` | 409 | akcja niedostępna w statusie / dla typu / stanu zatwierdzenia / reguły zgody |
| `change.forbidden_actor` | 403 | aktor nie spełnia reguły z kolumny „Kto” |
| `change.four_eyes_violation` | 403 | zatwierdzający jest zgłaszającym lub wykonawcą |
| `change.verifier_is_assignee` | 403 | wykonawca weryfikuje, a jest inna osoba |
| `change.approval_missing` | 409 | weryfikacja awaryjnej przed zatwierdzeniem po fakcie |
| `change.comment_required`, `change.comment_too_long` (> 4000) | 422 | komentarz |
| `change.not_ready` | 422 | readiness z błędami (`checks`) |
| `change.ci_owner_consent_missing` | 409 | `approve` bez zgód |
| `change.frozen` | 409 | edycja zamrożonej zmiany |
| `change.field_not_editable` | 422 | pole niedostępne w statusie |
| `change.invalid_edit` | 422 | nowa wartość nie spełnia reguł (`checks`) |
| `company.archived` | 409 | spółka zarchiwizowana: żadnych akcji ani edycji (domyka ADR 0007 §7 dla zmian; faza B dodaje też trigger `company_must_be_active()` na `changes`) |

**`allowed_actions` a walidacja.** `check_access` obejmuje: spółkę, status/typ/stan zatwierdzenia, regułę aktora, cztery oczy, weryfikującego i `approval_missing`. `allowed_actions` to dokładnie akcje bez błędu `check_access` (test na pełnej macierzy status × typ × zatwierdzenie × akcja × 10 aktorów, porównanej z wyrocznią spisaną z tabeli §4.2). Warunki danych — komentarz, readiness (`submit`, awaryjne `implement`, `approve`), zgody właścicieli (`approve`) — są sprawdzane dopiero w `execute`: przycisk jest widoczny, a błąd wyjaśnia, czego brakuje (formularz i tak blokuje wysłanie na podstawie `/readiness`, §10.3).

## 9. Wskazówki dla fazy B

- `execute()` → w jednej transakcji: `SELECT … FOR UPDATE` zmiany, kontrola `version`, `setattr` z `outcome.updates`, zgody, migawka CI, `audit.record(entity_type=change, action=transition, diff=make_diff(...), context=outcome.audit_context())`; aktor audytu `Actor.system()` gdy `outcome.performed_by_system`. `consent` i `approve` po fakcie nie zmieniają statusu — proponowane `action = transition` z `from_status = to_status` (albo nowa `AuditAction.CONSENT`; do decyzji w fazie B).
- `ChangeContext.members` — wszyscy członkowie spółki z co najmniej jedną rolą (jedno zapytanie); `categories` — wiersze dla `category_id`/`subcategory_id` z `available_in_company` dla kategorii głównej; `cis` — CI zmiany widoczne w spółce.
- Odpowiedź zmiany: `allowed_actions` (lista kodów) i proponowane `editable_fields`; `GET /readiness` → `[c.as_dict() for c in report.checks]` + `ok`.
- `deviations()` przyjmuje `WindowedDeviationSubject` (adapter serwisu musi podać `window_start`/`window_end`); `emergency_approval_overdue()` nadal przyjmuje `DeviationSubject` bez okna. Tabela `change_categories` potrzebuje nowej flagi tylko dla zgody (pkt 5); przejście `approved → cancelled` nie wymaga zmian schematu.

## 10. Rozstrzygnięcia właściciela (2026-10-29)

Pytania z pierwotnej wersji tego ADR:

1. **Zatwierdza tylko wskazany `approver_id`** — potwierdzone. Zastępstwo przez przepięcie `approver_id` w `pending_approval` przez approvera spółki spełniającego cztery oczy — potwierdzone (pkt 4).
2. **Rola approver jako autor/wykonawca** może wykonać `submit`, awaryjne `implement` i `cancel`; szkic edytuje każdy editor/approver spółki — przyjęte (pkt 4, 6).
3. **Zatwierdzający nie jest wymagany dla zmiany standardowej zatwierdzanej automatycznie** (efektywnie bez wymogu zatwierdzenia i bez zgody właściciela CI); jeśli jest wskazany, obowiązują cztery oczy. Dzięki temu wyjątek weryfikacji w spółce jednoosobowej realnie zachodzi (pkt 3, 4; CLAUDE.md §4.2, §4.3).
4. **Zgoda właściciela CI** wymagana jawnie także od właściciela, który jest autorem lub wykonawcą; wymagana też przed zatwierdzeniem po fakcie; `return` kasuje zgody — przyjęte (pkt 5).
5. **Awaryjna:** weryfikacja zablokowana do zatwierdzenia po fakcie (`change.approval_missing`); pełna readiness przy awaryjnym `implement` — przyjęte (pkt 2).
6. **Nowe przejście `approved → cancelled`**: autor lub wskazany zatwierdzający, komentarz wymagany (pkt 2; CLAUDE.md §4.2). Zatwierdzonej zmiany nadal nie można edytować.
7. `rejected` i `cancelled` są zamrożone (`change.frozen`) — przyjęte (pkt 6).
8. **Weryfikujący, który stracił rolę lub odszedł** — minimalne rozwiązanie z pkt 6 (approver przepina `verifier_id` w `implemented`, tylko gdy wskazany weryfikujący nie może już weryfikować; wpis w audycie). **Potwierdzone przez właściciela 2026-10-29.**
9. **`approve` ponownie sprawdza readiness**; okno, które już się zaczęło, to ostrzeżenie, nie błąd; pozostałe błędy blokują (pkt 2).
10. **Wdrożenie poza zatwierdzonym oknem** (zmiana inna niż awaryjna z oknem): dozwolone, ostrzeżenie `implementation.outside_window` w audycie i odstępstwo `implemented_outside_window` (pkt 7).
11. Komentarz do akcji: maksymalnie 4000 znaków — przyjęte.
