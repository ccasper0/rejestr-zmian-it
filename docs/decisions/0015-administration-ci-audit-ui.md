# 0015. Etap 6: administracja, role, inwentarz CI i dziennik audytu w UI

- Status: przyjęta; poprawki po recenzji i decyzje właściciela (2026-11-02) w §2, §1, §7, §11
- Data: 2026-10-30
- Dotyczy: CLAUDE.md §4.1, §5, §8, §10 (wspólny układ, ekran 4), §12 (Etap 6); `frontend/lib/features/{admin,ci,audit}/**`, `frontend/lib/app/router.dart`; `backend/app/api/v1/{companies,users,permissions}.py`, `backend/app/permissions.py`, `backend/app/services/companies.py`; ADR 0007, 0009, 0011, 0013, 0014

Wzorce z ADR 0014 obowiązują bez zmian: Riverpod (`FutureProvider.autoDispose(.family)` z kluczami-rekordami lub freezed), go_router ze stanem filtrów w query stringu, dio z kodowaniem każdego segmentu ścieżki (`ChangesApi.seg`), freezed + json_serializable, `data_table_2`, `WarsawTime`, `ApiProblem` po polsku, walidacja parametrów tras przed zbudowaniem ekranu, test kontraktu na prawdziwych odpowiedziach API.

## 1. Ekrany i adresy

| Adres | Ekran | Kto |
|---|---|---|
| `/admin/companies` | Spółki: tabela + panel „Nowa spółka” / edycja spółki | `app_admin` |
| `/admin/categories?status=active\|inactive` | Kategorie zmian (drzewo 2 poziomów) | `app_admin` |
| `/admin/ci-types?status=…` | Typy obiektów (CI) | `app_admin` |
| `/admin/permissions` | Macierz uprawnień (tylko odczyt) | `app_admin` |
| `/admin/users?q=&page=` | Użytkownicy (katalog `GET /users`) | `app_admin` |
| `/admin/users/{uuid}` | Użytkownik: role we wszystkich spółkach | `app_admin` |
| `/admin/audit?entity=&action=&actor=&from=&to=&page=` | Dziennik — łańcuch globalny | `app_admin` |
| `/c/{PREFIKS}/ci?q=&type=&status=&page=` | Obiekty (CI) spółki | członkowie; zapis: editor, approver, admin |
| `/c/{PREFIKS}/audit?entity=&action=&actor=&from=&to=&page=` | Dziennik audytu spółki | auditor spółki; admin — każdej spółki (także bez roli) |

- Ekrany administracyjne opakowuje `AdminGate`: inny użytkownik widzi „Brak dostępu”, a ekran **nie wysyła** żądań do API (test). Link „Administracja” w panelu był już tylko dla admina; „Spółki i słowniki” jest podświetlony na wszystkich zakładkach `/admin/*` poza użytkownikami.
- `userId` w adresie musi być UUID (`uuidPattern`), jak prefiks i numer zmiany w ADR 0014 §13 pkt 3 — spreparowany `..%2F` daje „Nie znaleziono strony” bez żądania.
- **Admin bez roli w spółce (decyzja właściciela 2026-11-02).** Przełącznik spółki adminowi pokazuje **wszystkie** spółki (`GET /companies` na ścieżce admina; bez roli — z dopiskiem „administrator”), a linki panelu admina bez członkostw wskazują pierwszą spółkę. Wspólny `AdminAwareCompanyGate` (`widgets/company_scope.dart`) wpuszcza admina bez roli tylko na ekrany, które API obsługuje ścieżką administracyjną: **Obiekty (CI)** i **Dziennik audytu**. **Rejestr zmian, karta, formularz i „Do zatwierdzenia”** pozostają za `CompanyGate`: „Brak dostępu” z wyjaśnieniem (rozdział obowiązków; nadanie sobie roli trafia do audytu).
- **Rozstrzygnięte 2026-11-02 (ADR 0016, wariant „a”) — backend daje adminowi bez roli podgląd rejestru i kart tylko do odczytu; dostosowanie UI (`CompanyGate`) należy do frontendu.** Opis sprzed decyzji: **Znana rozbieżność z §5 (do decyzji):** macierz §5 daje `app_admin` ✓ w wierszu „Podgląd rejestru, kart, ścieżki audytu”, ale API rejestru nie ma ścieżki administracyjnej — admin bez członkostwa dostaje 404 (ADR 0007 §4, ADR 0013 §7). UI trzyma się API. Usunięcie rozbieżności to albo zmiana §5 (✓ tylko z rolą w spółce), albo wąska ścieżka tylko do odczytu dla rejestru i kart (jak dla dziennika, §7).
- Filtry w URL: wartości spoza słowników (typ encji, akcja, kod typu CI, dzień, UUID aktora) są odrzucane przy czytaniu adresu, zamiast kończyć się 422 z API.

## 2. Dodatki w backendzie (minimalne, tylko odczyt)

| Endpoint | Deklaracja (`app/permissions.py`) | Uwagi |
|---|---|---|
| `GET /companies` + pole `counts` | bez zmian: `register.view`, `admin_action = company.manage` | `{active_ci, all_ci, editors, approvers, auditors, viewers}` — kolumny „Obiekty”, „Edytorzy”, „Zatwierdzający” (§10.4). Pole dodane, semantyka bez zmian. |
| `GET /users/{id}` | `membership.manage` (`require`, jak `GET /users`) | użytkownik + `memberships` we **wszystkich** spółkach; 404 `user.not_found` |
| `GET /permissions/matrix` | `register.view`, rodzaj `any_company` (jak słowniki, ADR 0011 §1) | `roles` (kolejność kolumn §5), `actions` (`action`, `label`, `note`, `roles`), `change_actions` (`akcja → wymagana akcja macierzy`) |

- **Liczniki — osobna transakcja tylko do odczytu (poprawka po recenzji).** `configuration_items` nie ma polityki `admin_scope` (ADR 0011 §7), więc w transakcji żądania admin bez członkostw widziałby 0 obiektów. Pierwsza wersja poszerzała **transakcję żądania** o spółki strony z `admin_scope = on` — recenzja: do końca żądania RLS przepuszczałby wtedy odczyt ich łańcuchów audytu i zapisy w `companies`/`company_memberships`/`company_categories`/zmianach/CI/`audit_log` tych spółek (bloker). Teraz liczniki liczy `app.db.run_read_only`: krótka, **osobna** transakcja z puli pomocniczej (jak zdarzenia logowania, ADR 0010 §5), pierwszą instrukcją `SET TRANSACTION READ ONLY`, zakres = wyłącznie spółki z tej strony, bez `admin_scope` i bez odczytu łańcucha globalnego, na końcu wycofana. Transakcja żądania nie jest poszerzana (jej zakres ustala jak dotąd `visible_companies`). Odrzucona alternatywa: funkcja `SECURITY DEFINER company_counts(uuid[])` — strażnik `test_no_rls_bypass_through_views_or_definer_functions` celowo zabrania takich funkcji. Testy (`tests/test_api_admin_views.py`): po wykonaniu `GET /companies` admina w **tej samej** transakcji żądania odczyt `audit_log` spółki A zwraca 0 wierszy, a `INSERT` do `company_memberships` A odrzuca RLS; `run_read_only` odrzuca zapis („read-only transaction”); liczniki członka i admina są poprawne.
- **Macierz z jednego źródła.** UI nie powiela §5: wiersze, kolumny i ✓ pochodzą z `PERMISSIONS`. Polskie opisy wierszy (`ACTION_DESCRIPTIONS`) leżą obok macierzy w `app/permissions.py`; test wymaga opisu dla każdej `Action` i sprawdza, że odpowiedź odpowiada `PERMISSIONS` i `CHANGE_ACTION_PERMISSIONS`. Odczyt dla każdego z rolą (nie tylko admina): to konfiguracja aplikacji, nie dane spółki; zależność nie otwiera `admin_scope`. Odrzucone: macierz zaszyta w UI (dwa źródła prawdy) i `require(…)` (otwierałoby ścieżkę administracyjną dla danych statycznych).
- Wszystkie trzy to odczyty — bez wpisu audytu (jak pozostałe GET). Macierz RBAC (`tests/test_rbac_matrix.py`) obejmuje nowe trasy; testy firmy stronicują teraz całą listę spółek (wspólna baza testowa ma ich ponad 500).
- CLAUDE.md §8 uzupełniony w tym samym commicie.

## 3. Spółki: tworzenie, edycja, archiwizacja

- **Przepływ tworzenia** (dwa wywołania): `POST /companies` (nazwa, prefiks, NIP, domyślny zatwierdzający, uoKSC) → jeśli zaznaczono kategorie, `PUT /companies/{id}/categories` z pełną listą **bez** zatwierdzających kategorii. Zatwierdzający kategorii musi mieć rolę `approver` w spółce (ADR 0011 §4), a nowa spółka nie ma członków — więc po utworzeniu panel przechodzi w tryb edycji z komunikatem „Następny krok: nadaj role, potem wskaż zatwierdzających dla kategorii”. Nieudany `PUT` nie cofa spółki (nie da się jej usunąć): panel pokazuje ostrzeżenie i kategorie można zapisać ponownie.
- Domyślnie zaznaczone są wszystkie aktywne kategorie główne (z opisem reguły: „wymaga zatwierdzenia” / „standard — bez zatwierdzenia”, „zgoda właściciela CI”); nieaktywnych nie można dodać (backend: 422), ale już przypisane zostają na liście z oznaczeniem.
- Domyślny zatwierdzający spółki wybierany z katalogu `GET /users` (aktywni): ADR 0007 §7 nie wymaga roli w spółce (spółka nie ma jeszcze członków). Zatwierdzający kategorii — tylko spośród aktywnych członków z rolą `approver` (nieaktualny override po odebraniu roli jest pokazywany z dopiskiem, nie znika po cichu).
- **Prefiks:** wielkie litery wymuszone formaterem, walidacja inline `^[A-Z]{2,8}$`, podgląd `CHG-{PREFIKS}-{RRRR}-0001` (rok wg czasu polskiego). Po utworzeniu pole tylko do odczytu; `PATCH` nigdy nie wysyła prefiksu.
- **NIP:** walidacja sumy kontrolnej i normalizacji (separatory, `PL`) powiela `app/domain/companies.py` wyłącznie dla UX; rozstrzyga backend (`company.invalid_data` z `field` trafia pod właściwe pole).
- `PATCH` wysyła tylko zmienione pola. Błędy `company.name_taken`, `company.prefix_taken`, `company.prefix_immutable`, `*.invalid_data` (`field`) są pokazywane przy polu; pozostałe — panelem błędu po polsku.
- **Archiwizacja:** dialog ze skutkami (rejestr i inwentarz tylko do odczytu, bez komentarzy/załączników, historia dostępna, operacja nieodwracalna w aplikacji, wpis w audycie) i potwierdzeniem przez wpisanie prefiksu. Zarchiwizowana spółka pozostaje edytowalna dla admina (ADR 0007 §7, ADR 0011 §4).
- Panel spółki zawiera też: kategorie z zatwierdzającymi, członków z rolami (pkt 4) oraz „Zweryfikuj łańcuch” spółki (admin weryfikuje każdą spółkę, ADR 0009 §3) i skróty do inwentarza/dziennika.

## 4. Role

- Rola jest zawsze ustawiana **pełnym zestawem** (`PUT …/members/{user_id}`, `[]` = odebranie dostępu, z ostrzeżeniem). Edytor ról (dialog z czterema checkboxami i opisem ról) jest wspólny dla panelu spółki („Członkowie i role”, „Dodaj osobę” z wyszukiwarką katalogu) i karty użytkownika („Role w spółkach”, „Nadaj rolę w spółce”).
- **Nadanie roli sobie** (admin edytuje własne konto): ostrzeżenie o rozdziale obowiązków i o wpisie w dzienniku (backend zapisuje `self_grant`, ADR 0007 §6); operacja dozwolona (§5).
- Nieaktywny użytkownik: nadanie nowej roli jest zablokowane już w dialogu (backend: 422 `membership.user_inactive`), odebranie — możliwe.
- Po zmianie ról unieważniane są: członkowie spółki, liczniki, karta użytkownika i — przy własnym koncie — `/me` (nawigacja i przełącznik spółek).

## 5. Słowniki

- Kategorie: drzewo (kategoria → podkategorie, wcięcie), filtr aktywności w URL; kategoria nieaktywna wyświetlana jako kontekst, gdy filtr „Nieaktywne” trafia w jej podkategorię. Reguła zatwierdzania liczona jak w backendzie: podkategoria kategorii wymagającej zatwierdzenia ma „wymaga zatwierdzenia (z kategorii)” i w formularzu checkbox jest zaznaczony i zablokowany z wyjaśnieniem (ADR 0011 §3 — podkategoria tylko zaostrza). Komunikat o regule nad drzewem.
- Kod (kategorii i typu CI) — walidacja inline formatu, po utworzeniu tylko do odczytu. Dezaktywacja i ponowna aktywacja przez `PATCH is_active` z potwierdzeniem; usuwania nie ma.

## 6. Inwentarz CI

- Filtry `q`, `type` (wielokrotny), `status` w URL; wyszukiwarka zapisuje URL po 400 ms. Dodawanie/edycja (typ, identyfikator, nazwa, opis, właściciel spośród członków spółki dowolnej roli, aktywność) dla `ci.manage` w niezarchiwizowanej spółce; viewer/auditor — tylko odczyt.
- **Admin bez roli w spółce** wchodzi na `/c/{PREFIKS}/ci` ścieżką administracyjną API (§5 daje mu inwentarz każdej spółki; ADR 0011 §1): spółka jest rozpoznawana z listy `GET /companies`, ekran pokazuje informację, że operacje trafiają do dziennika spółki.
- Błędy przy polach: `ci.identifier_taken` (identyfikator), `ci.owner_not_member` i `ci.owner_locked_by_change` (właściciel, z `detail` serwera — numer zmiany), `ci.type_*` (typ); `company.archived` — panelem.

## 7. Dziennik audytu

- `/c/{PREFIKS}/audit`: `GET /audit?company_id=…` — audytor spółki oraz **admin każdej spółki, także bez roli** (decyzja właściciela 2026-11-02; zmienia ADR 0009 §3 i CLAUDE.md §5). Pozostali członkowie: „Brak dostępu” z odesłaniem do ścieżki audytu na karcie zmiany. `/admin/audit` — łańcuch globalny (bez `company_id`).
- **Wąska ścieżka odczytu admina** (`app.permissions._admin_read_context`; `require_audit_chain(..., admin_read_any_company=True)` dla `GET /audit`, `require_company(..., admin_action=audit.read, admin_read_only=True)` dla `GET /companies/{id}/audit/status`): zakres transakcji **zastąpiony** jedną spółką (bez członkostw admina), `admin_scope` i odczyt łańcucha globalnego wyłączone, transakcja przełączona na READ ONLY (`SET TRANSACTION READ ONLY` — PostgreSQL pozwala przejść na tryb tylko do odczytu po zapytaniach) przed pierwszym odczytem. Nieistniejąca spółka: 404 jak dla każdego. Auditor bez członkostwa: nadal 404. Testy: macierz RBAC (admin 200 dla dziennika i statusu spółki), izolacja (admin — ścieżka administracyjna, losowy UUID — 404), `test_admin_reads_any_company_log_on_a_narrow_read_only_path` (w tej transakcji odczyt innej spółki = 0 wierszy, zapis odrzucony jako „read-only transaction”).
- Wpis: czas + IP (mono), „kto (role) — Obiekt: Akcja” + odnośnik z `context` (numer, identyfikator, kod, prefiks…), diff „przed → po” tym samym `DiffLine` co na karcie zmiany, **bez surowych kluczy i UUID** (poprawka po recenzji): etykiety pól po polsku zależnie od encji (np. „Opis” dla CI, „Status spółki”), osoby z listy członków / katalogu, `ci_type_id` → nazwa typu (słownik typów CI), `parent_id`/`category_id` → „KOD — nazwa” kategorii, `ci_ids` → identyfikatory CI spółki, role, ryzyko, tak/nie, status spółki; diff kategorii spółki (`company_category`, kluczowany kodem) jako „Kategoria FW: niedostępna → dostępna (zatwierdzający: Jan …)”. Sprawdzone na rzeczywistych kluczach diffów wszystkich encji w lokalnej bazie (`category`, `change`, `ci`, `ci_type`, `company`, `company_category`, `membership`, `user`). Dalej: komentarz, `#seq` i skrót sha256; „Szczegóły” pokazują `request_id`, `user_agent`, `prev_hash`, `hash` i pełny `context`.
- `GET /audit` nie zwraca `hash_valid` (w przeciwieństwie do ścieżki zmiany) — integralność ustala **weryfikacja**: „Zweryfikuj łańcuch” (`POST /audit/verify`, auditor/admin — te same role co przegląd) pokazuje wynik (`ok`, liczba wpisów, głowa, gdzie zapisano wynik), a przy naruszeniu oznacza na liście wpis `first_broken_seq`. Znacznik „Łańcuch spójny” spółki z `GET /companies/{id}/audit/status` (dla łańcucha globalnego nie ma endpointu statusu — tylko weryfikacja na żądanie). Weryfikacja sama jest wpisem, więc lista i znacznik są po niej odświeżane.
- Filtry: typ obiektu, akcja (słowniki `EntityType`/`AuditAction` z polskimi etykietami; test kontraktu sprawdza, że każdy typ i akcja z prawdziwych odpowiedzi ma etykietę), kto (członkowie spółki; dla łańcucha globalnego — katalog użytkowników), okres (dni czasu polskiego, koniec wyłączny w API — jak rejestr).

## 8. Niezapisane zmiany

- Panel spółki: trasa `/admin/companies` ma `onExit` → `ExitGuard` (ADR 0014 §13 pkt 2): przy niezapisanych danych lub kategoriach pyta „Odrzucić niezapisane zmiany?”, a przeładowanie karty ostrzega (`beforeunload`). Zamknięcie panelu i przejście do innej spółki pytają tak samo.
- Formularze w dialogach (kategoria, typ CI, obiekt CI, role): `PopScope` — „Anuluj”/Escape przy zmianach pyta przed odrzuceniem; tło dialogu go nie zamyka.

## 9. Responsywność i wygląd

Kolory, promienie i fonty wyłącznie z `core/theme.dart` (bez nowych tokenów); identyfikatory, kody, prefiksy, NIP, e-maile, skróty i daty w IBM Plex Mono; przyciski i zakładki ≥ 44 px. Panel spółki obok tabeli od 1400 px szerokości okna, węziej pod tabelą; < 900 px — szuflada (bez zmian). Test bez przepełnień na 400, 1000 i 1400 px.

## 10. Testy

- Backend: `tests/test_api_admin_views.py` (liczniki — członek i admin, użytkownik ze wszystkimi spółkami, 404/403, macierz = `PERMISSIONS`), macierz RBAC dla nowych tras.
- Frontend: `admin_companies_test` (walidacja prefiksu i NIP, podgląd ID, POST + PUT kategorii, 409 przy polu, PATCH tylko zmian, archiwizacja z prefiksem, strażnik wyjścia, „Brak dostępu” bez żądań), `admin_users_test` (URL katalogu, PUT pełnego zestawu ról, ostrzeżenie przy nadaniu sobie, nieaktywny użytkownik, błąd po polsku, członkowie w panelu spółki, spreparowany `userId`), `admin_dictionaries_test` (drzewo i wcięcie, filtr w URL, podkategoria nie znosi zatwierdzenia, kod tylko do odczytu, dezaktywacja, dialog z niezapisanymi zmianami, typy CI, macierz z API), `ci_inventory_test` (URL ↔ API, viewer bez zapisu, 409 przy polu, dezaktywacja, blokada właściciela, ścieżka admina), `audit_log_test` (URL ↔ API z granicą DST, odrzucanie złych wartości, diff, weryfikacja i oznaczenie wpisu, brak dostępu bez żądań, łańcuch globalny), `admin_narrow_test` (układ bez przepełnień), test kontraktu na nowych fiksturach (`tool/dump_admin_fixtures.py`).
- Scenariusz API: `tool/e2e_admin_scenario.py` (README frontendu).

## 11. Decyzje właściciela (2026-11-02)

1. `GET /permissions/matrix` — dla każdego z rolą (bez zmian).
2. Archiwizacja nieodwracalna w aplikacji — bez „Przywróć”.
3. Admin bez roli: przełącznik pokazuje wszystkie spółki; CI i dziennik audytu ścieżką administracyjną; rejestr — „Brak dostępu” (znana rozbieżność z §5 opisana w §1, do decyzji). **Rozstrzygnięte:** podgląd rejestru tylko do odczytu — ADR 0016.
4. Admin czyta dziennik **każdej** spółki bez członkostwa — wąska ścieżka tylko do odczytu (§7); ADR 0009 §3 i CLAUDE.md §5 zaktualizowane.
5. Nowa spółka: domyślnie wszystkie aktywne kategorie (bez zmian).
6. Dezaktywacja kont po stronie Entra ID — bez `PATCH /users/{id}`.

## 12. Poprawki po recenzji (2026-11-02)

- Bloker: liczniki `GET /companies` w osobnej transakcji tylko do odczytu (§2).
- Segmenty tras budowane z danych w panelu spółki i katalogu użytkowników kodowane `Uri.encodeComponent` (jak w `router.dart`).
- `UserAccount.isActive`, `UserDetail.isActive` wymagane (bez wartości domyślnej): brak pola to błąd parsowania, nie „aktywny”.
- Drzewo kategorii: wiersze wyrównane do lewej (wcześniej `Column` w karcie je wyśrodkowywał), stałe wcięcie podkategorii (32 px), akcje pod opisem na wąskich kartach; test pozycji.
- Diff w dzienniku bez surowych UUID i kluczy (§7); test.
