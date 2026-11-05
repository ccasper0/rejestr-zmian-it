# 0014. Frontend Etapu 5: logowanie, stan, rejestr, karta, formularz, czas, tabela

- Status: przyjęta; poprawki po recenzji Etapu 5 (2026-10-30) w §13; punkty z §12 rozstrzygnięte przy akceptacji Etapu 5 (2026-10-30)
- Data: 2026-10-30
- Dotyczy: CLAUDE.md §8, §10.1–10.3, §11.6, §12 (Etap 5); `frontend/lib/**`; ADR 0001, 0002, 0003, 0007, 0012, 0013
- Uzupełnienie (Etap 8): OIDC z §1 nie powstanie — logowanie kontami lokalnymi (e-mail + hasło, odświeżanie tokenów) opisują ADR 0018 i ADR 0020

Kontraktem API jest kod backendu (`backend/app/api/v1/*.py`, `backend/app/schemas/*.py`). Modele we frontendzie (`features/changes/data/models.dart`) odwzorowują te schematy 1:1 (freezed + json_serializable, `field_rename: snake` w `build.yaml`).

## 1. Logowanie i sesja

- **Abstrakcja `AuthProvider`** (`core/auth/auth.dart`, klasa `sealed`): `DevAuthProvider` (zaimplementowany) i `OidcAuthProvider` (punkt rozszerzenia). Ekran `/login` dobiera widok do implementacji.
- **Wybór trybu:** `--dart-define=AUTH_MODE=dev|oidc` wymusza tryb. Domyślnie (`auto`) aplikacja pyta API: `GET /auth/dev/users` istnieje tylko przy `AUTH_MODE=dev` w backendzie (poza nim trasa nie jest montowana, 404 — ADR 0007 §1). Źródłem prawdy pozostaje backend: ten sam build (np. obraz `web`) w środowisku produkcyjnym nigdy nie pokaże logowania deweloperskiego, a w lokalnym nie trzeba pamiętać o dodatkowym `--dart-define`. Inny błąd niż 404 (sieć, 5xx) jest pokazywany z „Spróbuj ponownie”, nie jest traktowany jak OIDC.
- **Dev:** lista z `GET /auth/dev/users` → `POST /auth/dev/token` → `AuthToken(access_token, expires_at = teraz + expires_in)`.
- **Token:** w pamięci (`AuthController`, Riverpod) i w `sessionStorage` (klucz `rejestr.auth`), żeby przeładowanie karty nie wylogowywało. `sessionStorage` jest per karta i znika po jej zamknięciu (w przeciwieństwie do `localStorage`). Ryzyko: skrypt wstrzyknięty w origin aplikacji (XSS) może odczytać token — to samo dotyczy tokenu w pamięci JS; ochroną jest CSP (Etap 8). Token uznajemy za wygasły minutę przed `expires_at`.
- **Bearer i 401:** `AuthInterceptor` (dio) dokleja `Authorization` do każdego żądania poza `/auth/*`. Odpowiedź 401 kończy sesję (`sessionExpired`) i router przenosi na `/login` z komunikatem „Sesja wygasła…”. Po zalogowaniu wracamy pod adres z `?from=` — przyjmowane są tylko ścieżki lokalne (`/…`, nie `//…`), bez otwartego przekierowania.
- **OIDC (Entra ID, authorization code + PKCE) — niezaimplementowane.** Wymaga decyzji, których nie da się bezpiecznie zgadnąć: tenant/issuer, `client_id` aplikacji SPA, redirect URI (proponowane `/auth/callback`), scope API (`api://…/access` zgodny z `OIDC_AUDIENCE` backendu), odnawianie tokenu (refresh token w SPA vs ponowne logowanie). Propozycja na Etap 8: `OidcAuthProvider` z własną implementacją PKCE (`package:web` + `crypto`) albo `oidc`/`msal`-podobnym pakietem po ocenie, konfiguracja przez `--dart-define` (`OIDC_ISSUER`, `OIDC_CLIENT_ID`, `OIDC_SCOPE`), token tylko w pamięci + ciche odnowienie. Do tego czasu tryb OIDC pokazuje komunikat „Logowanie kontem organizacji nie jest jeszcze dostępne”.

## 2. Spółka w URL i `/me`

- `GET /me` (`meProvider`, przeładowywany przy zmianie tokenu) daje członkostwa; prefiks z URL (`/c/{prefix}/…`) jest tłumaczony na `company_id` używane w API. Nieznany prefiks albo brak członkostwa → „Brak dostępu” (bez rozróżniania, jak 404 w API, §7.3).
- `/` przenosi do pierwszej spółki; admin bez członkostw — do `/admin/companies`; użytkownik bez ról — komunikat.
- Przełącznik spółki pokazuje członkostwa (z oznaczeniem archiwum) i opcję „Wszystkie spółki (audytor)” dla użytkownika z rolą audytora (ADR 0002).
- **`/c/all` (luka API):** nie ma endpointu zbiorczego rejestru (Etap 7: raport zbiorczy PDF pod `/c/all/reports`, ADR 0017 §13). Widok `all` pokazuje listę spółek audytora z przejściem do ich rejestrów i informację, że zestawienie zbiorcze będzie w „Raporty i eksport” (Etap 7, `POST /reports` z `company_id = null`). Nie udajemy rejestru scalonego z N zapytań (paginacja i sortowanie między spółkami byłyby niepoprawne).
- Licznik „Do zatwierdzenia” w panelu = `stats.pending_approval` bieżącej spółki; `/c/:prefix/approvals` przekierowuje do rejestru z filtrem `status=pending_approval`.

## 3. Zarządzanie stanem

- Riverpod 3: dane serwera jako `FutureProvider.autoDispose.family` z kluczami-rekordami (`(companyId, number)`, `(companyId, RegisterFilters)`), więc ekran po ponownym otwarciu pobiera świeże dane. Po każdej akcji/komentarzu/zapisie karta unieważnia: kartę, ścieżkę audytu, załączniki, znacznik łańcucha i kafelki.
- Stan formularza jest lokalny (`ChangeFormController`, `ChangeNotifier`) — to stan edycji, nie cache serwera.
- Ponawianie (Riverpod domyślnie ponawia błędy) tylko dla błędów przejściowych (sieć, 5xx), maks. 2 razy; 4xx (403/404/409/422) są ostateczne (`retryTransient` w `main.dart`).
- Zależności testowalne przez nadpisania: `httpClientAdapterProvider` (fałszywy adapter dio), `tokenStorageProvider`, `authModeSettingProvider`, `fileServiceProvider`, `initialLocationProvider`.

## 4. Strefa czasowa

- UI: zawsze `Europe/Warsaw`, `dd.MM.yyyy HH:mm` (`core/time.dart`, `WarsawTime`), niezależnie od strefy przeglądarki; API: ISO 8601 UTC z `Z`. Pola okna serwisowego są wybierane jako czas polski i zamieniane na UTC.
- Pakiet `timezone` z **pełną** bazą IANA (`data/latest.dart`): wariant `latest_10y` kończy się ok. 2031 r. i po tej dacie gubi czas letni. Ograniczenie pakietu: pełna baza ma reguły do 2037 r. (po nim przesunięcie stałe, bez DST) — do przeglądu przy aktualizacjach pakietu. Odrzucono `Intl.DateTimeFormat` przeglądarki przez JS interop: wynik zależy od wersji ICU przeglądarki i nie da się go przetestować na VM.
- Testy: przejście na czas letni (29.03.2026) i zimowy (25.10.2026, dwukrotna 02:30), niezależność od strefy maszyny, granice dni w filtrze okresu.

## 5. Rejestr (§10.1)

- Jedynym stanem ekranu są filtry w query stringu (`RegisterFilters`, freezed — głęboka równość jako klucz providera). Mapowanie URL → API:

| URL | API |
|---|---|
| `q`, `status`*, `type`*, `category`*, `ci`*, `assignee`, `approved_by` (`id` lub `system`) | to samo |
| `from`, `to` (dni `yyyy-MM-dd` czasu polskiego, oba włącznie) | `period_from` = początek dnia `from`, `period_to` = początek dnia po `to` (API: wyłącznie) |
| `period_by` (`created` domyślnie / `implemented`) | `period_by` |
| `sort` (domyślnie `-created_at`) | `sort` |
| `page` (od 1, 50 na stronę) | `offset`, `limit` |

  `*` = parametr powtarzalny (`status=a&status=b`). Wartości niepoprawne są pomijane; domyślne nie trafiają do URL. Wyszukiwarka zapisuje URL po 400 ms bezczynności.
- Kafelki z `GET /stats` są skrótami do filtrów (np. „Awaryjne (30 dni)” → `type=emergency&from=…`); kafelek awaryjnych pokazuje też `emergency_not_approved_in_24h`.
- Kolumna „Zatwierdził” to **faktyczny** zatwierdzający (`approved_by`) albo „system (automatycznie)” przy `auto_approved` — nigdy wskazany `approver` (ADR 0012 §4).
- „Eksport PDF” i „CSV” są widoczne, nieaktywne, z podpowiedzią (Etap 7). „Nowa zmiana” — tylko editor/approver aktywnej spółki. *Etap 7:* przyciski eksportu działają i są widoczne tylko przy prawie `export.register` — ADR 0017 §13.

## 6. Karta zmiany (§10.2)

- Karta po numerze (`GET …/changes/by-number/{number}`). Przyciski akcji **wyłącznie** z `allowed_actions` (stała kolejność, nieznane przyszłe akcje też są pokazywane); „Edytuj”, gdy `editable_fields` niepuste; „Karta PDF” nieaktywna (Etap 7; od Etapu 7 aktywna wg `export.change_card` — ADR 0017 §13).
- Akcja = dialog potwierdzenia z komentarzem. Wymagalność komentarza w dialogu powiela ADR 0012 §2 tylko dla UX (`return`, `reject`, `rollback`, `cancel` poza szkicem); rozstrzyga backend. Zawsze wysyłamy `version` z karty (dla `approve` wymagane — zatwierdza się treść, którą się widziało). 409 `change.version_conflict` → komunikat i odświeżenie karty; 422 `change.not_ready` → lista nieprzechodzących checków; ostrzeżenia z odpowiedzi (`warnings`) w komunikacie.
- Pasek etapów: Szkic → Do zatwierdzenia → Zatwierdzona → Wdrożona → Zweryfikowana; etap pominięty przy auto-zatwierdzeniu i przy awaryjnej wdrożonej przed zatwierdzeniem („oczekuje na zatwierdzenie po fakcie”); stany boczne (odrzucona/wycofana/anulowana) jako osobna etykieta za etapem, na którym zmiana zeszła ze ścieżki.
- Ścieżka audytu (`GET …/audit`, wszystkie strony): czas + IP (mono), „kto (rola) — akcja” (aktor `system` przy `actor_id = null`), diff „przed → po” (stara wartość przekreślona na czerwono, nowa zielona; identyfikatory osób, kategorii i CI zamieniane na nazwy z karty i listy członków), komentarz i ostrzeżenia z `context`, `#seq` i skrót sha256 (pełny w podpowiedzi), wpis z `hash_valid = false` oznaczony. Znacznik w nagłówku z `GET /companies/{cid}/audit/status`: `ok` „Łańcuch spójny” (zielony), `stale` „Weryfikacja nieaktualna”, `broken` „Łańcuch naruszony”, `unknown` „Łańcuch niezweryfikowany” + `checked_at`.
- Zgody właścicieli CI: sekcja widoczna, gdy są zgody, akcja `consent` lub CI ze zgodą; `by_requester_or_assignee` oznaczone ostrzeżeniem dla zatwierdzającego, `valid = false` jako „zgoda nieważna”.
- Załączniki: pobieranie przez dio z nagłówkiem `Authorization` (zwykły link nie przeniesie tokenu) i zapis `Blob` w przeglądarce; każde pobranie audytuje backend.

## 7. Formularz (§10.3)

- `/c/:prefix/changes/new` od razu tworzy szkic (`POST`, numer nadany natychmiast) i przechodzi do `/c/:prefix/changes/:number/edit`. Nowa trasa edycji jest dopisana do CLAUDE.md §10.3.
- Pola spoza `editable_fields` są tylko do odczytu (np. approver w `pending_approval` zmienia tylko zatwierdzającego i okno).
- `PATCH` wysyła **tylko zmienione** pola (pusty tekst → `null`) i `version`. Autozapis co 30 s, gdy są niezapisane zmiany. 409 → baner konfliktu (z `current_version`), autozapis i wysyłka wstrzymane; rozstrzygnięcie — §13 pkt 2. Inne błędy zapisu — baner z komunikatem.
- Opuszczenie formularza: zob. §13 pkt 2 (zapis z `await` przed wyjściem, bez zapisu w tle). „Anuluj” pyta o odrzucenie niezapisanych zmian; szkic zostaje (anulowanie zmiany to akcja `cancel` na karcie).
- „Kontrola przed wysłaniem” renderuje `GET …/readiness` (odświeżane po każdym zapisie). Dotyczy wersji zapisanej — przy niezapisanych zmianach panel to sygnalizuje. Kliknięcie błędu przewija do pola.
- Walidacja inline powiela backend wyłącznie dla UX: plan wycofania i okno przy ryzyku wysokim, kompletność i kolejność okna, cztery oczy, długość tytułu.
- „Wyślij do zatwierdzenia” jest widoczne tylko z `submit` w `allowed_actions` i aktywne tylko bez błędów inline i przy `readiness.ok`; kliknięcie: zapis → ponowna kontrola → dialog → `submit` z wersją po zapisie.
- Osoby z `GET /companies/{id}/members` (deklaruje `register.view`, więc editor ma dostęp — luka z zadania nie występuje): wykonawca/weryfikujący — editor/approver, zatwierdzający — approver. Podpowiedź domyślnego zatwierdzającego z `suggested_approver_id`; przy zmianie standardowej w kategorii bez wymogu zatwierdzenia i zgody właściciela CI — informacja o automatycznym zatwierdzeniu (flagi z `GET /categories`).
- Kategorie: `GET /companies/{id}/categories` (dostępne w spółce) + podkategorie `GET /categories?parent_id=…&active=true`; wybór kategorii podpowiada jej domyślne ryzyko, jeśli ryzyko jest puste. CI: wyszukiwanie `GET /companies/{cid}/ci?q=&active=true`; „Nowy obiekt” (`POST …/ci`) dla ról z `ci.manage`.
- Strefa załączników: przycisk wyboru pliku (bez przeciągania — wymagałoby dodatkowego pakietu; do decyzji).

## 8. Tabela i zależności

- **`data_table_2` 2.8.0** (nie pluto_grid): zamiennik `DataTable` z Material, dziedziczy motyw aplikacji, wystarcza przy paginacji po stronie serwera (50 wierszy). pluto_grid ma własny model danych i motyw, edycję komórek i wirtualizację, których tu nie potrzebujemy. Wersja 3.0.0 przeszła na osobny pakiet `material_ui` i jej `DataCell` jest niezgodny typem z `flutter/material` — dlatego 2.8.0 (ta sama linia, Flutter ≥ 3.47).
- **`timezone` 0.11.2** (pkt 4), **`web` 1.1.2** (już tranzytywna; bezpośrednio dla `sessionStorage` i plików przez importy warunkowe `dart.library.js_interop`, z zaślepkami dla testów na VM).
- Nowe zależności są przypięte dokładnie (`timezone: 0.11.2` itd.), pozostałe jak dotąd przez `pubspec.lock` (ADR 0003 przypina Fluttera 3.47.5).

## 9. Błędy API

`ApiProblem.from()` (`core/api_error.dart`): znany `code` → polski komunikat z tabeli; inaczej polski `detail` z API; inaczej tekst wg statusu HTTP; błędy sieci osobno. Gdy `detail` wnosi coś ponad komunikat (np. które CI), jest pokazywany jako szczegół, razem z `request_id` w panelach błędów. Dostępne są też rozszerzenia (`checks`, `fields`, `current_version`).

## 10. Dostępność i wygląd

Kolory i promienie wyłącznie z `core/theme.dart` (doszły tokeny diffu i palety komunikatów oparte na parach statusów §10 — kontrast ≥ 4.5:1); IBM Plex Sans, a numery, daty, skróty i identyfikatory CI w IBM Plex Mono; przyciski ≥ 44 px; poniżej 900 px panel jest szufladą, karta i formularz przechodzą na jedną kolumnę, tabela przewija się poziomo. Wskaźnik „API: połączono” ma wersję w drugiej linii (wcześniej był ucinany w panelu 232 px).

## 11. Testy

`test/features/`: formularz (plan wycofania przy wysokim ryzyku — inline i blokada wysyłki, okno przy wysokim ryzyku, wysyłka zablokowana przy błędach readiness, karty typu, zapis tylko zmian z wersją, autozapis 30 s, konflikt 409 i przeładowanie, pola tylko do odczytu, cztery oczy, nowy szkic, anulowanie), karta (przyciski tylko z `allowed_actions`, wersja w akcji, komentarz wymagany, 409, 422 z checkami, diff i aktor w audycie, znacznik łańcucha, zgoda niezależna, faktyczny zatwierdzający, wąski ekran), rejestr (URL → API, UI → URL, sortowanie i stronicowanie, przejście do karty, brak „Nowa zmiana” dla viewera), logowanie (przekierowanie i powrót, 404 → OIDC, 401 → wylogowanie, wylogowanie); `test/core/`: czas (DST), błędy API, filtry. API jest mockowane adapterem dio (`test/helpers.dart`, `FakeApi`).

## 12. Decyzje właściciela (akceptacja Etapu 5, 2026-10-30)

Właściciel zaakceptował etap bez zmian, więc obowiązują warianty domyślne: (1) OIDC w Etapie 8 — dane tenanta i decyzja o refresh tokenie wtedy; (2) `sessionStorage`; (4) widok zbiorczy audytora jako raport w Etapie 7, bez nowego endpointu; (5) bez przeciągania plików; (6) `GET /readiness` po autozapisie, bez `POST …/readiness`.

Pierwotne pytania:

1. OIDC (Entra ID, PKCE) w Etapie 8 — potrzebne: tenant/issuer, `client_id` SPA, redirect URI, scope API; czy dopuszczamy refresh token w SPA.
2. `sessionStorage` dla tokenu (przeładowanie nie wylogowuje) czy wyłącznie pamięć (każde przeładowanie = ponowne logowanie)?
3. ~~Zapis w tle przy opuszczeniu formularza~~ — zastąpione zapisem z `await` i blokadą wyjścia (§13 pkt 2).
4. Rejestr zbiorczy audytora (`/c/all`): czy potrzebny endpoint `GET /changes?company_ids=…` przed Etapem 7, czy wystarczy raport zbiorczy?
5. Przeciąganie plików do strefy załączników (dodatkowy pakiet) — potrzebne?
6. Kontrola przed wysłaniem dla niezapisanych zmian: wystarcza autozapis + `GET /readiness`, czy dodać `POST …/readiness` z treścią roboczą (bez zapisu)?

## 13. Poprawki po recenzji Etapu 5 (2026-10-30)

1. **Okno serwisowe trwale „brudne” (bloker).** `WarsawTime.fromWarsaw` zwracał `TZDateTime`, którego `==` jest prawdziwe tylko wobec innego `TZDateTime` — wybrane okno nigdy nie było równe wartości z API, więc formularz wysyłał PATCH co 30 s ze starą wersją (fałszywe 409). Teraz zwraca zwykły `DateTime` UTC, a kontroler porównuje chwile przez `WarsawTime.sameInstant` (`isAtSameMomentAs`, z obsługą null). Test przez prawdziwy wybór daty i godziny: zapis → brak niezapisanych zmian → brak kolejnego PATCH po 2 × 30 s.
2. **Brak cichej utraty danych przy wyjściu (bloker).** Usunięty zapis „fire-and-forget”. Trasa edycji ma `onExit` (go_router), który woła strażnika formularza (`core/navigation/exit_guard.dart`): czeka na trwający zapis i zapisuje resztę z `await`; gdy się nie uda (błąd, konflikt, blokada), użytkownik zostaje w formularzu, a baner wyjaśnia przyczynę i oferuje „Odrzuć zmiany i wyjdź” (z potwierdzeniem; wyjście na kartę zmiany — `onExit` nie zna celu nawigacji). Przeładowanie/zamknięcie karty przy niezapisanych zmianach — ostrzeżenie `beforeunload`. Po wylogowaniu (401 lub „Wyloguj”) strażnik przepuszcza: zapis i tak nie jest możliwy.
   **Konflikt 409** nie kasuje już lokalnych wartości: formularz pobiera nowszą wersję i pokazuje różnice pole po polu (serwer → moje), z wyborem „Zapisz moje na nowej wersji” (zapis pól różniących się od nowej wersji, z jej `version`) albo „Odrzuć moje zmiany” (z potwierdzeniem).
3. **Wstrzyknięcie ścieżki (bloker).** go_router dekoduje `..%2F` w parametrach, a dio normalizuje `..`, więc spreparowany link mógł wykonać dowolny GET z tokenem ofiary (np. audytowane pobranie załącznika). Teraz: (a) router waliduje `prefix` (`^[A-Z]{2,8}$` lub `all`) i `number` (`^CHG-[A-Z]{2,8}-[0-9]{4}-[0-9]{4,}$`) przed zbudowaniem ekranu — inaczej „Nie znaleziono strony”; (b) klient API koduje **każdy** segment ścieżki z danych (`ChangesApi.seg` = `Uri.encodeComponent`; `.`, `..` i puste są odrzucane). Testy: spreparowane adresy nie wywołują żadnego żądania poza białą listą powłoki; `../../ci?x#y` zostaje jednym zakodowanym segmentem.
4. **Scenariusz akceptacyjny i kontrakt.** README frontendu: „Scenariusz akceptacyjny Etapu 5” (przebieg przez API na CHG-ALFA-2026-0017, kroki w UI); `tool/e2e_api_scenario.py`, `tool/dump_api_fixtures.py` i test kontraktu na rzeczywistych odpowiedziach (`test/fixtures/api/`).
5. **Autozapis przy błędach blokujących:** każde 409 inne niż konflikt wersji (`change.frozen`, `company.archived`, …) oraz 422 `change.field_not_editable` zatrzymują autozapis (baner „Nie można zapisać zmian”), a formularz pobiera stan z serwera (`editable_fields`, status) bez nadpisywania wpisanych wartości.
6. `Consent.valid`, `Consent.byRequesterOrAssignee` i `AuditEntry.hashValid` są wymagane (bez wartości domyślnych): brak pola to błąd parsowania, a nie „zgoda ważna” czy „wpis spójny”.
7. Kafelek „Awaryjne (30 dni)” filtruje jak licznik (bez anulowanych); różnicę granicy (licznik: dokładnie 30 dni wstecz, filtr: od początku dnia) wyjaśnia podpowiedź.
8. `startOfIsoDay` odrzuca nieistniejące daty (`2026-02-31`).
9. `safeReturnPath` odrzuca `\`, znaki sterujące i wszystko ze schematem lub hostem (`Uri.parse`).
10. Błąd pobrania załącznika (odpowiedź bajtowa): `ApiProblem.from` dekoduje problem+json z bajtów/tekstu, więc komunikat jest po polsku.
