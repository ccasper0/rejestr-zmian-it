# Lista funkcjonalności — Rejestr zmian IT

Zwięzły przegląd funkcji aplikacji (stan: Etap 8). Szczegóły obsługi:
[instrukcja obsługi](instrukcja-obslugi.md); wdrożenie:
[deployment.md](deployment.md); specyfikacja: [CLAUDE.md](../CLAUDE.md);
decyzje: [docs/decisions](decisions/) (ADR).

Odwołania do norm wskazują, które wymagania dana funkcja **wspiera** — sama
aplikacja nie zapewnia zgodności, potrzebny jest także proces organizacyjny.
Skróty: **ISO** = ISO/IEC 27001:2022 Załącznik A; **uoKSC** = ustawa o
krajowym systemie cyberbezpieczeństwa.

---

## 1. Rejestr i cykl życia zmian

- **Rejestr zmian per spółka** — lista z kafelkami („Do zatwierdzenia”,
  „Zatwierdzone niewdrożone”, „Awaryjne (30 dni)”, „Wdrożone bez
  weryfikacji”), wyszukiwaniem, filtrami (okres wg rejestracji lub wdrożenia,
  kategoria, obiekt, status, typ, wykonawca, kto faktycznie zatwierdził),
  sortowaniem, stronicowaniem i oznaczeniem odstępstw. Filtry w adresie URL.
  ISO A.8.32. ADR 0013, 0014.
- **Numeracja zmian** `CHG-{PREFIKS}-{RRRR}-{NNNN}` — nadawana przy
  utworzeniu szkicu, osobno per spółka, od nowa co rok, bez luk z wyścigów
  (blokada licznika w transakcji). ADR 0013 §2.
- **Maszyna stanów** — Szkic → Do zatwierdzenia → Zatwierdzona → Wdrożona →
  Zweryfikowana oraz Odrzucona, Wycofana, Anulowana; zwrot do poprawy;
  przejścia wyłącznie przez akcje serwera, z kontrolą osoby wykonującej
  (zgłaszający, wykonawca, wskazany zatwierdzający, weryfikujący, właściciel
  CI). ISO A.8.32. ADR 0012.
- **Zasada czterech oczu** — zatwierdzający ≠ zgłaszający i ≠ wykonawca
  (kontrola przed wysłaniem, akcje, ograniczenie w bazie); zgłaszającego nie
  da się zmienić. ISO A.5.3, A.8.32. ADR 0012 §4.
- **Weryfikacja po wdrożeniu** — weryfikujący inny niż wykonawca; wyjątek z
  ostrzeżeniem w audycie, gdy w spółce nie ma innej uprawnionej osoby.
  ISO A.8.32. ADR 0012 §6.
- **Zmiany standardowe** — automatyczne zatwierdzenie przez `system`, gdy
  kategoria/podkategoria nie wymaga zatwierdzenia ani zgody właściciela CI;
  rozróżnienie „zatwierdzający wskazany” vs „kto faktycznie zatwierdził”.
  ISO A.8.32. ADR 0012 §3–4.
- **Zmiany awaryjne** — wdrożenie przed zatwierdzeniem, zatwierdzenie po
  fakcie w ciągu 24 h; brak zatwierdzenia lub spóźnione zatwierdzenie =
  odstępstwo; weryfikacja dopiero po zatwierdzeniu. ISO A.8.32. ADR 0012.
- **Zgoda właściciela CI** (np. systemy OT) — wymagana dla każdego obiektu
  zmiany przed zatwierdzeniem; unieważniana przy zwrocie do poprawy i zmianie
  właściciela. ISO A.8.32. ADR 0011 §3, ADR 0012 §5.
- **Kontrola przed wysłaniem** (`/readiness`) — jedna implementacja reguł
  kompletności (pola, kategoria, CI, plan wycofania i okno przy wysokim
  ryzyku, okno w przyszłości poza awaryjnymi, wykonawca, zatwierdzający,
  wymagania uoKSC) dla panelu UI, wysłania, wdrożenia awaryjnego i ponownie
  przy zatwierdzeniu. ISO A.8.32; uoKSC. ADR 0012 §2–3.
- **Zamrożenie** od statusu „Wdrożona” (oraz Odrzucona/Anulowana); wąskie
  wyjątki: przepięcie weryfikującego lub zatwierdzającego, który stracił
  uprawnienia — z wpisem w audycie. Korekta = nowa zmiana wskazująca oryginał
  (`supersedes_change_id`). ISO A.8.32, A.5.33. ADR 0012 §6.
- **Korekta zamrożonej zmiany z karty** — „Utwórz korektę” (edytor,
  zatwierdzający) tworzy szkic wskazujący oryginał, ze skopiowanymi polami
  merytorycznymi, obiektami i osobami (bez okna serwisowego); karta i
  formularz korekty pokazują numer oryginału z odnośnikiem, a karta oryginału
  — „Skorygowana przez” z odnośnikami i statusami korekt. ADR 0021.
- **Migawka obiektów** z chwili wdrożenia na karcie zmiany. ADR 0011 §9.
- **Optymistyczne blokowanie** — wersja zmiany (`If-Match`/pole), konflikt
  409 z porównaniem różnic w formularzu; zatwierdzenie wymaga wersji (428).
  ADR 0013 §7.
- **Formularz zmiany** — 4 sekcje, dodawanie CI w locie, podpowiedź
  domyślnego zatwierdzającego (kategoria w spółce → spółka), walidacja inline,
  autozapis co 30 s, zapis przy wyjściu. ADR 0014.
- **Komentarze** — tylko dopisywane (bez edycji i usuwania), w każdym
  statusie. ISO A.8.15. ADR 0013.
- **Załączniki-dowody** — sha256 każdego pliku, bez nadpisywania (nowa
  wersja = nowy rekord), limit rozmiaru (domyślnie 25 MiB), whitelist typów
  rozpoznawanych z zawartości pliku, każde pobranie w audycie, pobieranie
  zawsze jako plik. ISO A.8.32, A.5.28. ADR 0013 §4, ADR 0019 §3.
- **Odstępstwa** — wyliczane jedną funkcją dla rejestru i raportów: awaryjna
  bez zatwierdzenia w 24 h, wdrożona bez weryfikacji, wdrożona poza oknem,
  wycofana, zatwierdzona przez autora (błąd krytyczny). ISO A.8.32.
  ADR 0012 §7.

## 2. Klasyfikacja

- **Kategorie zmian** — słownik globalny, 2 poziomy, flagi „wymaga
  zatwierdzenia” i „wymaga zgody właściciela CI”, domyślne ryzyko; podkategoria
  może tylko zaostrzyć wymogi. Słownik startowy (ACC, NET, FW, SRV, PATCH, BKP,
  GPO, APP, SEC, OT). ADR 0011.
- **Kategorie per spółka** — wybór kategorii dostępnych w spółce i
  zatwierdzający dla kategorii (zastępuje domyślnego zatwierdzającego
  spółki). ADR 0011 §4.
- **Typ** (standardowa / normalna / awaryjna), **ryzyko** (niskie / średnie
  / wysokie), obiekty CI, osoby (zgłaszający, wykonawca, zatwierdzający,
  weryfikujący), okno serwisowe, numer zgłoszenia, podstawa/wymóg.
  ISO A.8.32.
- **Podmioty uoKSC** — flaga spółki wymuszająca podstawę/wymóg i weryfikującego
  w każdej zmianie. uoKSC.

## 3. Inwentarz obiektów (CI)

- **Typy obiektów** — słownik globalny (serwer, VM, urządzenie sieciowe,
  firewall, konto, grupa, aplikacja, system OT, inne + własne). ADR 0011.
- **Obiekty per spółka** — identyfikator unikalny w spółce (bez względu na
  wielkość liter), nazwa, opis, typ, właściciel; wyszukiwanie i filtry; bez
  usuwania — dezaktywacja. ISO A.5.9, A.8.9. ADR 0011.
- Każda operacja na CI w dzienniku audytu spółki. ISO A.8.15.

## 4. Wiele spółek (multi-tenancy)

- **Izolacja spółek w aplikacji** — kontekst spółki sprawdzany dla każdego
  żądania; zasób innej spółki = 404 (bez ujawniania istnienia), odmowa
  zapisywana w audycie. ISO A.8.3. ADR 0008.
- **Row-Level Security w PostgreSQL** na wszystkich tabelach z `company_id`
  (zakres spółek ustawiany w każdej transakcji); jawne, nazwane ścieżki
  administracyjne. ISO A.8.3. ADR 0008.
- **Spółki** — dodawanie, edycja, prefiks niezmienny, archiwizacja zamiast
  usuwania (rejestr i inwentarz tylko do odczytu, historia dostępna).
  ADR 0007, 0015.
- **Przełącznik spółki** i spółka w adresie (`/c/{PREFIKS}/…`); widok
  „Wszystkie spółki (audytor)” dla raportu zbiorczego. ADR 0002, 0014.

## 5. Uprawnienia (RBAC)

- **Role per spółka**: edytor, zatwierdzający, audytor, obserwator (kilka
  ról naraz); globalnie: administrator aplikacji. ISO A.5.15, A.5.18.
- **Jedno źródło prawdy** (`app/permissions.py`) — każdy endpoint deklaruje
  akcję; testy całej macierzy; macierz tylko do odczytu w UI
  (`GET /permissions/matrix`). ISO A.5.15. ADR 0015.
- **Rozdział obowiązków** — administrator nie jest automatycznie edytorem ani
  zatwierdzającym; nadanie roli samemu sobie trafia do audytu. ISO A.5.3,
  A.8.2. ADR 0007.
- **Podgląd administratora bez roli** — rejestr, karty, kontrola, ścieżka
  audytu, lista załączników tylko do odczytu (bez akcji, edycji, komentarzy
  i pobierania plików); eksport i inwentarz CI nazwaną ścieżką z audytem.
  ISO A.8.2. ADR 0016, ADR 0017 §4.
- **Akcje na zmianie** — matryca + reguły maszyny stanów (autor, wykonawca,
  wskazany zatwierdzający, cztery oczy, właściciel CI); karta zwraca
  `allowed_actions` i `editable_fields`, UI pokazuje tylko dozwolone.
  ADR 0012, 0013.

## 6. Audyt i integralność

- **Niemodyfikowalny dziennik** (`audit_log`) — wpis w tej samej transakcji
  co operacja (część serwisu, nie middleware); każdy endpoint modyfikujący
  tworzy wpis (test). ISO A.8.15. ADR 0005, 0006.
- **Łańcuch skrótów SHA-256** — osobny łańcuch per spółka + łańcuch
  globalny, kanoniczny JSON, blokada głowy łańcucha (brak rozwidleń przy
  równoległych zapisach). ISO A.8.15, A.5.33. ADR 0006.
- **Ochrona w bazie** — rola aplikacji `app_rw` ma na `audit_log`,
  komentarzach i załącznikach tylko INSERT/SELECT; triggery blokują UPDATE i
  DELETE; migracje osobną rolą `app_owner`. ISO A.8.15. ADR 0005, 0006.
- **Co jest logowane** — zmiany (diff „przed → po”, przejścia z
  komentarzem), CI, spółki, słowniki, role, konta, załączniki (sha256),
  pobrania, komentarze, eksporty (numer, `data_sha256`), logowania, nieudane
  logowania (agregacja w oknach czasowych — żadna próba nie ginie), odmowy
  dostępu; nigdy hasła ani tokeny. Aktor z rolami, IP, `request_id`.
  ISO A.8.15. ADR 0010, ADR 0018 §7.
- **Weryfikacja łańcucha** — API (`POST /audit/verify`), CLI
  (`verify-audit --company/--global`, kod wyjścia), automatycznie raz na dobę
  w workerze; wynik sam trafia do dziennika. ISO A.8.15. ADR 0009.
- **Znacznik „Łańcuch spójny”** na karcie zmiany (spójny / naruszony /
  nieaktualny / niezweryfikowany). ADR 0013 §11.
- **Przegląd dziennika** (`GET /audit`) z filtrami — audytor (swoje spółki),
  administrator (każda spółka, łańcuch globalny). ISO A.8.15, A.8.16.
  ADR 0009, 0015.
- **Ścieżka audytu zmiany** na karcie (z załącznikami, diffami i skrótami).
  ADR 0013.

## 7. Raporty i eksport

- **Raport rejestru PDF** — 9 sekcji (nagłówek, kafelki, zakres i filtry,
  tabela, odstępstwa, Załącznik A per kategoria i CI, opcjonalny Załącznik B
  z pełną ścieżką audytu, wynik weryfikacji łańcucha, podpisy); A4, fonty
  IBM Plex osadzone (polskie znaki), „Strona X z Y”. ISO A.8.32, A.8.15.
  ADR 0017.
- **Karta zmiany PDF** — wszystkie pola, osoby, oś czasu statusów, zgody
  właścicieli CI, załączniki z sha256, komentarze, pełny audit trail.
  ADR 0017 §5.
- **Raport zbiorczy audytora** — wszystkie spółki z rolą audytora, numer
  `RAP-{RRRR}-{NNNN}`, wpis w łańcuchu każdej objętej spółki. ADR 0017 §2, §6.
- **CSV rejestru** — UTF-8 z BOM, separator `;`, ochrona przed wstrzyknięciem
  formuł, numerowany i audytowany. ADR 0017 §7.
- **Integralność raportów** — `data_sha256` (skrót danych, w stopce, w
  `report_exports` i w audycie) i `file_sha256` (sprawdzany przy każdym
  pobraniu; zmieniony plik nie jest wydawany, próba audytowana); każde
  pobranie w audycie; numeracja `RAP-{PREFIKS}-{RRRR}-{NNNN}`. ISO A.5.28,
  A.8.15. ADR 0017.
- **Generowanie w tle** (arq + Redis) dla raportów > `REPORT_ASYNC_THRESHOLD`
  (200) zmian, odpytywanie statusu, sprzątanie zawieszonych zadań; limit
  `REPORT_MAX_CHANGES` (5000). ADR 0017 §8, §14.
- **Ekran raportów** — formularz parametrów i lista wygenerowanych raportów
  (numer, okres, autor, czas, sha256, pobieranie). ADR 0017 §13.

## 8. Administracja

- **Spółki** — tabela z licznikami (obiekty, edytorzy, zatwierdzający), panel
  nowej spółki z podglądem numeru, NIP z sumą kontrolną, domyślny
  zatwierdzający, kategorie spółki, flaga uoKSC, archiwizacja z
  potwierdzeniem. ADR 0015.
- **Słowniki** — kategorie zmian i typy CI: dodawanie, edycja, dezaktywacja;
  kody niezmienne. ADR 0011, 0015.
- **Użytkownicy** — katalog ze stanem konta (hasło, wymagana zmiana,
  blokada), zakładanie kont lokalnych z jednorazowo pokazywanym hasłem
  tymczasowym, reset hasła (odblokowanie, koniec sesji), zmiana nazwy,
  dezaktywacja i aktywacja, nadawanie/odbieranie uprawnień administratora
  (ochrona ostatniego administratora i własnego konta). ISO A.5.16, A.5.18,
  A.8.2. ADR 0018 §5, ADR 0020 §5.
- **Role w spółkach** — nadawanie z karty użytkownika i z panelu spółki,
  kilka ról naraz, ostrzeżenie przy nadawaniu roli sobie. ISO A.5.18.
  ADR 0015.
- **Macierz uprawnień** tylko do odczytu. ADR 0015.
- **CLI**: `seed-dictionaries` (słowniki startowe, także produkcja),
  `create-admin` (pierwszy administrator), `verify-audit`, `seed` (dane
  przykładowe, tylko dev). ADR 0018 §8.

## 9. Uwierzytelnianie i bezpieczeństwo

- **Konta lokalne z hasłem** (`AUTH_MODE=local`) — e-mail jako login, hasła
  argon2id (parametry OWASP, automatyczne podnoszenie parametrów),
  normalizacja NFKC. ISO A.5.17, A.8.5. ADR 0018.
- **Polityka haseł** (NIST SP 800-63B) — 12–128 znaków, bez prostych ciągów,
  bez e-maila i nazwiska, lista popularnych haseł, inne niż obecne; bez reguł
  składu i bez okresowej zmiany. ISO A.5.17. ADR 0018 §3.
- **Hasło tymczasowe** generowane przez serwer (~113 bitów), pokazywane raz,
  wymuszona zmiana przy pierwszym logowaniu (do tego czasu dostęp tylko do
  `/me`, zmiany hasła i wylogowania), **wygasa po 7 dniach**
  (`TEMP_PASSWORD_TTL_HOURS`; wraz z nim kończy się otwarta nim sesja).
  ISO A.5.17. ADR 0018 §5, §12.
- **Blokada konta** po 5 błędnych hasłach na 15 min; **limit nieudanych
  logowań z sieci** (30 / 5 min); identyczna odpowiedź dla wszystkich
  przyczyn porażki (brak enumeracji kont). ISO A.8.5. ADR 0018 §6.
- **Sesje** — token dostępu JWT 15 min, token odświeżania jednorazowy
  (rotacja, wykrycie ponownego użycia odwołuje sesję), bezczynność 120 min,
  maks. 12 h; sesja sprawdzana przy każdym żądaniu (wylogowanie, reset,
  dezaktywacja działają natychmiast). ISO A.8.5. ADR 0018 §4, ADR 0020.
- **Tryb deweloperski** (`AUTH_MODE=dev`) z użytkownikami testowymi —
  odrzucany przy `APP_ENV=prod`. ADR 0007, 0014.
- **Rate limiting w nginx** — limity żądań per IP (API, logowanie/zmiana
  hasła, odświeżanie), limit połączeń; odpowiedzi 429/413/503 w formacie
  problem+json. ISO A.8.6, A.8.5. ADR 0019 §1.
- **Nagłówki bezpieczeństwa** — CSP bez zewnętrznych źródeł (CanvasKit
  lokalnie, build Fluttera z `--csp`), `X-Content-Type-Options`,
  `Referrer-Policy`, `X-Frame-Options`, COOP/CORP, `Permissions-Policy`,
  HSTS po włączeniu TLS; restrykcyjna CSP i `no-store` dla API. ISO A.8.26.
  ADR 0019 §2.
- **Prawdziwy adres IP klienta** w audycie i limitach — zaufany tylko nginx,
  obsługa proxy TLS. ADR 0004, ADR 0019 §5.
- **Logi aplikacyjne JSON** (api, worker) z `request_id` wspólnym dla nginx,
  API i dziennika audytu; maskowanie haseł, tokenów i sekretów. ISO A.8.15,
  A.8.16. ADR 0019 §4.
- **Błędy w formacie RFC 9457** (`application/problem+json`) z kodami po
  angielsku i komunikatami po polsku. CLAUDE.md §8.

## 10. Wdrożenie i eksploatacja

- **Docker Compose** — `db` (PostgreSQL 16), `redis`, `migrate` (Alembic jako
  `app_owner`), `api`, `worker`, `web` (nginx + build Fluttera), opcjonalnie
  `backup`; healthcheck `/api/v1/health`. ADR 0004. [deployment.md](deployment.md).
- **Kopie zapasowe** — `scripts/backup.sh|ps1`: `pg_dump`, archiwum plików
  (załączniki, raporty), sumy SHA-256, retencja; usługa `backup` codziennie;
  opcjonalne szyfrowanie programem `age` (strumieniowo, klucz prywatny poza
  serwerem). ISO A.8.13, A.8.24. ADR 0019 §10.
  **Odtworzenie** `scripts/restore.sh|ps1` z weryfikacją sum i łańcuchów
  audytu; tryb próbny do osobnej bazy. ISO A.8.13. ADR 0019 §6.
- **Migracje Alembic** odwracalne (triggery audytu — tylko `app_owner`).
- **CI (GitHub Actions)** — ruff, mypy, pytest na PostgreSQL 16, flutter
  analyze/test/build, test dymny stosu Docker (nagłówki, 415, logi JSON, 429).
  ADR 0019 §7.
- **Konfiguracja** wyłącznie przez zmienne środowiskowe opisane w
  `.env.example`; brak sekretów w repozytorium.

## 11. Interfejs

- Aplikacja webowa (Flutter web) po polsku; czas `Europe/Warsaw`, format
  `dd.MM.yyyy HH:mm`; fonty IBM Plex Sans / Mono.
- Ekrany: logowanie i zmiana hasła, rejestr, karta zmiany, formularz zmiany,
  obiekty (CI), raporty i eksport, dziennik audytu, administracja (spółki,
  kategorie, typy CI, role i uprawnienia, użytkownicy).
- Układ responsywny (panel nawigacji zwija się na wąskim ekranie),
  komunikaty o limitach żądań i niedostępności serwera dla całej aplikacji.
  ADR 0014, 0020.

---

## Poza zakresem / ograniczenia

- **Brak SSO** (Microsoft Entra ID / OIDC) — decyzja właściciela z
  2026-11-03, tylko konta lokalne. ADR 0018 §1.
- **Brak samodzielnej rejestracji i resetu hasła e-mailem** — konta i resety
  wykonuje administrator; aplikacja nie wysyła e-maili ani powiadomień.
- **Brak zmiany e-maila (loginu)** — ani przez użytkownika, ani przez
  administratora. ADR 0018 §5, §12.
- **Brak MFA** (uwierzytelniania wieloskładnikowego).
- **Brak usuwania danych** — zmiany się anuluje, obiekty, kategorie, typy i
  konta dezaktywuje, spółki archiwizuje; komentarzy, załączników, raportów i
  wpisów audytu nie można edytować ani usuwać. Archiwizacji spółki nie można
  cofnąć w aplikacji.
- **Brak zbiorczego rejestru wielu spółek** — tylko raport zbiorczy PDF
  audytora. ADR 0017 §13.
- **Raport zbiorczy** tylko dla roli audytora (administrator bez tej roli go
  nie generuje). ADR 0017 §12.
- **Limity raportów** — maks. 5000 zmian w raporcie/CSV; Załącznik B do 1000
  wpisów na zmianę (z oznaczeniem obcięcia). ADR 0017.
- **Sesja per karta przeglądarki** (`sessionStorage`) — nowa karta wymaga
  zalogowania. ADR 0014, 0020.
- **TLS** — kontener nie terminuje TLS; wymagane zewnętrzne proxy (HSTS po
  jego włączeniu). [deployment.md](deployment.md) §5.
- **Docker Desktop** (Windows/macOS) nie przekazuje prawdziwego IP klienta —
  do audytu i limitów w produkcji Linux. ADR 0019 §5.
- **Fonty zastępcze** (np. emoji) są blokowane przez CSP — znaki spoza IBM
  Plex mogą się nie wyświetlać. ADR 0019 §2.
