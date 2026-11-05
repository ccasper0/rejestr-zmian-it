# 0005. Rdzeń audytu przed endpointami spółek

- Status: przyjęta (decyzja właściciela projektu)
- Data: 2026-10-28

## Kontekst
Etap 1 (wg pierwotnego planu) tworzy endpointy zapisujące (spółki, role), a dziennik audytu był zaplanowany w Etapie 2. Definition of Done (§15) wymaga wpisu audytu przy każdej modyfikacji, a §11.3 zabrania upraszczania audytu „na później”.

## Decyzja
Etap 1 zaczyna od rdzenia audytu (`audit_log`, `audit_chain_heads`, `audit.record()`, triggery, uprawnienia `app_rw`). Endpointy spółek i ról powstają już z audytem. Etap 2 dokańcza: weryfikacja łańcucha (API + CLI), `GET /audit`, zdarzenia auth i odmów dostępu, testy z kryterium Etapu 2.

## Konsekwencje
CLAUDE.md §12 zaktualizowany. Kryteria akceptacji Etapu 2 bez zmian.
