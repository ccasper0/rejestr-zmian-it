# 0020. Frontend: logowanie kontami lokalnymi, odświeżanie tokenów, konta w administracji (Etap 8)

- Status: przyjęta (decyzja właściciela 2026-11-04 — §8)
- Data: 2026-11-03
- Dotyczy: CLAUDE.md §10, §12 (Etap 8); `frontend/lib/{core/api_client.dart, core/auth/auth.dart, core/api_error.dart, core/service_notice.dart, core/session.dart, app/router.dart, app/app.dart, features/auth/*, features/admin/presentation/{users_page,account_dialogs}.dart, features/changes/presentation/attachments_section.dart, widgets/app_shell.dart}`; zastępuje część OIDC ADR 0014 §1; kontrakt: ADR 0018 §10, ADR 0019 §8

## 1. Tryby i usunięcie OIDC

- `OidcAuthProvider`, `AuthMethod.oidc`, `AuthModeSetting.oidc` usunięte. Tryby: `DevAuthProvider` (bez zmian) i `LocalAuthProvider` (`POST /auth/login`).
- Wykrywanie bez zmian (ADR 0014 §1): `GET /auth/dev/users` → 200 dev, 404 → konta lokalne; inny błąd → „Spróbuj ponownie”. `--dart-define=AUTH_MODE=dev|local` wymusza tryb; każda inna wartość (także dawne `oidc`) = `auto`.

## 2. Sesja i tokeny

- `AuthToken` przechowuje (pamięć + `sessionStorage`, klucz `rejestr.auth`, ADR 0014 §1): token dostępu i jego koniec, token odświeżania, jego wygaśnięcie z bezczynności (`refresh_expires_in`), bezwzględny koniec sesji (`session_expires_at`) i `must_change_password`. Odtworzenie po przeładowaniu przyjmuje wygasły token dostępu, jeśli sesję da się jeszcze odświeżyć.
- `AuthState.epoch` zmienia się przy każdej nowej sesji (logowanie, zmiana hasła, wylogowanie), ale nie przy odświeżeniu tokenów. `GET /me` jest kluczowany epoką, nie tokenem dostępu — inaczej co 15 min cała aplikacja przeładowywałaby dane.

## 3. Klient HTTP (`AuthInterceptor`)

- Bearer do każdego żądania poza publicznymi `/auth/login`, `/auth/refresh`, `/auth/dev/*` (ich odpowiedzi nie są też interpretowane jako koniec sesji).
- Odświeżanie: **proaktywne** (token dostępu traktowany jako wygasły minutę przed końcem → `refresh` przed wysłaniem żądania) i **reaktywne** (401 `auth.invalid_token` → jedno odświeżenie i jedno powtórzenie żądania; ponowne 401 kończy sesję). Body multipart jest przy powtórzeniu klonowane.
- **Single-flight w karcie:** jedno `POST /auth/refresh` naraz; pozostałe żądania czekają na jego wynik. Żądanie, które dostało 401 z tokenem już zastąpionym, nie odświeża ponownie (użyłoby zrotowanego tokenu — backend uznałby to za kradzież), tylko powtarza się z bieżącym tokenem. Między kartami nie ma koordynacji — każda karta ma własną sesję (`sessionStorage`).
- Odmowa odświeżenia (4xx poza 429, w tym 401 `auth.invalid_refresh_token`) → logowanie z komunikatem. Błąd sieci, 429, 5xx → sesja zostaje, żądanie kończy się błędem (użytkownik ponawia).
- 401 `auth.session_expired` → logowanie („Sesja wygasła lub została zakończona”); inne 401 → „Sesja wygasła”; 403 `auth.user_inactive` → logowanie („Twoje konto jest nieaktywne”); 403 `auth.password_change_required` → flaga `must_change_password`.
- Testy jednostkowe na rzeczywistym okablowaniu providerów (`test/core/auth_interceptor_test.dart`), w tym równoległe 401 → dokładnie jedno odświeżenie (sprawdzone mutacją: bez blokady test nie przechodzi).

## 4. Wymuszona zmiana hasła

- Źródła flagi: odpowiedź login/refresh/password, `GET /me` (serwer rozstrzyga — wartość z `/me` nadpisuje lokalną) i 403 `auth.password_change_required`.
- Router: zalogowany z flagą → każdy adres przekierowuje do `/account/password?from=…` (cel po zalogowaniu jest zachowany). Strona jest poza powłoką aplikacji (powłoka pobiera dane, które przy haśle tymczasowym dają 403). Wymuszona: tylko „Zmień hasło” i „Wyloguj”; dobrowolna (menu konta): „Anuluj”. Strażnik niezapisanego formularza zmiany przepuszcza wyjście przy wymuszonej zmianie (zapis i tak dałby 403).
- Sukces `POST /auth/password` = nowa sesja (`signIn`, nowa epoka, `/me` od nowa), powrót pod `from`.
- Walidacja w UI tylko jako UX: 12–128 znaków (punkty kodowe), potwierdzenie, różne od obecnego; reszta polityki opisana słownie. Błędy API przy polach: 400 `auth.invalid_current_password` (obecne), 422 `auth.password_*` (nowe); 423/409 — baner.

## 5. Administracja kont

- Katalog: kolumna „Stan konta” (nieaktywne, administrator, hasło ustawione / brak hasła, wymaga zmiany hasła, zablokowane do `dd.MM.yyyy HH:mm` Europe/Warsaw — tylko gdy `locked_until` w przyszłości) i „Nowy użytkownik” (e-mail, nazwa, administrator aplikacji; `POST /users` wywoływany z dialogu, więc 409 `user.email_taken` jest przy polu).
- Karta użytkownika, sekcja „Konto”: zmiana nazwy, reset hasła (potwierdzenie), dezaktywacja (potwierdzenie) / aktywacja, nadanie i odebranie uprawnień administratora (potwierdzenie obu). Własne konto: reset, dezaktywacja i odebranie roli administratora nieaktywne z wyjaśnieniem (backend i tak zwraca 409).
- Hasło tymczasowe: dialog bez zamykania kliknięciem w tło, ostrzeżenie „wyświetlane tylko raz”, `SelectableText` w IBM Plex Mono i „Kopiuj” (schowek). Hasło żyje wyłącznie w stanie tego dialogu — nie trafia do providerów, `sessionStorage`, logów ani komunikatów błędów.

## 6. Kody ADR 0019

- `ApiProblem` czyta `Retry-After` (sekundy) i buduje komunikaty: 429 `request.rate_limited` / `auth.too_many_attempts` („Spróbuj ponownie za 30 s / 2 min”), 413 `attachment.too_large` (limit w MB z `max_bytes`), 415 `attachment.type_not_allowed` (wykryty typ i lista dozwolonych z `allowed_types` z polskimi nazwami — odwzorowanie `LABELS` z `app/services/file_types.py`).
- 429 `request.rate_limited` i 503 `api.unavailable` z dowolnego niepublicznego żądania → pasek komunikatu dla całej aplikacji (root `ScaffoldMessenger`), najwyżej jeden na kod na 10 s. Ekrany dodatkowo pokazują błąd jak dotąd.
- Błąd wysyłania załącznika jest pokazywany przy przycisku (baner z nazwą pliku), nie w znikającym pasku — lista dozwolonych typów jest długa.

## 7. Uwagi do kontraktu (backend bez zmian w tym etapie)

1. **CORS nie udostępnia `Retry-After`** (`expose_headers` w `backend/app/main.py`): przy pracy na innym originie (`flutter run` na :5000) przeglądarka ukrywa nagłówek — komunikat bez czasu, formularz logowania blokuje się na domyślne 30 s. Przez nginx (ten sam origin) działa. Propozycja: dopisać `Retry-After` do `expose_headers`.
   **Zrealizowane** (commit c5274c4): `Retry-After` jest w CORS `expose_headers`, odliczanie działa także przy innym originie.
2. `POST /auth/login` odpowiada 422 `request.validation_error` dla e-maila dłuższego niż 254 znaki lub hasła > 1024 znaki — UI pokazuje ogólny komunikat walidacji.

## 8. Decyzje właściciela (2026-11-04)

Oba punkty zostają tak, jak zaimplementowano:

1. Komunikat 429/503 pokazywany w dwóch miejscach — pasek dla całej aplikacji oraz błąd na ekranie, który wywołał żądanie.
2. Potwierdzenie przy **nadaniu** (i odebraniu) uprawnień administratora; aktywacja konta bez potwierdzenia.

## 9. Wygasanie hasła tymczasowego (ADR 0018 §12 p. 4)

Backend ogranicza ważność hasła tymczasowego (`TEMP_PASSWORD_TTL_HOURS`, domyślnie 7 dni). Frontend:

1. `POST /auth/login` → 401 `auth.temporary_password_expired`: ekran logowania pokazuje „Hasło tymczasowe wygasło. Poproś administratora o ponowne ustawienie hasła.”.
2. `POST /auth/refresh` → ten sam kod: `AuthInterceptor` kończy sesję z tym komunikatem na ekranie logowania (zamiast ogólnego „Sesja wygasła…”). Wygaśnięcie samej sesji przy terminie (401 `auth.session_expired`) obsługuje dotychczasowa ścieżka.
3. `UserOut.temp_password_expires_at` (nullable, ustawione dokładnie przy `must_change_password`) — model `tempPasswordExpiresAt`. Etykiety stanu konta (lista i karta użytkownika): przed terminem „Wymaga zmiany hasła” + „ważne do dd.MM.yyyy HH:mm” (Europe/Warsaw); od terminu (termin włącznie) „Hasło tymczasowe wygasło” (wyróżnienie jak blokada).
4. Okno z jednorazowym hasłem pokazuje termin ważności z `user.temp_password_expires_at` odpowiedzi `POST /users` / `reset-password`; gdy pola brak — „ważne 7 dni”.
