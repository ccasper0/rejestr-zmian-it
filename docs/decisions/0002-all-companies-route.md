# 0002. Adres widoku „Wszystkie spółki (audytor)”

- Status: przyjęta (do potwierdzenia przez właściciela projektu)
- Data: 2026-10-28

## Kontekst
Spółka jest w URL (`/c/{prefix}/...`). Audytor może oglądać zbiorczo wszystkie swoje spółki.

## Decyzja
Pseudo-prefiks `all` (małe litery): `/c/all/...`. Prawdziwe prefiksy to 2–8 wielkich liter A–Z, więc kolizja jest niemożliwa.

## Konsekwencje
Backend musi traktować `all` jako „wszystkie spółki z członkostwem użytkownika z rolą auditor”, nigdy jako prefiks.
