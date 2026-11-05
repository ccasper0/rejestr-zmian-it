# 0003. Wersje narzędzi i obrazy

- Status: przyjęta
- Data: 2026-10-28

## Decyzje
- **Python:** obraz `python:3.13-slim`, `requires-python >=3.12`; CI testuje 3.12 i 3.13.
- **Flutter:** przypięty do 3.47.5. Gotowe obrazy (`ghcr.io/cirruslabs/flutter`) kończą się na 3.44 (Dart 3.12), a projekt wymaga Dart ^3.13.4, więc `frontend/Dockerfile` klonuje oficjalne repo Fluttera na tagu. Wersja musi być zgodna w `frontend/Dockerfile` (`FLUTTER_VERSION`) i `.github/workflows/ci.yml` (`flutter-version`).
- **WeasyPrint:** w extra `reports` backendu — na Windows wymaga runtime GTK/Pango do importu. Obraz Docker i CI instalują wszystkie extras.
- **Jeden obraz backendu** (`rejestr-backend:local`) dla `migrate`, `api`, `worker`; budowany tylko przez `migrate` (wspólny tag budowany równolegle przez kilka usług powodował błąd „image already exists”).

## Konsekwencje
Podbicie Fluttera = zmiana w dwóch miejscach. Pierwszy build obrazu `web` jest dłuższy (klonowanie SDK), kolejne korzystają z cache.
