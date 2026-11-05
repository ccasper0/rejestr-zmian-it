# 0007. Uwierzytelnianie, kontekst spółki i jawna ścieżka administratora

- Status: przyjęta (punkty „do potwierdzenia” czekają na właściciela projektu); §1 (OIDC) i §2 (JIT, synchronizacja profilu) zastąpione przez ADR 0018 — konta lokalne z hasłem (2026-11-03)
- Data: 2026-10-28
- Dotyczy: CLAUDE.md §2, §4.1, §5, §6.5, §7, §8; `backend/app/auth/`, `backend/app/permissions.py`, `backend/app/db.py`, migracja `0002`

## 1. Tryby uwierzytelniania

- `AUTH_MODE=oidc`: token Bearer RS256, klucze z JWKS wskazanego w `{OIDC_ISSUER}/.well-known/openid-configuration` (dokument discovery musi podawać ten sam `issuer`). Sprawdzane: podpis, `iss`, `aud = OIDC_AUDIENCE`, `exp`, `nbf` (tolerancja zegara 60 s), wymagane `exp`, `sub`, `iss`, `aud` i nagłówek `kid`. Klucze w cache 1 h. Nieznany `kid` wymusza jedno odświeżenie JWKS, nie częściej niż raz na 60 s (losowe `kid` nie zasypią IdP). Błąd pobrania kluczy daje 503 `auth.provider_unavailable`, nie 401.
- `AUTH_MODE=dev`: token HS256 podpisany `DEV_AUTH_SECRET` (min. 32 znaki, wymagany w trybie dev, `SecretStr`). `iss = urn:rejestr:dev-auth`, `aud = urn:rejestr:api`, ważność 8 h. Endpointy `GET /auth/dev/users` i `POST /auth/dev/token` są montowane wyłącznie w trybie dev (poza nim 404, bo trasy nie istnieją). Tryb dev przy `APP_ENV=prod` jest odrzucany już w `Settings`.
- Każdy weryfikator akceptuje dokładnie jeden algorytm, więc token dev nie przejdzie w trybie OIDC i odwrotnie (test). Oba tryby obsługuje ta sama zależność `get_current_user`.
- Brak `OIDC_ISSUER`/`OIDC_AUDIENCE` przy `AUTH_MODE=oidc`: API odmawia startu w `lifespan`, a nie przy imporcie `app.main`, bo import nie może wymagać dostawcy tożsamości (testy, narzędzia).
- Mapowanie claimów: `external_id = sub`; `email` z `email`, potem `preferred_username`, potem `upn` (Entra ID często nie wysyła `email`); `display_name` z `name`, potem e-mail, potem `sub`.

## 2. Provisioning JIT (OIDC)

- Pierwszy poprawny token nieznanego `sub` tworzy `users` (bez ról, `is_app_admin = false`). Robi to `INSERT … ON CONFLICT (external_id) DO NOTHING`: równoległe pierwsze żądania nie tworzą duplikatu, a wpis audytu powstaje tylko w transakcji, która faktycznie wstawiła wiersz.
- **Aktor wpisu audytu to sam użytkownik** (jego `id` i nazwa z tokenu, role puste), nie `system`. Zdarzenie wywołała uwierzytelniona tożsamość, za którą poręczył IdP, a `request_id` i IP wiążą wpis z żądaniem. Wpis trafia do łańcucha globalnego: `entity_type = user`, `action = create`, `context = {"source": "oidc_jit", "issuer": …}`.
- Zmiana `email`/`display_name` w kolejnych tokenach aktualizuje profil (`action = update`, `context.source = oidc_profile_sync`), bo `actor_display` w kolejnych wpisach ma odzwierciedlać aktualną nazwę.
- **JIT i synchronizacja profilu działają w osobnej, krótkiej transakcji, zatwierdzanej przed transakcją biznesową żądania** (`app.db.run_in_separate_transaction`, `users.resolve_identity`). Poprawka po recenzji Etapu 1. Pierwotnie działały w transakcji żądania i trzymały głowę łańcucha **globalnego** do COMMIT, a endpoint blokował potem wiersz spółki i łańcuch spółki. To odwrotna kolejność niż w ADR 0006 §7, a recenzent odtworzył `deadlock detected` (admin ze zmienionym `name` w tokenie robi `PUT /companies/C/members/U`, równolegle inny admin `PATCH /companies/C`).
- Konsekwencje:
  - utworzenie użytkownika lub zmiana profilu i ich wpisy audytu są zatwierdzane **niezależnie od wyniku żądania**. Żądanie zakończone błędem (np. 404) ich nie wycofuje. To zamierzone: IdP poręczył za tożsamość, zdarzenie miało miejsce, a w dzienniku i tak muszą trafić zdarzenia nieudanych żądań (Etap 2);
  - kolejne żądania z tym samym tokenem zastają aktualny profil. Nie ma ponownej synchronizacji ani kolejnego wpisu przy każdym żądaniu (test);
  - synchronizacja bez zmian nie zakłada blokad (porównanie bez `FOR UPDATE`). Przy zmianie wiersz `users` jest ponownie czytany z `FOR UPDATE`, więc równoległe żądania z tym samym nowym profilem dają **jeden** wpis `update` (test). Równoległe pierwsze logowania dają jednego użytkownika i jeden wpis `create` (test);
  - na każde uwierzytelnione żądanie przypadają dwie transakcje (krótka tożsamości, potem biznesowa). Ta pierwsza wykonuje się, zanim sesja żądania użyje połączenia, więc żądanie nie trzyma dwóch połączeń z puli naraz;
  - `resolve_identity` odmawia działania poza sesją otwartą przez helper. Ten sam helper służy w Etapie 2 do zdarzeń `login`/`login_failed`/`access_denied` (`app/auth/events.py`).
- W trybie dev nie ma JIT: token dla nieistniejącego `external_id` daje 401, a `/auth/dev/token` zwraca 404 `auth.dev_user_not_found`.
- `is_active = false` daje 403 `auth.user_inactive`. Brak lub niepoprawny token daje 401 `auth.invalid_token` z nagłówkiem `WWW-Authenticate: Bearer`.

## 3. Zakres transakcji (zmienne sesji dla RLS)

Poza odczytem/JIT/synchronizacją użytkownika (osobna transakcja, pkt 2) `get_current_user` działa w tej samej transakcji co cały endpoint (`SessionDep` jest buforowany przez FastAPI na żądanie, co sprawdza test) i ustawia przez `set_config(..., true)`:

| Zmienna | Kiedy | Wartość |
|---|---|---|
| `app.user_id` | zaraz po załadowaniu użytkownika, **przed** odczytem członkostw | UUID użytkownika |
| `app.company_ids` | po odczycie członkostw | spółki z co najmniej jedną rolą |
| `app.audit_global_read` | j.w. | `on` wyłącznie dla admina aplikacji (ADR 0006 §6; audytor czyta tylko łańcuchy swoich spółek) |
| `app.admin_scope` | j.w. | `off`; `on` tylko na ścieżce administratora (pkt 4) |

## 4. Jawna ścieżka administratora (§7 pkt 2)

- `app_admin` **nie** dostaje kontekstu rejestru spółki bez członkostwa (§5). `require_company(action)` zwraca 404 także adminowi. (Wyjątek — wąskie ścieżki tylko do odczytu: dziennik audytu spółki, ADR 0015 §7, i podgląd rejestru zmian, ADR 0016.)
- Ścieżka administracyjna jest deklarowana jawnie przy endpoincie:
  - `require(action)`: akcja globalna (spółki, słowniki, użytkownicy). Gdy przejdzie, ustawia `app.admin_scope = on`.
  - `require_admin_company(action)`: akcja administracyjna na jednej spółce (PATCH, archiwizacja, role). Najpierw sprawdzenie globalne (inaczej 403), potem spółka (jeśli nie istnieje, 404).
  - `require_company(action, admin_action=...)`: admin z prawem do `admin_action` wchodzi ścieżką administracyjną, pozostali przez członkostwo (np. `GET /companies/{id}/members`).
  - `visible_companies(action, admin_action=...)`: listy (`GET /companies`, admin widzi wszystkie).
- Na ścieżce administracyjnej dla konkretnej spółki zakres transakcji jest **poszerzany o tę spółkę** (`app.company_ids` + spółka docelowa) i ustawiane jest `app.admin_scope = on`. Bez tego istniejące polityki RLS `audit_log`/`audit_chain_heads` (migracja 0001) odrzuciłyby wpis `role_grant` w łańcuchu spółki, w której admin nie ma roli. Poszerzenie dotyczy tylko jednej transakcji jednego endpointu administracyjnego.
- Kody: dla endpointów wyłącznie administracyjnych użytkownik bez uprawnienia dostaje 403 niezależnie od istnienia zasobu (odpowiedź nie zależy od zasobu, więc nic nie ujawnia). Dla endpointów członkowskich brak członkostwa daje 404 (§7.3).

### Propozycja polityk dla fazy C (RLS)

Zrealizowane w migracji 0003. Ostateczne polityki, zaostrzenie UPDATE spółki i decyzja dla `users` są w ADR 0008.

- `companies`: SELECT `USING (id = ANY (app_company_ids()) OR app_admin_scope())`; INSERT/UPDATE `WITH CHECK (app_admin_scope())`.
- `company_memberships`: SELECT `USING (user_id = app_user_id() OR company_id = ANY (app_company_ids()) OR app_admin_scope())`; INSERT/UPDATE/DELETE tylko `app_admin_scope() AND company_id = ANY (app_company_ids())`.
- `users`: bez `company_id`, więc §7 nie wymaga RLS. Odczyt po `external_id` musi działać **przed** ustaleniem tożsamości (logowanie). Jeśli faza C doda RLS, polityka musi to dopuszczać, a INSERT (JIT) musi pozostać możliwy bez `admin_scope`.
- Funkcje pomocnicze `app_user_id()` i `app_admin_scope()` (analogiczne do `app_company_ids()`) dodaje faza C. Nazwy zmiennych sesji powyżej są kontraktem.
- `GET /auth/dev/users` i `POST /auth/dev/token` czytają `users` bez uwierzytelnienia (tylko tryb dev).

## 5. Deklaracje uprawnień

- Każda trasa deklaruje `AccessRule` przez jedną z powyższych zależności albo jest na liście `PUBLIC_ENDPOINTS` (`/health`, `/auth/dev/*`) lub `SELF_ENDPOINTS` (`/me`). Test introspekcji przechodzi po wszystkich trasach (`fastapi.routing.iter_route_contexts`, bo FastAPI 0.162 dołącza routery leniwie).
- **Do potwierdzenia:** `GET /me` nie deklaruje akcji z macierzy §5. Zwraca wyłącznie dane wywołującego i musi działać także dla użytkownika bez ról (świeżo utworzonego przez JIT). Nie wymyślamy dla niego nowej akcji, stąd osobna lista `SELF_ENDPOINTS`.
- `GET /companies` deklaruje `register.view` (filtr: spółki, w których użytkownik ma jakąkolwiek rolę) z `admin_action = company.manage` (admin widzi wszystkie).

## 6. Audyt spółek, użytkowników i ról

- Spółki (`create`, `update`, `archive`) i użytkownicy (`create`, `update`) trafiają do łańcucha **globalnego**. Członkostwa trafiają do łańcucha **spółki**: `entity_type = membership`, `entity_id = user_id`, `action = role_grant` lub `role_revoke` (osobny wpis na nadanie i na odebranie, każdy z diffem `roles` przed → po), w `context` są `user_id`, `user_display`, `granted`/`revoked` i `self_grant`.
- PUT z niezmienionym zestawem ról i PATCH bez faktycznej zmiany niczego nie modyfikują, więc nie tworzą wpisu.
- Zmiany ról w jednej spółce są serializowane przez `SELECT … FOR UPDATE` na wierszu spółki, dzięki czemu diff przed → po jest spójny.
- Seed działa przez serwisy jako aktor `system`, w trzech transakcjach, które nie mieszają łańcuchów: (1) globalny, (2) spółek, (3) globalny. Kolejność blokad z ADR 0006 §7 nie może więc zostać naruszona.

## 7. Dane

- `app_rw` nie ma `DELETE` na `companies` i `users`: spółki się archiwizuje, użytkowników dezaktywuje (wpisy audytu wskazują je po `id`). `company_memberships` zachowuje `DELETE`, bo odebranie roli usuwa wiersz, a ślad zostaje w audycie.
- `companies.prefix`: CHECK `^[A-Z]{2,8}$`, UNIQUE oraz trigger `BEFORE UPDATE OF prefix` (`23001`, także dla właściciela). Serwis odrzuca zmianę wcześniej, kodem 422 `company.prefix_immutable`.
- Nazwa spółki jest unikalna bez względu na wielkość liter (sprawdza serwis; w bazie UNIQUE rozróżnia wielkość liter). NIP jest normalizowany do 10 cyfr z kontrolą sumy.
- **Do potwierdzenia:** `default_approver_id` musi wskazywać aktywnego użytkownika, ale nie musi mieć roli `approver` w spółce. Przy tworzeniu spółka nie ma jeszcze członków. Czy zatwierdzający ma właściwą rolę, sprawdzi `readiness` w Etapie 4.
- **Do potwierdzenia:** zarchiwizowana spółka pozostaje widoczna dla członków (historia, audyt), a admin może ją edytować i zmieniać w niej role. Blokada tworzenia zmian/CI w zarchiwizowanej spółce należy do Etapów 3–4.
