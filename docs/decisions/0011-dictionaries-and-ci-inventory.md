# 0011. Słowniki globalne, kategorie spółek i inwentarz CI

- Status: przyjęta; punkty z §9 potwierdzone przez właściciela przy akceptacji Etapu 3 (2026-10-29)
- Data: 2026-10-29
- Dotyczy: CLAUDE.md §4.1, §5, §6.5, §7, §8, §12 (Etap 3), §13, §14; migracje `backend/alembic/versions/20261029_0006_dictionaries_and_ci.py`, `20261029_0007_company_active_guard.py`; `backend/app/domain/dictionaries.py`, `backend/app/services/{categories,ci_types,company_categories,configuration_items,seed}.py`, `backend/app/api/v1/{dictionaries,inventory}.py`, `backend/app/permissions.py`; ADR 0007, ADR 0008

## 1. Endpointy

| Metoda i ścieżka | Akcja (`app/permissions.py`) | Kto |
|---|---|---|
| `GET /categories` (`?active=&parent_id=&top_level=&limit=&offset=`) | `register.view`, rodzaj `any_company` | każdy z rolą w jakiejkolwiek spółce oraz `app_admin` |
| `POST /categories`, `PATCH /categories/{id}` | `dictionary.manage` | `app_admin` |
| `GET /ci-types` (`?active=`) | `register.view`, rodzaj `any_company` | jw. |
| `POST /ci-types`, `PATCH /ci-types/{id}` | `dictionary.manage` | `app_admin` |
| `GET /companies/{id}/categories` | `register.view` + `admin_action = company.manage` | członkowie spółki; admin ścieżką administracyjną |
| `PUT /companies/{id}/categories` | `company.manage` (rodzaj `admin_company`) | `app_admin` |
| `GET /companies/{cid}/ci` (`?q=&type=&active=&limit=&offset=`), `GET /companies/{cid}/ci/{id}` | `register.view` + `admin_action = ci.manage` | członkowie spółki; admin ścieżką administracyjną |
| `POST /companies/{cid}/ci`, `PATCH /companies/{cid}/ci/{id}` | `ci.manage` + `admin_action = ci.manage` | editor, approver spółki; admin ścieżką administracyjną |

`POST/PATCH /ci-types` oraz `GET /companies/{cid}/ci/{id}` dopisano do CLAUDE.md §8 (§4.1: „możliwość dodania przez admina”; karta CI jest potrzebna do testu izolacji zasobu i frontendu). Nie ma `DELETE`: słowniki i CI się dezaktywuje (`is_active = false`).

### Odczyt słowników: nowy rodzaj deklaracji `any_company`

Słowniki są globalne, nie należą do żadnej spółki, ale macierz §5 nie ma wiersza „odczyt słowników”. **Decyzja:** odczyt deklaruje `register.view` przez nową zależność `require_in_any_company(action)`: wystarczy, że akcja jest dozwolona w **co najmniej jednej** spółce użytkownika albo globalnie (`app_admin`). Użytkownik bez żadnej roli (świeżo po JIT) dostaje 403, zapisywane jak każda odmowa (`access_denied`, ADR 0010). Zależność nie otwiera ścieżki administracyjnej (`admin_scope` pozostaje `off`). Odrzucony wariant: dostęp dla każdego zalogowanego — wymagałby wyjątku obok `SELF_ENDPOINTS` bez uzasadnienia biznesowego.

### Ścieżka administracyjna dla akcji zapisu, które admin ma w macierzy

§5: inwentarz CI zarządza także `app_admin`, a ADR 0007 §4: admin nie jest członkiem spółek. Dotąd `admin_action` było dozwolone tylko dla akcji odczytu, bo ścieżka administracyjna pomija sprawdzenie akcji endpointu. **Decyzja:** `_check_admin_action` dopuszcza też `admin_action == action`, jeśli `app_admin` ma tę akcję w macierzy (dziś: `ci.manage`). Niczego się wtedy nie pomija — admin jest sprawdzany względem tej samej akcji. Dla `change.approve`/`change.edit_draft` (admin ich nie ma) deklaracja nadal kończy się `ValueError` przy imporcie (test w `tests/test_permissions.py`). Wpisy audytu admina mają `actor_roles = ["app_admin"]`.

**Wąski zakres RLS dla zapisu (poprawka po recenzji Etapu 3).** Na tej ścieżce zapisu (`admin_action == action`, akcja spoza `READ_ACTIONS`) `_admin_context(..., admin_scope=False)` tylko poszerza `app.company_ids` o spółkę docelową, **bez** `app.admin_scope = on`. Polityki `configuration_items` i `audit_log` spółki wymagają wyłącznie spółki w zakresie, a w tej transakcji RLS odrzuca zapis do `companies`, `company_memberships`, `company_categories` i słowników (test `tests/test_api_inventory.py::test_admin_write_path_opens_only_the_company_scope`). Ścieżki odczytu (`register.view` z `admin_action`) i endpointy wyłącznie administracyjne zachowują pełny `admin_scope`.

## 2. Kategorie zmian (`change_categories`)

- **Dwa poziomy:** `parent_id IS NULL` — kategoria, w przeciwnym razie podkategoria. Podkategoria nie może mieć dzieci: serwis zwraca 422 `category.depth_exceeded`, a trigger `change_categories_guard` (`BEFORE INSERT`) odrzuca to w bazie (`23514`).
- **`code` i `parent_id` są niezmienne** (serwis: 422 `category.code_immutable` / `category.parent_immutable`; trigger: `23001`, także dla właściciela). Kod to identyfikator w raportach i dziennikach (diff `company_category` jest kluczowany kodem), a przeniesienie podkategorii zmieniłoby znaczenie historycznych zmian (`changes.category_id` + `subcategory_id`). Niezmienność `parent_id` gwarantuje też, że kontrola głębokości przy `INSERT` wystarczy: kategoria z dziećmi nigdy nie stanie się podkategorią. PATCH przyjmuje te pola tylko bez zmiany (jak `prefix` spółki).
- Format kodu: 2–32 znaki, wielkie litery A–Z i cyfry, grupy łączone myślnikiem (`ACC`, `ACC-PRIV`, `NET-VLAN`). Kod nie jest normalizowany (wielkość liter wymuszona), więc unikalność jest z definicji niezależna od wielkości liter. CHECK w bazie powiela regułę.
- Nowa podkategoria nieaktywnej kategorii: 422 `category.parent_inactive`. Rodzic jest czytany `FOR SHARE` (poprawka po recenzji): równoległa dezaktywacja (`FOR UPDATE`) albo czeka na utworzenie podkategorii, albo — zatwierdzona wcześniej — jest widoczna i daje 422; nie powstanie aktywna podkategoria nieaktywnej kategorii (test deterministyczny `tests/test_inventory_services.py::test_subcategory_racing_parent_deactivation_is_rejected`). Dezaktywacja kategorii **nie** kaskaduje na podkategorie. **Etap 4:** kategoria/podkategoria jest dostępna dla nowej zmiany, gdy aktywne są obie (i kategoria główna jest dostępna w spółce, pkt 4).
- Wartości domyślne przy tworzeniu: podkategoria bez `requires_approval`/`default_risk` dziedziczy je z kategorii; kategoria główna — bezpiecznie: zatwierdzenie wymagane, ryzyko `medium`.

## 3. `requires_approval` podkategorii: tylko zaostrza

§13: ACC „nie (standard) — poza kontami uprzywilejowanymi”. **Decyzja:** efektywna wartość to `kategoria.requires_approval OR podkategoria.requires_approval` (`app.domain.dictionaries.effective_requires_approval`). Podkategoria może więc **wymusić** zatwierdzenie w kategorii standardowej (ACC + `ACC-PRIV` „Konto uprzywilejowane” → wymagane), ale nigdy go nie znosi w kategorii, która je wymaga. Odrzucony wariant „podkategoria nadpisuje w obie strony”: pojedyncza edycja słownika mogłaby zdjąć wymóg zatwierdzenia z całej grupy zmian np. sieciowych. `default_risk` podkategorii po prostu zastępuje wartość kategorii (to tylko podpowiedź dla formularza).

OT „tak + zgoda właściciela CI”: na razie `requires_approval = true`, `default_risk = high`. **Etap 4 (do zaprojektowania):** zgoda właściciela CI (`configuration_items.owner_user_id`) jako dodatkowy warunek przejścia `pending_approval → approved` dla kategorii OT. Proponujemy flagę słownikową (np. `requires_ci_owner_consent`) zamiast reguły zaszytej na kodzie `OT`; decyzja razem z maszyną stanów.

## 4. Kategorie dostępne w spółce (`company_categories`)

- Przypisuje się wyłącznie **kategorie główne** (422 `company_category.not_top_level`); ich podkategorie są dostępne razem z nimi. `GET /companies/{id}/categories` zwraca kategorie główne z `approver_override_id`, podkategorie — `GET /categories?parent_id=`.
- `PUT` ustawia **pełną** listę. Usunięcie dostępności to `DELETE` wiersza: `app_rw` ma `DELETE` tylko na tej tabeli z nowych (jak `company_memberships`, ADR 0007 §7), a ślad zostaje w dzienniku. Odrzucony wariant z flagą `is_enabled`: tabela ma charakter konfiguracji, a historia jest w audycie; flaga komplikowałaby unikalność i zapytania bez zysku dowodowego. Istniejące zmiany wskazują `change_categories`, nie `company_categories`, więc usunięcie wiersza ich nie dotyka.
- Nieaktywnej kategorii nie można **dodać** (422 `company_category.category_inactive`), ale już dostępną można zachować na liście po jej dezaktywacji (inaczej każdy PUT po dezaktywacji słownika by się nie udawał). Duplikat na liście: 422 `company_category.duplicate`; nieznane id: 422 `company_category.category_not_found`.
- **Zatwierdzający dla kategorii (`approver_override_id`) musi być aktywnym użytkownikiem z rolą `approver` w tej spółce** (422 `company_category.approver_not_eligible`). To świadomie ostrzej niż `companies.default_approver_id` (ADR 0007 §7: tylko aktywny użytkownik), bo spółka przy tworzeniu nie ma jeszcze członków, a w chwili `PUT` kategorii spółka istnieje i ma członków. Sprawdzane są tylko **zmieniane** wartości: nieaktualny override (np. po odebraniu roli) nie blokuje PUT dotyczącego innych kategorii. **Etap 4:** `readiness` sprawdzi, czy domyślny zatwierdzający (override → domyślny spółki) ma rolę `approver`.
- Zmiany jednej spółki są serializowane `SELECT … FOR UPDATE` na wierszu spółki (tylko ścieżka administracyjna może go zablokować, ADR 0008).
- Zarchiwizowana spółka: admin może zmieniać jej kategorie (spójnie z ADR 0007 §7 — admin edytuje zarchiwizowaną spółkę).

## 5. Inwentarz CI (`configuration_items`)

- **`identifier` unikalny w spółce bez względu na wielkość liter** (`FW-01` = `fw-01`): indeks unikalny `(company_id, lower(identifier))` oraz kontrola w serwisie (409 `ci.identifier_taken`; wyścig dwóch transakcji też daje 409, test deterministyczny). Spójnie z nazwami spółek (migracja 0004). Wartość jest przycinana, wielkość liter zachowana. Różne spółki mogą mieć ten sam identyfikator.
- `identifier` **można zmieniać** (zmiany będą wskazywać CI po `id`). **Do potwierdzenia (Etap 4):** czy zamrożona zmiana (`implemented`+) ma przechowywać migawkę identyfikatora/nazwy CI z chwili wdrożenia, żeby karta zmiany i raport pokazywały historyczną nazwę.
- `ci_type_id`: typ musi istnieć i być aktywny przy tworzeniu i przy **zmianie** typu (422 `ci.type_not_found` / `ci.type_inactive`); CI z typem zdezaktywowanym później zachowuje go.
- `owner_user_id`: aktywny użytkownik z **dowolną** rolą w spółce (422 `ci.owner_not_member`). Właściciel CI to osoba merytoryczna (np. do zgody OT), nie musi zatwierdzać ani edytować. Admin bez członkostwa nie może być właścicielem.
- **Zarchiwizowana spółka: inwentarz zamrożony** — `POST`/`PATCH` CI dają 409 `company.archived`, odczyt działa (historia). Zamyka część punktu „do potwierdzenia” z ADR 0007 §7 dotyczącą CI (zmiany — Etap 4).
  - **Wyścig z archiwizacją (poprawka po recenzji).** Kontrola w serwisie czyta `ctx.company` bez blokady, więc archiwizacja zatwierdzona między kontrolą a zapisem pozwalała utworzyć CI w zarchiwizowanej spółce. Migracja 0007 dodaje trigger `BEFORE INSERT OR UPDATE` na `configuration_items` z funkcją `company_must_be_active()`: blokuje wiersz spółki `FOR SHARE` i odrzuca zapis (`23001`, komunikat `company_archived:`), gdy spółka jest zarchiwizowana. `archive_company` blokuje ten wiersz `FOR UPDATE`, więc operacje się serializują: archiwizacja pierwsza → zapis CI czeka, a po jej zatwierdzeniu (READ COMMITTED: zablokowany wiersz jest czytany ponownie w najnowszej wersji) widzi `archived` i serwis zwraca 409; zapis CI pierwszy → archiwizacja czeka do jego końca. Testy deterministyczne obu kolejności: `tests/test_inventory_services.py::test_ci_write_racing_an_archive_is_rejected` i `::test_archive_waits_for_a_ci_write_in_progress`; zapis z pominięciem serwisu: `tests/test_inventory_schema.py::test_ci_of_an_archived_company_cannot_be_written`.
  - Funkcja jest `SECURITY DEFINER` (właściciel `app_owner`, ustalony `search_path`), bo `SELECT … FOR SHARE` na `companies` podlega polityce UPDATE dostępnej tylko na ścieżce administracyjnej (ADR 0008 §1). `app_rw` nie ma do niej `EXECUTE` (trigger i tak się wykona), więc strażnik `test_no_rls_bypass_through_views_or_definer_functions` przechodzi. Kolejność blokad: wiersz spółki przed głową łańcucha spółki, tak samo jak w `archive_company`, `set_member_roles` i `PUT …/categories`, więc bez cyklu.
  - **Wzorzec dla Etapu 4:** ten sam trigger (`EXECUTE FUNCTION company_must_be_active()`) na `changes` (oraz komentarzach i załącznikach, jeśli mają być zamrożone). Funkcja jest ogólna — używa `NEW.company_id` i `TG_TABLE_NAME`.
  - `company_categories` nie ma tego triggera: admin może konfigurować zarchiwizowaną spółkę (ADR 0007 §7, pkt 4 powyżej), a ich zapis i tak serializuje `FOR UPDATE` na wierszu spółki.
  - `update_item` wykonuje walidacje bez autoflush (`session.no_autoflush`): wcześniej wyszukanie typu CI wypychało zmieniony wiersz poza `_flush`, więc konflikt (duplikat identyfikatora przy równoległym PATCH, archiwizacja) kończył się 500 zamiast 409 — wykryte testem wyścigu PATCH (`test_concurrent_ci_identifier_change_is_409`).
- `company_id` jest niezmienny (trigger `company_id_immutable`, `23001`): RLS `WITH CHECK` sam w sobie pozwoliłby przenieść wiersz między dwiema spółkami z zakresu tej samej transakcji. Ten sam trigger chroni `company_categories`.
- Wyszukiwanie `q` (ILIKE po identyfikatorze i nazwie, `%`/`_` traktowane dosłownie), `type` (kody typów, wielokrotny), `active`; sortowanie po identyfikatorze bez względu na wielkość liter; `limit/offset/total`.
- Bez optymistycznego blokowania (`version`) — §4.1 wymaga go tylko dla zmian. Równoległe PATCH tego samego CI są serializowane `FOR UPDATE`, więc diff w audycie jest spójny.

## 6. Audyt

| Encja | Łańcuch | `entity_type` / `entity_id` | Akcje |
|---|---|---|---|
| kategoria | globalny | `category` / id kategorii | `create`, `update`, `deactivate` (zmiana `is_active` true→false; reaktywacja to `update`) |
| typ CI | globalny | `ci_type` / id typu | jw. |
| kategorie spółki | spółki | `company_category` / id spółki | `update` (jeden wpis na skuteczny PUT) |
| CI | spółki | `ci` / id CI | `create`, `update`, `deactivate` |

- Diff kategorii spółki jest kluczowany kodem kategorii: `{"NET": {"before": null, "after": {"approver_override_id": …}}}` (`null` = niedostępna), `context = {added, removed, override_changed}` (listy kodów).
- `context` CI: `{identifier, ci_type_code}`; kategorii przy tworzeniu podkategorii: `{parent_code}`; przy edycji: `{code}`.
- Żądanie bez faktycznej zmiany niczego nie zapisuje i nie tworzy wpisu (jak w ADR 0007 §6).
- Wpis powstaje w tej samej transakcji co zmiana danych, w serwisie. Test „każdy endpoint modyfikujący tworzy wpis” obejmuje wszystkie 7 nowych tras zapisu (`tests/test_rbac_matrix.py::MODIFYING`).

## 7. RLS i uprawnienia `app_rw`

| Tabela | SELECT | INSERT / UPDATE | DELETE |
|---|---|---|---|
| `change_categories`, `ci_types` | wszyscy (`USING (true)`) | tylko `app_admin_scope()` | brak uprawnienia |
| `company_categories` | `company_id ∈ zakres` | `app_admin_scope()` **i** `company_id ∈ zakres` | jak INSERT |
| `configuration_items` | `company_id ∈ zakres` | `company_id ∈ zakres` (+ trigger: spółka nie może być zarchiwizowana, migracja 0007) | brak uprawnienia |

- Słowniki nie mają `company_id`, więc §7 nie wymaga RLS i strażnik w `tests/test_rls.py` ich nie obejmuje. **Mimo to** mają polityki zapisu ograniczone do ścieżki administracyjnej — obrona w głębi dla „zapis: admin” (aplikacyjnie wymusza to `dictionary.manage`). Odczyt jest otwarty, bo słowniki nie zawierają danych spółek.
- `configuration_items`: zapis w zakresie spółki (editor/approver; macierz egzekwuje aplikacja). Sam `admin_scope` nie otwiera CI innych spółek — ścieżka administracyjna poszerza zakres o jedną spółkę (ADR 0007 §4); test `test_ci_rls_isolates_companies`.
- Uprawnienia: wszystkie cztery tabele `SELECT, INSERT, UPDATE`; `DELETE` tylko `company_categories`; bez `TRUNCATE` (test `test_app_rw_privileges_on_inventory_tables`). Funkcje triggerów bez `EXECUTE` dla `app_rw`.
- Migracja 0006 jest odwracalna; `downgrade` tylko jako właściciel tabel. Usuwa dane biznesowe tych tabel (ich historia zostaje w `audit_log`).

## 8. Dane startowe

- **Słowniki to dane referencyjne, nie przykładowe.** Nie wstawiamy ich migracją: wiersze dodane przez migrację (rola `app_owner`) nie miałyby wpisów audytu, a §6.5 wymaga logowania utworzenia kategorii. Zamiast tego `python -m app.cli seed-dictionaries` (dozwolone także przy `APP_ENV=prod`) ładuje je przez serwisy jako aktor `system`, w jednej transakcji łańcucha globalnego. Idempotentne: dodaje tylko brakujące kody, nigdy nie zmienia istniejących (admin mógł je edytować). Dopisane do CLAUDE.md §14.
- `python -m app.cli seed` (tylko dev) = tożsamości (Etap 1) + słowniki + per spółka (osobna transakcja, wyłącznie łańcuch tej spółki — kolejność blokad z ADR 0006 §7): dostępne kategorie (ALFA wszystkie z override `FW` → `dev-approver`; BETA i GAMMA bez OT) oraz 31 CI (ALFA 13, BETA 10, GAMMA 8; każdy typ użyty, 4 nieaktywne — utworzone i od razu zdezaktywowane, więc w dzienniku są `create` + `deactivate`). Zarchiwizowane spółki są pomijane.
- Wpisy audytu tworzone przez `seed-dictionaries` mają w `context` operatora: `{"source": "cli", "command": "seed-dictionaries", "os_user", "host"}` — jak `verify-audit` (ADR 0009 §5), bo komenda działa także w produkcji (`seed` analogicznie, z `command = "seed"`).
- **Ponowny seed nie nadpisuje decyzji admina (poprawka po recenzji).** Kategorie są ustawiane **tylko w spółce, która nie ma jeszcze żadnych** — świadomie wycofana kategoria nie wraca. Kategorie brakujące lub nieaktywne w słowniku, override bez roli `approver`, właściciel CI spoza spółki i nieaktywny typ CI są pomijane z wpisem w raporcie zamiast błędu. Gdyby serwis mimo to zgłosił błąd (`ProblemError`), CLI wypisuje komunikat po polsku na stderr i kończy się kodem 1 (bez tracebacku).
- Kody podkategorii: `{KATEGORIA}-{SKRÓT}`, np. `ACC-PRIV`, `NET-VLAN`, `SRV-DECOM`, `PATCH-CRIT` (ryzyko `high`).

## 9. Potwierdzone przez właściciela (akceptacja Etapu 3)

1. Odczyt słowników wymaga roli w dowolnej spółce (użytkownik bez ról: 403) — pkt 1.
2. Semantyka `requires_approval` podkategorii „tylko zaostrza” i model ACC przez `ACC-PRIV` — pkt 3.
3. Override zatwierdzającego kategorii wymaga roli `approver` w spółce (ostrzej niż domyślny zatwierdzający spółki) — pkt 4.
4. Zamrożenie inwentarza CI zarchiwizowanej spółki (409) — pkt 5.
5. Migawka identyfikatora/nazwy CI w zamrożonej zmianie — pkt 5; realizacja w Etapie 4.
6. Zgoda właściciela CI dla OT jako flaga słownikowa (np. `requires_ci_owner_consent`) — pkt 3; realizacja w Etapie 4.
