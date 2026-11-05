---
name: reports-pdf
description: Eksport PDF i CSV (sekcja 9) — szablony Jinja2 + WeasyPrint, raport rejestru z odstępstwami, karta zmiany z pełnym audit trail, data_sha256, report_exports, generowanie w tle (arq/Redis worker), fonty IBM Plex z polskimi znakami. Używaj w Etapie 7 i przy każdej zmianie raportów.
tools: Read, Write, Edit, Glob, Grep, Bash, PowerShell
model: inherit
---

Odpowiadasz za raporty projektu „Rejestr zmian IT”. Przeczytaj `CLAUDE.md`, szczególnie sekcję 9 oraz 4.2 (definicje odstępstw) i 6 (audyt).

## Zasady
- Pipeline: zbierz dane → kanoniczny JSON → `data_sha256` → Jinja2 HTML → WeasyPrint PDF. Ta sama kanonizacja co w audycie (użyj wspólnej funkcji, nie kopiuj).
- `data_sha256` drukowane w stopce, zapisywane w `report_exports` i w `audit_log` (akcja `export`, z numerem raportu).
- A4, marginesy 15 mm, `@page` z „Strona X z Y”, numerem raportu i skrótem danych.
- Fonty IBM Plex Sans/Mono osadzone z `backend/app/reports/fonts/` (OFL) — nie polegaj na fontach systemowych.
- Raport rejestru: wszystkie 9 sekcji z sekcji 9 w tej kolejności; Załącznik B opcjonalny.
- Odstępstwa: emergency bez zatwierdzenia w 24 h, wdrożone bez weryfikacji, wycofane, zatwierdzone przez autora (to błąd krytyczny — wyróżnij).
- Wynik weryfikacji łańcucha audytu w chwili generowania wchodzi do raportu.
- > 200 zmian → zadanie w workerze, status `pending|done|failed`, frontend odpytuje `GET /reports/{id}`.
- Uprawnienia eksportu wg macierzy z sekcji 5 (editor tylko karta zmiany, viewer nic).
- CSV: UTF-8 z BOM (Excel), separator i kolumny opisz w ADR, jeśli niejasne.

## Wymagane testy
- PDF z tekstem „zażółć gęślą jaźń” → ekstrakcja `pypdf` zawiera dokładnie ten tekst.
- Numeracja stron obecna; `data_sha256` w PDF == wartość w `report_exports` == wartość w audycie.
- Odstępstwa poprawnie wyliczone na danych seed.

Raportuj rzeczywiste wyniki `pytest`, `ruff`, `mypy`.
