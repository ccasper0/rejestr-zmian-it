# 0004. Publiczny healthcheck i zaufanie do proxy

- Status: przyjęta
- Data: 2026-10-28

## Decyzje
- `GET /api/v1/health` jest publiczny (bez uwierzytelnienia) i wpisany do `PUBLIC_ENDPOINTS` w `app/permissions.py`. Test macierzy uprawnień akceptuje endpoint tylko, gdy deklaruje akcję RBAC albo jest na tej liście.
- IP klienta (`audit_log.ip_address`) pochodzi wyłącznie od zaufanego proxy: nginx ustawia `X-Forwarded-For $remote_addr` (jeden przeskok), uvicorn ufa wyłącznie stałemu adresowi kontenera nginx `172.28.0.10` (`FORWARDED_ALLOW_IPS`; zaufanie do całej podsieci `172.28.0.0/16` obejmowało też bramę Dockera `172.28.0.1`, przez którą przychodzi ruch z hosta — IP dało się podrobić). Port API publikowany tylko na `127.0.0.1`.
- `X-Request-ID` przyjmowany tylko jako poprawny UUID; inaczej backend generuje własny. Ten identyfikator trafia do `audit_log.request_id`.

## Uzasadnienie
`--forwarded-allow-ips=*` powodowało, że uvicorn brał kontrolowany przez klienta wpis `X-Forwarded-For` — IP w dzienniku audytu byłoby fałszowalne (ISO 27001 A.8.15).
