# 0010. Zdarzenia uwierzytelniania w dzienniku: logowanie, nieudane logowania, odmowy dostępu

- Status: przyjęta (punkty „do potwierdzenia” czekają na właściciela projektu); §1 dla kont lokalnych doprecyzowany w ADR 0018 §7 (`login` zapisuje `POST /auth/login`)
- Data: 2026-10-29
- Dotyczy: CLAUDE.md §6.5, §7; `backend/app/auth/events.py`, `backend/app/services/auth_events.py`, `backend/app/auth/dependencies.py`, `backend/app/permissions.py`, `backend/app/worker.py`, migracja `backend/alembic/versions/20261029_0005_auth_events.py`; ADR 0006 §7, ADR 0007 §2

Wszystkie zdarzenia trafiają do łańcucha **globalnego**: `entity_type = auth`, `entity_id` = użytkownik, którego dotyczą (lub `NULL`). Zapisywane są w **osobnej transakcji** (`app.db.run_in_separate_transaction`), zatwierdzanej przed zakończeniem żądania błędem, bo transakcja żądania przy 401/403/404 jest wycofywana. Zamyka to punkt „do potwierdzenia” z ADR 0006 §7: odmowy idą do łańcucha globalnego z `context.target_company_id`, a nie do łańcucha spółki docelowej.

## 1. Definicja „logowania” dla tokenów Bearer

API jest bezstanowe: każde żądanie niesie token, nie ma sesji ani endpointu logowania (poza trybem dev).

**Decyzja.** Zdarzenie `login` = **pierwsze żądanie z danym tokenem**.

- Token identyfikuje **odcisk** (`token_fingerprint`): SHA-256 z kanonicznego JSON jego **jawnych** claimów `iss, sub, aud, iat, nbf, exp, jti, uti, sid` (tych, które występują). Odcisk nie pozwala odtworzyć ani użyć tokenu (brak podpisu). Nie zapisujemy tokenu ani jego hasha, bo hash całego tokenu byłby trwałym identyfikatorem poświadczenia.
- Tabela `auth_logins (token_fingerprint UNIQUE, user_id, issuer, issued_at, expires_at)`. W tej samej osobnej transakcji, w której działa rozpoznanie tożsamości (JIT i synchronizacja profilu, ADR 0007 §2), wykonywane jest `INSERT … ON CONFLICT DO NOTHING RETURNING`. Wpis audytu tworzy wyłącznie transakcja, która faktycznie wstawiła wiersz. Działa to przy **dowolnej liczbie procesów API**, bo rozstrzyga unikalność w bazie, a nie pamięć procesu. Kolejne żądania z tym samym tokenem kosztują jeden indeksowany `SELECT`.
- Nowy token od IdP (odświeżenie co ok. godzinę w Entra ID, ponowne logowanie, nowy token dev) to nowe zdarzenie `login`. Wychodzi kilka do kilkunastu wpisów na użytkownika dziennie zamiast jednego na każde żądanie.
- Kontekst wpisu: `issuer`, `token_fingerprint` (do korelacji, nie jest sekretem), `token_issued_at`, `token_expires_at`. Aktor to użytkownik, z rolą globalną `app_admin`, jeśli ją ma. Członkostwa nie są jeszcze w tym momencie wczytane.
- Logowanie nieaktywnego użytkownika nie jest zdarzeniem `login`, tylko `login_failed` (pkt 3).
- Testy (`tests/test_auth_events.py`): jeden wpis przy kilku żądaniach z tym samym tokenem, nowy token daje nowy wpis, 20 równoległych żądań w **dwóch instancjach aplikacji** (osobne pule, jak dwa procesy) daje jeden wpis i jeden wiersz.

**Do potwierdzenia:** czy „logowanie” ma oznaczać sesję u IdP (np. claim `auth_time` lub `sid`), a nie token. Wymaga to, by Entra ID wysyłał te claimy w tokenie dostępowym API, co zależy od konfiguracji. Zmiana dotyczy tylko listy claimów w `FINGERPRINT_CLAIMS`.

## 2. Odmowy dostępu (`access_denied`)

- Zapisywane jest każde 403 (akcja niedozwolona dla ról, także na endpointach globalnych) oraz każde **404 `company.not_found`** wynikające z braku członkostwa lub nieistniejącej spółki (§7.3). Ten zakres jest szerszy niż minimum z §6.5.
- Aktor: użytkownik (role globalne i role w spółce docelowej). Kontekst: `{status, reason, target_company_id, method, path}`, gdzie `reason` to kod akcji (np. `company.manage`), `no_membership` albo `not_found`. `not_found` oznacza 404 na jawnej ścieżce administratora dla nieistniejącej spółki (poprawka po recenzji Etapu 2; test `test_admin_path_404_is_recorded`). Ścieżka bez query string.
- **Bez agregacji.** Aktor jest uwierzytelniony i rozliczalny, a każda próba sięgnięcia po obcą spółkę jest istotnym zdarzeniem bezpieczeństwa. Zalew odmów od jednego konta ograniczy limit żądań z Etapu 8. **Do potwierdzenia**, czy agregować także odmowy (mechanizm z pkt 3 łatwo rozszerzyć).

## 3. Nieudane logowania (`login_failed`) i ochrona przed zalewem

Nieudane logowanie może wywołać anonimowy klient w dowolnej liczbie. Jeden wpis na każdą próbę oznaczałby, że atakujący dowolnie powiększa dziennik i blokuje głowę łańcucha globalnego (każdy wpis ją serializuje). Pominięcie prób jest wykluczone przez §6.5 i §11.3.

**Decyzja: zliczanie w oknach czasowych z próbkowaniem wykładniczym i dokładnym podsumowaniem.**

- Przyczyny (`reason`): `missing_token`, `invalid_token` (`detail` = komunikat weryfikatora, maks. 200 znaków, nigdy treść tokenu), `unknown_user` (z `subject` wyłącznie z tokenu o **zweryfikowanym** podpisie), `user_inactive` (aktor = ten użytkownik).
- **Kubeł** = przyczyna + sieć klienta (IPv4 `/32`, IPv6 `/64`, bo jeden host lub abonent zwykle dostaje całe `/64`) + użytkownik (tylko `user_inactive`). **Okno** = stały przedział czasu `AUTH_FAILURE_WINDOW_SECONDS` (domyślnie 300 s, wyrównany do epoki, liczony zegarem bazy).
- Tabela `auth_failure_windows (window_start, window_seconds, bucket) UNIQUE`. Okno to para (początek, długość), więc instancje z różnym `AUTH_FAILURE_WINDOW_SECONDS` nie mieszają liczników (poprawka po recenzji; migracja 0005 poprawiona w miejscu, bo nie była jeszcze na `main` ani na wdrożeniu). Tabela ma licznik `count` (atomowy `INSERT … ON CONFLICT DO UPDATE SET count = count + 1`) i `logged_count` (stan licznika przy ostatnim wpisie).
- **Wpis natychmiast**, gdy licznik kubła w oknie jest potęgą dwójki: 1., 2., 4., 8., … próba (`context.count_in_window`). Pierwsza próba z danego źródła jest więc zawsze widoczna od razu, z IP i User-Agent, a skala ataku z dokładnością do 2×. Przy n próbach powstaje ⌊log₂ n⌋ + 1 wpisów zamiast n.
- **Podsumowanie po zamknięciu okna.** Dla każdego okna i kubła z `count > logged_count` powstaje wpis z `summary = true`, **dokładnym** `count_in_window`, `not_recorded_individually` oraz `first_at`/`last_at`. Aktor to `system`, IP i User-Agent puste, nowe `request_id`. Każda próba jest więc policzona w dzienniku. Podsumowania pisze:
  - worker (`arq`, cron co minutę, `unique` — jedno uruchomienie na klaster): `app.worker.auth_maintenance`;
  - oportunistycznie każde kolejne nieudane logowanie (do 5 zamkniętych okien), więc mechanizm działa także bez workera.

  Wiersze są blokowane przez `FOR UPDATE SKIP LOCKED`, więc równoległe procesy nie czekają na siebie i nie piszą podsumowania dwa razy.
- **Wiele źródeł** (np. rotacja adresów IPv6): gdy w oknie jest już `AUTH_FAILURE_MAX_BUCKETS` kubłów (domyślnie **200**), nowe źródła trafiają do jednego kubła `{reason}|overflow`.
- **Globalny limit wpisów natychmiastowych** (poprawka po recenzji Etapu 2): w jednym oknie powstaje najwyżej `AUTH_FAILURE_MAX_IMMEDIATE_ENTRIES` (domyślnie **200**) wpisów natychmiastowych łącznie dla wszystkich kubłów. Liczba już zapisanych wynika dokładnie z danych: w otwartym oknie `logged_count` przyjmuje tylko wartości 1, 2, 4, …, więc kubeł z `logged_count = 2^k` dał `k + 1` wpisów (długość bitowa, arytmetyka całkowita). Powyżej limitu próby są tylko liczone, a podsumowanie okna zapisuje je wszystkie (`not_recorded_individually`). **Nic nie ginie.**
- Przy zalewie na jedno okno przypada więc najwyżej ok. `MAX_IMMEDIATE_ENTRIES + MAX_BUCKETS + liczba przyczyn` wpisów (domyślnie ok. 400 na 5 minut), niezależnie od liczby prób i adresów. Przy współbieżności oba limity są przybliżone o kilka wpisów. Test: `test_immediate_entries_are_capped_per_window_but_summarized`.
- **Kolejność blokad:** własny kubeł, potem inne kubły (`SKIP LOCKED`, bez czekania), na końcu głowa łańcucha globalnego. Żadna inna ścieżka nie blokuje kubłów, więc nie ma cyklu oczekiwań.
- Aktor przy kliencie nieuwierzytelnionym: `system` z `context.authenticated = false`. §6.1 rezerwuje `actor_id = NULL` dla `system`, a model `Actor` nie dopuszcza innej nazwy bez `id`. **Do potwierdzenia:** czy wprowadzić osobny znacznik aktora „anonimowy” (zmiana kontraktu §6.1 i nowa wersja formatu hasha nie są potrzebne, bo `actor_display` jest zwykłym tekstem, ale zmienia się walidacja `Actor`).

Testy (`tests/test_auth_events.py`): 9 prób daje wpisy przy 1, 2, 4, 8 i sumę 9 w tabeli (odporne na przejście granicy okna); 40 prób daje 6 wpisów; podsumowanie zamkniętego okna ma dokładną liczbę 5 i `not_recorded_individually = 1`, a drugie uruchomienie nie dubluje wpisu; kubeł `overflow` przy limicie; IPv6 `/64`; brak treści tokenu w dzienniku; łańcuch globalny pozostaje spójny.

## 4. Sprzątanie danych operacyjnych

`auth_logins` i `auth_failure_windows` nie są dowodem, dowodem jest `audit_log`.

**Krótkie transakcje (poprawka po recenzji Etapu 2).** `auth_maintenance` zapisuje podsumowania partiami po `FLUSH_BATCH` (50), **każda partia we własnej transakcji**. Purge to osobna transakcja. Każdy wpis podsumowania blokuje głowę łańcucha globalnego do COMMIT. Pierwsza wersja domykała cały zaległy backlog w jednej transakcji, więc inne zapisy globalne (login, JIT, access_denied, z `lock_timeout = 5 s`) kończyły się wtedy błędem 500. Testy: `test_maintenance_commits_each_batch` (różne `xmin` partii) i `test_other_global_writers_proceed_during_maintenance` (zapis z `lock_timeout = 400 ms` przechodzi w trakcie domykania backlogu; przy jednej transakcji kończy się `LockNotAvailable`).

`auth_maintenance` usuwa:

- `auth_logins` tokenów wygasłych ponad dobę temu (weryfikator i tak je odrzuci, więc nie mogą ponownie „zalogować”),
- okna zamknięte ponad dobę temu, których wszystkie próby są już w dzienniku (`logged_count = count`).

Uprawnienia `app_rw`: `auth_logins` — `SELECT, INSERT, DELETE` (wiersze niezmienne); `auth_failure_windows` — `SELECT, INSERT, UPDATE, DELETE`. Tabele nie mają `company_id`, więc nie mają RLS (jak `users`, ADR 0008 §3), a strażnik w `tests/test_rls.py` ich nie obejmuje. Test uprawnień jest w `tests/test_db_roles.py`. Migracja 0005 jest odwracalna (`downgrade` tylko jako właściciel). Usunięcie tabel nie usuwa danych audytowych.

## 5. Koszt i osobna pula połączeń (poprawka po recenzji Etapu 2)

- Każde uwierzytelnione żądanie miało już osobną transakcję tożsamości (ADR 0007 §2). Teraz dochodzi w niej indeksowany `SELECT` w `auth_logins`, a przy pierwszym użyciu tokenu `INSERT` i wpis audytu.
- **Problem (wzajemna blokada puli, nie „czekanie”).** Odmowa dostępu jest zapisywana, gdy transakcja żądania **już trzyma połączenie** (`set_current_user`, członkostwa, zakres RLS). Pierwsza wersja brała połączenie dla osobnej transakcji z **tej samej** puli (5 + 10). Przy 15 równoległych odmowach każde żądanie trzymało jedno połączenie i czekało na drugie, którego nikt nie mógł oddać, bo oddanie wymagało właśnie tego drugiego. Cały proces API stał do `pool_timeout` (30 s), a potem wszystkie żądania kończyły się 500 bez wpisu w dzienniku. Przy puli 1 + 0 wystarczało jedno żądanie (odtworzone testem).
- **Decyzja: osobna pula pomocnicza** (`Database.aux_engine`, `DB_AUX_POOL_SIZE` + `DB_AUX_MAX_OVERFLOW`, domyślnie 2 + 3). Korzystają z niej **wszystkie** transakcje `run_in_separate_transaction`: rozpoznanie tożsamości z JIT i synchronizacją profilu, `login`, `login_failed`, `access_denied`. Transakcja pomocnicza nigdy nie potrzebuje połączenia z puli głównej, a nie może zająć dwóch połączeń pomocniczych (jedno na wywołanie, bez zagnieżdżania), więc w grafie oczekiwań na połączenia nie ma cyklu. Przy przeciążeniu transakcje pomocnicze kolejkują się za innymi krótkimi transakcjami pomocniczymi. Oczekiwanie na blokady wierszy też nie tworzy cyklu: transakcja żądania wołająca helper nie trzyma blokad głów łańcuchów (helper odmawia, ADR 0006 §7) i nie czeka na transakcję pomocniczą żadnego innego żądania.
- Odrzucona alternatywa: zwolnienie połączenia żądania (rollback) przed zapisem odmowy. Chroniłaby tylko odmowy, a nie `login`/`login_failed`/JIT, i wymagałaby zmiany cyklu życia `SessionDep`.
- Pula główna jest konfigurowalna (`DB_POOL_SIZE`, `DB_MAX_OVERFLOW`, `DB_POOL_TIMEOUT_SECONDS`). Na proces przypada maksymalnie (główna + pomocnicza) połączeń, czyli domyślnie 20. Suma po procesach musi zmieścić się w `max_connections`.
- Test regresyjny: `tests/test_auth_events.py::test_denials_do_not_deadlock_a_single_connection_pool`. Obie pule mają po jednym połączeniu bez nadmiaru, wysyłane są 4 równoległe żądania kończące się 404 i 4 kończące się 403. Wszystkie dostają swój kod, a wszystkie odmowy są w dzienniku. Na wersji ze wspólną pulą ten sam test daje same 500.

## 6. Konfiguracja

Nowe zmienne (opisane w `.env.example`): `AUTH_FAILURE_WINDOW_SECONDS` (10–86400, domyślnie 300), `AUTH_FAILURE_MAX_BUCKETS` (≥ 1, domyślnie 200), `AUTH_FAILURE_MAX_IMMEDIATE_ENTRIES` (≥ 1, domyślnie 200), pule połączeń `DB_POOL_SIZE`, `DB_MAX_OVERFLOW`, `DB_POOL_TIMEOUT_SECONDS`, `DB_AUX_POOL_SIZE`, `DB_AUX_MAX_OVERFLOW` (pkt 5).
