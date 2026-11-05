# 0001. Kontrakt `API_URL` we frontendzie

- Status: przyjęta
- Data: 2026-10-28

## Kontekst
CLAUDE.md §14 uruchamia frontend z `--dart-define=API_URL=http://localhost:8000`. W Dockerze frontend jest serwowany przez nginx, który proxuje `/api/` do usługi `api`.

## Decyzja
`API_URL` to sam origin API, **bez** `/api`. Klient sam dokleja `/api/v1`.
- brak `API_URL` → `http://localhost:8000/api/v1`
- `API_URL=` (pusty, jawnie ustawiony) → `/api/v1` — ten sam origin (build w Dockerze)
- `API_URL=https://host` → `https://host/api/v1`

## Konsekwencje
Ten sam build działa za dowolnym hostem nginx. Rozróżnienie „brak” vs „pusty” opiera się na `bool.hasEnvironment('API_URL')`.
