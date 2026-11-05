# Wdrożenie produkcyjne — Rejestr zmian IT

Instrukcja dla administratora uruchamiającego aplikację na serwerze. Decyzje
techniczne: [ADR 0019](decisions/0019-hardening.md) (utwardzenie),
[ADR 0004](decisions/0004-public-health-and-proxy-trust.md) (IP klienta),
[ADR 0018](decisions/0018-local-password-accounts.md) (konta lokalne). Specyfikacja:
[CLAUDE.md](../CLAUDE.md).

Dla użytkowników aplikacji (także administratora aplikacji po wdrożeniu):
[instrukcja obsługi](instrukcja-obslugi.md) i
[lista funkcjonalności](funkcjonalnosci.md).

## 1. Wymagania

- Linux (zalecany) z Docker Engine 24+ i Docker Compose v2 (`docker compose`).
  Windows/macOS z Docker Desktop nadaje się do testów, ale nie zapisuje
  prawdziwego IP klienta (patrz §8).
- 2 vCPU, 4 GB RAM, 20 GB dysku na start (baza + załączniki rosną z czasem);
  osobne miejsce na kopie zapasowe (najlepiej poza serwerem).
- Reverse proxy z certyfikatem TLS przed kontenerem `web` (nginx, Caddy,
  Traefik, load balancer) — aplikacja w kontenerze mówi tylko HTTP.
- Dostęp wychodzący z serwera do internetu nie jest wymagany w czasie pracy
  (frontend nie korzysta z CDN; tylko budowa obrazów pobiera zależności).

## 2. Konfiguracja

Wszystkie zmienne są opisane w [`.env.example`](../.env.example) (po polsku).
Skopiuj go do `.env` i uzupełnij:

```bash
cp .env.example .env
chmod 600 .env
```

Minimum dla produkcji:

| Zmienna | Wartość |
|---|---|
| `APP_ENV` | `prod` |
| `AUTH_MODE` | `local` (konta lokalne z hasłem, ADR 0018). `dev` jest przy `APP_ENV=prod` odrzucany przy starcie API |
| `POSTGRES_PASSWORD`, `APP_OWNER_PASSWORD`, `APP_RW_PASSWORD` | trzy różne, losowe hasła (min. 32 znaki) |
| `DATABASE_URL`, `MIGRATIONS_DATABASE_URL` | z hasłami `app_rw` / `app_owner` jak wyżej |
| `AUTH_JWT_SECRET` | klucz podpisywania tokenów (ADR 0018): wymagany przy `AUTH_MODE=local`, min. 64 znaki przy `APP_ENV=prod` (32 w dev), np. `openssl rand -hex 48` |
| `DEV_AUTH_SECRET` | puste |
| `TEMP_PASSWORD_TTL_HOURS` | `168` (domyślnie, 7 dni) — ważność hasła tymczasowego (nowe konto, reset przez administratora, `create-admin --generate-password`); po terminie logowanie zwraca `401 auth.temporary_password_expired`, a sesja otwarta tym hasłem kończy się — potrzebny ponowny reset (ADR 0018 §12) |
| `NGINX_HSTS` | `max-age=31536000; includeSubDomains` — **tylko** gdy serwis jest dostępny wyłącznie przez HTTPS |
| `NGINX_TRUSTED_PROXIES` | adres proxy TLS przed `web` (patrz §5) |
| `CORS_ORIGINS` | puste, jeśli frontend i API są pod tym samym adresem (domyślny układ) |
| `LOG_FORMAT` | `json` |

Generowanie hasła/klucza: `openssl rand -hex 32` (Linux) albo w PowerShell:

```powershell
$b = New-Object byte[] 32; [Security.Cryptography.RandomNumberGenerator]::Create().GetBytes($b)
($b | ForEach-Object { $_.ToString('x2') }) -join ''
```

Hasła w URL-ach baz: tylko znaki `A-Z a-z 0-9 - _ .` (inaczej percent-encoding).

## 3. Pierwsze uruchomienie

```bash
docker compose up -d --build          # migrate stosuje migracje (app_owner) i kończy pracę
docker compose ps                     # db, redis, api, worker, web: (healthy); migrate: exited (0)
curl -fsS http://localhost:8080/api/v1/health
```

Role bazy (`app_owner` — właściciel schematu, tylko migracje; `app_rw` —
aplikacja, bez uprawnień właściciela, podlega RLS) tworzy skrypt
`deploy/postgres/init/10-roles.sh` przy **pierwszym** starcie pustego wolumenu.

Słowniki startowe (kategorie zmian z CLAUDE.md §13, typy obiektów CI) —
dozwolone w produkcji, powtarzalne:

```bash
docker compose run --rm api python -m app.cli seed-dictionaries
```

Pierwsze konto administratora aplikacji (ADR 0018). Bez opcji hasło podajesz
w terminalu (dwukrotnie, ukryte) albo jedną linią na standardowym wejściu — jest
to hasło stałe, bez wymuszonej zmiany. Z `--generate-password` komenda wypisuje
raz losowe **hasło tymczasowe**: zmiana wymuszona przy pierwszym logowaniu,
ważne `TEMP_PASSWORD_TTL_HOURS` (domyślnie 7 dni) — zaloguj się przed terminem.

```bash
docker compose run --rm api python -m app.cli create-admin --email admin@example.com --name "Jan Kowalski"
```

Dalsze konta, role w spółkach i spółki zakłada administrator w aplikacji
(Administracja). **Nie** uruchamiaj `python -m app.cli seed` w produkcji (dane
przykładowe; komenda odmawia działania przy `APP_ENV=prod`).

## 4. Porty i sieć

| Usługa | Port | Uwagi |
|---|---|---|
| `web` (nginx) | `${WEB_PORT:-8080}` na wszystkich interfejsach | jedyny port dla użytkowników — wystaw go tylko do proxy TLS (firewall) |
| `api` | `127.0.0.1:8000` | tylko lokalnie (diagnostyka; `/api/v1/docs` i `/api/v1/openapi.json` istnieją tylko przy `APP_ENV=dev`, w produkcji 404 — ADR 0019 §9); w produkcji można usunąć mapowanie |
| `db` | `127.0.0.1:5432` | tylko lokalnie; w produkcji można usunąć mapowanie |
| `redis` | `127.0.0.1:6379` | tylko lokalnie; w produkcji można usunąć mapowanie |

Sieć compose ma stałą podsieć `172.28.0.0/16`; nginx ma adres `172.28.0.10`,
jedyny zaufany przez API (`FORWARDED_ALLOW_IPS`). Przy kolizji z siecią
lokalną zmień razem: `subnet`, `ip_range`, `gateway`, adres `web` i
`FORWARDED_ALLOW_IPS` (patrz komentarze w `docker-compose.yml`).

## 5. TLS, reverse proxy i HSTS

Kontener `web` mówi HTTP na porcie 80. TLS kończy proxy przed nim. Przykład
(nginx na hoście, certyfikat z firmowego CA lub Let's Encrypt):

```nginx
server {
    listen 443 ssl http2;
    server_name rejestr.example.com;
    ssl_certificate     /etc/ssl/rejestr.crt;
    ssl_certificate_key /etc/ssl/rejestr.key;
    client_max_body_size 26m;                       # >= NGINX_CLIENT_MAX_BODY_SIZE
    location / {
        proxy_pass http://127.0.0.1:8080;
        proxy_set_header Host $host;
        proxy_set_header X-Forwarded-For $remote_addr;   # zastąp, nie doklejaj
        proxy_set_header X-Forwarded-Proto https;
        proxy_read_timeout 130s;
    }
}
server { listen 80; server_name rejestr.example.com; return 301 https://$host$request_uri; }
```

W `.env`:

```dotenv
# adres, z którego proxy łączy się z kontenerem web (tak jak widzi go kontener):
# proxy na hoście -> brama sieci compose 172.28.0.1; osobna maszyna -> jej IP
NGINX_TRUSTED_PROXIES=172.28.0.1
NGINX_HSTS=max-age=31536000; includeSubDomains
```

- `NGINX_TRUSTED_PROXIES` włącza moduł `realip`: nginx przyjmuje
  `X-Forwarded-For` **tylko** od tego adresu i traktuje go jako IP klienta
  (limity żądań, dziennik audytu). Nigdy `0.0.0.0/0`.
- Od tego samego adresu nginx przyjmuje `X-Forwarded-Proto` (tylko wartość
  `https` lub `http`, bez rozróżniania wielkości liter; listy typu `https, http`
  są ignorowane) i przekazuje go do API. Od każdego innego klienta —
  także łączącego się z `web` bezpośrednio — nagłówek jest ignorowany i API
  dostaje `http` (schemat połączenia z nginx); klient nie podrobi `https`.
  Proxy TLS musi więc **ustawiać** `X-Forwarded-Proto https` (jak w przykładzie).
- HSTS jest wysyłany tylko w odpowiedziach na żądania, które według zaufanego
  proxy przyszły przez HTTPS (RFC 6797: nie w odpowiedziach HTTP). Brak
  nagłówka HSTS za proxy TLS = źle ustawione `NGINX_TRUSTED_PROXIES` albo
  proxy nie wysyła `X-Forwarded-Proto https`. Sprawdzenie:
  `curl -sI https://rejestr.example.com/ | grep -i strict-transport`.
- `NGINX_HSTS` włączaj dopiero, gdy HTTPS działa poprawnie — przeglądarki
  zapamiętują HSTS na `max-age` (rok) i odmówią HTTP. Zacznij od
  `max-age=300`, potem zwiększ.
- Proxy TLS nie powinno dodawać własnych nagłówków CSP — nginx w `web`
  wysyła pełny zestaw (CSP, X-Content-Type-Options, Referrer-Policy,
  Permissions-Policy, X-Frame-Options, COOP, CORP).
- Gdy proxy jest na hoście, port `web` wystaw tylko na `127.0.0.1`
  (np. `WEB_PORT=127.0.0.1:8080`).

## 6. Nagłówki bezpieczeństwa i CSP

Polityka dla aplikacji (Flutter web, CanvasKit serwowany lokalnie — obraz
budowany z `--csp --no-web-resources-cdn`, build przerywa się, gdyby CanvasKit
miał być ładowany z CDN):

```
default-src 'self'; script-src 'self' 'wasm-unsafe-eval'; style-src 'self' 'unsafe-inline';
img-src 'self' data: blob:; font-src 'self' data:; connect-src 'self'; worker-src 'self' blob:;
manifest-src 'self'; object-src 'none'; frame-src 'none'; base-uri 'self'; form-action 'self';
frame-ancestors 'none'
```

Odpowiedzi API: `default-src 'none'; frame-ancestors 'none'` + `Cache-Control:
no-store`. Szczegóły i uzasadnienie: ADR 0019 §2. Sprawdzenie:

```bash
curl -sI http://localhost:8080/ | grep -iE 'content-security|x-content-type|referrer|permissions|x-frame|cross-origin'
```

Gdy frontend jest budowany z innym adresem API (`WEB_API_URL`), ta sama
wartość trafia automatycznie do `connect-src`.

## 7. Limity żądań (rate limiting)

nginx ogranicza żądania per IP klienta; po przekroczeniu zwraca `429`
`application/problem+json` z kodem `request.rate_limited` i nagłówkiem
`Retry-After`:

| Ścieżka | Zmienne | Domyślnie |
|---|---|---|
| `/api/` | `NGINX_API_RATE`, `NGINX_API_BURST` | 20 żądań/s, seria 100 |
| `/api/v1/auth/login`, `/auth/password`, `/auth/dev/token` | `NGINX_AUTH_RATE`, `NGINX_AUTH_BURST` | 10/min, seria 10 |
| `/api/v1/auth/refresh` | `NGINX_REFRESH_RATE`, `NGINX_REFRESH_BURST` | 30/min, seria 20 |
| połączenia równoczesne | `NGINX_CONN_PER_IP` | 50 |

Użytkownicy za jednym NAT-em (biuro z jednym publicznym IP) dzielą limity —
przy kilkudziesięciu osobach zwiększ `NGINX_AUTH_BURST` (poranne logowania).
Za proxy TLS limity działają poprawnie tylko z ustawionym
`NGINX_TRUSTED_PROXIES` (inaczej wszyscy mają IP proxy). Blokadę konta po
nieudanych logowaniach realizuje dodatkowo API (ADR 0018).

Zbyt duże żądanie (powyżej `NGINX_CLIENT_MAX_BODY_SIZE`) nginx odrzuca kodem
`413` `attachment.too_large`; dokładny limit pliku (`ATTACHMENT_MAX_BYTES`)
egzekwuje API. API niedostępne → `503` `api.unavailable`.

## 8. Adres IP klienta w dzienniku audytu

Łańcuch: klient → (proxy TLS, `NGINX_TRUSTED_PROXIES`) → nginx `web`
(zastępuje `X-Forwarded-For` adresem klienta) → uvicorn
(`--proxy-headers`, ufa tylko `FORWARDED_ALLOW_IPS=172.28.0.10`) →
`audit_log.ip_address`. Podrobiony przez klienta `X-Forwarded-For` jest
ignorowany (test w CI).

**Docker Desktop (Windows/macOS):** ruch z przeglądarki przechodzi przez NAT
maszyny wirtualnej Dockera, więc nginx widzi adres bramy (np. `172.28.0.1`),
a nie prawdziwe IP — tego nie da się obejść konfiguracją aplikacji. Na
Linuksie z Docker Engine nginx widzi prawdziwe IP, jeśli ruch nie przechodzi
przez `userland-proxy` (ustaw `"userland-proxy": false` w
`/etc/docker/daemon.json`) albo gdy przed `web` stoi proxy TLS z
`NGINX_TRUSTED_PROXIES`.

## 9. Załączniki

- Limit rozmiaru: `ATTACHMENT_MAX_BYTES` (domyślnie 25 MiB) → `413
  attachment.too_large`; `NGINX_CLIENT_MAX_BODY_SIZE` musi być nieco większy
  (narzut multipart; domyślnie `26m`).
- Typ pliku rozpoznawany z **zawartości** (sygnatury, struktura dokumentów
  Office/ODF, tekst), nie z nagłówka przeglądarki; dozwolone typy:
  `ATTACHMENT_ALLOWED_TYPES` (domyślnie PDF, PNG, JPEG, TXT/LOG, CSV, JSON, XML,
  ZIP, DOCX, XLSX, ODT, ODS, MSG, EML). Inne → `415
  attachment.type_not_allowed`. HTML, SVG i pliki wykonywalne są zawsze
  rozpoznawane jako takie, niezależnie od rozszerzenia.
- Pliki leżą w wolumenie `storage` — obejmij go kopią zapasową (§10).

## 10. Kopie zapasowe

Kopia = zrzut bazy (`pg_dump`, format custom) + archiwum plików (wolumen
`storage`: załączniki, raporty PDF) + plik sum SHA-256. Zrzut wykonuje
superużytkownik `postgres` — rola `app_rw` podlega RLS i zrzut byłby
niepełny. Zrzut zawiera właścicieli obiektów (`app_owner`) i uprawnienia
(`app_rw`, w tym ograniczenie do INSERT/SELECT na `audit_log`, triggery
ochronne, polityki RLS), ale **nie** same role — tworzy je skrypt init bazy.

Jednorazowo (z katalogu repozytorium, przy działającej bazie):

```bash
scripts/backup.sh                          # -> ./backups/rejestr-YYYYMMDDTHHMMSSZ.{dump,-storage.tar.gz,sha256}
BACKUP_DIR=/mnt/kopie BACKUP_RETENTION_DAYS=30 scripts/backup.sh
```

```powershell
.\scripts\backup.ps1
.\scripts\backup.ps1 -BackupDir D:\kopie -RetentionDays 30
```

Automatycznie — usługa `backup` (profil compose), codziennie o `BACKUP_AT`
(UTC) do `BACKUP_HOST_DIR`, z retencją `BACKUP_RETENTION_DAYS`:

```bash
docker compose --profile backup up -d backup
docker compose logs backup
docker compose --profile backup run --rm backup sh /opt/backup/backup-loop.sh --once   # kopia teraz
```

Alternatywnie cron na hoście: `30 1 * * * cd /opt/rejestr && scripts/backup.sh >> /var/log/rejestr-backup.log 2>&1`.

### Monitoring kopii (healthcheck usługi `backup`)

Nieudana kopia nie może zostać zauważona dopiero przy odtwarzaniu (ISO/IEC
27001 A.8.13). Usługa `backup` zapisuje w katalogu kopii znaczniki
`.backup-last-success` (po każdej udanej kopii, także `--once`; dopiero po
sprawdzeniu sum SHA-256) i `.backup-last-failure` (po nieudanym zaplanowanym
uruchomieniu). Healthcheck kontenera (`deploy/backup/healthcheck.sh`, co 5 min)
zgłasza **`unhealthy`**, gdy:

- ostatnie zaplanowane uruchomienie się nie udało (do najbliższej udanej kopii),
- ostatnia udana kopia jest starsza niż `BACKUP_MAX_AGE_HOURS` (domyślnie 26 h),
- od startu usługi minęło `BACKUP_MAX_AGE_HOURS`, a udanej kopii nie ma.

```bash
docker compose --profile backup ps backup                       # STATUS: (healthy) / (unhealthy)
docker inspect --format '{{.State.Health.Status}}' "$(docker compose --profile backup ps -q backup)"
docker inspect --format '{{json .State.Health.Log}}' "$(docker compose --profile backup ps -q backup)"   # przyczyna
```

Status `backup` włącz do monitoringu (Zabbix/Prometheus/skrypt z
`docker events --filter event=health_status`) z alertem na `unhealthy`. Kopie
wykonywane skryptami `scripts/backup.sh|ps1` (cron, Harmonogram zadań) nie
aktualizują znaczników — monitoruj wtedy kod wyjścia zadania lub wiek
najnowszego pliku `rejestr-*.sha256`.

Kopie przenoś poza serwer (inna lokalizacja, nośnik offline). Zawierają dane
osobowe (imiona, e-maile, adresy IP z dziennika audytu) i skróty haseł —
włącz szyfrowanie (niżej).

### Szyfrowanie kopii (age)

Opcjonalne, zalecane w produkcji ([ADR 0019 §10](decisions/0019-hardening.md)).
Kopie są szyfrowane programem [age](https://age-encryption.org) **kluczem
publicznym**; do odszyfrowania potrzebny jest **klucz prywatny**, którego
**nie trzymamy na serwerze produkcyjnym** — przejęcie serwera lub katalogu
kopii nie daje dostępu do treści kopii.

Gdy szyfrowanie jest włączone, zrzut i archiwum plików są szyfrowane
strumieniowo (`pg_dump | age`, `tar | age`) — niezaszyfrowany plik nie powstaje
na dysku ani w kontenerze. Powstają `rejestr-STEMPEL.dump.age`,
`rejestr-STEMPEL-storage.tar.gz.age` i `rejestr-STEMPEL.sha256` (sumy plików
**zaszyfrowanych**, sprawdzalne bez klucza: `sha256sum -c`). Retencja usuwa też
pliki `*.age`. Brak programu `age` przy ustawionym kluczu = błąd, kopia nie
powstaje (nigdy nie zapisujemy po cichu kopii bez szyfrowania).

1. **Para kluczy** — na stacji administratora lub komputerze offline, nie na
   serwerze (`apt install age` / `dnf install age` / `winget install FiloSottile.age`):

   ```bash
   age-keygen -o rejestr-backup.key      # klucz prywatny (AGE-SECRET-KEY-1...)
   age-keygen -y rejestr-backup.key      # wypisuje klucz publiczny age1...
   ```

   Klucz prywatny przechowuj poza serwerem: sejf haseł / menedżer sekretów
   zespołu IT oraz kopia offline (wydruk lub szyfrowany nośnik w sejfie).
   Zalecane dwa klucze: zespołu i awaryjny (w sejfie) — kopia jest wtedy
   szyfrowana dla obu i odszyfruje ją każdy z nich. Utrata wszystkich kluczy
   prywatnych = utrata kopii.

2. **Włączenie** — klucze publiczne (nie są sekretem):

   - usługa `backup`: w `.env` `BACKUP_AGE_RECIPIENT=age1…,age1…` (przecinki
     między kluczami), potem `docker compose --profile backup up -d --build backup`
     (obraz z `age`: `deploy/backup/Dockerfile`);
   - skrypty (nie czytają `.env`): zmienna środowiskowa `BACKUP_AGE_RECIPIENT`
     albo `BACKUP_AGE_RECIPIENTS` = plik z kluczami publicznymi, po jednym w
     linii (`age -R`; tylko skrypty):

     ```bash
     BACKUP_AGE_RECIPIENTS=/etc/rejestr/backup-recipients.txt scripts/backup.sh
     ```

     ```powershell
     $env:BACKUP_AGE_RECIPIENT = 'age1...'; .\scripts\backup.ps1
     .\scripts\backup.ps1 -AgeRecipientsFile C:\rejestr\backup-recipients.txt
     ```

3. **Odtworzenie** — klucz prywatny przynieś na serwer docelowy tylko na czas
   odtwarzania (plik z prawami `600`, najlepiej na nośniku wymiennym) i usuń
   go po zakończeniu; skrypt przyjmuje pliki `*.age` (§ Odtworzenie niżej):
   `--identity PLIK` / `-Identity PLIK` albo zmienna `BACKUP_AGE_IDENTITY`.
   Kolejność: suma SHA-256 plików zaszyfrowanych → próbne odszyfrowanie całości
   (zły klucz lub uszkodzony plik zatrzymuje skrypt, zanim cokolwiek zostanie
   usunięte) → odszyfrowanie strumieniowe do `pg_restore` / `tar`.

4. **Test odtworzenia** — po włączeniu szyfrowania i potem raz na kwartał
   wykonaj odtworzenie próbne z kopii `*.age` kluczem z sejfu (sprawdza
   jednocześnie kopię i to, że klucz prywatny jest dostępny i właściwy):

   ```bash
   scripts/restore.sh backups/rejestr-….dump.age --db rejestr_restore_test \
       --identity /media/usb/rejestr-backup.key
   docker compose exec db psql -U postgres -c 'DROP DATABASE rejestr_restore_test'
   ```

   Samo odszyfrowanie bez bazy (np. na stacji administratora):
   `age -d -i rejestr-backup.key rejestr-….dump.age | pg_restore --list | head`.

Zmiana kluczy: ustaw nowe klucze publiczne — nowe kopie są szyfrowane nowymi
kluczami; stare klucze prywatne zachowaj, dopóki istnieją kopie nimi
zaszyfrowane (okres retencji + kopie archiwalne poza serwerem).

### Odtworzenie

1. Na docelowym serwerze: repozytorium w tej samej wersji co kopia (lub
   nowszej — migracje zastosujesz potem), `.env` z hasłami ról.
2. Uruchom samą bazę (pierwszy start pustego wolumenu tworzy role):
   `docker compose up -d db`. Na istniejącym stosie zatrzymaj aplikację:
   `docker compose stop api worker web`.
3. Odtwórz bazę i pliki, z weryfikacją sum i łańcuchów audytu:

   ```bash
   scripts/restore.sh backups/rejestr-20261103T013000Z.dump \
       --storage backups/rejestr-20261103T013000Z-storage.tar.gz --force
   ```

   ```powershell
   .\scripts\restore.ps1 .\backups\rejestr-20261103T013000Z.dump `
       -Storage .\backups\rejestr-20261103T013000Z-storage.tar.gz -Force
   ```

   Kopia zaszyfrowana — te same polecenia z plikami `*.age` i kluczem
   prywatnym:

   ```bash
   scripts/restore.sh backups/rejestr-20261103T013000Z.dump.age \
       --storage backups/rejestr-20261103T013000Z-storage.tar.gz.age \
       --identity /media/usb/rejestr-backup.key --force
   ```

   ```powershell
   .\scripts\restore.ps1 .\backups\rejestr-20261103T013000Z.dump.age `
       -Storage .\backups\rejestr-20261103T013000Z-storage.tar.gz.age `
       -Identity E:\rejestr-backup.key -Force
   ```

   Skrypt: sprawdza SHA-256 → (kopia `*.age`: próbne odszyfrowanie) → tworzy pustą bazę z uprawnieniami jak skrypt
   init (istniejąca baza z danymi jest usuwana tylko z `--force`) →
   `pg_restore` w jednej transakcji → odtwarza pliki → uruchamia
   `python -m app.cli verify-audit --global` oraz `--company PREFIKS` dla każdej
   spółki. Kod wyjścia ≠ 0, jeśli którykolwiek łańcuch jest naruszony.
   Weryfikacja dopisuje wpis do każdego łańcucha (to jest dowód odtworzenia).
4. `docker compose up -d` (migrate doprowadzi schemat do bieżącej wersji).

Odtworzenie próbne (zalecane raz na kwartał, dowód dla ISO 27001 A.8.13) —
do bazy o innej nazwie, bez naruszania produkcji. **Bez `--storage`**: pliki
są zawsze odtwarzane do wolumenu `storage` projektu, czyli nadpisałyby pliki
działającej aplikacji (archiwum plików sprawdzisz sumą SHA-256 i
`tar -tzf`):

```bash
scripts/restore.sh backups/rejestr-....dump --db rejestr_restore_test
docker compose exec db psql -U postgres -c 'DROP DATABASE rejestr_restore_test'
```

## 11. Aktualizacja wersji

```bash
scripts/backup.sh                         # zawsze przed aktualizacją
git fetch && git checkout <tag-wersji>
docker compose build
docker compose up -d                      # migrate: alembic upgrade head (app_owner), potem api/worker
docker compose ps && docker compose logs migrate
```

Migracje uruchamia wyłącznie jednorazowa usługa `migrate` jako `app_owner`;
`api` i `worker` startują dopiero po jej sukcesie. Wycofanie wersji = odtworzenie
kopii sprzed aktualizacji (migracje w dół nie są procedurą produkcyjną).

## 12. Weryfikacja łańcucha audytu

- Worker weryfikuje wszystkie łańcuchy codziennie o 02:30 UTC; wynik zasila
  znacznik „Łańcuch spójny” (nieświeży po `AUDIT_STATUS_MAX_AGE_HOURS`).
- Ręcznie (kod wyjścia 0 = spójny, 1 = naruszony lub błąd):

  ```bash
  docker compose exec api python -m app.cli verify-audit --global
  docker compose exec api python -m app.cli verify-audit --company ALFA
  ```

- W aplikacji: Dziennik audytu → „Weryfikuj łańcuch” (audytor, administrator).
- Naruszenie łańcucha = incydent bezpieczeństwa: zabezpiecz kopie i logi,
  porównaj z ostatnią spójną kopią (odtworzenie próbne).

## 13. Logi

- `api` i `worker`: JSON w jednej linii na zdarzenie (`LOG_FORMAT=json`) —
  `timestamp` (UTC), `level`, `logger`, `message`, `request_id`, `user_id`,
  `company_id`; linia dostępu (`logger: app.access`) z `method`, `path` (bez
  query string), `status`, `duration_ms`, `client_ip`. Hasła, tokeny, sekrety,
  nagłówki `Authorization`/`Cookie` i dane logowania w URL-ach są maskowane
  (`[REDACTED]`).
- `web` (nginx): log dostępu w JSON z tym samym `request_id`.
- `request_id` = nagłówek `X-Request-ID` odpowiedzi = `audit_log.request_id`
  — pozwala połączyć linię logu, wpis audytu i zgłoszenie użytkownika.
- Podgląd: `docker compose logs -f api`. Rotacja: sterownik `json-file`
  Dockera — ustaw w `/etc/docker/daemon.json`:
  `{"log-driver":"json-file","log-opts":{"max-size":"50m","max-file":"10"}}`,
  albo wyślij logi do SIEM (sterownik `syslog`/`gelf`/`fluentd`).
- Logi aplikacyjne nie zastępują dziennika audytu — źródłem prawdy o
  operacjach na danych jest `audit_log`.

## 14. Rotacja sekretów

| Sekret | Procedura | Skutek |
|---|---|---|
| hasło `app_rw` | `docker compose exec db psql -U postgres -c "ALTER ROLE app_rw PASSWORD '...'"`, zmień `APP_RW_PASSWORD` i `DATABASE_URL` w `.env`, `docker compose up -d api worker` | krótka przerwa API |
| hasło `app_owner` | jw. dla `app_owner`, `APP_OWNER_PASSWORD`, `MIGRATIONS_DATABASE_URL` | brak (używane tylko przy migracjach) |
| hasło `postgres` | `ALTER ROLE postgres PASSWORD '...'`, `POSTGRES_PASSWORD` w `.env`, `docker compose --profile backup up -d backup` | brak |
| `AUTH_JWT_SECRET` | nowa wartość w `.env`, `docker compose up -d api worker` | wszyscy użytkownicy logują się ponownie |
| hasło użytkownika | reset przez administratora w aplikacji | hasło tymczasowe, zmiana wymuszona |

`POSTGRES_PASSWORD`/`APP_*_PASSWORD` są czytane przez skrypt init tylko przy
pierwszym starcie wolumenu — późniejsza zmiana w `.env` bez `ALTER ROLE` nie
działa. Po każdej rotacji sprawdź `docker compose ps` (healthy).

## 15. Lista kontrolna bezpieczeństwa produkcji

- [ ] `APP_ENV=prod`, `AUTH_MODE=local`, `DEV_AUTH_SECRET` puste
- [ ] wszystkie hasła i klucze losowe (≥ 32 znaki), różne od przykładów; `.env` z prawami `600`, poza repozytorium
- [ ] pierwszy administrator utworzony `create-admin`, hasło tymczasowe zmienione; brak danych `seed`
- [ ] TLS na proxy przed `web`, przekierowanie HTTP→HTTPS, `NGINX_HSTS` ustawione
- [ ] `NGINX_TRUSTED_PROXIES` = adres proxy TLS (IP klientów w audycie i limitach), proxy ustawia `X-Forwarded-Proto https`
- [ ] z zewnątrz dostępny tylko port proxy (443); porty 8000/5432/6379 tylko `127.0.0.1` lub usunięte; firewall
- [ ] `curl -sI https://…/` pokazuje CSP, HSTS, X-Content-Type-Options; `…/api/v1/health` → 200
- [ ] limity żądań dopasowane do liczby użytkowników za NAT
- [ ] `ATTACHMENT_ALLOWED_TYPES` przejrzane (bez `text/html`, `image/svg+xml`, plików wykonywalnych)
- [ ] kopie zapasowe: usługa `backup` lub cron, kopie poza serwerem, odtworzenie próbne wykonane i udokumentowane
- [ ] monitoring kopii: status usługi `backup` (`healthy`/`unhealthy`) w systemie monitoringu z alertem; przy cronie — alert na kod wyjścia
- [ ] szyfrowanie kopii: `BACKUP_AGE_RECIPIENT` ustawione (zalecane w produkcji — kopie zawierają skróty haseł i dane osobowe), klucz prywatny poza serwerem (sejf + kopia offline), odtworzenie próbne z `*.age` wykonane
- [ ] `verify-audit --global` i dla każdej spółki → spójny; worker działa (weryfikacja nocna)
- [ ] rotacja logów Dockera lub wysyłka do SIEM; `LOG_FORMAT=json`
- [ ] aktualizacje obrazów bazowych (postgres, redis, nginx, python) w planie utrzymania
