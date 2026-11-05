#!/usr/bin/env bash
# Kopia zapasowa "Rejestr zmian IT": baza (pg_dump, format custom) + pliki
# (wolumen "storage": załączniki i raporty) + sumy SHA-256, z retencją.
# ADR 0019 §6, instrukcja: docs/deployment.md, sekcja "Kopie zapasowe".
#
#   scripts/backup.sh [-d KATALOG] [-r DNI] [--skip-storage]
#
# Uruchamiaj z katalogu głównego repozytorium (tam, gdzie docker-compose.yml
# i .env), przy działającej usłudze db. Odpowiednik dla Windows: scripts/backup.ps1.
#
# Dlaczego jako "postgres": rola app_rw podlega RLS (zrzut byłby niepełny),
# a pg_dump roli bez BYPASSRLS przerywa zrzut tabel z politykami. Superużytkownik
# widzi wszystko; zrzut zawiera właścicieli (app_owner) i uprawnienia (app_rw),
# ale NIE same role - te tworzy skrypt init bazy (deploy/postgres/init).
#
# Zmienne środowiskowe (opcjonalne):
#   BACKUP_DIR             katalog kopii (domyślnie ./backups)
#   BACKUP_RETENTION_DAYS  ile dni trzymać kopie (domyślnie 14; 0 = bez usuwania)
#   COMPOSE_PROJECT_NAME   nazwa projektu compose (domyślnie z docker-compose.yml)
#   POSTGRES_DB            nazwa bazy (domyślnie rejestr)
#
# Szyfrowanie kopii programem age (ADR 0019 §10) - gdy ustawiona jest którakolwiek
# z poniższych zmiennych, zrzut i archiwum plików są szyfrowane STRUMIENIOWO
# (pg_dump | age, tar | age; żaden niezaszyfrowany plik nie trafia na dysk hosta),
# powstają pliki *.dump.age i *-storage.tar.gz.age, a sumy SHA-256 liczone są
# z plików zaszyfrowanych. Obie zmienne naraz = wszyscy odbiorcy z obu.
#   BACKUP_AGE_RECIPIENT   klucz publiczny odbiorcy (age1...) - age -r; kilka
#                          kluczy rozdziel przecinkami
#   BACKUP_AGE_RECIPIENTS  ścieżka do pliku z kluczami publicznymi (po jednym
#                          w linii) - age -R
# Brak programu age przy ustawionej zmiennej = błąd (kopia nie powstaje).
# Klucz prywatny NIE jest potrzebny do kopii i nie powinien leżeć na serwerze.
set -euo pipefail
# Git Bash (Windows): do not rewrite container paths such as /tmp/... into C:/...
export MSYS_NO_PATHCONV=1

BACKUP_DIR="${BACKUP_DIR:-./backups}"
RETENTION_DAYS="${BACKUP_RETENTION_DAYS:-14}"
DB_NAME="${POSTGRES_DB:-rejestr}"
WITH_STORAGE=1

usage() { awk 'NR > 1 && /^#/ { sub(/^# ?/, ""); print; next } NR > 1 { exit }' "$0"; }

while [ $# -gt 0 ]; do
    case "$1" in
        -d|--dir) BACKUP_DIR="$2"; shift 2 ;;
        -r|--retention-days) RETENTION_DAYS="$2"; shift 2 ;;
        --skip-storage) WITH_STORAGE=0; shift ;;
        -h|--help) usage; exit 0 ;;
        *) echo "Nieznany argument: $1" >&2; usage >&2; exit 2 ;;
    esac
done

case "$RETENTION_DAYS" in
    ''|*[!0-9]*) echo "BACKUP_RETENTION_DAYS musi być liczbą dni" >&2; exit 2 ;;
esac

compose() { docker compose "$@"; }

# Native Windows programs (age.exe) do not understand MSYS paths such as /c/...
native_path() {
    if command -v cygpath >/dev/null 2>&1; then cygpath -w "$1"; else printf '%s' "$1"; fi
}

AGE_ARGS=()
if [ -n "${BACKUP_AGE_RECIPIENT:-}" ]; then
    IFS=',' read -r -a age_keys <<< "$BACKUP_AGE_RECIPIENT"
    for key in "${age_keys[@]}"; do
        key="${key#"${key%%[![:space:]]*}"}"   # trim leading whitespace
        key="${key%"${key##*[![:space:]]}"}"   # trim trailing whitespace
        [ -z "$key" ] || AGE_ARGS+=(-r "$key")
    done
fi
if [ -n "${BACKUP_AGE_RECIPIENTS:-}" ]; then
    if [ ! -f "$BACKUP_AGE_RECIPIENTS" ]; then
        echo "BACKUP_AGE_RECIPIENTS: brak pliku z kluczami publicznymi: ${BACKUP_AGE_RECIPIENTS}" >&2
        exit 2
    fi
    AGE_ARGS+=(-R "$(native_path "$BACKUP_AGE_RECIPIENTS")")
fi
ENCRYPT=0
SUFFIX=""
if [ -n "${BACKUP_AGE_RECIPIENT:-}${BACKUP_AGE_RECIPIENTS:-}" ]; then
    if [ "${#AGE_ARGS[@]}" -eq 0 ]; then
        echo "BACKUP_AGE_RECIPIENT nie zawiera żadnego klucza publicznego." >&2
        exit 2
    fi
    if ! command -v age >/dev/null 2>&1; then
        echo "Ustawiono BACKUP_AGE_RECIPIENT(S), ale nie znaleziono programu age w PATH." >&2
        echo "Kopia NIE została wykonana (nie zapisujemy kopii bez szyfrowania)." >&2
        echo "Instalacja: apt install age / dnf install age / winget install FiloSottile.age" >&2
        exit 1
    fi
    # Fail before dumping anything if a recipient is malformed.
    if ! age "${AGE_ARGS[@]}" </dev/null >/dev/null; then
        echo "Nieprawidłowy klucz publiczny age w BACKUP_AGE_RECIPIENT(S)." >&2
        exit 2
    fi
    ENCRYPT=1
    SUFFIX=".age"
fi

# An interrupted encrypted write leaves only a *.part file, removed here.
partial=""
trap '[ -z "$partial" ] || rm -f "$partial"' EXIT

# stdin -> age -> $1 (via $1.part, renamed only after the whole pipeline succeeded).
encrypt_to() { age "${AGE_ARGS[@]}" -o "$(native_path "$1")"; }

if [ -z "$(compose ps -q db 2>/dev/null)" ]; then
    echo "Usługa db nie działa (docker compose up -d db)." >&2
    exit 1
fi

mkdir -p "$BACKUP_DIR"
stamp="$(date -u +%Y%m%dT%H%M%SZ)"
base="rejestr-${stamp}"
dump="${base}.dump${SUFFIX}"

if [ "$ENCRYPT" = 1 ]; then
    echo "==> pg_dump bazy ${DB_NAME} (format custom, szyfrowanie age)"
    # Streamed: pg_dump stdout -> age -> file. pipefail + set -e: a failed
    # pg_dump aborts the script and the trap removes the .part file.
    partial="${BACKUP_DIR}/${dump}.part"
    compose exec -T db pg_dump -U postgres -d "$DB_NAME" --format=custom --compress=6 \
        | encrypt_to "$partial"
    mv "$partial" "${BACKUP_DIR}/${dump}"
    partial=""
else
    echo "==> pg_dump bazy ${DB_NAME} (format custom)"
    tmp_in_container="/tmp/${dump}"
    compose exec -T db pg_dump -U postgres -d "$DB_NAME" --format=custom --compress=6 \
        --file="$tmp_in_container"
    compose cp "db:${tmp_in_container}" "${BACKUP_DIR}/${dump}"
    compose exec -T db rm -f "$tmp_in_container"
fi

files=("$dump")
if [ "$WITH_STORAGE" = 1 ]; then
    db_container="$(compose ps -q db)"
    project="$(docker inspect --format '{{index .Config.Labels "com.docker.compose.project"}}' "$db_container")"
    volume="$(docker volume ls -q \
        --filter "label=com.docker.compose.project=${project}" \
        --filter "label=com.docker.compose.volume=storage")"
    if [ -z "$volume" ]; then
        echo "Nie znaleziono wolumenu storage projektu ${project} - pomijam pliki." >&2
    else
        echo "==> archiwum plików (wolumen ${volume})"
        storage="${base}-storage.tar.gz${SUFFIX}"
        db_image="$(docker inspect --format '{{.Config.Image}}' "$db_container")"
        # Archiwum powstaje w kontenerze pomocniczym i jest kopiowane strumieniem
        # (bez montowania katalogu hosta - działa tak samo na Linuksie i Windows).
        if [ "$ENCRYPT" = 1 ]; then
            partial="${BACKUP_DIR}/${storage}.part"
            docker run --rm -v "${volume}:/data:ro" "$db_image" \
                tar -C /data -czf - . | encrypt_to "$partial"
            mv "$partial" "${BACKUP_DIR}/${storage}"
            partial=""
        else
            docker run --rm -v "${volume}:/data:ro" "$db_image" \
                tar -C /data -czf - . > "${BACKUP_DIR}/${storage}"
        fi
        files+=("$storage")
    fi
fi

echo "==> sumy SHA-256"
(
    cd "$BACKUP_DIR"
    sha256sum "${files[@]}" > "${base}.sha256"
    sha256sum -c --quiet "${base}.sha256"
)

if [ "$RETENTION_DAYS" -gt 0 ]; then
    # rejestr-* covers every kind of file: *.dump, *.dump.age, *-storage.tar.gz[.age],
    # *.sha256 and leftover *.part files.
    echo "==> retencja: usuwam kopie starsze niż ${RETENTION_DAYS} dni"
    find "$BACKUP_DIR" -maxdepth 1 -type f -name 'rejestr-*' -mtime "+${RETENTION_DAYS}" \
        -print -delete
fi

echo "Gotowe: ${BACKUP_DIR}/${base}.* ($(du -ch "${files[@]/#/${BACKUP_DIR}/}" | tail -n1 | cut -f1))"
