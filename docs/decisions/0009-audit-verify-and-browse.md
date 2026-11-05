# 0009. Weryfikacja i przegląd dziennika audytu: API, uprawnienia, CLI

- Status: przyjęta (punkty „do potwierdzenia” czekają na właściciela projektu)
- Data: 2026-10-29
- Dotyczy: CLAUDE.md §5, §6.4, §7, §8, §12 (Etap 2); `backend/app/api/v1/audit.py`, `backend/app/services/audit.py` (`verify_and_record`, `list_entries`), `backend/app/permissions.py` (`require_audit_chain`), `backend/app/cli.py`; ADR 0006 §6, ADR 0008 §6

## 1. Wybór łańcucha: parametr `company_id` w zapytaniu

`POST /audit/verify` i `GET /audit` działają zawsze na **jednym** łańcuchu:

- `company_id` podane — łańcuch tej spółki,
- `company_id` pominięte — łańcuch **globalny**.

Ta sama semantyka w obu endpointach. Sortowanie `seq` malejąco (wymaganie z §8) ma sens tylko w obrębie jednego łańcucha. Przegląd „wszystkich spółek audytora” to kilka wywołań, po jednym na spółkę. Odrzucony wariant: `company_id` pominięte = suma łańcuchów widocznych dla użytkownika. Wtedy znaczenie parametru zależałoby od roli, a kolejność wpisów z różnych łańcuchów byłaby umowna.

Uprawnienia sprawdza jedna zależność `require_audit_chain(action, admin_any_company=…)` (rodzaj `audit_chain` w `AccessRule`):

| Łańcuch | Kto | Odpowiedź dla pozostałych |
|---|---|---|
| globalny | wyłącznie `app_admin` (ADR 0006 §6, ADR 0008 §6) | 403 — łańcuch globalny zawsze istnieje, więc odpowiedź niczego nie ujawnia |
| spółki | członek z rolą dającą akcję (`auditor`; `app_admin` z dowolnym członkostwem) | brak członkostwa lub nieistniejąca spółka: **404** `company.not_found`, identyczne z odpowiedzią dla losowego UUID (§7.3); członek bez uprawnienia: 403 |

Każda odmowa trafia do dziennika (`access_denied`, ADR 0010).

## 2. Nowa akcja `audit.read` (`Action.AUDIT_READ`)

§8 opisuje `GET /audit` jako „przegląd dziennika (auditor/admin)”, ale macierz §5 nie ma dla niego wiersza. Wiersz „Podgląd rejestru, kart, ścieżki audytu” (wszystkie role) dotyczy ścieżki audytu **jednej zmiany** (`GET /changes/{id}/audit`, Etap 4). Cały dziennik spółki (członkostwa, odmowy, weryfikacje, wszystkie zmiany) to szerszy zakres.

**Decyzja.** Nowa akcja `AUDIT_READ = {app_admin, auditor}`, zgodna z §8. Testy: `tests/test_rbac_matrix.py` (`test_audit_actions_in_the_matrix` i macierz parametryzowana), `tests/test_audit_api.py`.

**Potwierdzone przez właściciela (akceptacja Etapu 2, 2026-10-29):** wiersz „Przegląd całego dziennika audytu (`GET /audit`) | ✓ | — | — | ✓ | —” w tabeli §5 CLAUDE.md (wiersz jest już dopisany; kod działa według tej akcji).

## 3. `app_admin` a łańcuchy spółek

- **Weryfikacja: dowolna istniejąca spółka** (jawna ścieżka administracyjna, `_admin_context`). Zakres transakcji jest poszerzany wyłącznie o tę spółkę, a wpis weryfikacji ma `context.admin_path = true`. Uzasadnienie: §5 daje adminowi weryfikację, a wynik to wyłącznie metadane (`ok`, `checked`, `first_broken_seq`, głowa łańcucha), bez danych biznesowych. Nadzór nad integralnością wszystkich łańcuchów jest zadaniem administratora (CLI robi to samo jako `system`).
- **Przegląd wpisów: tylko z członkostwem** (bez ścieżki administracyjnej, admin bez roli w spółce dostaje 404). Wpisy łańcucha spółki zawierają dane biznesowe (diffy zmian), a ADR 0007 §4 już przyjął, że admin bez członkostwa nie dostaje kontekstu rejestru spółki. Admin może nadać sobie rolę, co samo trafia do audytu (`role_grant`, `self_grant`).

**Zmienione decyzją właściciela (2026-11-02, ADR 0015 §7):** admin czyta wpisy łańcucha **każdej** spółki także bez członkostwa (`GET /audit?company_id=`, `GET /companies/{id}/audit/status`). Nie przez `_admin_context`, lecz wąską ścieżką `_admin_read_context`: zakres transakcji = wyłącznie ta spółka (bez członkostw admina, bez `admin_scope`, bez odczytu łańcucha globalnego), a transakcja jest przełączana na READ ONLY przed pierwszym odczytem. Auditor bez członkostwa nadal dostaje 404. Akapit wyżej („tylko z członkostwem”) opisuje stan sprzed tej decyzji.

## 4. Zapis wyniku weryfikacji (`audit.verify_and_record`)

- Najpierw przeliczenie łańcucha (`verify_chain_with_head`: wynik + głowa `seq`/`hash` odczytana na początku weryfikacji), potem w tej samej transakcji wpis `entity_type = audit`, `action = verify`, `entity_id` = spółka (globalny: `NULL`), `context = {chain, ok, checked, first_broken_seq, head_seq, head_hash, source, …}`. Wpis trafia do **weryfikowanego** łańcucha i leży poza zweryfikowanym zakresem (`seq > head_seq`). Następna weryfikacja go obejmie.
- **Łańcuch naruszony, który odrzuca dopisanie.** Trigger `BEFORE INSERT` (ADR 0006 §5) wymaga, by `prev_hash` nowego wpisu był równy zapisanemu hashowi poprzednika. Jeśli więc zmanipulowano ostatni wpis albo cofnięto głowę, dopisanie do tego łańcucha się nie uda. Wykrycie naruszenia nie może jednak zniknąć razem z wycofaną transakcją:
  - dla łańcucha **naruszonego** dopisanie idzie w `SAVEPOINT`;
  - gdy łańcuch spółki je odrzuci, wpis trafia do łańcucha **globalnego** z `target_company_id` i `chain_append_failed = true` (kolejność blokad z ADR 0006 §7: najpierw spółka, potem globalny);
  - gdy i to się nie uda (albo naruszony jest sam łańcuch globalny), API zwraca wynik z `recorded_in = null` i `audit_entry = null`, a serwer loguje błąd (ERROR). CLI wypisuje ostrzeżenie na stderr i kończy się kodem 1. Ukrycie wyniku przed weryfikującym byłoby gorsze niż brak wpisu, bo właśnie wykryto naruszenie.
  - Dopisanie do łańcucha, który zweryfikował się poprawnie, nie ma ścieżki zapasowej: błąd oznacza nieoczekiwaną sytuację i kończy się 500.
- Odpowiedź `POST /audit/verify`: `{company_id, chain, ok, checked, first_broken_seq, head_seq, head_hash, verified_at, recorded_in, audit_entry: {company_id, seq, hash}}`. Kod 200 także dla naruszonego łańcucha, bo operacja weryfikacji się udała.

### Znane ograniczenie: obcięcie ogona razem z wpisem weryfikacji (plan)

Wpis weryfikacji trafia do weryfikowanego łańcucha spółki. Właściciel bazy (`app_owner`, triggery wyłączone) może usunąć ogon łańcucha **razem** z tym wpisem i cofnąć głowę. Pozostała część łańcucha jest wtedy spójna, a `verify` nie wykryje obcięcia, bo nic w tym łańcuchu nie pamięta, że był dłuższy (ADR 0006 §5: granica ochrony przed właścicielem).

**Propozycja na przyszłość: kotwice.** Przy każdej weryfikacji łańcucha spółki dopisywać do łańcucha **globalnego** kotwicę `{company_id, head_seq, head_hash}`. `verify` spółki porównywałby wynik z ostatnią kotwicą: głowa poniżej `head_seq` kotwicy albo inny hash wpisu `head_seq` oznacza obcięcie lub podmianę. Nie wdrożono tego w Etapie 2, bo:

- audytor nie czyta łańcucha globalnego (ADR 0006 §6, ADR 0008 §6), a odczyt kotwic z niego wymagałby nowej ścieżki RLS lub funkcji `SECURITY DEFINER`, której strażnik w `tests/test_rls.py` celowo zabrania (osobna decyzja bezpieczeństwa);
- kotwica w tej samej bazie też może zostać obcięta przez właściciela (choć wymaga to zgodnej manipulacji dwoma łańcuchami). Pełną ochronę daje dopiero kotwica **poza bazą**: hash głowy w raportach PDF (Etap 7, ADR 0006 §5) lub okresowa publikacja.

Do decyzji najpóźniej w Etapie 7, razem z raportem zbiorczym audytora (ADR 0008 §6, rozszerzenie `subject_company_id`).

## 5. CLI `python -m app.cli verify-audit --company PREFIX | --global`

- Działa rolą aplikacji `app_rw` (`DATABASE_URL`), przez ten sam serwis co API (`verify_and_record`), z aktorem `system`. §6.1 rezerwuje `actor_id = NULL` dla `system`, a `Actor` wymusza nazwę `system`, więc zamiast proponowanego „system (CLI)” pochodzenie jest w `context`: `{"source": "cli", "command": "verify-audit", "os_user": …, "host": …}` (informacyjnie, wartości z systemu operacyjnego). `ip_address` i `user_agent` są puste.
- **Jawny, minimalny zakres RLS** w jednej transakcji:
  1. `--company`: prefiks jest normalizowany do wielkich liter i sprawdzany wzorcem `^[A-Z]{2,8}$`. Spółka jest wyszukiwana na ścieżce administracyjnej (`apply_company_scope([], admin_scope=True)`), bo bez członkostwa wiersz `companies` jest widoczny tylko tam (ADR 0008).
  2. Zakres jest **zastępowany** dokładnie łańcuchem tej spółki (`apply_company_scope([company_id])`, bez `admin_scope` i bez odczytu globalnego). Weryfikacja i jej wpis działają już bez uprawnień administracyjnych.
  3. `--global`: wyłącznie `global_audit_read`, bez spółek i bez `admin_scope`.
- Bezpieczeństwo: CLI nie dostaje niczego, czego nie ma proces API. Każdy, kto zna `DATABASE_URL`, może ustawić te zmienne sesji (ADR 0008 §5). Ochroną jest dostęp do sekretu i do hosta, a nie sama komenda. Komenda zostawia ślad w dzienniku (wpis `verify` z `os_user`/`host`).
- Kody wyjścia: `0` łańcuch spójny; `1` łańcuch naruszony, nieznany lub błędny prefiks albo błąd bazy. Komunikaty po polsku: wynik na stdout, błędy i ostrzeżenia na stderr.
- Testy: `tests/test_audit_verify.py`. Obejmują spójny łańcuch z polskimi znakami w nazwie spółki, wpis zmodyfikowany przez właściciela (`first_broken_seq` w wyjściu i we wpisie), łańcuch globalny, łańcuchy odrzucające dopisanie, nieznany i błędny prefiks oraz niedostępną bazę.

## 6. Kryteria akceptacji Etapu 2 (§12) — gdzie są testy

| Kryterium | Test |
|---|---|
| UPDATE/DELETE/TRUNCATE rolą `app_rw` się nie udaje | `tests/test_audit_log.py::test_app_rw_cannot_update_delete_or_truncate` |
| Wpis zmodyfikowany przez właściciela (triggery wyłączone) wykrywa `verify` z poprawnym `first_broken_seq` | serwis: `test_audit_log.py::test_modified_entry_is_detected` (+ warianty); API: `test_audit_verify.py::test_api_detects_entry_modified_by_the_owner`; CLI: `test_audit_verify.py::test_cli_detects_entry_modified_by_the_owner` |
| 50 równoległych zapisów nie rozwidla łańcucha | serwis: `test_audit_log.py::test_fifty_parallel_writers_do_not_fork_the_chain`; API: `test_audit_verify.py::test_fifty_parallel_api_verifications_keep_the_chain_linear` (50 równoległych `POST /audit/verify`, każdy dopisuje wpis do tego samego łańcucha) |
| Każdy endpoint modyfikujący tworzy wpis | `test_rbac_matrix.py::test_every_modifying_endpoint_writes_audit`. Liczy wpisy z `request_id` danego żądania z pominięciem zdarzeń `auth`, żeby wpis `login` nie zaliczał testu za endpoint. `test_every_modifying_route_is_checked_for_audit` pilnuje, by lista obejmowała wszystkie trasy POST/PUT/PATCH/DELETE. |
| Izolacja | `tests/isolation_cases.py::QUERY_CASES` (trasy ze spółką w parametrze zapytania; strażnik wymusza wpisanie każdej takiej trasy) i `test_isolation_api.py::test_foreign_company_in_query_is_404_like_a_missing_one` |
