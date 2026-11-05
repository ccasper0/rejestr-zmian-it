# 0006. Przechowywanie łańcucha audytu: NULL dla łańcucha globalnego, zegar, brak FK, RLS

- Status: przyjęta (punkty oznaczone „do potwierdzenia” czekają na właściciela projektu)
- Data: 2026-10-28
- Dotyczy: CLAUDE.md §6.1–6.4, §7; migracja `backend/alembic/versions/20261028_0001_audit_core.py`

## 1. Łańcuch globalny a unikalność NULL

**Problem.** Łańcuch globalny ma `company_id IS NULL`. W PostgreSQL `UNIQUE (company_id, seq)` domyślnie traktuje NULL-e jako różne, więc w łańcuchu globalnym mogłyby powstać dwa wpisy o tym samym `seq` (rozwidlenie), a w `audit_chain_heads` — wiele głów globalnych.

**Decyzja.** `UNIQUE NULLS NOT DISTINCT` (PostgreSQL 15+, mamy 16) na `audit_log (company_id, seq)` i `audit_chain_heads (company_id)`. Odrzucony wariant: sentinel (np. UUID zerowy). Wymagałby odstępstwa od §6.1 („NULL dla zdarzeń globalnych”) i pilnowania, żeby sentinel nigdy nie trafił do tabel biznesowych.

**Konsekwencje.**
- `audit_chain_heads` ma `id uuid PK` (kolumna z NULL nie może być kluczem głównym) oraz `created_at`/`updated_at` zgodnie z §4.1.
- `ON CONFLICT ON CONSTRAINT uq_audit_chain_heads_company_id DO NOTHING` działa też dla NULL.
- Zapytania o łańcuch mają dwie jawne postaci (`IS NULL` / `= :id`), bo `IS NOT DISTINCT FROM` nie korzysta z indeksu.
- Test: duplikat `seq` w łańcuchu globalnym → `23505`.

## 2. `occurred_at`: zegar bazy

**Decyzja.** `record()` po zablokowaniu głowy łańcucha odczytuje `SELECT clock_timestamp()` i tę samą wartość (`datetime` z asyncpg, mikrosekundy) wstawia do kolumny i do hasha. Odczyt następuje po blokadzie, więc w obrębie łańcucha znaczniki czasu rosną razem z `seq`, niezależnie od liczby instancji API i rozjazdu ich zegarów. `timestamptz` i `datetime` mają tę samą precyzję (1 µs), a kanoniczny format zawsze ma 6 cyfr ułamka i `Z`, więc wartość odczytana z bazy daje identyczny tekst.

**Wymuszenie w bazie.** Trigger `BEFORE INSERT` odrzuca `occurred_at` spoza `[now(), clock_timestamp()]`, czyli spoza bieżącej transakcji. Aplikacja nie może więc wpisać czasu wstecz ani w przyszłość.

## 3. Kanoniczny JSON (`app/domain/canonical.py`)

Jedna funkcja dla zapisu, weryfikacji i (w Etapie 7) `data_sha256` raportów. Reguły są zamrożone (zmiana unieważnia wszystkie istniejące hashe):
- posortowane klucze, separatory `(",", ":")`, `ensure_ascii=False`, wynik w UTF-8;
- `datetime` musi mieć strefę i jest zapisywany jako UTC `YYYY-MM-DDTHH:MM:SS.ffffffZ`; `date` → ISO; UUID → małe litery;
- `Decimal` → **string** (`str(d)`), `Enum` → `value`, zbiory → posortowane;
- **`float` jest odrzucany.** `jsonb` przechowuje liczby jako `numeric`, a po odczycie np. `1e300` wraca jako liczba całkowita, co zmieniłoby hash. W domenie nie ma pól zmiennoprzecinkowych.

`diff` i `context` są normalizowane **przed** obliczeniem hasha, a do bazy trafia dokładnie to, co zostało zahashowane.

### 3a. Kanoniczny zapis `ip_address` (poprawka po recenzji Etapu 1)

**Problem.** Pierwsza wersja hashowała `str(IPv6Address)`. Format adresów IPv4-mapped (`::ffff:a.b.c.d`) w `str()` zmieniał się między wydaniami CPython (`::ffff:102:304` vs `::ffff:1.2.3.4`). Weryfikacja na innej wersji Pythona niż zapis zgłosiłaby zerwany łańcuch, mimo że dane się nie zmieniły.

**Decyzja.** Własny, zamrożony formatter `app.domain.audit.format_ip`, niezależny od `str(ipaddress.*)`. Używa go `normalize_ip` zarówno przy zapisie (`record`), jak i przy weryfikacji (`verify_chain`).
- IPv4: zapis dziesiętny z kropkami, bez zer wiodących.
- IPv4-mapped (`::ffff:0:0/96`) jest zamieniany na **IPv4** (`a.b.c.d`) i jako IPv4 trafia do kolumny `inet`. Odczyt z bazy daje więc ten sam tekst. Tak gniazda dual-stack przedstawiają klientów IPv4.
- Pozostałe IPv6 w postaci skróconej RFC 5952 §4, zaimplementowanej deterministycznie: małe litery, bez zer wiodących w grupach, `::` zastępuje najdłuższy ciąg co najmniej dwóch grup zerowych (przy remisie pierwszy), pojedyncza grupa zerowa nie jest skracana. Bez notacji mieszanej z IPv4 (RFC 5952 §5 to tylko zalecenie), więc IPv4-compatible (`::a.b.c.d`, przestarzały) i NAT64 zapisujemy w czystych grupach szesnastkowych (`::c000:201`).
- Adres ze strefą (`%eth0`) i prefiks inny niż hostowy (`/32`, `/128`) są odrzucane. Tekst `a.b.c.d/32` (np. `inet::text`) jest akceptowany.

Testy: wektory w `tests/test_audit_domain.py` (definicja formatu; zmiana któregokolwiek unieważnia zapisane hashe) oraz test przejścia przez bazę w `tests/test_audit_log.py`. Ten drugi zapisuje wpis, odczytuje `ip_address` (wartość z drivera, `inet::text` i `host()`), sprawdza rodzinę adresu (4 dla IPv4-mapped) i weryfikuje łańcuch. Kontrola krzyżowa z `IPv6Address.compressed` obejmuje tylko adresy spoza `::/96` i `::ffff:0:0/96` i jedynie chroni przed literówkami. Definicją są wektory.

Wpływ na istniejące dane: Etap 1 nie był wdrożony. Gdyby istniały wpisy z adresem IPv4-mapped zapisanym jako IPv6, ich weryfikacja zgłosi zerwanie (wymagałaby jednorazowej migracji z ADR).

## 4. Brak FK na `audit_log.company_id` / `actor_id`

**Decyzja.** Nie dodajemy FK (teraz ani później). Uzasadnienie:
- dziennik ma być samowystarczalnym dowodem (`actor_display`, `actor_roles` są zamrożone), niezależnym od losu wierszy w `companies`/`users`;
- wpisy globalne nie mają spółki, a nieudane logowanie może dotyczyć użytkownika, którego nie ma w `users`;
- FK zakładałby blokadę `KEY SHARE` na wierszu spółki przy każdym wpisie audytu, co oznacza dodatkową rywalizację o blokady na i tak serializowanej ścieżce;
- spółek się nie usuwa (archiwizacja), więc FK nie chroniłby przed niczym realnym.

Poprawność `company_id` zapewnia serwis (kontekst spółki z `get_company_context`) oraz polityka RLS `WITH CHECK`.

## 5. Ochrona w bazie (ponad §6.3)

- `app_rw`: `audit_log` tylko `SELECT, INSERT` (+ `USAGE` na sekwencji), `audit_chain_heads` tylko `SELECT, INSERT, UPDATE`, `alembic_version` tylko `SELECT`.
- Triggery `BEFORE UPDATE OR DELETE` i `BEFORE TRUNCATE` na `audit_log` → wyjątek (`23001`), również dla właściciela.
- Trigger `BEFORE INSERT` (SECURITY DEFINER, żeby RLS nie ukrył poprzedniego wpisu) wymusza liniowość: `seq = 1` → `prev_hash = '0'*64`, w przeciwnym razie `prev_hash` = hash wpisu `seq-1` tego samego łańcucha. Rozwidlenie albo luka są więc niemożliwe także przy zapisie z pominięciem serwisu.
- Trigger na `audit_chain_heads`: głowa powstaje pusta (0, `'0'*64`), przesuwa się dokładnie o 1 i musi wskazywać istniejący wpis z tym hashem; `DELETE`/`TRUNCATE` są zablokowane.
- `app_rw` nie może `SET session_replication_role` (wyłączenie triggerów) ani `ALTER TABLE` (test).
- `downgrade` migracji działa tylko jako właściciel tabel (`app_owner`). Przy niepustym `audit_log` odmawia, chyba że podano `-x allow_audit_data_loss=yes`.

Granica ochrony: właściciel (`app_owner`) może wyłączyć triggery i zmienić dane. Wykrywa to `verify_chain` (testy), dopóki atakujący nie przeliczy całego ogona łańcucha i głowy. Pełna ochrona wymaga zakotwiczenia głowy poza bazą (faza B / Etap 7: hash głowy w raportach PDF, opcjonalnie publikacja okresowa).

## 6. RLS na tabelach audytu

- Funkcje `app_company_ids()` (z `app.company_ids`; brak lub pusty = brak spółek) i `app_global_audit_read()` (z `app.audit_global_read = 'on'`). Ustawia je `app.db.apply_company_scope(session, ids, global_audit_read=...)` przez `set_config(..., true)` (odpowiednik `SET LOCAL`).
- `audit_log`: SELECT — spółki z zakresu oraz łańcuch globalny tylko przy jawnym `global_audit_read`. INSERT — spółki z zakresu oraz zawsze globalne (logowania, nieudane logowania, odmowy dostępu).
- **Kto czyta łańcuch globalny (poprawka po recenzji Etapu 1, decyzja koordynatora):** wyłącznie `app_admin`. `CurrentUser.global_audit_read` = `is_app_admin`. Pierwotnie także audytor dowolnej spółki, ale łańcuch globalny zawiera dane wszystkich spółek (nazwy, NIP, e-maile użytkowników, odmowy dostępu z `target_company_id`), co narusza izolację (CLAUDE.md §1 pkt 2, §7). Konsekwencja: audytor czyta i weryfikuje łańcuchy **swoich** spółek, a łańcuch globalny czyta i weryfikuje tylko admin (`verify_chain(None)` w transakcji audytora daje `AuditScopeError`, test w `tests/test_rls.py`). Możliwe rozszerzenie (jawny `subject_company_id`) opisuje ADR 0008 §6.
- `audit_chain_heads`: spółki z zakresu + głowa globalna.
- `audit.record()` nie używa `RETURNING`, bo RETURNING wymaga widoczności wiersza dla SELECT. Model ma `implicit_returning=False`.
- `verify_chain()` odmawia (`AuditScopeError`) weryfikacji łańcucha spoza zakresu. Niewidoczny łańcuch wyglądałby jak pusty i dawał fałszywe „ok”.
- Bez `FORCE ROW LEVEL SECURITY`. Aplikacja i testy łączą się jako `app_rw` (nie właściciel, `NOBYPASSRLS` — asercja w testach), a właściciel służy tylko migracjom. **Do potwierdzenia:** czy dodać `FORCE` jako dodatkowy bezpiecznik. Kosztem byłoby jawne ustawianie zakresu w narzędziach właściciela (np. w kryminalistycznym odczycie). Rozstrzygnięte w ADR 0008 §2: bez `FORCE`.

## 7. Zasady dla wywołujących `record()`

- Wywołanie w transakcji biznesowej (`AuditError`, gdy sesja nie jest w transakcji).
- Kolejność blokad: najpierw łańcuchy spółek, na końcu globalny (unikanie zakleszczeń). Wiersze biznesowe (np. `companies … FOR UPDATE`) blokujemy **przed** wpisem audytu, który je opisuje.
- Zapisy niezwiązane z transakcją biznesową (JIT/synchronizacja profilu, w Etapie 2 zdarzenia `login`/`login_failed`/`access_denied`) idą przez `app.db.run_in_separate_transaction`, czyli w osobnej, krótkiej transakcji zatwierdzanej **przed** transakcją żądania (ADR 0007 §2). Helper odmawia działania, gdy transakcja żądania trzyma już blokadę głowy łańcucha (`audit.held_chain_locks`), bo wewnętrzna czekałaby na zewnętrzną, a takiego zakleszczenia PostgreSQL nie wykryje. Ustawia też `lock_timeout = 5s`.
- Regresja: recenzent Etapu 1 odtworzył `deadlock detected`. Synchronizacja profilu admina w transakcji żądania blokowała głowę globalną, a potem `PUT /companies/C/members/U` blokował wiersz spółki, w tym samym czasie `PATCH /companies/C` (wiersz spółki, potem głowa globalna). Test deterministyczny i wariant swobodny są w `tests/test_auth_identity_sync.py`.
- `request_id`: parametr → `get_request_id()` → nowy `uuid4` (CLI/worker).
- **Do potwierdzenia (faza B / Etap 2):** odmowy dostępu (403/404 do zasobu innej spółki) zapisujemy w łańcuchu **globalnym** z `context.target_company_id`. Zapis do łańcucha spółki B przez użytkownika spoza B wymagałby poszerzania zakresu RLS. Pozwalałby też tworzyć dowolnie wiele łańcuchów przez odpytywanie losowych UUID. Rozstrzygnięte w ADR 0010: łańcuch globalny.

## 8. Role w testach

SQL ról jest w `deploy/postgres/init/roles.psql`. Wywołuje go `10-roles.sh` (rozszerzenie `.psql` jest ignorowane przez entrypoint obrazu). Testy montują ten sam katalog jako `/docker-entrypoint-initdb.d` w kontenerze testcontainers, uruchamiają `alembic upgrade head` jako `app_owner` (prawdziwe CLI), a kod aplikacji testują jako `app_rw`.
