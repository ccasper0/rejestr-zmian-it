# Instrukcja obsługi — Rejestr zmian IT

Instrukcja dla użytkowników aplikacji „Rejestr zmian IT”: administratora
aplikacji, zatwierdzających, edytorów, audytorów i obserwatorów. Opisuje
działanie aplikacji w wersji z Etapu 8 (konta lokalne z hasłem).

Nazwy przycisków, pól i komunikatów są podane dokładnie tak, jak w aplikacji
(w cudzysłowie „…”). Wszystkie daty i godziny w interfejsie są w czasie
polskim (`Europe/Warsaw`), w formacie `dd.MM.yyyy HH:mm`.

Powiązane dokumenty: [lista funkcjonalności](funkcjonalnosci.md),
[wdrożenie produkcyjne](deployment.md), specyfikacja
[CLAUDE.md](../CLAUDE.md), decyzje projektowe w [docs/decisions](decisions/).

## Spis treści

1. [Szybki start per rola](#1-szybki-start-per-rola)
2. [Role i pojęcia](#2-role-i-pojęcia)
3. [Pierwsze logowanie i konto](#3-pierwsze-logowanie-i-konto)
4. [Układ aplikacji](#4-układ-aplikacji)
5. [Rejestr zmian](#5-rejestr-zmian)
6. [Karta zmiany](#6-karta-zmiany)
7. [Tworzenie i edycja zmiany](#7-tworzenie-i-edycja-zmiany)
8. [Kontrola przed wysłaniem](#8-kontrola-przed-wysłaniem)
9. [Cykl życia zmiany](#9-cykl-życia-zmiany)
10. [Komentarze i załączniki](#10-komentarze-i-załączniki)
11. [Obiekty CI](#11-obiekty-ci)
12. [Raporty i eksport](#12-raporty-i-eksport)
13. [Dziennik audytu](#13-dziennik-audytu)
14. [Administracja](#14-administracja)
15. [Kto co może](#15-kto-co-może)
16. [Rozwiązywanie problemów i FAQ](#16-rozwiązywanie-problemów-i-faq)

---

## 1. Szybki start per rola

Role nadaje się **osobno w każdej spółce** — ta sama osoba może być np.
edytorem w jednej spółce i audytorem w innej. Administrator aplikacji to
uprawnienie globalne, niezależne od ról w spółkach.

### Administrator aplikacji

1. Zaloguj się (pierwsze konto zakłada się poleceniem `create-admin` — patrz
   [14.8](#148-pierwszy-administrator)); jeśli dostałeś hasło tymczasowe,
   ustaw własne.
2. **Spółki i słowniki → Spółki → „Nowa spółka”**: nazwa, „Prefiks ID”
   (niezmienny!), NIP, „Podmiot objęty uoKSC”, „Kategorie dostępne w spółce”
   → „Utwórz spółkę”.
3. **Użytkownicy i role → „Nowy użytkownik”**: e-mail, imię i nazwisko →
   „Utwórz konto”. Skopiuj hasło tymczasowe (pokazywane tylko raz) i przekaż
   je użytkownikowi bezpiecznym kanałem.
4. Na karcie użytkownika: „Nadaj rolę w spółce” (edytor, zatwierdzający,
   audytor, obserwator).
5. W panelu spółki ustaw „Domyślny zatwierdzający” i ewentualnie
   „Zatwierdzający dla kategorii”.

Administrator **nie** jest automatycznie edytorem ani zatwierdzającym w
spółkach (rozdział obowiązków) — patrz [14.9](#149-administrator-bez-roli-w-spółce).

### Edytor

1. Zaloguj się hasłem tymczasowym od administratora i ustaw własne hasło.
2. **Rejestr zmian → „Nowa zmiana”** — szkic dostaje numer od razu
   (np. `CHG-ALFA-2026-0142`).
3. Wypełnij 4 sekcje formularza, aż panel „Kontrola przed wysłaniem” pokaże
   „Gotowa do wysłania”.
4. „Wyślij do zatwierdzenia”.
5. Po zatwierdzeniu, jeśli jesteś wykonawcą: wdroż zmianę i na karcie kliknij
   „Oznacz jako wdrożoną”. Jeśli jesteś weryfikującym: „Potwierdź weryfikację”.

### Zatwierdzający

1. Zaloguj się i ustaw własne hasło.
2. **„Do zatwierdzenia”** w panelu nawigacji (licznik = zmiany oczekujące
   w spółce).
3. Otwórz kartę zmiany, przejrzyj opis, plany, obiekty i ścieżkę audytu.
4. „Zatwierdź”, „Zwróć do poprawy” (z komentarzem) albo „Odrzuć”
   (z komentarzem). Nie zatwierdzisz zmiany, w której jesteś zgłaszającym lub
   wykonawcą (zasada czterech oczu).
5. Pilnuj zmian awaryjnych: „Zatwierdź po fakcie” w ciągu 24 h od wdrożenia.

Zatwierdzający może też robić wszystko to, co edytor (tworzyć zmiany,
prowadzić inwentarz CI).

### Audytor

1. Zaloguj się i ustaw własne hasło.
2. **Rejestr zmian** i karty zmian — podgląd, filtry, eksport CSV.
3. **Raporty i eksport** — raport rejestru w PDF za okres (z odstępstwami,
   opcjonalnie z Załącznikiem B — pełną ścieżką audytu).
4. **Dziennik audytu** — przegląd dziennika spółki i „Zweryfikuj łańcuch”.
5. Jeśli masz rolę audytora w kilku spółkach: w przełączniku spółki wybierz
   „Wszystkie spółki (audytor)” → „Raport zbiorczy”.

### Obserwator

1. Zaloguj się i ustaw własne hasło.
2. **Rejestr zmian** — przeglądanie listy, filtrowanie, otwieranie kart zmian
   ze ścieżką audytu, przeglądanie obiektów (CI). Obserwator nie tworzy,
   nie edytuje, nie komentuje i nie eksportuje.

---

## 2. Role i pojęcia

| Rola w aplikacji | Nazwa w interfejsie | Opis (z okna nadawania ról) |
|---|---|---|
| `app_admin` | „Administrator” | Spółki, słowniki, użytkownicy i role. Nie daje ról w spółkach. |
| `approver` | „Zatwierdzający” | „Zatwierdza i odrzuca zmiany (nie własne), może też je tworzyć.” |
| `editor` | „Edytor” | „Tworzy i edytuje zmiany, prowadzi inwentarz CI.” |
| `auditor` | „Audytor” | „Przegląda rejestr i cały dziennik audytu, weryfikuje łańcuch, eksportuje.” |
| `viewer` | „Obserwator” | „Tylko podgląd rejestru i kart zmian.” |

Osoby na zmianie (niezależnie od roli w spółce):

- **Zgłaszający** — osoba, która utworzyła zmianę (nie da się jej zmienić).
- **Wykonawca** — wdraża zmianę; musi mieć w spółce rolę edytora lub
  zatwierdzającego.
- **Zatwierdzający (wskazany)** — osoba z rolą zatwierdzającego, która ma
  podjąć decyzję. Na karcie osobno widać „Zatwierdził” — kto faktycznie
  zatwierdził (albo „system (automatycznie)”).
- **Weryfikujący** — potwierdza po wdrożeniu, że zmiana działa; rola edytora
  lub zatwierdzającego. Pole może pozostać puste („— dowolny uprawniony —”) —
  wtedy zweryfikować może każdy edytor lub zatwierdzający spółki.
- **Właściciel obiektu (CI)** — członek spółki (dowolna rola) wskazany przy
  obiekcie; wyraża zgodę na zmiany w kategoriach, które jej wymagają (np. OT).

Typy zmian (karty wyboru w formularzu):

- **Standardowa** — „Powtarzalna, o niskim ryzyku, wg ustalonej procedury.
  Kategoria bez wymogu zatwierdzenia jest zatwierdzana automatycznie.”
- **Normalna** — „Wymaga oceny i zatwierdzenia przed wdrożeniem.”
- **Awaryjna** — „Pilna — może zostać wdrożona przed zatwierdzeniem;
  zatwierdzenie po fakcie w ciągu 24 h.”

Ryzyko: „Niskie”, „Średnie”, „Wysokie”.

Statusy: „Szkic”, „Do zatwierdzenia”, „Zatwierdzona”, „Wdrożona”,
„Zweryfikowana” oraz końcowe „Odrzucona”, „Wycofana”, „Anulowana”.

---

## 3. Pierwsze logowanie i konto

### 3.1 Logowanie

Ekran logowania: pola „E-mail” i „Hasło”, przycisk „Zaloguj się”. Konto
zakłada wyłącznie administrator aplikacji — nie ma samodzielnej rejestracji
ani przypomnienia hasła e-mailem („Nie pamiętasz hasła lub konto jest
zablokowane? Poproś administratora aplikacji o reset hasła.”).

Przy każdym nieudanym logowaniu komunikat jest taki sam: „Nieprawidłowy e-mail
lub hasło albo konto jest zablokowane/nieaktywne.” — aplikacja celowo nie
zdradza, czy konto istnieje.

### 3.2 Pierwsze logowanie hasłem tymczasowym

1. Administrator przekazuje Ci e-mail (login) i **hasło tymczasowe** —
   20 znaków w grupach `xxxxx-xxxxx-xxxxx-xxxxx`, wygenerowane przez serwer.
2. Po zalogowaniu aplikacja od razu przechodzi do ekranu „Zmiana hasła” z
   komunikatem „Wymagana zmiana hasła — Logujesz się hasłem tymczasowym. Ustaw
   własne hasło, aby kontynuować pracę.” Dopóki nie zmienisz hasła, dostępne
   są tylko „Zmień hasło” i „Wyloguj”.
3. Wpisz „Obecne hasło (tymczasowe)”, „Nowe hasło” i „Powtórz nowe hasło”,
   kliknij „Zmień hasło”.

Hasło tymczasowe służy tylko do pierwszego logowania i jest **ważne 7 dni**
(wartość domyślna, `TEMP_PASSWORD_TTL_HOURS`). Po tym terminie logowanie nim
kończy się komunikatem „Hasło tymczasowe wygasło. Poproś administratora o
ponowne ustawienie hasła.”, a otwarta nim sesja zostaje zakończona. Jeśli
hasło zgubisz albo wygasło, poproś administratora o reset hasła (dostaniesz
nowe hasło tymczasowe z nowym terminem).

### 3.3 Wymagania dla hasła

Sprawdzane przez serwer (UI pokazuje je w ramce „Wymagania dla hasła”):

- od **12 do 128 znaków** — najlepiej kilka niepowiązanych słów (fraza);
- nie może być jednym powtórzonym znakiem ani prostym ciągiem z klawiatury,
  cyfr lub alfabetu (np. „qwerty…”, „1234…”, „abcd…”);
- nie może zawierać adresu e-mail, jego części przed „@” ani imienia i
  nazwiska (fragmenty od 4 znaków, bez względu na wielkość liter i spacje);
- nie może być na liście popularnych haseł;
- musi być inne niż obecne hasło.

„Wielkie litery, cyfry ani znaki specjalne nie są wymagane.” Hasło nie wygasa
okresowo — zmiana jest wymuszana tylko po haśle tymczasowym.

### 3.4 Blokada konta

**5 kolejnych błędnych haseł blokuje konto na 15 minut** (wartości domyślne,
konfigurowalne przez administratora wdrożenia). Kolejne próby w czasie
blokady jej nie przedłużają. Odblokowanie: upływ czasu albo reset hasła przez
administratora. Udane logowanie zeruje licznik.

Błędne „Obecne hasło” przy zmianie hasła liczy się tak samo — a gdy w ten
sposób dojdzie do blokady, wszystkie Twoje sesje zostają zakończone.

Niezależnie od blokady konta, zbyt wiele nieudanych logowań z jednej sieci
(domyślnie 30 w ciągu 5 minut) powoduje komunikat „Zbyt wiele nieudanych prób
logowania z tej sieci. Spróbuj ponownie za …” — przycisk logowania pokazuje
odliczanie.

### 3.5 Sesja

- Sesja wygasa po **120 minutach bezczynności** i najpóźniej **12 godzin**
  od zalogowania (wartości domyślne). Wtedy zobaczysz „Sesja wygasła lub
  została zakończona. Zaloguj się ponownie.”
- Sesja jest przechowywana **w karcie przeglądarki** — zamknięcie karty
  kończy pracę; nowa karta wymaga ponownego zalogowania.
- **Nie używaj „Duplikuj kartę”** przeglądarki. Zduplikowana karta dostaje
  kopię sesji; gdy obie karty odnowią sesję, system uznaje to za ponowne
  użycie jednorazowego tokenu i ze względów bezpieczeństwa kończy sesję w obu
  kartach („Sesja wygasła lub została zakończona…”). Drugą kartę otwórz
  zwykłym linkiem i zaloguj się w niej osobno.
- Wylogowanie: menu konta na dole panelu nawigacji („Menu konta”) →
  „Wyloguj”.
- Reset hasła przez administratora, dezaktywacja konta i zmiana hasła kończą
  sesje natychmiast (nie trzeba czekać na wygaśnięcie).

### 3.6 Zmiana hasła

Menu konta (na dole panelu nawigacji) → „Zmień hasło”. Po zmianie hasła
„wszystkie Twoje sesje (także w innych kartach i przeglądarkach) zostaną
zakończone; ta karta pozostanie zalogowana.” Przycisk „Anuluj” wraca do pracy
bez zmiany.

Swojego **e-maila (loginu) nie można zmienić** — ani samodzielnie, ani przez
administratora.

### 3.7 Konto bez ról

Jeśli konto nie ma jeszcze roli w żadnej spółce, po zalogowaniu zobaczysz
„Brak dostępu do spółek — Twoje konto nie ma jeszcze roli w żadnej spółce.
Poproś administratora aplikacji o nadanie dostępu.”

---

## 4. Układ aplikacji

### 4.1 Panel nawigacji

Ciemny panel po lewej (na wąskim ekranie — górny pasek z menu wysuwanym):

- „Rejestr zmian IT” (logo),
- przełącznik spółki („Wybierz spółkę”),
- linki spółki: „Rejestr zmian”, „Do zatwierdzenia” (z licznikiem
  oczekujących), „Obiekty (CI)”, „Raporty i eksport”, „Dziennik audytu”,
- sekcja „Administracja” (tylko administrator aplikacji): „Spółki i
  słowniki”, „Użytkownicy i role”,
- na dole: inicjały, nazwa i rola użytkownika oraz „Menu konta” („Zmień
  hasło”, „Wyloguj”).

„Do zatwierdzenia” to rejestr spółki odfiltrowany do statusu „Do
zatwierdzenia” (wszystkie oczekujące zmiany w spółce).

### 4.2 Przełącznik spółki

Lista zawiera spółki, w których masz rolę (zarchiwizowane z dopiskiem
„(archiwum)”). Administrator widzi także pozostałe spółki z dopiskiem
„(administrator)” — patrz [14.9](#149-administrator-bez-roli-w-spółce).
Audytor ma dodatkową pozycję „Wszystkie spółki (audytor)”.

Zmiana spółki zachowuje bieżącą sekcję (np. z raportów jednej spółki
przechodzisz do raportów drugiej).

### 4.3 Adresy

Wybrana spółka jest w adresie, więc linki można zapisywać i przesyłać:

| Adres | Ekran |
|---|---|
| `/c/PREFIKS/changes` | rejestr zmian spółki (filtry w parametrach adresu) |
| `/c/PREFIKS/changes/new` | nowa zmiana (tworzy szkic i przechodzi do edycji) |
| `/c/PREFIKS/changes/CHG-PREFIKS-RRRR-NNNN` | karta zmiany |
| `/c/PREFIKS/changes/CHG-…/edit` | edycja zmiany |
| `/c/PREFIKS/approvals` | rejestr odfiltrowany do „Do zatwierdzenia” |
| `/c/PREFIKS/ci` | obiekty (CI) |
| `/c/PREFIKS/reports` | raporty i eksport |
| `/c/PREFIKS/audit` | dziennik audytu spółki |
| `/c/all/reports` | raport zbiorczy audytora |
| `/admin/companies`, `/admin/categories`, `/admin/ci-types`, `/admin/permissions` | administracja |
| `/admin/users`, `/admin/users/{id}` | użytkownicy i role |
| `/admin/audit` | łańcuch globalny dziennika audytu |
| `/account/password` | zmiana hasła |
| `/login` | logowanie |

Bez zalogowania każdy adres prowadzi do logowania, a po zalogowaniu wraca pod
pierwotny adres. Adres spółki, w której nie masz roli, kończy się ekranem
„Brak dostępu” („Spółka „…” nie istnieje albo nie masz w niej żadnej roli.”)
— aplikacja celowo nie zdradza, czy spółka istnieje.

---

## 5. Rejestr zmian

Ekran „Rejestr zmian” (`/c/PREFIKS/changes`).

### 5.1 Przyciski

- „Eksport PDF” — przechodzi do „Raporty i eksport” z bieżącymi filtrami
  (zatwierdzający, audytor, administrator).
- „CSV” — od razu pobiera rejestr w CSV z bieżącymi filtrami (jw.).
- „Odśwież”.
- „Nowa zmiana” — edytor i zatwierdzający, gdy spółka nie jest
  zarchiwizowana.

### 5.2 Kafelki

Kliknięcie kafelka ustawia odpowiedni filtr:

- „Do zatwierdzenia” — zmiany w statusie „Do zatwierdzenia”;
- „Zatwierdzone niewdrożone” — status „Zatwierdzona”;
- „Awaryjne (30 dni)” — awaryjne zarejestrowane w ostatnich 30 dniach (bez
  anulowanych), z dopiskiem „w tym bez zatwierdzenia w 24 h: N”;
- „Wdrożone bez weryfikacji” — status „Wdrożona”.

### 5.3 Wyszukiwanie i filtry

- „Szukaj: numer, tytuł, zgłoszenie”.
- „Okres” (dni kalendarzowe, czas polski) i „Data”: „wdrożenia” albo
  „rejestracji”.
- „Kategoria”, „Obiekt”, „Status”, „Typ”, „Wykonawca”.
- „Zatwierdził” — „Kto faktycznie zatwierdził”: osoba albo „system
  (automatycznie)”.
- „Wyczyść filtry”.

Filtry są zapisywane w adresie strony.

### 5.4 Tabela

Kolumny: numer (link do karty), „Zmiana”, „Kategoria”, „Obiekt (CI)”, „Typ”
(awaryjna wyróżniona czerwoną ramką), „Status”, „Wykonawca”, „Zatwierdził”,
„Wdrożenie”. Czerwona ikona przy tytule oznacza **odstępstwo** — po
najechaniu widać jego opis (patrz [12.2](#122-raport-rejestru-pdf)).

Stopka: „Zmian: N” / „Wyświetlono X–Y z N”, „Sortowanie:” („Najnowsze”,
„Najstarsze”, „Numer malejąco”, „Numer rosnąco”, „Wdrożenie: najnowsze”,
„Wdrożenie: najstarsze”, „Tytuł A–Z”, „Tytuł Z–A”, „Status”) i
stronicowanie.

W zarchiwizowanej spółce: „Spółka jest zarchiwizowana — rejestr jest tylko do
odczytu.”

### 5.5 Eksport CSV

Plik CSV: kodowanie UTF-8 z BOM, separator `;` (otwiera się poprawnie w
polskim Excelu), daty w czasie polskim. Kolumny: Spółka, Numer, Tytuł,
Kategoria, Podkategoria, Typ, Ryzyko, Status, Obiekty (CI), Zgłaszający,
Wykonawca, Zatwierdzający (wskazany), Zatwierdził, Data zatwierdzenia, Okno
od, Okno do, Data wdrożenia, Weryfikujący, Data weryfikacji, Odstępstwa,
Zgłoszenie, Podstawa / wymóg, Data rejestracji. Każdy eksport CSV dostaje
numer raportu, jest zapisywany na liście raportów i w dzienniku audytu.
Limit: 5000 zmian (domyślnie) — przy większym zakresie zawęź okres lub filtry.

---

## 6. Karta zmiany

Adres `/c/PREFIKS/changes/NUMER`.

**Nagłówek**: ścieżka „Rejestr zmian / numer”, status, typ, „Ryzyko: …”,
tytuł; dla korekty — oznaczenie „Korekta wcześniejszej zmiany”; przy
odstępstwie — „Odstępstwo” albo „Odstępstwo krytyczne”.

**Przyciski** — pokazywane są tylko akcje, które serwer pozwala Ci wykonać
teraz (zależnie od roli, statusu i Twojej funkcji na zmianie):

- „Edytuj” — gdy możesz edytować jakiekolwiek pole;
- „Karta PDF” — eksport karty (administrator, zatwierdzający, edytor,
  audytor);
- akcje: „Wyślij do zatwierdzenia”, „Zatwierdź” / „Zatwierdź po fakcie”,
  „Wdróż awaryjnie” / „Oznacz jako wdrożoną”, „Potwierdź weryfikację”,
  „Wyraź zgodę (właściciel CI)”, „Zwróć do poprawy”, „Odrzuć”, „Wycofaj”,
  „Anuluj zmianę”.

Każda akcja otwiera okno z opisem skutków i polem „Komentarz (wymagany)” albo
„Komentarz (opcjonalnie)”.

**Pasek etapów**: Szkic → Do zatwierdzenia → Zatwierdzona → Wdrożona →
Zweryfikowana (z oznaczeniem etapów pominiętych, np. „pominięte —
zatwierdzenie automatyczne”, i oczekujących, np. „oczekuje na zatwierdzenie
po fakcie”).

**Lewa kolumna**:

- „Opis zmiany”: „Co i dlaczego”, „Zgłoszenie”, „Plan wdrożenia”, „Plan
  wycofania”, „Wpływ”, „Załączniki”;
- „Zgody właścicieli obiektów (CI)” — gdy kategoria wymaga zgody;
- „Komentarze”;
- „Ścieżka audytu” — wpisy od najstarszego: czas i adres IP, kto (rola) —
  akcja, zmiany pól „przed → po”, skrót sha256 wpisu; w nagłówku znacznik
  stanu łańcucha (patrz [13.2](#132-znacznik-łańcuch-spójny)).

**Prawa kolumna**:

- „Klasyfikacja”: „Spółka”, „Kategoria”, „Typ”, „Ryzyko”, „Zgłaszający”,
  „Wykonawca”, „Zatwierdzający (wskazany)”, „Zatwierdził”, „Okno serwisowe”,
  „Wdrożenie”, „Weryfikujący”, „Weryfikacja”, „Podstawa / wymóg”,
  „Zarejestrowano”;
- „Obiekty, których dotyczy” — od wdrożenia pokazywana jest migawka stanu
  obiektów z chwili wdrożenia („Stan obiektów z chwili wdrożenia
  (migawka).”), z informacją o obecnym identyfikatorze, jeśli się zmienił.

---

## 7. Tworzenie i edycja zmiany

### 7.1 Nowa zmiana

„Nowa zmiana” od razu **tworzy szkic i nadaje numer** w formacie
`CHG-{PREFIKS}-{RRRR}-{NNNN}` (numeracja od 0001 w każdym roku, osobno dla
każdej spółki), a potem otwiera formularz edycji. Szkic, którego nie
potrzebujesz, anuluj na karcie przyciskiem „Anuluj zmianę” — zmian się nie
usuwa.

### 7.2 Sekcje formularza

1. **„1. Czego dotyczy”** — „Tytuł zmiany” (najwyżej 500 znaków),
   „Kategoria”, „Podkategoria (opcjonalnie)”, „Obiekty (CI), których dotyczy
   zmiana” — wyszukiwanie „Szukaj obiektu: identyfikator lub nazwa”, wybrane
   obiekty jako chipy; przycisk „Nowy obiekt” dodaje obiekt do inwentarza w
   locie („Typ obiektu”, „Identyfikator (np. FW-01)”, „Nazwa”, „Opis
   (opcjonalnie)” → „Dodaj obiekt”).
2. **„2. Typ i ryzyko”** — trzy karty „Typ zmiany” (Standardowa / Normalna /
   Awaryjna) i „Ryzyko” (Niskie / Średnie / Wysokie).
3. **„3. Opis i plan”** — „Opis i uzasadnienie (co i dlaczego)”, „Plan
   wdrożenia”, „Plan wycofania (wymagany przy wysokim ryzyku)”, „Wpływ
   (usługi, użytkownicy, przerwa)”.
4. **„4. Osoby, termin, dowody”** — „Wykonawca”, „Zatwierdzający” (z
   podpowiedzią „Domyślny zatwierdzający: …” i przyciskiem „Ustaw
   domyślnego”), „Weryfikujący” („— dowolny uprawniony —” = pole puste),
   „Okno serwisowe od (czas polski)”, „Okno serwisowe do (czas polski)”,
   „Zgłoszenie (np. SD-1234)”, „Podstawa / wymóg (np. ISO/IEC 27001:2022
   A.8.32)”, „Załączniki”.

Domyślny zatwierdzający: najpierw zatwierdzający przypisany do kategorii w
spółce, a jeśli go nie ma — domyślny zatwierdzający spółki (pomijany, gdy jest
zgłaszającym lub wykonawcą). Dla zmiany standardowej w kategorii bez wymogu
zatwierdzenia formularz pokazuje: „Zmiana standardowa w tej kategorii zostanie
zatwierdzona automatycznie (system) — zatwierdzający nie jest wymagany.”

Formularz od razu podpowiada najczęstsze błędy (np. „Plan wycofania jest
wymagany przy wysokim ryzyku.”, „Koniec okna musi być późniejszy niż jego
początek.”, „Zasada czterech oczu: zatwierdzający nie może być zgłaszającym
ani wykonawcą.”), ale decyduje serwer — patrz [rozdział 8](#8-kontrola-przed-wysłaniem).

### 7.3 Zapisywanie

- „Zapisz szkic” — zapis ręczny.
- **Autozapis co 30 s**, gdy są niezapisane zmiany. Stan zapisu widać obok
  numeru: „Niezapisane zmiany (autozapis co 30 s)”, „Zapisywanie…”,
  „Zapisano HH:mm”, „Brak niezapisanych zmian”.
- Przy wyjściu z formularza (link, inny ekran) aplikacja najpierw zapisuje
  zmiany; gdy zapis się nie uda: „Nie udało się zapisać zmian — pozostajesz w
  formularzu.”
- „Anuluj” wychodzi do karty zmiany; przy niezapisanych zmianach pyta
  „Odrzucić niezapisane zmiany?” („Wróć do edycji” / „Odrzuć zmiany”). Szkic
  zachowuje numer i ostatnią zapisaną treść.
- „Wyślij do zatwierdzenia” zapisuje formularz i wysyła zmianę — jest
  nieaktywny, dopóki „Kontrola przed wysłaniem” pokazuje błędy.

### 7.4 Kto i kiedy może edytować

| Status | Kto edytuje | Co |
|---|---|---|
| „Szkic” | edytor lub zatwierdzający spółki | wszystkie pola (poza zgłaszającym) |
| „Do zatwierdzenia” | zatwierdzający spółki, który nie jest zgłaszającym ani wykonawcą | tylko „Zatwierdzający” i okno serwisowe; nowe wartości muszą spełniać reguły kontroli |
| „Zatwierdzona” | nikt | — („Zatwierdzonej zmiany nie można edytować.”) |
| „Wdrożona” | zatwierdzający (≠ zgłaszający, ≠ wykonawca) — wyjątkowo | „Weryfikujący”, gdy wskazany weryfikujący nie może już weryfikować (nieaktywny lub bez roli); w zmianie awaryjnej bez zatwierdzenia także „Zatwierdzający”, gdy wskazany nie jest już aktywnym zatwierdzającym |
| „Zweryfikowana”, „Wycofana”, „Odrzucona”, „Anulowana” | nikt | zmiana zamrożona |

Pola niedostępne w danym statusie są wyszarzone („Pole niedostępne do
edycji”). Każda edycja trafia do dziennika audytu z wartościami „przed → po”.

### 7.5 Konflikt wersji

Każdy zapis zawiera wersję zmiany. Jeśli ktoś inny zapisał zmianę w
międzyczasie, formularz pokazuje baner „Ktoś inny zapisał tę zmianę” /
„Zmiana ma już nowszą wersję”: Twoje wartości zostają w formularzu, autozapis
jest wstrzymany, a pod banerem widać „Różnice (wersja z serwera → Twoja
wartość)”. Do wyboru:

- „Zapisz moje na nowej wersji” — Twoje wartości nadpisują nową wersję;
- „Odrzuć moje zmiany” — formularz wczytuje wersję z serwera;
- „Odrzuć zmiany i wyjdź”.

Na karcie zmiany konflikt przy akcji (np. „Zatwierdź”) kończy się oknem
„Zmiana została zmieniona przez kogoś innego” — karta jest odświeżana;
sprawdź aktualny stan zmiany i spróbuj ponownie. Zatwierdzający zawsze
zatwierdza wersję, którą widzi na karcie.

---

## 8. Kontrola przed wysłaniem

Panel „Kontrola przed wysłaniem” w formularzu pokazuje listę reguł z serwera
(„Odśwież kontrolę”) i podsumowanie: „Gotowa do wysłania” albo „N pozycji do
poprawy”. Pozycje mają poziom „Błąd” (blokuje wysłanie) lub „Uwaga”
(ostrzeżenie). Kontrola dotyczy **ostatniej zapisanej wersji** — przy
niezapisanych zmianach panel to sygnalizuje.

Reguły (pokazywane są tylko te, które dotyczą danej zmiany):

| Reguła (komunikat w panelu) | Kiedy |
|---|---|
| „Tytuł zmiany jest podany.” | zawsze |
| „Typ zmiany jest wybrany (standardowa, normalna lub awaryjna).” | zawsze |
| „Ryzyko jest określone.” | zawsze |
| „Opis zmiany i uzasadnienie są podane.” | zawsze |
| „Plan wdrożenia jest podany.” | zawsze |
| „Kategoria zmiany jest wybrana.” | zawsze |
| „Kategoria jest aktywna i dostępna w tej spółce.” | gdy wybrano kategorię |
| „Podkategoria jest aktywna i należy do wybranej kategorii.” | gdy wybrano podkategorię |
| „Wskazano co najmniej jeden obiekt (CI), którego dotyczy zmiana.” | zawsze |
| „Wszystkie obiekty (CI) należą do spółki zmiany.” / „Wszystkie obiekty (CI) są aktywne.” | gdy wybrano obiekty |
| „Każdy obiekt (CI) ma aktywnego właściciela w spółce, który wyrazi zgodę na zmianę (wymóg kategorii).” | kategoria wymaga zgody właściciela CI (np. OT) |
| „Plan wycofania jest podany - wymagany przy wysokim ryzyku.” | ryzyko wysokie |
| „Okno serwisowe (od i do) jest podane - wymagane przy wysokim ryzyku.” | ryzyko wysokie |
| „Okno serwisowe ma podany zarówno początek, jak i koniec.” | podano tylko jedną granicę okna |
| „Początek okna serwisowego jest wcześniejszy niż jego koniec.” | podano okno |
| „Początek okna serwisowego jest w przyszłości.” | podano okno; **nie dotyczy zmian awaryjnych** |
| „Wykonawca jest wskazany.” / „Wykonawca jest aktywnym użytkownikiem z rolą edytora lub zatwierdzającego w spółce.” | zawsze |
| „Zatwierdzający jest wskazany.” / „…z rolą zatwierdzającego w spółce.” / „Zatwierdzający jest inną osobą niż zgłaszający i wykonawca (zasada czterech oczu).” | zawsze, poza zmianą zatwierdzaną automatycznie (wtedy: „Zatwierdzający nie jest wymagany - zmiana standardowa zostanie zatwierdzona automatycznie.”; jeśli mimo to wskazano zatwierdzającego, reguły czterech oczu obowiązują) |
| „Podstawa/wymóg jest podany - wymagany w podmiocie objętym uoKSC.” | spółka objęta uoKSC |
| „Weryfikujący jest wskazany - wymagany w podmiocie objętym uoKSC.” | spółka objęta uoKSC |
| „Weryfikujący jest aktywnym użytkownikiem z rolą edytora lub zatwierdzającego w spółce.” | wskazano weryfikującego |
| „Weryfikujący jest inną osobą niż wykonawca.” | weryfikujący = wykonawca. Gdy w spółce nie ma nikogo innego, kto mógłby zweryfikować — tylko „Uwaga”, odnotowana w audycie |

Te same reguły sprawdza serwer przy wysłaniu, przy wdrożeniu awaryjnym i
ponownie przy zatwierdzeniu. Przy zatwierdzeniu jedynym wyjątkiem jest okno,
którego początek już minął — wtedy zatwierdzenie jest dozwolone z
ostrzeżeniem zapisanym w audycie („Początek okna serwisowego już minął -
zatwierdzenie jest dozwolone i zostanie odnotowane w audycie.”).

---

## 9. Cykl życia zmiany

### 9.1 Przejścia statusów

| Akcja (przycisk) | Z → do | Kto | Komentarz |
|---|---|---|---|
| „Wyślij do zatwierdzenia” | Szkic → Do zatwierdzenia | zgłaszający lub wykonawca (rola edytora/zatwierdzającego) | opcjonalny |
| „Zwróć do poprawy” | Do zatwierdzenia → Szkic | wskazany zatwierdzający | **wymagany** |
| „Zatwierdź” | Do zatwierdzenia → Zatwierdzona | wskazany zatwierdzający (≠ zgłaszający, ≠ wykonawca) | opcjonalny |
| „Odrzuć” | Do zatwierdzenia → Odrzucona | wskazany zatwierdzający | **wymagany** |
| „Oznacz jako wdrożoną” | Zatwierdzona → Wdrożona | wykonawca | opcjonalny |
| „Potwierdź weryfikację” | Wdrożona → Zweryfikowana | wskazany weryfikujący (a gdy nie wskazano — dowolny edytor/zatwierdzający), nie wykonawca, jeśli to możliwe | opcjonalny |
| „Wycofaj” | Wdrożona → Wycofana | wykonawca lub wskazany zatwierdzający | **wymagany** |
| „Anuluj zmianę” | Szkic → Anulowana | zgłaszający | opcjonalny |
| „Anuluj zmianę” | Zatwierdzona → Anulowana | zgłaszający lub wskazany zatwierdzający | **wymagany** |
| „Wdróż awaryjnie” | Szkic → Wdrożona (tylko awaryjna) | zgłaszający lub wykonawca | opcjonalny |
| „Zatwierdź po fakcie” | Wdrożona (awaryjna bez zatwierdzenia) | wskazany zatwierdzający | opcjonalny |
| „Wyraź zgodę (właściciel CI)” | bez zmiany statusu | właściciel obiektu (CI) zmiany | opcjonalny |

Komentarz może mieć najwyżej 4000 znaków. Statusy „Odrzucona”, „Wycofana” i
„Anulowana” są końcowe.

Status zmienia wyłącznie serwer — przyciskiem akcji na karcie. Po akcji
aplikacja pokazuje np. „Status zmiany: Zatwierdzona.”, a ostrzeżenia
(odstępstwa) dopisuje po „Uwaga:”.

### 9.2 Zmiana normalna (typowy przebieg)

1. Edytor tworzy szkic, uzupełnia formularz, „Wyślij do zatwierdzenia”.
2. Wskazany zatwierdzający przegląda kartę i:
   - „Zatwierdź” — serwer ponownie sprawdza wszystkie reguły kontroli;
   - „Zwróć do poprawy” — zmiana wraca do autora jako szkic (podaj, co
     poprawić);
   - „Odrzuć” — stan końcowy (podaj powód).
   W statusie „Do zatwierdzenia” zatwierdzający może przez „Edytuj” zmienić
   zatwierdzającego (np. przekazać innej osobie) i przesunąć okno serwisowe.
3. Wykonawca wdraża zmianę w oknie serwisowym i klika „Oznacz jako wdrożoną”
   („Od tej chwili karta jest zamrożona.”). Wdrożenie poza zatwierdzonym
   oknem jest dozwolone, ale zapisywane jako odstępstwo („Zmianę wdrożono
   poza zatwierdzonym oknem serwisowym - odstępstwo.”).
4. Weryfikujący sprawdza efekt i klika „Potwierdź weryfikację” — albo
   wykonawca/zatwierdzający klika „Wycofaj” (z komentarzem), jeśli zmianę
   trzeba było cofnąć.

### 9.3 Zasada czterech oczu

Zatwierdzający **nie może być zgłaszającym ani wykonawcą** zmiany. Pilnują
tego: kontrola przed wysłaniem, serwer przy akcjach „Zatwierdź”, „Odrzuć”,
„Zwróć do poprawy” (komunikat „Zasada czterech oczu: nie możesz zatwierdzić
zmiany, której jesteś zgłaszającym lub wykonawcą.”) oraz ograniczenie w
bazie danych. Zgłaszającego nie da się zmienić po utworzeniu zmiany. Raport
rejestru wykazuje zmianę zatwierdzoną przez autora jako „BŁĄD KRYTYCZNY”
(nie powinna nigdy wystąpić).

Weryfikujący powinien być inną osobą niż wykonawca. Wyjątek: w spółce nie ma
nikogo innego z rolą edytora lub zatwierdzającego — wtedy wykonawca może
zweryfikować zmianę, a dziennik audytu zapisuje ostrzeżenie.

### 9.4 Zmiana standardowa — automatyczne zatwierdzenie

Gdy zmiana jest **standardowa**, a jej kategoria i podkategoria **nie
wymagają zatwierdzenia ani zgody właściciela CI**, „Wyślij do zatwierdzenia”
od razu przenosi ją do statusu „Zatwierdzona”. Zatwierdza „system”: aplikacja
pokazuje „Zmiana standardowa została zatwierdzona automatycznie (system).”, w
rejestrze i raportach w kolumnie „Zatwierdził” widać „system
(automatycznie)”, a w dzienniku audytu aktor to `system` z informacją, kto
wysłał zmianę. Zatwierdzający nie jest wtedy wymagany.

Przykład z danych startowych: kategoria „ACC — Konta i uprawnienia” nie
wymaga zatwierdzenia, ale jej podkategoria „Konto uprzywilejowane” — tak
(podkategoria może tylko zaostrzyć wymóg). Zmiana normalna lub awaryjna
zawsze przechodzi przez zatwierdzającego.

### 9.5 Zmiana awaryjna — zatwierdzenie po fakcie

1. Edytor tworzy zmianę typu „Awaryjna” i uzupełnia ją (obowiązują reguły
   kontroli, poza wymogiem okna w przyszłości).
2. Zgłaszający lub wykonawca klika na karcie „Wdróż awaryjnie” — zmiana
   przechodzi ze szkicu od razu do „Wdrożona”, bez zatwierdzenia.
3. Wskazany zatwierdzający musi kliknąć „Zatwierdź po fakcie” **w ciągu 24 h
   od wdrożenia**. Zatwierdzenie później jest możliwe, ale pozostaje
   odstępstwem („Zmiana awaryjna zatwierdzona po upływie 24 h od wdrożenia -
   odstępstwo.”). Zmiana bez zatwierdzenia po 24 h jest oznaczana w rejestrze
   i raportach jako odstępstwo, a kafelek „Awaryjne (30 dni)” pokazuje
   „w tym bez zatwierdzenia w 24 h”.
4. Weryfikacja jest możliwa dopiero po zatwierdzeniu po fakcie („Zmiana
   awaryjna musi zostać zatwierdzona po fakcie przed weryfikacją.”).

Jeśli wskazany zatwierdzający nie jest już aktywnym zatwierdzającym, inny
zatwierdzający spółki (nie zgłaszający, nie wykonawca) może przez „Edytuj”
przepiąć zatwierdzającego na siebie i zatwierdzić po fakcie (z wpisem w
audycie; odstępstwo 24 h pozostaje, jeśli termin minął).

### 9.6 Zgoda właściciela CI (np. systemy OT)

Gdy kategoria lub podkategoria ma ustawione „Wymaga zgody właściciela obiektu
(CI)” (w danych startowych: „OT — Systemy OT / przemysłowe”):

- każdy obiekt zmiany musi mieć aktywnego właściciela w spółce (reguła
  kontroli);
- zmiana nigdy nie jest zatwierdzana automatycznie;
- w statusie „Do zatwierdzenia” (oraz w wdrożonej zmianie awaryjnej przed
  zatwierdzeniem po fakcie) właściciel obiektu klika „Wyraź zgodę (właściciel
  CI)” — zgoda dotyczy jego obiektów; właściciel może mieć dowolną rolę w
  spółce (także obserwatora);
- „Zatwierdź” jest możliwe dopiero, gdy zgodę wyrażono dla **każdego**
  obiektu zmiany („Brak zgody właściciela obiektów (CI): …”);
- karta pokazuje sekcję „Zgody właścicieli obiektów (CI)” („Brak zgody”,
  „Zgoda: …”, „Zgoda nieważna (zmienił się właściciel)”); jeśli zgodę wyraził
  zgłaszający lub wykonawca, widać ostrzeżenie „Zgoda niezależna? Właściciel
  jest zgłaszającym lub wykonawcą”;
- „Zwróć do poprawy” kasuje zebrane zgody — po poprawkach właściciele
  wyrażają je ponownie;
- właściciela obiektu nie można zmienić, dopóki zmiana czeka na jego zgodę.

### 9.7 Zamrożenie i korekta

Od statusu „Wdrożona” (oraz w statusach „Odrzucona” i „Anulowana”) zmiana
jest **zamrożona** — pól merytorycznych nie można edytować („Zmiana jest
zamrożona i nie może być edytowana. Korekta wymaga nowej zmiany.”). Wyjątki
opisuje tabela w [7.4](#74-kto-i-kiedy-może-edytować). Komentarze i
załączniki można dodawać nadal.

Korektę zamrożonej zmiany rejestruje się jako **nową zmianę**, która wskazuje
oryginał:

1. Otwórz kartę zamrożonej zmiany (Wdrożona, Zweryfikowana, Wycofana,
   Odrzucona albo Anulowana) i kliknij **„Utwórz korektę”**. Przycisk widzą
   edytorzy i zatwierdzający aktywnej spółki (nie: obserwator, audytor ani
   administrator w podglądzie tylko do odczytu).
2. Potwierdź w oknie „Utworzyć korektę zmiany?”. Aplikacja tworzy szkic z
   nowym numerem i kopiuje z oryginału: tytuł (z dopiskiem „Korekta: ”),
   kategorię i podkategorię, obiekty (CI), typ, ryzyko, opis, plan wdrożenia,
   plan wycofania, wpływ, zgłoszenie, podstawę/wymóg oraz wykonawcę,
   zatwierdzającego i weryfikującego (osoby, które nie są już członkami
   spółki, są pomijane). **Okna serwisowego nie kopiuje** — wyznacz je od nowa.
3. Otwiera się formularz szkicu z banerem „Korekta zmiany CHG-…” (przycisk
   „Otwórz oryginał”). Popraw to, czego dotyczy korekta, i wyślij do
   zatwierdzenia — korekta przechodzi pełną ścieżkę jak każda zmiana.

Oryginał pozostaje bez zmian. Karta korekty ma w nagłówku link „Korekta
zmiany CHG-…” prowadzący do oryginału, a karta oryginału pod tytułem —
wiersz „Skorygowana przez:” z numerami korekt (linki) i ich statusami. Powiązania nie można zmienić po utworzeniu
szkicu — błędną korektę anuluj i utwórz nową.

### 9.8 Anulowanie

- Szkic anuluje jego zgłaszający („Anuluj zmianę”) — np. niepotrzebny szkic.
- Zmianę zatwierdzoną, której już nie trzeba wdrażać, anuluje zgłaszający lub
  wskazany zatwierdzający — z komentarzem.
- Zmiany „Do zatwierdzenia” nie anuluje się bezpośrednio — zatwierdzający ją
  zwraca lub odrzuca.

---

## 10. Komentarze i załączniki

### 10.1 Komentarze

Sekcja „Komentarze” na karcie: pole „Nowy komentarz” i „Dodaj komentarz”.
Komentarze dodają edytorzy i zatwierdzający spółki, w każdym statusie (także
w zmianie zamrożonej), poza spółką zarchiwizowaną. Komentarzy **nie można
edytować ani usuwać**; każdy trafia do dziennika audytu. Komentarze do akcji
(np. powód odrzucenia) są widoczne w ścieżce audytu.

### 10.2 Załączniki

- Dodawanie: przycisk „Dodaj plik” (karta zmiany i sekcja 4 formularza) —
  edytorzy i zatwierdzający, w każdym statusie, poza spółką zarchiwizowaną.
  Przeznaczenie: „Dowody: zrzuty ekranu, eksporty konfiguracji, protokoły.”
- **Limit rozmiaru**: domyślnie **25 MiB** na plik (ustawienie
  `ATTACHMENT_MAX_BYTES`). Większy plik: „Plik jest zbyt duży (maksymalnie
  … MB).” Pusty plik jest odrzucany.
- **Dozwolone typy** (domyślnie, ustawienie `ATTACHMENT_ALLOWED_TYPES`):
  PDF, PNG, JPEG, tekst (TXT, LOG), CSV, JSON, XML, ZIP, DOCX, XLSX, ODT,
  ODS, MSG (Outlook), EML (e-mail). Typ jest rozpoznawany **po zawartości
  pliku, nie po rozszerzeniu nazwy** — np. program `.exe` przemianowany na
  `.pdf` zostanie odrzucony: „Niedozwolony typ pliku (…). Dozwolone typy
  załączników: …”. Domyślnie odrzucane są m.in. GIF, WebP, PPTX, ODP, stare
  pliki Office (97–2003), archiwa 7z/GZIP, HTML, SVG i programy.
- Każdy plik dostaje skrót **sha256** (widoczny przy załączniku) — dowód, że
  plik się nie zmienił. Załączników nie można nadpisać ani usunąć: nowa wersja
  = nowy załącznik.
- **Pobieranie**: kliknięcie załącznika („Pobierz …”) — każdy członek spółki;
  plik zawsze pobiera się jako plik (nie otwiera się w przeglądarce). **Każde
  pobranie trafia do dziennika audytu.** Administrator bez roli w spółce widzi
  listę załączników z sha256, ale nie może ich pobrać.

Sprawdzenie skrótu pobranego pliku: Windows PowerShell —
`Get-FileHash plik.pdf -Algorithm SHA256`; Linux — `sha256sum plik.pdf`.
Wynik porównaj ze skrótem przy załączniku.

---

## 11. Obiekty CI

Ekran „Obiekty (CI)” (`/c/PREFIKS/ci`) — inwentarz obiektów spółki
(serwery, maszyny wirtualne, urządzenia sieciowe, firewalle, konta, grupy,
aplikacje, systemy OT…).

- Wyszukiwanie „Szukaj: identyfikator, nazwa”, filtry „Typ” i aktywność
  („Wszystkie”, „Aktywne”, „Nieaktywne”), „Wyczyść filtry”.
- Tabela: „Identyfikator”, „Nazwa”, „Typ”, „Właściciel”, „Status”.
- **Dodawanie** — „Nowy obiekt”: „Typ *”, „Identyfikator *” (np. `FW-01`;
  unikalny w spółce bez względu na wielkość liter), „Nazwa *”, „Opis”,
  „Właściciel” (członek spółki o dowolnej roli; wyraża zgodę na zmiany w
  kategoriach wymagających zgody właściciela) → „Dodaj”.
- **Edycja** — kliknij wiersz, zmień pola → „Zapisz”.
- **Dezaktywacja** — odznacz „Obiekt aktywny”. „Obiektów się nie usuwa.
  Nieaktywnego nie można wybrać w nowej zmianie.” Zmiany historyczne
  zachowują obiekt.

Obiekty dodają i edytują: edytorzy, zatwierdzający i administrator aplikacji
(także bez roli w spółce — z komunikatem „zarządzasz inwentarzem jako
administrator aplikacji”). Audytor i obserwator tylko przeglądają. Każda
operacja trafia do dziennika audytu spółki. W spółce zarchiwizowanej
inwentarz jest tylko do odczytu.

---

## 12. Raporty i eksport

Ekran „Raporty i eksport” (`/c/PREFIKS/reports`).

### 12.1 Kto może eksportować

- Raport rejestru (PDF) i CSV: zatwierdzający, audytor, administrator
  aplikacji.
- Karta zmiany (PDF): dodatkowo edytor (przycisk „Karta PDF” na karcie
  zmiany; edytor widzi na ekranie raportów tylko listę „Wygenerowane karty
  zmian”).
- Obserwator nie eksportuje („Rola obserwatora nie obejmuje eksportu.”).

### 12.2 Raport rejestru PDF

Formularz „Nowy raport rejestru (PDF)”:

- „Okres (czas polski, oba dni włącznie)”: „Od dnia”, „Do dnia”, przycisk
  „Bieżący kwartał”; „Okres według daty”: „wdrożenia” albo „rejestracji”;
- „Filtry”: wyszukiwanie, „Status”, „Typ”, „Kategoria”, „Obiekt”,
  „Wykonawca”, „Zatwierdził”;
- „Dołącz załącznik B — pełna ścieżka audytu” (raport będzie znacznie
  dłuższy);
- „Generuj PDF”.

„Eksport PDF” w rejestrze otwiera ten formularz z filtrami rejestru (bez
okresu — z bieżącym kwartałem).

Raport ma numer `RAP-{PREFIKS}-{RRRR}-{NNNN}` i sekcje:

1. nagłówek: tytuł, spółka, okres, numer raportu, data i autor wygenerowania;
2. kafelki: liczba zmian, zatwierdzone przed wdrożeniem, awaryjne, wdrożone
   bez weryfikacji;
3. zakres i zastosowane filtry;
4. tabela rejestru: numer i status, tytuł i obiekty, kategoria, typ
   (awaryjna w czerwonej ramce), wykonawca, „Zatwierdził”, wdrożenie,
   weryfikacja;
5. **odstępstwa**:
   - zmiana awaryjna niezatwierdzona w ciągu 24 h od wdrożenia (także
     zatwierdzona po terminie),
   - zmiana wdrożona bez weryfikacji (status „Wdrożona”),
   - zmiana wdrożona poza zatwierdzonym oknem serwisowym (nie dotyczy
     awaryjnych i zmian bez pełnego okna),
   - zmiana wycofana,
   - zmiana zatwierdzona przez zgłaszającego lub wykonawcę — „BŁĄD
     KRYTYCZNY” w czerwonej ramce;
6. Załącznik A: zestawienie per kategoria i per obiekt (CI);
7. Załącznik B (opcjonalny): ścieżka audytu każdej zmiany z diffami (do 1000
   wpisów na zmianę — przy przekroczeniu raport to zaznacza);
8. wynik weryfikacji łańcucha audytu spółki w chwili generowania (ze skrótem
   głowy łańcucha);
9. pola podpisów: „Sporządził”, „Zatwierdził (właściciel procesu)”.

Każda strona ma w stopce numer raportu, **sha256 danych** i „Strona X z Y”.

### 12.3 Karta zmiany PDF

Przycisk „Karta PDF” na karcie zmiany: wszystkie pola, odstępstwa, osoby,
okno, obiekty (z migawką), zgody właścicieli CI, oś czasu statusów,
załączniki z sha256, komentarze i pełna ścieżka audytu z diffami „przed →
po”. Plik pobiera się od razu („Pobrano kartę zmiany w PDF (raport …).”) i
pojawia się na liście raportów.

### 12.4 Raport zbiorczy audytora

Audytor z rolą w kilku spółkach: przełącznik spółki → „Wszystkie spółki
(audytor)” → „Raport zbiorczy” (adres `/c/all/reports`). Raport obejmuje
**wszystkie spółki, w których masz rolę audytora** („Zakres: wszystkie spółki,
w których masz rolę audytora: …”). Filtry obiektu i osób są niedostępne
(dotyczą jednej spółki). Numer: `RAP-{RRRR}-{NNNN}`. Raport zbiorczy na
liście widzi tylko jego autor (inni audytorzy tych spółek go nie widzą), a
pobrać go może tylko dopóki ma rolę audytora we wszystkich spółkach raportu.
Wpis o eksporcie trafia do dziennika audytu każdej spółki objętej raportem. Zbiorczego **rejestru** (listy zmian) wszystkich spółek nie
ma — wybierz spółkę, aby przejrzeć jej rejestr. Administrator bez roli
audytora nie generuje raportu zbiorczego.

### 12.5 Generowanie w tle

Raport rejestru obejmujący **więcej niż 200 zmian** (ustawienie
`REPORT_ASYNC_THRESHOLD`) jest generowany w tle: „Raport … jest generowany w
tle”. Plik pobierze się automatycznie, gdy będzie gotowy, jeśli nie opuścisz
ekranu; później pobierzesz go z listy. Mniejsze raporty i karty zmian
powstają od razu. Raport większy niż 5000 zmian jest odrzucany („Raport
obejmowałby … zmian (maksymalnie …). Zawęź okres lub filtry.”).

### 12.6 Lista wygenerowanych raportów

„Wygenerowane raporty”: „Numer”, „Rodzaj”, „Okres”, „Spółka”,
„Wygenerował”, „Kiedy”, „Zmian”, „SHA-256 danych” (ikona kopiuje pełny
skrót), „Status” („Pobierz”, „Generowanie — odśwież listę, aby sprawdzić
status”, „Błąd”). Lista pokazuje raporty, które możesz eksportować (raport
zbiorczy — tylko własne). **Każde pobranie raportu trafia do dziennika
audytu.**

### 12.7 Integralność raportu — sha256

- **sha256 danych** (`data_sha256`) to skrót kanonicznego zapisu danych, z
  których zbudowano raport. Jest drukowany w stopce każdej strony, zapisany
  na liście raportów i we wpisie dziennika audytu „Eksport” (raport / eksport,
  w szczegółach wpisu: `data_sha256`, `file_sha256`, numer raportu).
- **sha256 pliku** (`file_sha256`) to skrót całego pliku PDF/CSV. Serwer
  sprawdza go przy każdym pobraniu — plik zmieniony w magazynie nie zostanie
  wydany („Plik raportu został zmieniony w magazynie i nie zostanie wydany.”),
  a próba trafia do dziennika audytu.

Jak sprawdzić wydrukowany lub przesłany raport:

1. Porównaj „sha256 danych” ze stopki z kolumną „SHA-256 danych” na liście
   raportów (po numerze raportu).
2. Audytor/administrator: w „Dziennik audytu” ustaw „Obiekt: Raport”,
   „Akcja: Eksport”, znajdź wpis z numerem raportu i rozwiń „Szczegóły” —
   `data_sha256` musi być ten sam.
3. Dla pliku: policz sha256 pobranego pliku (`Get-FileHash … -Algorithm
   SHA256` / `sha256sum …`) i porównaj z `file_sha256` z tego wpisu.

Zgodność skrótu danych oznacza, że raport pokazuje dokładnie zapisane dane;
zgodność skrótu pliku — że plik nie był zmieniany po wygenerowaniu.

---

## 13. Dziennik audytu

### 13.1 Co jest zapisywane

Każda operacja zmieniająca dane trafia do niemodyfikowalnego dziennika, w tej
samej transakcji co sama operacja: utworzenie, edycja (z wartościami „przed →
po”) i każda zmiana statusu zmiany (z komentarzem), zgody właścicieli CI,
komentarze, dodanie i każde pobranie załącznika (z sha256), obiekty CI,
spółki, kategorie, typy obiektów, kategorie spółek, nadanie i odebranie ról,
konta użytkowników (założenie, zmiana, dezaktywacja, reset i zmiana hasła,
blokada), eksporty i pobrania raportów (z numerem i `data_sha256`),
logowania, nieudane logowania, wylogowania, odnowienia sesji, odmowy dostępu
oraz same weryfikacje łańcucha. Hasła, skróty haseł i tokeny nigdy nie trafiają
do dziennika.

Każdy wpis ma czas serwera (UTC), aktora (lub `system`) z rolami w chwili
zdarzenia, adres IP, identyfikator żądania (`request_id`) i skrót sha256
powiązany ze skrótem poprzedniego wpisu. Każda spółka ma **osobny łańcuch**,
a zdarzenia globalne (spółki, słowniki, użytkownicy, logowania, odmowy
dostępu) — **łańcuch globalny**. Zmiana lub usunięcie dowolnego wpisu
przerywa łańcuch i jest wykrywane przy weryfikacji; baza danych odrzuca
modyfikacje i usuwanie wpisów.

### 13.2 Znacznik „Łańcuch spójny”

W nagłówku „Ścieżka audytu” na karcie zmiany (widoczny dla każdej roli):

- **„Łańcuch spójny”** — „Ostatnia weryfikacja łańcucha audytu spółki
  potwierdziła jego spójność, a nowsze wpisy są spójne.”;
- **„Łańcuch naruszony”** — „Weryfikacja wykryła naruszenie łańcucha audytu.
  Powiadom audytora lub administratora.”;
- **„Weryfikacja nieaktualna”** — ostatnia weryfikacja jest zbyt stara
  (domyślnie ponad 26 h) lub od niej dopisano zbyt wiele wpisów;
- **„Łańcuch niezweryfikowany”** — łańcuch spółki nie był jeszcze
  weryfikowany.

Serwer weryfikuje wszystkie łańcuchy automatycznie raz na dobę (02:30 UTC).
Wpis, którego skrót nie zgadza się z treścią, jest oznaczony „Skrót niezgodny
z treścią wpisu”.

### 13.3 Ścieżka audytu zmiany

Na karcie zmiany (każda rola, także administrator bez roli): wszystkie wpisy
dotyczące zmiany i jej załączników, od najstarszych.

### 13.4 Przegląd dziennika i weryfikacja (audytor, administrator)

Ekran „Dziennik audytu” (`/c/PREFIKS/audit`) — cały łańcuch spółki:

- filtry „Obiekt” (typ obiektu: Zmiana, Obiekt (CI), Spółka, Role w spółce,
  Kategoria, Załącznik, Raport, Użytkownik, Logowanie i dostęp, …), „Akcja”
  (Utworzenie, Edycja, Zmiana statusu, Eksport, Pobranie załącznika, Nadanie
  roli, Odmowa dostępu, …), „Kto”, „Okres”, „Wyczyść filtry”;
- przy wpisie „Szczegóły”: `request_id`, identyfikator obiektu, przeglądarka,
  kontekst, `prev_hash` i `hash`;
- **„Zweryfikuj łańcuch”** — przelicza cały łańcuch i pokazuje wynik:
  „Łańcuch spółki spójny” albo „Łańcuch spółki naruszony — pierwszy niezgodny
  wpis #N”, liczbę sprawdzonych wpisów i „sha256 głowy”. Wynik weryfikacji
  sam trafia do dziennika (do weryfikowanego łańcucha; gdy naruszony łańcuch
  spółki odrzuca dopisanie — do łańcucha globalnego).

Audytor przegląda i weryfikuje łańcuchy **swoich** spółek. Administrator —
łańcuch każdej spółki (także bez roli w niej, tylko do odczytu) oraz
**łańcuch globalny** („Łańcuch globalny”, `/admin/audit`). Pozostałe role
widzą na tym ekranie informację, że cały dziennik przeglądają audytor i
administrator, a ścieżka audytu pojedynczej zmiany jest na jej karcie.

Weryfikację można też uruchomić z serwera (administrator wdrożenia):
`python -m app.cli verify-audit --company PREFIKS` lub `--global`
(kod wyjścia 0 = spójny, 1 = naruszony lub błąd) — patrz
[deployment.md](deployment.md) §12.

---

## 14. Administracja

Sekcja „Administracja” w panelu nawigacji — tylko administrator aplikacji.
„Spółki i słowniki” ma zakładki: „Spółki”, „Kategorie zmian”, „Typy obiektów
(CI)”, „Role i uprawnienia”. Osobno: „Użytkownicy i role”. Wszystkie operacje
trafiają do dziennika audytu. Przy wyjściu z niezapisanego formularza
aplikacja pyta „Odrzucić niezapisane zmiany?”.

### 14.1 Spółki

Tabela: „Spółka”, „Prefiks ID”, „Obiekty”, „Edytorzy”, „Zatwierdzający”,
„Status” („Aktywna” / „Zarchiwizowana”).

„Nowa spółka”:

- „Nazwa *” (unikalna);
- „Prefiks ID *” — od 2 do 8 wielkich liter A–Z, z podglądem „Przykładowy
  numer zmiany”. **Prefiksu nie można później zmienić** — jest częścią
  numerów zmian i raportów oraz adresów;
- „NIP” — opcjonalny, 10 cyfr z poprawną sumą kontrolną;
- „Domyślny zatwierdzający”;
- „Kategorie dostępne w spółce” (z oznaczeniem reguły: „wymaga
  zatwierdzenia”, „standard — bez zatwierdzenia”, „zgoda właściciela CI”;
  „Wszystkie” / „Żadna”);
- „Podmiot objęty uoKSC” — „Zmiany wymagają wtedy podstawy/wymogu i osoby
  weryfikującej.”;
- „Utwórz spółkę”.

Następny krok po utworzeniu: nadaj role (sekcja „Członkowie i role”: „Dodaj
osobę”, „Zmień role”), a potem wskaż zatwierdzających.

Panel istniejącej spółki: dane („Zapisz dane”), „Domyślny zatwierdzający”
(„Podpowiadany w nowych zmianach, gdy kategoria nie ma własnego
zatwierdzającego.”), „Kategorie dostępne w spółce” z polem „Zatwierdzający
dla kategorii” (do wyboru osoby z rolą zatwierdzającego w spółce; „Zapisz
kategorie”), „Członkowie i role”, „Dziennik audytu spółki” („Zweryfikuj
łańcuch”) i „Archiwizacja”.

**Archiwizacja** („Archiwizuj spółkę”, potwierdzenie wpisaniem prefiksu):
spółek się nie usuwa. Po archiwizacji nie można tworzyć zmian ani wykonywać
akcji, dodawać komentarzy ani załączników, inwentarz CI jest zamrożony;
członkowie zachowują odczyt historii i dziennika audytu. Archiwizacji nie
można cofnąć w aplikacji. Dane spółki, kategorie i role administrator może
nadal zmieniać.

### 14.2 Kategorie zmian

Słownik globalny, dwa poziomy (kategoria i podkategoria). „Nowa kategoria”,
„Dodaj podkategorię”, „Edytuj”, „Aktywuj” / „Dezaktywuj”, filtr aktywności.
Pola: „Kod *” (niezmienny), „Nazwa *”, „Wymaga zatwierdzenia”, „Wymaga zgody
właściciela obiektu (CI)”, „Domyślne ryzyko” (podpowiedź w formularzu).

- Podkategoria może tylko **zaostrzyć** wymóg kategorii (np. wprowadzić
  zatwierdzenie w kategorii standardowej), nigdy go znieść.
- Kategorii się nie usuwa — dezaktywuje. Nieaktywnej kategorii nie można
  wybrać w nowych zmianach ani udostępnić kolejnej spółce; istniejące zmiany
  ją zachowują.
- Spółce udostępnia się kategorie główne (podkategorie razem z nimi).

### 14.3 Typy obiektów (CI)

Słownik globalny (startowo: serwer, maszyna wirtualna, urządzenie sieciowe,
firewall, konto, grupa, aplikacja, system OT, inne). „Nowy typ”, „Edytuj”,
„Aktywuj” / „Dezaktywuj”. „Kod typu jest niezmienny. Typów się nie usuwa —
dezaktywuje.” Nieaktywnego typu nie można wybrać dla nowego obiektu.

### 14.4 Role i uprawnienia

Zakładka „Role i uprawnienia” pokazuje macierz uprawnień **tylko do odczytu**
— pochodzi z konfiguracji serwera (patrz [rozdział 15](#15-kto-co-może)) —
oraz listę „Akcje na zmianie” z wymaganym uprawnieniem.

### 14.5 Użytkownicy — zakładanie konta

„Użytkownicy i role” → „Nowy użytkownik”:

- „E-mail (login)” — „Adresu nie można później zmienić.”;
- „Imię i nazwisko”;
- „Administrator aplikacji” — opcjonalnie;
- „Utwórz konto”.

Serwer generuje **hasło tymczasowe** i pokazuje je **tylko raz** w oknie
„Konto zostało utworzone”: „Hasło jest wyświetlane tylko raz — Skopiuj je
teraz i przekaż użytkownikowi bezpiecznym kanałem (nie w tej samej wiadomości
co login). Po zamknięciu okna nie da się go ponownie wyświetlić — pozostanie
tylko kolejny reset hasła.” Użyj „Kopiuj”. Administrator nie wybiera haseł
użytkowników. Hasło tymczasowe jest ważne 7 dni — jeśli użytkownik nie zaloguje
się w tym czasie, wykonaj ponownie „Resetuj hasło”.

Lista użytkowników: wyszukiwanie „Szukaj: nazwisko, e-mail, identyfikator”,
kolumny „Użytkownik”, „E-mail”, „Stan konta”: „Nieaktywne”, „Administrator”,
„Hasło ustawione” / „Brak hasła”, „Wymaga zmiany hasła”, „Zablokowane do …”.

### 14.6 Użytkownicy — karta użytkownika

Sekcja „Konto”:

- „Zmień nazwę”;
- „Resetuj hasło” (dla konta bez hasła: „Nadaj hasło tymczasowe”) — nowe
  hasło tymczasowe pokazywane jednorazowo; obecne hasło przestaje działać,
  wszystkie sesje użytkownika są kończone, **blokada konta jest zdejmowana**,
  a przy logowaniu użytkownik musi ustawić własne hasło (nowe hasło
  tymczasowe ma nowy, 7-dniowy termin ważności). To także sposób na
  **odblokowanie** konta przed upływem 15 minut;
- „Dezaktywuj” / „Aktywuj” — dezaktywowany użytkownik jest natychmiast
  wylogowany ze wszystkich sesji i nie może się zalogować; role w spółkach
  pozostają zapisane, ale nowych nie można mu nadawać (można odbierać);
  kont się nie usuwa;
- „Nadaj uprawnienia administratora” / „Odbierz uprawnienia administratora”
  (z potwierdzeniem) — uprawnienia administratora nie dają ról w spółkach.

Ograniczenia: własnego konta nie dezaktywujesz, nie odbierzesz sobie
uprawnień administratora i nie zresetujesz własnego hasła (zmień je w menu
konta); ostatniego aktywnego administratora nie można dezaktywować ani
zdegradować.

### 14.7 Role w spółkach

Na karcie użytkownika: „Role w spółkach” — „Nadaj rolę w spółce” (wybór
spółki, potem ról) i „Zmień role”. Okno „Role: …” pozwala zaznaczyć kilka ról
jednocześnie (Edytor, Zatwierdzający, Audytor, Obserwator) → „Zapisz role”.
Odznaczenie wszystkich ról odbiera dostęp do spółki („Bez żadnej roli
użytkownik straci dostęp do tej spółki.”). Role można też nadawać w panelu
spółki („Członkowie i role”).

Nadanie roli **samemu sobie** jest dozwolone, ale narusza domyślny rozdział
obowiązków i jest zapisywane w dzienniku audytu („Nadajesz rolę sobie”).

### 14.8 Pierwszy administrator

Pierwsze konto administratora zakłada administrator wdrożenia poleceniem
`python -m app.cli create-admin --email … --name …`. Hasło jest wpisywane w
terminalu (dwukrotnie, ukryte) albo podawane jedną linią na standardowe wejście
i musi spełniać politykę haseł; z opcją `--generate-password` serwer generuje
hasło tymczasowe (wypisane raz, zmiana wymuszona przy pierwszym logowaniu,
ważne 7 dni — zaloguj się przed terminem).
Hasła nigdy nie podaje się jako argumentu polecenia. Szczegóły:
[deployment.md](deployment.md) §3.

### 14.9 Administrator bez roli w spółce

Administrator aplikacji widzi w przełączniku także spółki, w których nie ma
roli („(administrator)”). W takiej spółce działa **ścieżką administracyjną**:

- **tylko do odczytu**: rejestr zmian, karty zmian, „Kontrola przed
  wysłaniem”, ścieżka audytu zmiany, lista załączników (nazwy i sha256),
  kafelki — z banerem „Podgląd administratora — tylko odczyt”. Nie wykonuje
  akcji, nie edytuje, nie komentuje i **nie pobiera** plików załączników.
  Link „Do zatwierdzenia” nie jest pokazywany;
- **eksport PDF i CSV** jest dozwolony i zapisywany w dzienniku audytu spółki
  jako eksport administratora;
- **inwentarz CI** może prowadzić (to uprawnienie administratora);
- **dziennik audytu spółki** — przegląd i weryfikacja łańcucha.

Aby pracować w rejestrze (tworzyć, zatwierdzać), administrator musi nadać
sobie rolę w spółce — co zostanie zapisane w dzienniku audytu. Administrator
**z rolą** w spółce działa wyłącznie według tej roli.

---

## 15. Kto co może

Macierz uprawnień (taka sama jak w zakładce „Role i uprawnienia”). Role w
kolumnach 2–5 dotyczą konkretnej spółki.

| Akcja | Administrator | Zatwierdzający | Edytor | Audytor | Obserwator |
|---|---|---|---|---|---|
| Zarządzanie spółkami (dodaj, edytuj, archiwizuj) | ✓ | — | — | — | — |
| Słowniki globalne (kategorie, typy CI) | ✓ | — | — | — | — |
| Przypisywanie ról w spółce | ✓ | — | — | — | — |
| Konta użytkowników (zakładanie, reset hasła, dezaktywacja) | ✓ | — | — | — | — |
| Inwentarz CI spółki (dodawanie, edycja; bez usuwania — dezaktywacja) | ✓ | ✓ | ✓ | — | — |
| Tworzenie i edycja zmian w szkicu | — | ✓ | ✓ | — | — |
| Przypisywanie kategorii, CI, wykonawcy, zatwierdzającego | — | ✓ | ✓ | — | — |
| Zatwierdzanie, odrzucanie, zwrot do poprawy | — | ✓ (nie własnych) | — | — | — |
| Podgląd rejestru, kart, ścieżki audytu zmiany | ✓ (bez roli — tylko odczyt) | ✓ | ✓ | ✓ | ✓ |
| Eksport rejestru (PDF, CSV) | ✓ | ✓ | — | ✓ | — |
| Eksport karty zmiany (PDF) | ✓ | ✓ | ✓ | ✓ | — |
| Weryfikacja łańcucha audytu | ✓ | — | — | ✓ | — |
| Przegląd całego dziennika audytu | ✓ | — | — | ✓ | — |

Uzupełnienia:

- Wysłanie, wdrożenie, weryfikacja, wycofanie i anulowanie wymagają roli
  edytora lub zatwierdzającego **oraz** odpowiedniej funkcji na zmianie
  (zgłaszający, wykonawca, weryfikujący, wskazany zatwierdzający) — patrz
  [9.1](#91-przejścia-statusów).
- Zgodę właściciela CI wyraża właściciel obiektu — z dowolną rolą w spółce.
- Komentarze i załączniki dodają edytorzy i zatwierdzający; pobierać
  załączniki mogą wszyscy członkowie spółki.
- Audytor czyta i weryfikuje łańcuchy tylko swoich spółek; łańcuch globalny —
  wyłącznie administrator.
- Administrator nie jest automatycznie edytorem ani zatwierdzającym w
  spółkach (rozdział obowiązków).

---

## 16. Rozwiązywanie problemów i FAQ

### Logowanie i konto

| Komunikat | Co zrobić |
|---|---|
| „Nieprawidłowy e-mail lub hasło albo konto jest zablokowane/nieaktywne.” | Sprawdź e-mail i hasło (wielkość liter w haśle ma znaczenie). Po 5 błędnych próbach konto jest zablokowane na 15 min — odczekaj albo poproś administratora o reset hasła. Konto mogło też zostać dezaktywowane. |
| „Zbyt wiele nieudanych prób logowania z tej sieci. Spróbuj ponownie za …” | Odczekaj podany czas. Limit dotyczy całej sieci (np. biura za jednym adresem IP). |
| „Przed dalszą pracą musisz zmienić hasło tymczasowe.” | Ustaw własne hasło na ekranie „Zmiana hasła”. |
| „Obecne hasło jest nieprawidłowe.” | Wpisz aktualne hasło (przy pierwszym logowaniu — tymczasowe). Błędne próby liczą się do blokady konta. |
| „Hasło musi mieć co najmniej 12 znaków.” / „Hasło jest zbyt proste…” / „Hasło nie może zawierać adresu e-mail ani imienia i nazwiska.” / „To hasło jest zbyt popularne…” / „Nowe hasło musi się różnić od obecnego.” | Wybierz inne hasło — najlepiej frazę z kilku niepowiązanych słów (patrz [3.3](#33-wymagania-dla-hasła)). |
| „Konto jest czasowo zablokowane po nieudanych próbach. Spróbuj później albo poproś administratora o reset hasła.” | Odczekaj 15 min albo poproś o reset hasła. |
| „Sesja wygasła lub została zakończona. Zaloguj się ponownie.” | Sesja wygasła (120 min bezczynności, 12 h od zalogowania), hasło zostało zmienione lub zresetowane albo nastąpiło wylogowanie. Zaloguj się ponownie. |
| „Twoje konto jest nieaktywne. Skontaktuj się z administratorem.” | Konto zostało dezaktywowane — skontaktuj się z administratorem. |
| „Brak dostępu do spółek” | Konto nie ma roli w żadnej spółce — poproś administratora o nadanie roli. |
| „Hasło tymczasowe wygasło. Poproś administratora o ponowne ustawienie hasła.” | Minęło 7 dni od nadania hasła tymczasowego. Administrator robi „Resetuj hasło” i przekazuje nowe. |
| Zgubione hasło tymczasowe | Administrator robi „Resetuj hasło” i przekazuje nowe hasło tymczasowe. |

### Dostęp

| Komunikat | Co zrobić |
|---|---|
| „Brak dostępu” — „Spółka „…” nie istnieje albo nie masz w niej żadnej roli.” | Sprawdź prefiks w adresie lub wybierz spółkę w przełączniku. Dostęp nadaje administrator. |
| „Brak uprawnień do wykonania tej operacji.” | Twoja rola nie obejmuje tej operacji (patrz [rozdział 15](#15-kto-co-może)). |
| „Nie możesz wykonać tej operacji na tej zmianie.” | Akcję wykonuje inna osoba na zmianie (np. wykonawca, wskazany zatwierdzający, zgłaszający). Sprawdź „Klasyfikację” na karcie. |
| „Spółka jest zarchiwizowana — zmiany i obiekty są tylko do odczytu.” | Spółka jest w archiwum — nie można jej modyfikować. |

### Zmiany

| Komunikat | Co zrobić |
|---|---|
| „Zmiana nie spełnia warunków” (okno z listą błędów) | Popraw pozycje z listy (te same co w „Kontroli przed wysłaniem”), zapisz i wyślij ponownie. |
| „Zasada czterech oczu: nie możesz zatwierdzić zmiany, której jesteś zgłaszającym lub wykonawcą.” | Zmianę musi zatwierdzić inna osoba z rolą zatwierdzającego — wskaż ją w polu „Zatwierdzający”. |
| „Ta operacja wymaga komentarza.” | Zwrot do poprawy, odrzucenie, wycofanie i anulowanie zatwierdzonej zmiany wymagają komentarza. |
| „Ta operacja nie jest dozwolona w bieżącym stanie zmiany.” | Status zmiany się zmienił — odśwież kartę. |
| „Brakuje zgody właściciela obiektu (CI) na tę zmianę.” | Poproś właścicieli obiektów o „Wyraź zgodę (właściciel CI)” na karcie zmiany. |
| „Zmiana awaryjna musi zostać zatwierdzona po fakcie przed weryfikacją.” | Wskazany zatwierdzający musi najpierw kliknąć „Zatwierdź po fakcie”. |
| „Wykonawca nie może zweryfikować własnej zmiany, gdy w spółce jest inna osoba uprawniona do weryfikacji.” | Weryfikację wykonuje inna osoba (edytor lub zatwierdzający). |
| „Zmiana jest zamrożona i nie może być edytowana. Korekta wymaga nowej zmiany.” | Zarejestruj korektę jako nową zmianę (patrz [9.7](#97-zamrożenie-i-korekta)). |
| „Tego pola nie można zmienić w tym statusie.” | W statusie „Do zatwierdzenia” zmienia się tylko zatwierdzającego i okno (zatwierdzający); w innych pola są zamrożone. |
| „Ktoś inny zapisał tę zmianę” / „Zmiana została zmieniona przez kogoś innego” | Konflikt wersji — patrz [7.5](#75-konflikt-wersji). |
| „Edycja niedostępna” | Zmiany nie możesz teraz edytować (status, uprawnienia albo zamrożenie). Wróć do karty („Wróć do karty”). |
| „Brak uprawnień — Nowe zmiany mogą rejestrować edytorzy i zatwierdzający aktywnej spółki.” | Potrzebujesz roli edytora lub zatwierdzającego w spółce. |
| „Wybrana osoba nie jest członkiem tej spółki.” | Wybierz osobę z rolą w tej spółce lub poproś administratora o nadanie roli. |

### Załączniki i obiekty

| Komunikat | Co zrobić |
|---|---|
| „Plik jest zbyt duży (maksymalnie … MB).” / „Przesłany plik jest zbyt duży.” | Zmniejsz plik (np. spakuj do ZIP) albo podziel go. |
| „Niedozwolony typ pliku (…). Dozwolone typy załączników: …” | Zapisz dowód w dozwolonym formacie (np. PDF, PNG). Typ jest rozpoznawany po zawartości — zmiana rozszerzenia nie pomoże. |
| „Plik jest pusty.” | Wybierz właściwy plik. |
| „Obiekt o tym identyfikatorze już istnieje w spółce.” | Identyfikator CI musi być unikalny w spółce (bez względu na wielkość liter) — użyj istniejącego obiektu. |
| „Nie można zmienić właściciela obiektu, którego dotyczy zmiana oczekująca na zgodę.” | Poczekaj na decyzję w sprawie tej zmiany. |
| „Właściciel obiektu musi być członkiem spółki.” | Wybierz osobę z rolą w spółce. |

### Raporty

| Komunikat | Co zrobić |
|---|---|
| „Podaj okres raportu (początek i koniec).” / „Początek okresu nie może być późniejszy niż jego koniec.” | Uzupełnij lub popraw okres. |
| „Raport obejmowałby … zmian (maksymalnie …). Zawęź okres lub filtry.” | Podziel raport na krótsze okresy albo zawęź filtry. |
| „Raport jest jeszcze generowany. Spróbuj ponownie za chwilę.” | Raport w tle — odśwież listę („Odśwież listę”). |
| „Generowanie raportu … nie powiodło się — wygeneruj raport ponownie.” | Wygeneruj raport ponownie; jeśli problem się powtarza, zgłoś administratorowi. |
| „Kolejka generowania raportów jest chwilowo niedostępna…” | Spróbuj za chwilę albo zawęź raport do ≤ 200 zmian (generowanie od razu). |
| „Plik raportu został zmieniony w magazynie i nie zostanie wydany. Skontaktuj się z administratorem.” | Zgłoś administratorowi — możliwe naruszenie integralności; próba jest w dzienniku audytu. Wygeneruj raport ponownie. |

### Ogólne

| Komunikat | Co zrobić |
|---|---|
| „Przekroczono limit żądań. Spróbuj ponownie za …” | Serwer ogranicza liczbę żądań z jednego adresu IP — odczekaj chwilę. |
| „Serwer aplikacji jest chwilowo niedostępny. Spróbuj ponownie za chwilę.” | Trwa restart lub aktualizacja — spróbuj za chwilę; jeśli trwa dłużej, zgłoś administratorowi. |
| „Brak połączenia z serwerem.” | Sprawdź połączenie sieciowe / VPN. |
| „Błąd serwera. Spróbuj ponownie.” | Spróbuj ponownie; zgłaszając problem, podaj czas zdarzenia — administrator odnajdzie żądanie w logach po `request_id`. |

### FAQ

**Czy mogę usunąć zmianę, obiekt, spółkę, komentarz lub załącznik?**
Nie. Zmiany się anuluje, obiekty i kategorie dezaktywuje, spółki archiwizuje,
konta dezaktywuje. Komentarzy i załączników nie można edytować ani usuwać —
to wymóg audytowalności.

**Dlaczego nie mogę zatwierdzić własnej zmiany?** Zasada czterech oczu
(ISO/IEC 27001 A.8.32): zatwierdzający musi być inną osobą niż zgłaszający i
wykonawca.

**Dlaczego moja zmiana standardowa od razu jest „Zatwierdzona”?** Jej
kategoria nie wymaga zatwierdzenia — zatwierdza ją system (patrz
[9.4](#94-zmiana-standardowa--automatyczne-zatwierdzenie)).

**Co to jest odstępstwo?** Odchylenie od procesu zmian wykazywane w rejestrze
i raporcie: zmiana awaryjna bez zatwierdzenia w 24 h, wdrożona bez
weryfikacji, wdrożona poza oknem, wycofana albo zatwierdzona przez autora.

**Dlaczego nie widzę przycisku akcji?** Karta pokazuje tylko akcje, które
możesz wykonać teraz — zależą od statusu, Twojej roli w spółce i Twojej
funkcji na zmianie.

**Czy mogę zmienić swój e-mail?** Nie — e-mail jest loginem i nie można go
zmienić. W razie potrzeby administrator zakłada nowe konto i dezaktywuje
stare.
