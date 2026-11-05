# 0021. Frontend: korekta zamrożonej zmiany z karty

- Status: przyjęta (decyzja właściciela 2026-11-04)
- Data: 2026-11-04
- Dotyczy: CLAUDE.md §4.2 („Korekta = nowa zmiana z `supersedes_change_id`”), §8, §10.2–10.3; `frontend/lib/features/changes/{data/models.dart, presentation/correction.dart, presentation/change_card_page.dart, presentation/change_form_page.dart}`; kontrakt: ADR 0013 §1 i §12 pkt 4, ADR 0012 §6

## Kontekst

Korekta działała tylko przez API: `POST /companies/{cid}/changes` przyjmuje `supersedes_change_id` (ustawiany wyłącznie przy tworzeniu, potem niezmienny — trigger), oryginał musi istnieć w **tej samej** spółce (złożony FK; inaczej 422 `change.supersedes_not_found`), uprawnienie jak przy każdym szkicu (`change.edit_draft`: editor, approver; spółka aktywna). Backend **nie** wymaga, by oryginał był zamrożony (ADR 0013 §12 pkt 4). Pierwotnie karta zwracała tylko `supersedes_change_id`; numer oryginału i lista korekt doszły w aktualizacji poniżej.

## Decyzje

1. **Przycisk „Utwórz korektę”** na karcie, gdy status jest w zbiorze zamrożonym backendu (`FROZEN_STATUSES`: `implemented`, `verified`, `rolled_back`, `rejected`, `cancelled`) i użytkownik może tworzyć zmiany w spółce — ta sama reguła co „Nowa zmiana” w rejestrze: członkostwo z rolą editor/approver, spółka aktywna, karta czytana jako `access = member` (nie `admin_read_only`, nie ścieżka administracyjna). `allowed_actions`/`editable_fields` tego nie rozstrzygają (dla zamrożonej zmiany są puste), więc decyduje rola z `/me`. Ograniczenie do statusów zamrożonych to reguła UI; API pozostaje liberalne.
2. **Potwierdzenie** w dialogu („Utworzyć korektę zmiany?”) z wyjaśnieniem: nowy numer, co jest kopiowane, okno do wyznaczenia od nowa, oryginał bez zmian. Utworzenie szkicu nadaje numer i trafia do audytu, więc nie dzieje się jednym kliknięciem.
3. **Kopiowane pola** (`ChangeCorrection.draftFields`): `supersedes_change_id`, tytuł z prefiksem „Korekta: ” (bez dublowania przy korekcie korekty, przycięty do 500 znaków; pusty tytuł → „Korekta: CHG-…”), kategoria, podkategoria, typ, ryzyko, opis, plan wdrożenia, plan wycofania, wpływ, `requirement_ref`, `ticket_ref`, CI (wszystkie, także nieaktywne — readiness je wskaże), wykonawca, zatwierdzający, weryfikujący. **Nie** kopiujemy okna serwisowego (planowane od nowa; okno oryginału zwykle już minęło) ani dat/statusu cyklu życia. Puste wartości nie są wysyłane; bez `approver_id` API podpowiada domyślnego zatwierdzającego (§4.3). Osoby, które nie są już członkami spółki (`GET /members`), są pomijane — API odrzuciłoby je 422 `change.user_not_found`; kwalifikację (rola, aktywność, cztery oczy wobec nowego zgłaszającego) ocenia readiness.
4. Po utworzeniu: komunikat i przejście do `/c/:prefix/changes/:number/edit` szkicu korekty. Błąd API (problem+json) — komunikat po polsku, karta zostaje.
5. **Numer oryginału** z pola karty `supersedes_number` (bez dodatkowych żądań). Karta korekty pokazuje w nagłówku link „Korekta zmiany CHG-…”; formularz szkicu korekty — baner „Korekta zmiany CHG-…” z przyciskiem „Otwórz oryginał”. Gdy `supersedes_number` jest puste przy ustawionym `supersedes_change_id` (starsze API), zostaje prosta etykieta „Korekta wcześniejszej zmiany” bez linku.
6. **Odwrotny odnośnik**: karta oryginału pod tytułem pokazuje „Skorygowana przez:” z listą korekt z `superseded_by` (numer jako link do karty + pigułka statusu, od najstarszej). Pusta lista — brak wiersza. Przycisk „Utwórz korektę” pozostaje dostępny także wtedy (kolejna korekta jest dozwolona).

## Aktualizacja 2026-11-04: braki API usunięte

Karta zmiany (`ChangeOut`: `GET …/changes/{id}`, `GET …/changes/by-number/{number}`, odpowiedzi `POST`/`PATCH` i `ActionOut.change`; także ścieżka `admin_read_only`, ADR 0016) ma dwa pola tylko do odczytu: `supersedes_number: str | null` (numer oryginału) i `superseded_by: [{id, number, status}]` (korekty wskazujące na tę zmianę, w tej samej spółce, od najstarszej). Oba kierunki jednym zapytaniem (indeks `ix_changes_supersedes_change_id`); wiersze rejestru (`ChangeSummaryOut`) ich nie mają. Karta PDF pokazuje „Korekta zmiany” i „Skorygowana przez” (wchodzą do danych `data_sha256` nowych raportów). Frontend korzysta z nich (pkt 5–6): model `Change.supersedesNumber`, `Change.supersededBy` (`LinkedChange`); dodatkowe `GET` oryginału usunięte.

## Testy

- `test/features/change_correction_test.dart`: widoczność przycisku wg statusu (5 zamrożonych / 3 niezamrożone) i roli (editor, approver — tak; viewer, auditor, `admin_read_only` — nie), pełne body `POST` (z `supersedes_change_id`, bez okna i dat), anulowanie dialogu, błąd API, nawigacja do edycji i baner w formularzu, link na karcie korekty, etykieta bez `supersedes_number` (bez żądania o oryginał), „Skorygowana przez” z pigułkami i nawigacją, tytuł i pomijanie byłych członków.
- Kontrakt: `test/fixtures/api/change_correction{,_original}.json` — rzeczywiste odpowiedzi API (`tool/dump_correction_fixture.py`: korekta zweryfikowanej zmiany ALFA, ciało jak z frontendu, potem anulowana). Pola `supersedes_number` i `superseded_by` dopisano w fiksturach kart (`change_*`, `action_result.change`) ręcznie wg `LinkedChangeOut`, bo lokalny stos działał jeszcze na backendzie sprzed 88cba40 — przy następnym zrzucie zostaną nadpisane rzeczywistymi odpowiedziami.
