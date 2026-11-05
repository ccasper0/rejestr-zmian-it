# 0008. Row-Level Security: polityki tabel tożsamości, brak FORCE, `users` bez RLS, strażnik

- Status: przyjęta (punkty „do potwierdzenia” czekają na właściciela projektu)
- Data: 2026-10-28
- Dotyczy: CLAUDE.md §5, §7, §12 (Etap 1); migracja `backend/alembic/versions/20261028_0003_identity_rls.py`; ADR 0006 §6, ADR 0007 §3–4

## 1. Polityki

Funkcje pomocnicze (wszystkie `STABLE`, bez `SECURITY DEFINER`, odporne na brak ustawienia; po transakcji z `set_config(..., true)` połączenie z puli ma `''`, co też oznacza „brak”):

| Funkcja | Zmienna | Brak / `''` / inna wartość |
|---|---|---|
| `app_company_ids()` (0001) | `app.company_ids` | `{}` |
| `app_global_audit_read()` (0001) | `app.audit_global_read` | `false` (tylko dokładnie `on`) |
| `app_user_id()` (0003) | `app.user_id` | `NULL` (porównanie nigdy nie jest prawdziwe) |
| `app_admin_scope()` (0003) | `app.admin_scope` | `false` (tylko dokładnie `on`) |

Osobna polityka dla każdej komendy, wyłącznie `TO app_rw`:

| Tabela | SELECT (`USING`) | INSERT (`WITH CHECK`) | UPDATE (`USING` i `WITH CHECK`) | DELETE (`USING`) |
|---|---|---|---|---|
| `companies` | `id ∈ zakres` lub admin | admin | admin **i** `id ∈ zakres` | brak uprawnienia (archiwizacja) |
| `company_memberships` | `company_id ∈ zakres` lub `user_id = app_user_id()` lub admin | admin **i** `company_id ∈ zakres` | admin **i** `company_id ∈ zakres` | admin **i** `company_id ∈ zakres` |
| `audit_log`, `audit_chain_heads` | bez zmian (ADR 0006 §6): `admin_scope` **nie** poszerza odczytu dziennika | | | |

Uzasadnienie wyborów odbiegających od propozycji z ADR 0007 §4:

- **UPDATE spółki wymaga też `id ∈ zakres`.** Ścieżka administracyjna dla jednej spółki i tak poszerza zakres o spółkę docelową (`_admin_context`). Dzięki temu błąd w endpoincie administracyjnym spółki X nie zmieni spółki Y. INSERT nie może tego wymagać, bo nowej spółki nie ma jeszcze w zakresie. Seed (krok 3, domyślni zatwierdzający) ustawia teraz zakres na swoje spółki.
- **`user_id = app_user_id()` w SELECT członkostw.** Członkostwa są czytane po `set_current_user`, ale przed `apply_company_scope` (ADR 0007 §3). Użytkownik widzi swoje role we wszystkich spółkach i nic poza nimi (test).
- **Członek spółki widzi wszystkich członków tej spółki.** `GET /companies/{id}/members` jest dostępne dla każdej roli (§5: podgląd).

Konsekwencje:

- `SELECT … FOR UPDATE/SHARE` na `companies` podlega także polityce UPDATE, więc wiersz spółki może zablokować tylko ścieżka administracyjna (test). Kontrole FK z tabel podrzędnych (`changes.company_id` itd.) nie są tym objęte, bo działają z uprawnieniami właściciela. Etap 4 serializuje numerację na `number_sequences`, a nie na `companies`.
- `_admin_context` (`app/permissions.py`) najpierw włącza zakres administracyjny, a dopiero potem szuka spółki. Wcześniej admin bez członkostwa dostawał 404, bo wiersz był dla niego niewidoczny (błąd wykryty przez testy po włączeniu RLS). Dla nieistniejącego id poszerzony zakres jest nieszkodliwy: żądanie kończy się 404, a transakcja jest wycofywana.
- Odczyt bez ustawionego zakresu zwraca 0 wierszy, a nie błąd. Wyjątkiem jest głowa łańcucha **globalnego** w `audit_chain_heads`, widoczna zawsze z założenia (ADR 0006 §6: wpisy globalne, np. nieudane logowania, zapisuje każdy).

## 2. Bez `FORCE ROW LEVEL SECURITY`

**Decyzja.** Nie włączamy `FORCE` na żadnej tabeli. Zamyka to punkt „do potwierdzenia” z ADR 0006 §6, o ile właściciel projektu nie zdecyduje inaczej.

Uzasadnienie:

1. **`FORCE` nie chroni przed właścicielem.** Właściciel może w każdej chwili wykonać `ALTER TABLE … NO FORCE ROW LEVEL SECURITY`, `DISABLE ROW LEVEL SECURITY` albo `DROP POLICY`. Przed nadużyciem roli `app_owner` chroni ograniczenie jej użycia (tylko migracje) i łańcuch skrótów (ADR 0006 §5), a nie RLS.
2. **Ciche, częściowe migracje danych.** RLS nie zgłasza błędu, tylko filtruje. Przy `FORCE` migracja danych (backfill, `UPDATE … SET`) uruchomiona przez właściciela bez ustawionego zakresu zmieniłaby **zero lub część** wierszy i zakończyłaby się „sukcesem”. Każda migracja danych musiałaby ustawiać `app.admin_scope` i pełną listę spółek, a pomyłka nie byłaby widoczna.
3. **Właściwe zabezpieczenie to to, by aplikacja nigdy nie była właścicielem.** Testy (`tests/test_rls.py`, `tests/test_db_roles.py`) sprawdzają, że `app_rw` nie jest superuserem ani nie ma `BYPASSRLS`, nie jest właścicielem żadnej relacji w `public`, nie ma `CREATE` na schemacie (nie utworzy tabeli, której byłaby właścicielem), a wszystkie tabele ze spółką należą do `app_owner`.

Wpływ na migracje danych: migracje działają jako `app_owner` i widzą wszystkie wiersze, tak jak do tej pory. Gdyby właściciel zdecydował się na `FORCE`, każda migracja danych musi jawnie ustawić `set_config('app.admin_scope','on',true)` i `app.company_ids` (wszystkie spółki), a odczyt kryminalistyczny jako właściciel także. Zmiana wymaga nowej migracji i aktualizacji tego ADR.

## 3. `users` bez RLS

**Decyzja.** Tabela `users` nie ma RLS. §7 wymaga RLS dla tabel z `company_id`, a `users` takiej kolumny nie ma: użytkownik jest wspólny dla wielu spółek.

Uzasadnienie:

- Odczyt po `external_id` musi działać **przed** ustaleniem tożsamości (logowanie, `GET /auth/dev/users`, `POST /auth/dev/token`), a JIT musi móc wstawić wiersz bez ścieżki administracyjnej. Polityka, która by to dopuszczała (np. „zawsze, gdy `app.user_id` nie jest ustawione”), niczego by nie chroniła.
- Polityka „użytkownicy spółek z mojego zakresu” wymagałaby podzapytania do `company_memberships`, które samo ma RLS, oraz zależnych od siebie polityk dwóch tabel. Tworzyłoby to ryzyko rekursji polityk i spadku wydajności przy każdym złączeniu z `users`.
- `users` nie zawiera danych biznesowych spółek. Pola to tożsamość (`email`, `display_name`, flagi).

Ochrona w warstwie aplikacji: `GET /users` tylko dla admina, członkowie wyłącznie przez `GET /companies/{id}/members` (członkostwo lub ścieżka administracyjna), `DELETE` niedostępne dla `app_rw`.

**Do potwierdzenia:** czy katalog użytkowników (e-maile) ma być ukryty przed użytkownikami innych spółek również na poziomie bazy. Gdyby tak, proponujemy funkcję `SECURITY DEFINER` do wyszukiwania po `external_id` przy logowaniu oraz politykę opartą na członkostwach. Do decyzji przed Etapem 8.

## 4. Strażnik „zapomnianego zakresu”

`tests/test_rls.py` przez introspekcję `pg_class`, `pg_attribute`, `pg_policies` sprawdza **każdą** tabelę w `public` z kolumną `company_id` (oraz `companies` jako korzeń z kluczem `id`):

- RLS włączone, właściciel `app_owner`, co najmniej jedna polityka obejmująca `app_rw`;
- każde wyrażenie polityki zależy od zakresu transakcji (`app_company_ids()`, `app_admin_scope()` lub `app_user_id()`), więc `USING (true)` zostanie odrzucone;
- każda komenda, do której `app_rw` ma uprawnienie, ma jawną politykę permisywną;
- zachowanie: przy zakresie obcej spółki żadna tabela nie zwraca wierszy spółek;
- brak widoków bez `security_invoker` i funkcji `SECURITY DEFINER` wykonywalnych przez `app_rw` (obie rzeczy omijają RLS);
- test mutacyjny potwierdza, że strażnik wykrywa tabele bez RLS, bez polityk lub z polityką ignorującą zakres. Tabele testowe powstają w transakcji, która jest wycofywana.

Wyjątki (`RLS_EXEMPT` w teście) wymagają uzasadnienia w ADR. Obecnie lista jest pusta. `report_exports` (Etap 7) ma `company_id NULL` dla raportu wielospółkowego audytora i będzie potrzebowało polityki analogicznej do `audit_log`.

Izolacja w API: `tests/isolation_cases.py` to jedna lista endpointów ze spółką. Test wymusza, że każda trasa z `{company_id}` jest na liście i ma rodzaj zgodny z deklaracją w `app/permissions.py`. Kolejne etapy dopisują do niej swoje endpointy (z `foreign_resource` dla zasobów, np. `changes/{id}`).

## 5. Granice ochrony

- **RLS oparte na zmiennych sesji chroni przed błędami aplikacji** (brak filtra, obce id), a nie przed atakującym, który wykonuje dowolny SQL jako `app_rw`: taki atakujący może wywołać `set_config('app.admin_scope','on',true)`. Ochrona przed tym to brak SQL budowanego z tekstu (tylko ORM i parametry wiązane), osobna rola i łańcuch audytu. **Do potwierdzenia / Etap 8:** czy utwardzić ustawianie zakresu (np. funkcja `SECURITY DEFINER` weryfikująca podpisany token zakresu).
- `admin_scope` nie daje odczytu dziennika audytu. Ścieżka administracyjna jednej spółki poszerza jednak `app.company_ids` o tę spółkę na czas jednej transakcji (ADR 0007 §4), więc w tej transakcji łańcuch tej spółki jest czytelny. Endpointy administracyjne go nie zwracają.

## 6. Odczyt łańcucha globalnego: tylko `app_admin` (poprawka po recenzji Etapu 1)

**Problem.** `global_audit_read` (zmienna `app.audit_global_read`, funkcja `app_global_audit_read()`) był włączany dla admina **i audytora dowolnej spółki**. Łańcuch globalny zawiera zdarzenia wszystkich spółek: tworzenie i edycję spółek (nazwy, NIP), użytkowników (e-maile), a od Etapu 2 także odmowy dostępu z `target_company_id`. Audytor spółki A widziałby więc dane spółki B, co jest sprzeczne z CLAUDE.md §1 pkt 2 i §7.

**Decyzja (koordynator).** `global_audit_read` tylko dla `app_admin` (`CurrentUser.global_audit_read = is_app_admin`). Polityki RLS się nie zmieniają (migracja nie jest potrzebna). Zmienia się wyłącznie to, komu aplikacja otwiera jawną ścieżkę odczytu.

Konsekwencje:
- audytor czyta i weryfikuje łańcuchy swoich spółek (`POST /audit/verify?company_id=…`). Weryfikacja łańcucha globalnego (`company_id` pominięte) jest tylko dla admina. Audytor bez dostępu dostanie odmowę (`AuditScopeError` w serwisie; w API 403 dla łańcucha globalnego i 404 dla obcej spółki, ADR 0009 §1);
- raport zbiorczy audytora „Wszystkie spółki” (Etap 7) obejmuje łańcuchy jego spółek, a nie łańcuch globalny. Zdarzenia globalne dotyczące jego spółek (np. zmiana nazwy spółki) nie są w nim widoczne bez rozszerzenia poniżej;
- testy: `tests/test_principal.py` (każda rola, w tym audytor wszystkich spółek, ma `False`; admin ma `True`) oraz `tests/test_rls.py::test_global_audit_chain_is_readable_by_app_admins_only`. W transakcji żądania zbudowanej przez `current_user` audytor widzi tylko łańcuch swojej spółki, a admin tylko globalny, każdy weryfikuje wyłącznie swoje łańcuchy.

**Możliwe rozszerzenie (nie wdrożone): `subject_company_id`.** Gdyby audytor potrzebował zdarzeń globalnych dotyczących jego spółek (zmiany danych spółki, odmowy dostępu do niej), dodajemy do `audit_log` kolumnę `subject_company_id uuid NULL` (spółka, której dotyczy wpis globalny, objęta hashem jako nowe pole payloadu od określonego `seq` lub wersji formatu) oraz politykę SELECT `company_id IS NULL AND subject_company_id = ANY (app_company_ids())`. Audytor widziałby wtedy podzbiór łańcucha globalnego. **Nie mógłby go jednak zweryfikować** (weryfikacja wymaga ciągłości wszystkich `seq`), więc musiałby dostać od admina wynik weryfikacji lub podpisany hash głowy. Alternatywa: zapisywać takie zdarzenia podwójnie (globalnie i w łańcuchu spółki), co wymaga zachowania kolejności blokad z ADR 0006 §7. Decyzja do podjęcia najpóźniej w Etapie 7 (raport zbiorczy).
