# 0018. Konta lokalne z hasłem zamiast Entra ID / OIDC (Etap 8, część 1)

- Status: przyjęta (decyzja właściciela 2026-11-03: bez Entra ID / OIDC); punkty z §12 rozstrzygnięte decyzją właściciela 2026-11-04
- Data: 2026-11-03
- Dotyczy: CLAUDE.md §2, §4.1 (`users`), §5, §6.5, §8, §12 (Etap 8); migracje `backend/alembic/versions/20261103_0010_local_accounts.py`, `20261104_0011_temp_password_expiry.py`; `backend/app/{config.py, auth/*, domain/passwords.py, domain/common_passwords.txt, services/local_auth.py, services/users.py, services/auth_events.py, api/v1/auth.py, api/v1/users.py, permissions.py, cli.py}`; zastępuje ADR 0007 §1–2 (OIDC, JIT) i doprecyzowuje ADR 0010 §1 (definicja „logowania”) dla kont lokalnych

ISO/IEC 27001:2022 A.5.17 (informacje uwierzytelniające), A.8.5 (bezpieczne uwierzytelnianie), A.8.15 (logowanie); NIST SP 800-63B §5.1.1; OWASP Password Storage / Authentication Cheat Sheets.

## 1. Tryby i usunięcie OIDC

- `AUTH_MODE` = `local` (domyślny, produkcja) | `dev`. Inna wartość — błąd konfiguracji. `dev` przy `APP_ENV=prod` jest odrzucany już w `Settings` (bez zmian). Tryb dev działa jak dotąd: użytkownicy z seeda bez haseł, `GET /auth/dev/users`, `POST /auth/dev/token`.
- Kod OIDC usunięty w całości (nic poza nim go nie używało): `app/auth/oidc.py` (JWKS, discovery), JIT i synchronizacja profilu (`users.provision_user`/`sync_profile`), `IdentityProviderUnavailableError` (503), zmienne `OIDC_*`, zależności `httpx` (runtime) i `pyjwt[crypto]` (zostaje `pyjwt` dla HS256), testy `test_jwks_grace.py` i część OIDC w `test_api_auth.py`/`test_auth_tokens.py`/`test_auth_identity_sync.py` (testy `run_in_separate_transaction` przeniesione do `test_separate_transaction.py`). Kolumna `users.external_id` zostaje jako stabilny `sub` tokenów: `local:<uuid>` dla kont lokalnych, `dev-*` dla użytkowników seeda.
- Frontend (ADR 0014 §1) wykrywa tryb jak dotąd: `GET /auth/dev/users` → 404 oznacza teraz tryb `local` (formularz e-mail + hasło), nie OIDC.

## 2. Model danych (migracja 0010, odwracalna)

- `users`: e-mail jest loginem — unikalny bez względu na wielkość liter (`uq_users_email_lower` na `lower(email)`). Migracja odmawia działania, gdy istnieją duplikaty (wypisuje je), zamiast coś po cichu zmieniać.
- `user_credentials` (osobna tabela, nie kolumny `users`): `password_hash` (argon2id, CHECK `LIKE '$argon2id$%'`), `password_changed_at`, `must_change_password`, `failed_attempts`, `locked_until`. Osobna tabela, bo obiekt `User` (ładowany przy każdym żądaniu, serializowany w `/users`, `/me`, snapshotach audytu) nigdy nie zawiera skrótu hasła, a uprawnienia da się zawęzić do kolumn. Brak wiersza = konto bez hasła (użytkownicy dev; nie zalogują się w trybie `local`).
- `auth_sessions`: jedna sesja na zalogowanie (`sid` tokenów dostępu): `expires_at` (bezwzględny limit), `refreshed_at`, `revoked_at`, `revoke_reason` (`logout`, `password_change`, `password_reset`, `lockout`, `deactivated`, `refresh_token_reuse`, `temporary_password_expired`).
- `auth_refresh_tokens`: wyłącznie SHA-256 tokenu (`token_hash` UNIQUE), `expires_at` (bezczynność), `rotated_at` (jednorazowość).
- Triggery (także dla właściciela): sesja odwołana nie może zostać przywrócona ani zmieniona; `user_id`/`expires_at` sesji i cały token odświeżania (poza jednorazowym ustawieniem `rotated_at`) są niezmienne.
- `app_rw` (minimalnie): `user_credentials` — SELECT, INSERT, UPDATE tylko kolumn hasła/blokady (bez DELETE, bez zmiany `user_id`); `auth_sessions` — SELECT, INSERT, DELETE (sprzątanie), UPDATE `refreshed_at`, `revoked_at`, `revoke_reason`, `updated_at`; `auth_refresh_tokens` — SELECT, INSERT, DELETE, UPDATE `rotated_at`, `updated_at`. Test: `test_db_roles.py::test_app_rw_privileges_on_local_account_tables`.
- Migracja 0011 (§12 p. 4): `user_credentials.temp_password_expires_at` — termin ważności hasła tymczasowego, ustawiony **dokładnie wtedy**, gdy `must_change_password` (CHECK `ck_user_credentials_temp_password_expiry`); istniejące hasła tymczasowe dostają `password_changed_at + 168 h`; `app_rw` ma UPDATE tej kolumny. Downgrade (tylko właściciel tabeli) usuwa kolumnę.
- Brak `company_id` → brak RLS (jak `users`, ADR 0008 §3). Rozważono RLS na `user_credentials` (odczyt skrótów tylko w „ścieżce logowania”), ale każda transakcja `app_rw` mogłaby ją otworzyć tak samo jak serwis — bez realnego zysku; ochroną jest argon2id i brak skrótu w API/audycie.
- Downgrade tylko jako `app_owner`; przy niepustym `user_credentials` wymaga `-x allow_credential_loss=yes` (inaczej usunąłby wszystkie hasła).
- Sprzątanie (`auth_maintenance`, worker): sesje wygasłe ponad dobę temu (z tokenami — `ON DELETE CASCADE`). Tokeny zrotowane żywej sesji zostają do końca sesji — są potrzebne do wykrycia ponownego użycia.

## 3. Hasła

- **Skrót:** argon2id (`argon2-cffi`), parametry OWASP: m = 19 MiB, t = 2, p = 1, sól 16 B, skrót 32 B. Parametry są zapisane w skrócie; po udanym logowaniu `check_needs_rehash` → skrót jest podnoszony do bieżących parametrów (`context.password_rehashed` we wpisie `login`). Hashowanie i weryfikacja w wątku (`asyncio.to_thread`), nigdy na pętli zdarzeń, i bez trzymania połączenia z bazą.
- **Normalizacja:** NFKC przed sprawdzeniem polityki i przed hashowaniem/weryfikacją (63B §5.1.1.2).
- **Polityka** (`app/domain/passwords.py`, czysty Python): 12–128 znaków (punkty kodowe), nie jeden powtórzony znak ani prosty ciąg (klawiatura/cyfry/alfabet), nie zawiera e-maila, jego części lokalnej ani pełnej nazwy użytkownika (≥ 4 znaki, bez względu na wielkość liter i spacje), nie jest na liście popularnych haseł (`common_passwords.txt` w repo, offline, ok. 13 tys. pozycji ≥ 12 znaków, w tym polskie i specyficzne dla produktu; rozszerzalna). Ograniczenie: lista nie pochodzi z korpusu wycieków (bez pobierania z sieci) — to ręczny rdzeń plus wygenerowane typowe wzorce (popularne słowa angielskie i polskie, imiona, miasta, kluby, miesiące, ciągi klawiaturowe z cyframi, latami 1985–2026 i „!”), więc nie zastępuje sprawdzenia w pełnym korpusie (np. HIBP offline), które można dodać później. Bez reguł składu („znak specjalny”) — zgodnie z NIST. Nowe hasło musi różnić się od obecnego. Kody: `auth.password_too_short`, `auth.password_too_long`, `auth.password_too_simple`, `auth.password_contains_identity`, `auth.password_too_common`, `auth.password_reused` (422, `detail` po polsku).
- **Bez wymuszonej okresowej zmiany** (63B): zmiana wymuszana tylko po haśle tymczasowym (`must_change_password`).

## 4. Tokeny i sesje

- **Token dostępu:** JWT HS256 podpisany `AUTH_JWT_SECRET` (`SecretStr`; min. 32 znaki, przy `APP_ENV=prod` min. 64, odrzucany „nielosowy” — < 8 różnych znaków). `iss = urn:rejestr:local-auth`, `aud = urn:rejestr:api`, `sub = external_id`, `sid`, `iat`, `nbf`, `exp`, `jti`; bez ról i bez danych osobowych. Czas życia `AUTH_ACCESS_TOKEN_MINUTES` (domyślnie 15, maks. 60). Weryfikator przyjmuje dokładnie HS256, ten issuer i ten klucz (token dev nie przejdzie i odwrotnie — test). Brak klucza: API odmawia startu w `lifespan` (import `app.main` go nie wymaga — testy, narzędzia).
- **Sesja sprawdzana przy każdym żądaniu** (w krótkiej transakcji tożsamości, ADR 0007 §2: jeden indeksowany SELECT `auth_sessions ⟕ user_credentials`). Wylogowanie, zmiana/reset hasła, dezaktywacja i blokada z `POST /auth/password` działają **natychmiast**, a nie dopiero po wygaśnięciu tokenu dostępu. Odwołana/wygasła sesja → 401 `auth.session_expired` (+ `login_failed`, przyczyna `session_invalid`).
- **Token odświeżania:** 32 losowe bajty (base64url), w bazie tylko SHA-256. Jednorazowy: `POST /auth/refresh` oznacza go `rotated_at` i wydaje nowy (rotacja). **Wykrywanie ponownego użycia:** przedstawienie zrotowanego tokenu odwołuje całą sesję (`session_revoke`, `refresh_token_reuse`) — złodziej i właściciel muszą zalogować się ponownie. Wygasa po `AUTH_REFRESH_IDLE_MINUTES` bez użycia (domyślnie 120) i najpóźniej z sesją (`AUTH_SESSION_MAX_HOURS`, domyślnie 12 h od zalogowania).
- **Dlaczego refresh token w treści odpowiedzi, a nie ciasteczko HttpOnly:** frontend trzyma sesję w `sessionStorage` (ADR 0014; per karta, znika po zamknięciu). Ciasteczko HttpOnly chroniłoby przed odczytem przez XSS, ale wymaga ochrony CSRF, `SameSite`/CORS z poświadczeniami dla pracy deweloperskiej z innego originu (port 5000) i nie rozwiązuje problemu, że XSS i tak wykonuje żądania w imieniu użytkownika. Ograniczamy więc skutki kradzieży: krótki token dostępu, natychmiastowe odwołanie po stronie serwera, rotacja + wykrywanie ponownego użycia, limit bezczynności i bezwzględny limit sesji; ochroną przed XSS jest CSP (część devops Etapu 8). Odpowiedzi z tokenami mają `Cache-Control: no-store`.
- **Wymóg dla klienta:** odświeżanie jednocześnie najwyżej jedno na kartę (single-flight). Dwa równoległe `refresh` tym samym tokenem to z definicji ponowne użycie — sesja zostanie odwołana.
- **Odrzucone:** sesja tylko po stronie serwera z nieprzezroczystym tokenem (bez JWT) — równie dobra, ale zmieniałaby kontrakt `Authorization: Bearer` i weryfikator dla trybu dev; długi token dostępu bez odświeżania — dłuższe okno nadużycia przy wycieku.

## 5. Endpointy, uprawnienia i `must_change_password`

| Endpoint | Dostęp | Uwagi |
|---|---|---|
| `POST /auth/login` | publiczny (tylko `local`) | `PUBLIC_ENDPOINTS` |
| `POST /auth/refresh` | publiczny (tylko `local`) | `PUBLIC_ENDPOINTS` |
| `POST /auth/logout` | zalogowany (tylko `local`) | `SELF_ENDPOINTS`; dozwolony z hasłem tymczasowym |
| `POST /auth/password` | zalogowany (tylko `local`) | `SELF_ENDPOINTS`; dozwolony z hasłem tymczasowym |
| `GET /me` | zalogowany | `SELF_ENDPOINTS`; dozwolony z hasłem tymczasowym; pole `must_change_password` |
| `POST /users`, `POST /users/{id}/reset-password`, `PATCH /users/{id}` | `user.manage` (tylko `app_admin`) | nowa akcja w macierzy §5; montowane w obu trybach |

- Gdy `must_change_password`, każdy inny endpoint odpowiada 403 `auth.password_change_required` (i wpis `access_denied`, przyczyna `password_change_required`). Realizacja jawna, bez porównywania ścieżek: trzy powyższe endpointy używają zależności `get_current_user_pending_password_change`, wszystkie inne `get_current_user` (bezpośrednio albo przez `app.permissions`).
- **Hasło tymczasowe generuje serwer** (`POST /users`, reset): 20 znaków z CSPRNG, alfabet bez znaków mylących (0/O, 1/l/I), w grupach `xxxxx-xxxxx-xxxxx-xxxxx` (~113 bitów), zwracane **jednorazowo** w odpowiedzi (`no-store`), w bazie tylko skrót. Uzasadnienie: administrator nie wybiera (i nie zna z góry, nie powtarza) słabych haseł, nie ma kanału, w którym hasło od admina musiałoby być przyjęte i zwalidowane, a `must_change_password` wymusza zmianę przy pierwszym logowaniu. Pole `password` w `POST /users` jest odrzucane (422, `extra="forbid"`).
- Reset przez admina: nowe hasło tymczasowe, `must_change_password`, wyzerowanie licznika i `locked_until` (odblokowanie), odwołanie wszystkich sesji. Własnego hasła admin nie resetuje (409 `user.self_password_reset` — służy do tego `POST /auth/password` z obecnym hasłem).
- `PATCH /users/{id}`: `display_name`, `is_active`, `is_app_admin` (e-mail — login — nie jest tu edytowalny). Dezaktywacja odwołuje wszystkie sesje (wpis `deactivate`). Admin nie dezaktywuje ani nie odbiera roli sobie (409 `user.cannot_modify_self`), a ostatni aktywny `app_admin` nie może zostać dezaktywowany ani zdegradowany (409 `user.last_admin`). Wszyscy aktywni admini i cel są blokowani jednym zapytaniem `FOR UPDATE` posortowanym po `id` — dwóch adminów degradujących się nawzajem jest serializowanych, bez zakleszczenia.
- **Wygasanie hasła tymczasowego** (§12 p. 4): hasło tymczasowe (`POST /users`, reset, `create-admin --generate-password`) jest ważne `TEMP_PASSWORD_TTL_HOURS` (domyślnie 168 h = 7 dni) od nadania; termin zapisuje się przy nadaniu (`temp_password_expires_at`), więc zmiana zmiennej nie przesuwa terminów haseł już wydanych, a admin widzi dokładną datę.
  - Logowanie **poprawnym**, ale wygasłym hasłem tymczasowym → 401 `auth.temporary_password_expired` („Hasło tymczasowe wygasło. Poproś administratora o ponowne ustawienie hasła.”), bez sesji, wpis `login_failed` z przyczyną `temporary_password_expired`. Wygaśnięcie jest sprawdzane **dopiero po** poprawnej weryfikacji hasła (i po sprawdzeniu, że konto jest aktywne i niezablokowane) — bez hasła odpowiedź jest zwykłym `auth.invalid_credentials`, więc rozróżnienie nic nie zdradza. Nie jest to zgadywanie: nie zwiększa licznika blokady i nie liczy się do limitu z sieci (nie należy do `PASSWORD_GUESS_REASONS`); licznik nie jest też zerowany (sesja nie powstaje).
  - Sesja otwarta hasłem tymczasowym nie przeżyje terminu: jej `expires_at` = min(teraz + `AUTH_SESSION_MAX_HOURS`, termin hasła), a sprawdzenie sesji przy każdym żądaniu odrzuca sesję konta z wygasłym hasłem tymczasowym (401 `auth.session_expired` — także `POST /auth/password`). `POST /auth/refresh` po terminie → 401 `auth.temporary_password_expired`, sesja odwołana (`revoke_reason = temporary_password_expired`, wpis `session_revoke`) — ścieżka dla sesji sprzed migracji albo po skróceniu terminu. Przed terminem `POST /auth/password` działa normalnie i zeruje termin (nowa sesja ma pełną długość).
  - Reset przez admina nadaje nowe hasło z nowym terminem. `create-admin` z hasłem podanym przez operatora: hasło stałe, bez terminu. `create-admin --generate-password`: hasło tymczasowe z tym samym terminem (wypisane w terminalu — to ten sam powód wygasania); jeśli pierwszy admin nie zaloguje się w terminie, a nie ma innego admina, odzyskanie wymaga dziś operacji na bazie (rozważyć komendę CLI resetu).
- Odpowiedzi `/users` zawierają **stan** hasła (`has_password`, `must_change_password`, `password_changed_at`, `locked_until`, `temp_password_expires_at` — w przeszłości = hasło tymczasowe wygasło), nigdy skrót.

## 6. Logowanie, blokada, enumeracja, limit z sieci

- **Ta sama odpowiedź** 401 `auth.invalid_credentials` (identyczne ciało poza `request_id`) dla: nieznanego e-maila, złego hasła, konta bez hasła, konta zablokowanego (także z poprawnym hasłem — inaczej blokada zdradzałaby trafienie), konta nieaktywnego (także z poprawnym hasłem). Komunikat wspomina, że konto może być zablokowane lub nieaktywne.
- **Zbliżony czas:** nieznany e-mail i konto bez hasła są weryfikowane względem skrótu-atrapy o tych samych parametrach; konto zablokowane/nieaktywne też przechodzi weryfikację (wynik ignorowany). Test sprawdza, że ścieżka „brak konta” wykonuje pełną weryfikację argon2id.
- **Blokada konta:** `AUTH_LOCKOUT_THRESHOLD` (domyślnie 5) kolejnych złych haseł → `locked_until = teraz + AUTH_LOCKOUT_MINUTES` (domyślnie 15), licznik zerowany; próby w trakcie blokady jej nie przedłużają (ograniczenie DoS na cudze konto). Odblokowanie: upływ czasu albo reset przez admina. Udane logowanie zeruje licznik. Złe „obecne hasło” w `POST /auth/password` liczy się tak samo, a blokada z tej ścieżki dodatkowo **odwołuje wszystkie sesje** (ktoś z cudzą sesją zgaduje hasło). Konto zablokowane: `POST /auth/password` → 423 `auth.account_locked`.
- **Limit z sieci klienta (aplikacja):** blokada konta nie widzi rozpylania haseł po wielu kontach z jednego źródła. Liczniki istnieją już w `auth_failure_windows` (ADR 0010 §3, wspólne dla wszystkich procesów API), więc `POST /auth/login` odmawia 429 `auth.too_many_attempts` (+ `Retry-After` do końca okna), gdy sieć klienta (IPv4 /32, IPv6 /64) ma w bieżącym oknie ≥ `AUTH_LOGIN_MAX_FAILURES_PER_NETWORK` (domyślnie 30, 0 = wył.) nieudanych prób z przyczyn „zgadywania” (`unknown_email`, `invalid_password`, `no_password`, `account_locked`). Odpowiedź 429 nic nie mówi o koncie. Brak osobnego limitu „per konto” — byłby duplikatem blokady konta.
- **Granica z nginx (devops, Etap 8):** nginx ogranicza **liczbę żądań** per IP (np. `limit_req` na `/api/v1/auth/` i ogólnie) — chroni przed zalewem i kosztem argon2id, zanim żądanie dotrze do API. Aplikacja liczy **semantyczne porażki** (złe hasło, nieznany e-mail) per konto i per sieć oraz zapisuje je w audycie. Uwaga: limit aplikacji opiera się na adresie klienta, który API widzi tylko przez zaufany nginx (`FORWARDED_ALLOW_IPS`, ADR 0004).
- **Pule połączeń:** logowanie i odświeżanie działają w osobnych transakcjach (porażka musi zostać zapisana mimo błędu odpowiedzi) z **głównej** puli (`run_in_separate_transaction(main_pool=True)`, wolno tylko bez transakcji zewnętrznej) — zalew logowań nie może wyczerpać małej puli pomocniczej, której potrzebuje każde uwierzytelnione żądanie (ADR 0010 §5). Kolejność blokad: wiersz `user_credentials`/sesji → kubeł porażek → głowa łańcucha globalnego (nigdy odwrotnie).

## 7. Audyt (łańcuch globalny)

| Zdarzenie | `entity_type`/`action` | Aktor | Kontekst / diff |
|---|---|---|---|
| zalogowanie | `auth`/`login` | użytkownik | `method=password`, `session_id`, `session_expires_at`, `must_change_password`, `password_rehashed` |
| nieudane logowanie | `auth`/`login_failed` (agregacja ADR 0010 §3) | `system` (`authenticated=false`); `entity_id` = konto, jeśli znane | `reason`: `unknown_email` (bez e-maila — użytkownicy wpisują tam hasła), `invalid_password`, `no_password`, `account_locked`, `user_inactive`, `rate_limited`, `invalid_refresh_token`, `session_invalid`, `temporary_password_expired` (poprawne hasło tymczasowe po terminie / odświeżenie sesji po terminie); `invalid_current_password` z aktorem = użytkownik |
| blokada | `user`/`lockout` | `system` | diff `locked_until`; `trigger` (`login`/`password_change`), `threshold`, `lockout_minutes`, `sessions_revoked` |
| odnowienie tokenów | `auth`/`token_refresh` | użytkownik | `session_id` |
| ponowne użycie tokenu odświeżania | `auth`/`session_revoke` | `system` | `session_id`, `reason=refresh_token_reuse`, `token_rotated_at` |
| odświeżenie sesji po terminie hasła tymczasowego | `auth`/`session_revoke` | `system` | `session_id`, `reason=temporary_password_expired`, `temp_password_expires_at` |
| wylogowanie | `auth`/`logout` | użytkownik | `session_id`, `already_revoked` |
| zmiana hasła | `user`/`password_change` | użytkownik | diff `password_changed_at`, `must_change_password`, `temp_password_expires_at`; `sessions_revoked`, `new_session_id` |
| reset hasła | `user`/`password_reset` | admin | diff stanu hasła (`has_password`, `must_change_password`, `password_changed_at`, `failed_attempts`, `locked_until`, `temp_password_expires_at`); `sessions_revoked`, `temporary_password_issued` |
| założenie konta | `user`/`create` | admin albo `system` (CLI) | diff profilu + stanu hasła; `source` (`admin`/`cli`), `temporary_password_issued` |
| zmiana / dezaktywacja | `user`/`update` / `deactivate` | admin | diff profilu; `sessions_revoked` przy dezaktywacji |

- **Definicja „logowania” dla kont lokalnych** (doprecyzowanie ADR 0010 §1): zdarzenie `login` zapisuje `POST /auth/login` (raz na sesję). Żądania z tokenem dostępu nie tworzą już wpisu „pierwszego użycia tokenu” — każdy token dostępu powstaje z zapisanego zdarzenia (`login`, `token_refresh`, `password_change`). W trybie dev zostaje dotychczasowa definicja (pierwsze żądanie z tokenem). Koszt: ok. 4 wpisy `token_refresh` na godzinę aktywnej sesji przy domyślnych 15 min.
- **Bez sekretów:** `audit.record` odrzuca (błąd programistyczny `AuditError`) diff/kontekst zawierający na dowolnej głębokości klucz `password`, `password_hash`, `new_password`, `current_password`, `temporary_password`, `access_token`, `refresh_token`, `token_hash`, `secret`. Testy sprawdzają, że w wpisach nie ma `$argon2`, haseł (także tymczasowych) ani tokenów.
- Każdy endpoint modyfikujący tworzy ≥ 1 wpis: `/users*` w ogólnym teście macierzy (`test_every_modifying_endpoint_writes_audit`), `/auth/*` (publiczne/self, tylko w trybie `local`) w `test_every_local_auth_endpoint_writes_audit_without_secrets`.

## 8. Pierwszy administrator i seed

- `python -m app.cli create-admin --email … --name …` (tylko `AUTH_MODE=local`): hasło **nigdy z argumentu** (historia powłoki, lista procesów) — z terminala dwukrotnie (ukryte, `getpass`) albo jedna linia ze standardowego wejścia (automatyzacja: `… < plik` / potok z menedżera sekretów); walidowane polityką. `--generate-password`: hasło tymczasowe wypisane raz, zmiana przy pierwszym logowaniu. Aktor `system`, `context.source = cli`, `os_user`, `host`. Działa jako `app_rw` przez ten sam serwis co `POST /users`.
- `python -m app.cli seed` (tylko `APP_ENV=dev`) — jak dotąd: użytkownicy `dev-*` bez haseł (logowanie przez `AUTH_MODE=dev`).

## 9. Konfiguracja (opisana w `.env.example`)

`AUTH_MODE` (`local`|`dev`, domyślnie `local`), `AUTH_JWT_SECRET`, `AUTH_ACCESS_TOKEN_MINUTES` (15), `AUTH_REFRESH_IDLE_MINUTES` (120), `AUTH_SESSION_MAX_HOURS` (12), `AUTH_LOCKOUT_THRESHOLD` (5), `AUTH_LOCKOUT_MINUTES` (15), `AUTH_LOGIN_MAX_FAILURES_PER_NETWORK` (30), `TEMP_PASSWORD_TTL_HOURS` (168, §12 p. 4). Usunięte: `OIDC_ISSUER`, `OIDC_AUDIENCE`, `OIDC_CLIENT_ID`, `OIDC_JWKS_GRACE_SECONDS`. `docker-compose.yml`: domyślnie `AUTH_MODE=local`, przekazuje nowe zmienne.

## 10. Kontrakt dla frontendu (skrót)

- `POST /auth/login {email, password}` → 200 `{access_token, token_type:"Bearer", expires_in, refresh_token, refresh_expires_in, session_expires_at, must_change_password}`; 401 `auth.invalid_credentials`; 401 `auth.temporary_password_expired` (poprawne hasło tymczasowe po terminie — komunikat „poproś administratora o reset hasła”, bez sesji); 429 `auth.too_many_attempts` (`Retry-After`); 422 walidacja.
- `POST /auth/refresh {refresh_token}` → 200 jak wyżej (nowy refresh token — stary jest od tej chwili nieważny); 401 `auth.invalid_refresh_token` → ekran logowania; 401 `auth.temporary_password_expired` (sesja z hasłem tymczasowym po jego terminie — sesja odwołana) → ekran logowania z tym komunikatem.
- Każde żądanie: 401 `auth.invalid_token` (np. wygasły token dostępu) → jedno (single-flight) `refresh` i powtórzenie żądania; 401 `auth.session_expired` lub nieudany refresh → logowanie; 403 `auth.password_change_required` → formularz zmiany hasła.
- `POST /auth/password {current_password, new_password}` → 200 nowa para tokenów (wszystkie poprzednie sesje, także bieżąca, są zakończone); 400 `auth.invalid_current_password`; 422 `auth.password_*`; 423 `auth.account_locked`.
- `POST /auth/logout` (Bearer) → 204.
- `GET /me` → `must_change_password`.

## 11. Testy

`tests/test_passwords.py` (polityka, argon2id, NFKC, rehash, atrapa, hasła tymczasowe), `tests/test_local_auth.py` (logowanie i identyczne odpowiedzi, blokada i odblokowanie, limit z sieci, rotacja i wykrycie ponownego użycia, wylogowanie, wygasły token odświeżania, hasło tymczasowe ogranicza dostęp, wygasanie hasła tymczasowego (logowanie, sesja, odświeżenie, reset, termin w `/users`), polityka przy zmianie, złe obecne hasło → blokada + odwołanie sesji, 423, zakładanie konta i jednorazowe hasło, reset przez admina, dezaktywacja, ostatni admin, RBAC, audyt bez sekretów, strażnik sekretów w `audit.record`, triggery, sprzątanie, CLI `create-admin`), `tests/test_auth_tokens.py` (weryfikator lokalny, rozdzielność z dev, algorytmy), `tests/test_config.py` (tryby, siła klucza, dev zabroniony w prod), `tests/test_rbac_matrix.py` (nowe endpointy w pełnej macierzy i teście audytu; trasy zależne od trybu), `tests/test_db_roles.py` (uprawnienia kolumnowe, downgrade).

## 12. Decyzje właściciela (2026-11-04)

Wszystkie rekomendacje przyjęte:

1. Domyślne wartości **bez zmian**: token dostępu 15 min, bezczynność 120 min, sesja 12 h, blokada 5 prób / 15 min, limit sieci 30 porażek / 5 min.
2. `PATCH /users/{id}` **może** nadawać i odbierać `is_app_admin` (jak zaimplementowano: z ochroną przed zmianą siebie i ostatniego aktywnego admina, z wpisem audytu); CLI pozostaje drogą dla pierwszego admina.
3. **Bez** zmiany e-maila (loginu) przez admina — jak dotąd (nowy e-mail = nowe konto, stare dezaktywowane).
4. Hasło tymczasowe **wygasa po 7 dniach** (`TEMP_PASSWORD_TTL_HOURS`, domyślnie 168) — wdrożone, szczegóły w §5 (wygasanie), §2 (migracja 0011), §7, §10.
5. **Bez MFA** (uwierzytelniania wieloskładnikowego) — także dla `app_admin`. Ryzyko (ISO/IEC 27001:2022 A.8.5: przejęte hasło administratora daje kontrolę nad kontami i rolami) właściciel **świadomie akceptuje** (decyzja z 2026-11-04, po recenzji Etapu 8). Środki kompensujące: polityka haseł (§3), blokada konta i limit sieci (§6), krótki token dostępu i limity sesji, odwołanie sesji przy resecie/dezaktywacji, rozdział obowiązków (admin nie jest automatycznie editorem/approverem), pełny audyt zdarzeń kont i ról w łańcuchu globalnym, dostęp wyłącznie przez TLS. TOTP dla administratorów może zostać dodane w kolejnym etapie bez zmiany modelu kont (osobna tabela sekretów, osobny ADR).
