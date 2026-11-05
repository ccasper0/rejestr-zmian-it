# 0019. Utwardzenie infrastruktury i backendu (Etap 8, część 2)

- Status: przyjęta (decyzja właściciela 2026-11-04 — §9)
- Data: 2026-11-03
- Dotyczy: CLAUDE.md §2, §6.3, §8, §11, §12 (Etap 8); `deploy/nginx/templates/**`, `frontend/Dockerfile`, `docker-compose.yml`, `.env.example`, `backend/app/{logs.py, services/file_types.py, services/attachments.py, config.py, main.py, permissions.py, worker.py}`, `scripts/{backup,restore}.{sh,ps1}`, `deploy/backup/backup-loop.sh`, `docs/deployment.md`, `.github/workflows/ci.yml`; ADR 0004, ADR 0010, ADR 0013 §4, ADR 0018

Logowanie kontami lokalnymi (ADR 0018) jest osobną częścią Etapu 8; ten ADR dotyczy wyłącznie warstwy infrastruktury, nagłówków, limitów, logów i kopii.

## 1. Rate limiting — w nginx, nie w API

- `limit_req` per IP klienta (`$binary_remote_addr`), trzy strefy: `api` (całe `/api/`, domyślnie 20 r/s, seria 100), `auth` (`/api/v1/auth/login`, `/auth/password`, `/auth/dev/token`; 10 r/min, seria 10), `refresh` (`/api/v1/auth/refresh`; 30 r/min, seria 20) + `limit_conn` 50 połączeń na IP. Wartości: zmienne `NGINX_*` (szablon nginx, `envsubst` obrazu nginx ograniczony filtrem `^NGINX_`, domyślne w `frontend/Dockerfile` i `docker-compose.yml`).
- Odpowiedź 429 w formacie API: `application/problem+json`, `code = request.rate_limited`, tytuł „Zbyt wiele żądań”, `Retry-After`, `X-Request-ID`. Analogicznie błędy generowane przez samego nginx: 413 (`attachment.too_large`, ciało powyżej `NGINX_CLIENT_MAX_BODY_SIZE`) i 502/503/504 → 503 `api.unavailable`. `error_page` nie dziedziczy się do `location` z własnymi `error_page` — snippet proxy deklaruje je ponownie (test statyczny).
- Dlaczego nginx: jeden punkt dla wszystkich procesów API (bez Redisa w ścieżce żądania), odrzucenie przed aplikacją i bazą. Limity per IP nie zastępują blokady konta po nieudanych logowaniach (ADR 0018) ani agregacji `login_failed` w audycie (ADR 0010) — to trzy różne warstwy.
- Ograniczenie: użytkownicy za jednym NAT-em dzielą limit; za proxy TLS bez `NGINX_TRUSTED_PROXIES` wszyscy mają IP proxy. Opisane w `docs/deployment.md` §7.

## 2. Nagłówki bezpieczeństwa i CSP

- Wszystkie odpowiedzi: `X-Content-Type-Options: nosniff`, `Referrer-Policy: same-origin`, `X-Frame-Options: DENY`, `Cross-Origin-Opener-Policy: same-origin`, `Cross-Origin-Resource-Policy: same-origin`, `Permissions-Policy` (kamera, mikrofon, geolokalizacja, płatności, USB, … wyłączone). Snippet `security-headers.inc` jest dołączany w każdej `location` z własnym `add_header` (nginx nie dziedziczy wtedy nagłówków z poziomu `server`) — test statyczny.
- HSTS: `Strict-Transport-Security "${NGINX_HSTS}"` — domyślnie pusty = nagłówek nie jest wysyłany (nginx pomija `add_header` z pustą wartością). Włączany jawnie, gdy TLS kończy proxy przed `web` (`docs/deployment.md` §5). Kontener nie terminuje TLS sam.
- CSP aplikacji: `default-src 'self'; script-src 'self' 'wasm-unsafe-eval'; style-src 'self' 'unsafe-inline'; img-src 'self' data: blob:; font-src 'self' data:; connect-src 'self' [NGINX_CSP_CONNECT_EXTRA]; worker-src 'self' blob:; manifest-src 'self'; object-src 'none'; frame-src 'none'; base-uri 'self'; form-action 'self'; frame-ancestors 'none'`.
  - Build: `flutter build web --release --csp --no-web-resources-cdn` (Flutter 3.47.5). `--no-web-resources-cdn` → `"useLocalCanvasKit":true` w `flutter_bootstrap.js`, CanvasKit (`canvaskit/*.js|wasm`) z tego samego originu, bez `gstatic.com`. `--csp` → dart2js bez `new Function`/`eval`. Krok w `frontend/Dockerfile` przerywa build, gdyby któryś warunek nie był spełniony (sprawdzone na zbudowanym obrazie).
  - `'wasm-unsafe-eval'` (kompilacja WebAssembly CanvasKit), nie `'unsafe-eval'`. Skrypty wyłącznie `'self'` (index.html nie ma skryptów inline).
  - `style-src 'unsafe-inline'`: silnik Fluttera wstawia elementy `<style>` i atrybuty `style`; nonce wymagałby dynamicznego `flutter_bootstrap.js` per odpowiedź. Ryzyko ograniczone (tylko style).
  - Fonty zastępcze Noto (glify spoza IBM Plex) silnik pobiera z `fonts.gstatic.com` — **celowo zablokowane** przez CSP (brak zewnętrznych CDN); polskie znaki pokrywa IBM Plex. Skutek: rzadkie symbole spoza Plex (np. emoji) jako „tofu” + wpis CSP w konsoli przeglądarki.
  - `NGINX_CSP_CONNECT_EXTRA` = `WEB_API_URL` (compose) — gdy frontend woła API pod innym originem.
- Odpowiedzi API (`/api/`): `Content-Security-Policy: default-src 'none'; frame-ancestors 'none'; base-uri 'none'; form-action 'none'`, `Cache-Control: no-store`. Pobranie załącznika ma dodatkowo własną politykę API (`default-src 'none'; sandbox`) — przeglądarka egzekwuje obie. `X-Content-Type-Options` z API jest ukrywany (`proxy_hide_header`), żeby nie był zdublowany. Swagger UI i schemat OpenAPI istnieją tylko przy `APP_ENV=dev` (§9 p. 4); w dev przez nginx UI nie działa (CDN zablokowany) — dostępny bezpośrednio na `127.0.0.1:8000/api/v1/docs`.

## 3. Załączniki: whitelist typów po zawartości

- Typ zapisywany w `attachments.content_type` jest **wykrywany z zawartości** (`app/services/file_types.py`, czysty Python, bez libmagic): sygnatury (PDF, PNG, JPEG, GIF, WebP, BMP, TIFF, GZIP, 7z, OLE2, MZ, ELF), ZIP rozróżniany po wpisach archiwum (`[Content_Types].xml` + `word/`/`xl/`/`ppt/` → DOCX/XLSX/PPTX; `mimetype` ODF → ODT/ODS/ODP; inaczej ZIP; archiwum nie jest rozpakowywane), OLE2 + rozszerzenie `.msg` → MSG, tekst = brak bajtów sterujących binarnych w **całym** pliku (także UTF-16 z BOM, teksty 8-bitowe np. CP1250). Podtyp tekstu z rozszerzenia (CSV, JSON, XML, EML), ale HTML i SVG są rozpoznawane po treści niezależnie od rozszerzenia.
- `ATTACHMENT_ALLOWED_TYPES` (lista MIME, puste = domyślna): PDF, PNG, JPEG, `text/plain` (txt/log), CSV, JSON, XML, ZIP, DOCX, XLSX, ODT, ODS, MSG, EML. Nieznana wartość na liście → API nie startuje. Typ spoza listy → **415 `attachment.type_not_allowed`** (`detail` po polsku z listą dozwolonych, rozszerzenia `detected_type`, `allowed_types`); plik tymczasowy usuwany, brak wiersza i wpisu audytu (nic nie zapisano).
- Deklarowany przez klienta `Content-Type` trafia tylko do kontekstu wpisu audytu `attach` (`declared_content_type`) — dowód rozbieżności, bez wpływu na decyzję.
- Limit rozmiaru: bez zmian (`ATTACHMENT_MAX_BYTES`, 413 `attachment.too_large`). `client_max_body_size` nginx = `NGINX_CLIENT_MAX_BODY_SIZE` (domyślnie `26m` ≥ 25 MiB + narzut multipart; test statyczny pilnuje relacji domyślnych wartości).

## 4. Logi aplikacyjne JSON

- `app/logs.py`, standardowy `logging` (bez nowej zależności): `LOG_FORMAT=json|console` (domyślnie `json`), `LOG_LEVEL`. Pola: `timestamp` (UTC, ms, `Z`), `level`, `logger`, `message`, `request_id`, `user_id`, `company_id`, pola `extra`, `exception`.
- `request_id` = `audit_log.request_id` = `X-Request-ID`. nginx przekazuje swój `$request_id` w postaci UUID (`map`), loguje dostęp w JSON z tym samym identyfikatorem — linia nginx, linia API i wpis audytu łączą się jednym kluczem.
- `user_id`/`company_id`: zależności uprawnień (`permissions._declare`) po rozwiązaniu `CurrentUser`/`CompanyContext` dopisują je do kontekstu żądania (mutowalny holder w `ContextVar`, bo zależności synchroniczne działają na kopii kontekstu). Żądania tylko z `CurrentUserDep` (bez akcji RBAC, np. `/me`) nie mają `user_id` w linii dostępu — świadome uproszczenie, bez zmian w `app/auth`.
- Linia dostępu `app.access` z własnego middleware (metoda, ścieżka **bez query string**, status, `duration_ms`, `client_ip`); poziom WARNING dla 401/403/429, ERROR dla 5xx; udane `/health` pomijane. Access log uvicorna wyłączony (`--no-access-log` + logger wyłączony).
- Maskowanie (`redact`): wartości kluczy `password|secret|token|authorization|cookie|api_key|credential|session|private_key|signature` (rekurencyjnie), w tekście: `Bearer …`/`Basic …`, JWT, `klucz=wartość` dla haseł/tokenów/sekretów, hasła w URL-ach (`scheme://user:hasło@`). Stosowane do komunikatu, argumentów, pól `extra` i tracebacków.
- Worker: ta sama konfiguracja w `startup` (po `dictConfig` arq).

## 5. Prawdziwe IP klienta

- Bez zmian względem ADR 0004 (nginx zastępuje `X-Forwarded-For` adresem klienta, uvicorn ufa tylko `172.28.0.10`). Nowe: `set_real_ip_from ${NGINX_TRUSTED_PROXIES}` + `real_ip_header X-Forwarded-For` — gdy przed `web` stoi proxy TLS, nginx przyjmuje IP klienta od niego (limity i audyt). Domyślnie `127.0.0.1/32` (nikt).
- Docker Desktop (Windows/macOS): NAT maszyny wirtualnej — nginx widzi bramę (`172.28.0.1`), nie da się tego naprawić konfiguracją aplikacji; na Linuksie bez `userland-proxy` albo za proxy TLS IP jest prawdziwe (`docs/deployment.md` §8).

## 6. Kopie zapasowe i odtworzenie

- `scripts/backup.sh` / `backup.ps1`: `pg_dump --format=custom` jako **`postgres`** (rola `app_rw` podlega RLS, a `pg_dump` roli bez BYPASSRLS przerywa zrzut tabel z politykami) + archiwum wolumenu `storage` (załączniki, raporty — bez nich zrzut nie odtwarza dowodów) + plik sum SHA-256 (format `sha256sum`) + retencja (`BACKUP_RETENTION_DAYS`). Pliki binarne przenoszone `docker cp` (PowerShell 5.1 psuje binaria w przekierowaniach).
- `scripts/restore.sh` / `restore.ps1`: sprawdzenie SHA-256 → pusta baza z uprawnieniami jak `roles.psql` (role muszą istnieć — init bazy; istniejąca baza z tabelami usuwana tylko z `--force`/`-Force`) → `pg_restore --single-transaction --exit-on-error` (dane ładowane przed utworzeniem triggerów i ograniczeń — triggery ochronne nie blokują odtworzenia) → pliki → `verify-audit --global` i `--company` dla każdej spółki (kod ≠ 0 przy naruszeniu). Weryfikacja dopisuje wpis do każdego łańcucha (dowód odtworzenia). `--db` pozwala na odtworzenie próbne obok produkcji.
- Usługa `backup` (profil compose) — codziennie `BACKUP_AT` (UTC), do `BACKUP_HOST_DIR`.
- Sprawdzone lokalnie na jednorazowym stosie: zrzut → odtworzenie do osobnej bazy i do bazy głównej (`--force`) z plikami; po odtworzeniu: 4 łańcuchy spójne, `app_rw` bez UPDATE na `audit_log`, 3 triggery `audit_log`, RLS na 16 tabelach, właściciel `app_owner`, plik załącznika z tym samym sha256.

## 7. CI

Job `docker-compose`: nagłówki (CSP, nosniff, Referrer-Policy, Permissions-Policy, X-Frame-Options, COOP; brak HSTS po HTTP; CSP API), lokalny CanvasKit (`application/wasm`, `useLocalCanvasKit`), 415 dla pliku wykonywalnego udającego PDF i 201 `application/pdf` dla PDF wysłanego jako `octet-stream`, linia `app.access` w JSON z `request_id`, brak JWT w logach, na końcu 429 problem+json po serii logowań. Job `frontend`: `flutter build web` z tymi samymi flagami co obraz. Testy statyczne konfiguracji: `backend/tests/test_deploy_config.py`.

## 8. Kody błędów (dla frontendu)

| HTTP | `code` | Źródło | Komunikat (`detail`) |
|---|---|---|---|
| 415 | `attachment.type_not_allowed` | API | „Niedozwolony typ pliku (…). Dozwolone typy załączników: …” (+ `detected_type`, `allowed_types`) |
| 413 | `attachment.too_large` | API (dokładny limit) lub nginx (ciało żądania) | „Załącznik jest zbyt duży…” / „Przesłany plik jest zbyt duży.” |
| 429 | `request.rate_limited` | nginx | „Przekroczono limit żądań. Odczekaj chwilę i spróbuj ponownie.” (+ `Retry-After`) |
| 503 | `api.unavailable` | nginx (API nie odpowiada) | „Serwer aplikacji jest chwilowo niedostępny. Spróbuj ponownie za chwilę.” |

## 9. Decyzje właściciela (2026-11-04)

Wszystkie rekomendacje przyjęte:

1. Domyślne limity żądań **bez zmian** (20 r/s API; 10/min logowanie; 30/min refresh); przy wielu użytkownikach za wspólnym NAT-em administrator podnosi serię (`NGINX_AUTH_BURST`, `docs/deployment.md` §7).
2. Domyślna lista typów załączników **bez zmian** (GIF/WebP/PPTX/ODP/stare pliki Office/7z/GZIP rozpoznawane, ale wyłączone — włączane przez `ATTACHMENT_ALLOWED_TYPES`).
3. Fonty zastępcze Noto **zablokowane** przez CSP (bez samodzielnego hostowania).
4. Dokumentacja API **wyłączona poza `APP_ENV=dev`**: przy `APP_ENV=prod` `/api/v1/docs`, `/api/v1/redoc` i `/api/v1/openapi.json` zwracają 404 (problem+json) — `create_app` ustawia `docs_url`/`openapi_url` tylko w dev (test `tests/test_health.py`). Nginx, CI ani frontend nie korzystają ze schematu.
5. Szyfrowanie kopii zapasowych **opcjonalnie przez `age`** (kopie zawierają dane osobowe i skróty haseł) — wdrożone w skryptach kopii i usłudze `backup` — §10, opis w `docs/deployment.md` (Kopie zapasowe).

## 10. Szyfrowanie kopii (age)

Decyzja właściciela 2026-11-04: kopie bazy zawierają dane osobowe i skróty haseł — **opcjonalne szyfrowanie kopii programem [age](https://age-encryption.org)** w skryptach kopii (uzupełnia §6).

- **Włączenie**: `BACKUP_AGE_RECIPIENT` — klucz publiczny `age1…` (`age -r`; kilka kluczy rozdzielonych przecinkami, np. klucz zespołu + awaryjny w sejfie) i/lub `BACKUP_AGE_RECIPIENTS` — plik kluczy publicznych (`age -R`). Obie naraz = wszyscy odbiorcy. Brak zmiennych = dotychczasowe zachowanie (kopie bez szyfrowania). PowerShell: także parametry `-AgeRecipient` / `-AgeRecipientsFile`.
- **Strumieniowo, bez pliku pośredniego**: `pg_dump` (na stdout) `| age -o X.part` i `tar -czf - | age`; nazwy `rejestr-STEMPEL.dump.age`, `rejestr-STEMPEL-storage.tar.gz.age`. Plik `.part` jest zmieniany na docelowy dopiero po sukcesie całego potoku (`pipefail`; przerwany zapis jest usuwany), więc nieudany `pg_dump` nie zostawia poprawnie zaszyfrowanego, uciętego zrzutu. Nie szyfrujemy zrzutu już zapisanego na dysk — niezaszyfrowana kopia nie powstaje ani na hoście, ani w kontenerze.
- **Sumy SHA-256** (dotychczasowy plik `rejestr-STEMPEL.sha256`, format `sha256sum`) liczone z plików zaszyfrowanych — integralność sprawdzalna bez klucza prywatnego. Retencja (`rejestr-*`) obejmuje `*.age` i pozostałe `*.part`.
- **Bezpieczne niepowodzenie**: zmienna ustawiona, a brak programu `age` albo klucz nieprawidłowy (próbne szyfrowanie pustego wejścia przed zrzutem) = błąd, kopia nie powstaje. Nigdy po cichu kopia bez szyfrowania.
- **Odtworzenie** (`restore.sh` / `restore.ps1`): przyjmuje `*.dump.age` / `*-storage.tar.gz.age`; klucz prywatny z `--identity` / `-Identity` albo `BACKUP_AGE_IDENTITY` (`age -d -i`). Kolejność: suma SHA-256 plików zaszyfrowanych → próbne odszyfrowanie całości do `/dev/null` (zły klucz / uszkodzony plik zatrzymuje skrypt przed usunięciem bazy lub plików) → `age -d | pg_restore` (stdin; sprawdzone na pełnym schemacie: triggery, RLS, właściciel `app_owner`) i `age -d | tar`.
- **Klucz prywatny nie jest przechowywany na serwerze produkcyjnym** — powstaje i jest przechowywany poza nim (sejf haseł zespołu IT + kopia offline), przynoszony tylko na czas odtwarzania. Przejęcie serwera lub katalogu kopii nie ujawnia treści kopii. `BACKUP_AGE_IDENTITY` nie występuje w `.env.example` jako wartość do ustawienia.
- **Usługa `backup`** (compose): obraz `deploy/backup/Dockerfile` (`postgres:16-alpine` + `age` z Alpine). Obsługuje tylko `BACKUP_AGE_RECIPIENT` (wartość z `.env`); `BACKUP_AGE_RECIPIENTS` to ścieżka hosta, niewidoczna w kontenerze — usługa odmawia startu zamiast pisać kopie bez szyfrowania. Przy okazji: każde zaplanowane uruchomienie jest osobnym procesem `backup-loop.sh --once`, bo `set -e` nie działa w funkcji wywołanej z listy `||` (nieudany `pg_dump` był wcześniej sumowany jak poprawna kopia).
- **PowerShell**: bajty są przepisywane między procesami (`System.Diagnostics.Process`, `Stream.CopyTo`), nie przez potok PowerShella (dekoduje wyjście jako tekst). .NET Framework (PowerShell 5.1) dopisuje preambułę `Console.InputEncoding` (BOM UTF-8) do przekierowanego stdin procesu — skrypty na czas startu procesu ustawiają kodowanie bez preambuły (bez tego zaszyfrowany zrzut miał 3 dodatkowe bajty i `pg_restore` go odrzucał).
- Sprawdzone lokalnie (osobny projekt compose, `age` 1.3.2 w kontenerze): `backup.sh`, `backup.ps1` (PowerShell 7.6 i 5.1) i usługa `backup` (`--once` i pętla) → `restore.sh` / `restore.ps1` z kluczem z `-R` i z `-r`, z plikami i `verify-audit` (4 łańcuchy spójne, pliki z tym samym sha256); kopie z bash odtwarzane przez PowerShell; błędy: brak `age`, zły klucz publiczny, brak/zły klucz prywatny (baza nietknięta), zmieniony bajt (suma), nieudany `pg_dump` (brak plików).

## 11. Poprawki z recenzji (2026-11-04): schemat za proxy TLS, monitoring kopii

- **`X-Forwarded-Proto` tylko od zaufanego proxy.** Wcześniej nginx przekazywał do API `$scheme` — za proxy TLS (`NGINX_TRUSTED_PROXIES`) API widziało `http`. Teraz `geo $realip_remote_addr` (adres TCP rozmówcy sprzed podmiany przez `realip`) sprawdza, czy żądanie przyszło od `NGINX_TRUSTED_PROXIES`; tylko wtedy jego `X-Forwarded-Proto` (wyłącznie wartość `https` lub `http`, bez rozróżniania wielkości liter — `map` nginx; inne wartości, np. lista `https, http`, są ignorowane) przechodzi jako `$forwarded_proto`, w każdym innym przypadku `$scheme` (nginx słucha wyłącznie HTTP). Klient łączący się bezpośrednio nie podrobi `https`. Zaufanie po stronie API bez zmian (`FORWARDED_ALLOW_IPS` = tylko kontener `web`, §5).
- **HSTS tylko przez HTTPS** (RFC 6797 §7.2): `Strict-Transport-Security` = `NGINX_HSTS` wyłącznie gdy `$forwarded_proto = https`; w odpowiedziach HTTP nagłówka nie ma. Za proxy TLS wymaga poprawnego `NGINX_TRUSTED_PROXIES` i `X-Forwarded-Proto https` z proxy (`docs/deployment.md` §5).
- **Monitoring kopii (ISO/IEC 27001 A.8.13).** Nieudana kopia trafiała tylko do logu kontenera. `backup-loop.sh` zapisuje w katalogu kopii znacznik `.backup-last-success` (po kopii ze sprawdzonymi sumami, także w trybie `--once`; zapis atomowy) i `.backup-last-failure` (nieudane zaplanowane uruchomienie). Healthcheck usługi `backup` (`deploy/backup/healthcheck.sh`) = `unhealthy`, gdy ostatnie uruchomienie się nie udało, ostatnia udana kopia jest starsza niż `BACKUP_MAX_AGE_HOURS` (domyślnie 26 h) albo od startu pętli minął ten czas bez udanej kopii. Tryb `--once` działa jak dotąd (kod wyjścia; `set -e` nadal poza listą `if`/`||`). Kopie ze skryptów hosta znaczników nie aktualizują — monitoring kodu wyjścia zadania. Zalecenie produkcyjne: `BACKUP_AGE_RECIPIENT` ustawione (kopie zawierają skróty haseł i dane osobowe).
- Testy statyczne: `backend/tests/test_deploy_config.py`.
- Sprawdzone lokalnie (osobny projekt compose): bezpośredni klient z `X-Forwarded-Proto: https` → API widzi `http` (przekierowanie `http://…`), brak HSTS; z `NGINX_TRUSTED_PROXIES` = adres rozmówcy → `https://…` i HSTS, lista `https, http` → `http`. Usługa `backup`: `--once` zapisuje znacznik sukcesu, nieudane zaplanowane uruchomienie (pętla) zmienia status kontenera na `unhealthy`, kolejna udana kopia przywraca `ok`; kopia starsza niż 26 h i brak kopii po okresie karencji → `unhealthy`.
