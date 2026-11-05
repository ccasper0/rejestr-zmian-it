#!/usr/bin/env bash
# Odtworzenie "Rejestr zmian IT" z kopii scripts/backup.sh + weryfikacja.
# ADR 0019 §6, instrukcja: docs/deployment.md, sekcja "Odtworzenie".
#
#   scripts/restore.sh KOPIA.dump[.age] [--storage KOPIA-storage.tar.gz[.age]]
#                      [--db NAZWA] [--identity PLIK] [--force] [--skip-verify]
#                      [--no-checksum]
#
# Kopie zaszyfrowane (*.age, ADR 0019 §10) są odszyfrowywane strumieniowo
# (age -d | pg_restore, age -d | tar) kluczem prywatnym z pliku tożsamości
# --identity albo BACKUP_AGE_IDENTITY (age -d -i). Klucz prywatny przynieś na
# czas odtworzenia (nie przechowuj go na serwerze produkcyjnym) i usuń po nim.
#
# Kroki:
#   1. sprawdza sumy SHA-256 (plik KOPIA.sha256 obok zrzutu; dla *.age - sumy
#      plików zaszyfrowanych, sprawdzane PRZED odszyfrowaniem), a dla *.age
#      próbnie odszyfrowuje całość (klucz, integralność) zanim cokolwiek usunie;
#   2. tworzy PUSTĄ bazę (domyślnie rejestr) z uprawnieniami ról app_owner/app_rw
#      jak skrypt init (role muszą istnieć - tworzy je init przy pierwszym starcie
#      wolumenu db); istniejąca baza z danymi jest usuwana TYLKO z --force;
#   3. pg_restore (jako postgres, jedna transakcja, przerwanie przy błędzie);
#   4. opcjonalnie odtwarza pliki (wolumen storage) z archiwum --storage -
#      ZASTĘPUJE pliki w wolumenie projektu (nie używaj przy próbnym --db);
#   5. weryfikuje łańcuchy audytu: python -m app.cli verify-audit --global oraz
#      --company dla każdej spółki (wynik weryfikacji trafia do dziennika).
#
# Przed odtworzeniem bazy produkcyjnej zatrzymaj aplikację:
#   docker compose stop api worker web
# Uruchamiaj z katalogu głównego repozytorium (docker-compose.yml, .env).
# Odpowiednik dla Windows: scripts/restore.ps1.
set -euo pipefail
# Git Bash (Windows): do not rewrite container paths such as /tmp/... into C:/...
export MSYS_NO_PATHCONV=1

DUMP=""
STORAGE=""
DB_NAME="${POSTGRES_DB:-rejestr}"
IDENTITY="${BACKUP_AGE_IDENTITY:-}"
FORCE=0
VERIFY=1
CHECKSUM=1

usage() { awk 'NR > 1 && /^#/ { sub(/^# ?/, ""); print; next } NR > 1 { exit }' "$0"; }

while [ $# -gt 0 ]; do
    case "$1" in
        --storage) STORAGE="$2"; shift 2 ;;
        --db) DB_NAME="$2"; shift 2 ;;
        --identity) IDENTITY="$2"; shift 2 ;;
        --force) FORCE=1; shift ;;
        --skip-verify) VERIFY=0; shift ;;
        --no-checksum) CHECKSUM=0; shift ;;
        -h|--help) usage; exit 0 ;;
        -*) echo "Nieznana opcja: $1" >&2; usage >&2; exit 2 ;;
        *) DUMP="$1"; shift ;;
    esac
done

[ -n "$DUMP" ] || { usage >&2; exit 2; }
[ -f "$DUMP" ] || { echo "Brak pliku: $DUMP" >&2; exit 2; }
[ -z "$STORAGE" ] || [ -f "$STORAGE" ] || { echo "Brak pliku: $STORAGE" >&2; exit 2; }
case "$DB_NAME" in
    *[!a-z0-9_]*|'') echo "Nazwa bazy: tylko a-z, 0-9, _" >&2; exit 2 ;;
esac

case "$DUMP" in
    *.dump|*.dump.age) ;;
    *) echo "Oczekiwany plik *.dump albo *.dump.age: $DUMP" >&2; exit 2 ;;
esac

compose() { docker compose "$@"; }
psql_db() { compose exec -T db psql -v ON_ERROR_STOP=1 -U postgres -At "$@"; }

# Native Windows programs (age.exe) do not understand MSYS paths such as /c/...
native_path() {
    if command -v cygpath >/dev/null 2>&1; then cygpath -w "$1"; else printf '%s' "$1"; fi
}
is_encrypted() { case "$1" in *.age) return 0 ;; *) return 1 ;; esac; }
# Decrypted plaintext goes to stdout only - never to a file.
decrypt() { age -d -i "$(native_path "$IDENTITY")" "$(native_path "$1")"; }

ENCRYPTED=0
if is_encrypted "$DUMP" || { [ -n "$STORAGE" ] && is_encrypted "$STORAGE"; }; then
    ENCRYPTED=1
    if ! command -v age >/dev/null 2>&1; then
        echo "Kopia jest zaszyfrowana (*.age), a programu age nie ma w PATH" >&2
        echo "(apt install age / dnf install age / winget install FiloSottile.age)." >&2
        exit 1
    fi
    if [ -z "$IDENTITY" ]; then
        echo "Kopia jest zaszyfrowana (*.age): wskaż plik klucza prywatnego age" >&2
        echo "(--identity PLIK albo BACKUP_AGE_IDENTITY)." >&2
        exit 2
    fi
    [ -f "$IDENTITY" ] || { echo "Brak pliku klucza prywatnego: $IDENTITY" >&2; exit 2; }
fi

# 1. sumy kontrolne -----------------------------------------------------------
if [ "$CHECKSUM" = 1 ]; then
    sums="${DUMP%.age}"
    sums="${sums%.dump}.sha256"
    [ -f "$sums" ] || { echo "Brak pliku sum kontrolnych $sums (--no-checksum, aby pominąć)" >&2; exit 1; }
    echo "==> sprawdzam SHA-256 ($sums)"
    ( cd "$(dirname "$sums")" && sha256sum -c "$(basename "$sums")" )
fi

if [ "$ENCRYPTED" = 1 ]; then
    # Trial decryption to /dev/null: a wrong key or a damaged file fails here,
    # before the existing database or files are touched.
    for f in "$DUMP" ${STORAGE:+"$STORAGE"}; do
        if is_encrypted "$f"; then
            echo "==> sprawdzam odszyfrowanie $(basename "$f")"
            decrypt "$f" >/dev/null || {
                echo "Nie udało się odszyfrować $f (zły klucz prywatny lub uszkodzony plik)." >&2
                exit 1
            }
        fi
    done
fi

if [ -z "$(compose ps -q db 2>/dev/null)" ]; then
    echo "Usługa db nie działa (docker compose up -d db)." >&2
    exit 1
fi
db_container="$(compose ps -q db)"

for role in app_owner app_rw; do
    if [ "$(psql_db -d postgres -c "SELECT 1 FROM pg_roles WHERE rolname = '${role}'")" != 1 ]; then
        echo "Brak roli ${role}: baza docelowa musi być zainicjalizowana skryptem deploy/postgres/init." >&2
        exit 1
    fi
done

# 2. pusta baza ----------------------------------------------------------------
exists="$(psql_db -d postgres -c "SELECT 1 FROM pg_database WHERE datname = '${DB_NAME}'")"
if [ "$exists" = 1 ]; then
    tables="$(psql_db -d "$DB_NAME" -c \
        "SELECT count(*) FROM pg_tables WHERE schemaname = 'public'")"
    if [ "$tables" != 0 ] && [ "$FORCE" != 1 ]; then
        echo "Baza ${DB_NAME} zawiera ${tables} tabel. Odtworzenie ją USUNIE - użyj --force" >&2
        echo "(najpierw: docker compose stop api worker web)." >&2
        exit 1
    fi
    echo "==> usuwam istniejącą bazę ${DB_NAME}"
    psql_db -d postgres -c "DROP DATABASE \"${DB_NAME}\" WITH (FORCE)"
fi

echo "==> tworzę pustą bazę ${DB_NAME}"
psql_db -d postgres -c \
    "CREATE DATABASE \"${DB_NAME}\" TEMPLATE template0 ENCODING 'UTF8' LOCALE 'C.UTF-8'"
psql_db -d "$DB_NAME" <<SQL
REVOKE ALL ON DATABASE "${DB_NAME}" FROM PUBLIC;
GRANT CONNECT, TEMPORARY, CREATE ON DATABASE "${DB_NAME}" TO app_owner;
GRANT CONNECT, TEMPORARY ON DATABASE "${DB_NAME}" TO app_rw;
REVOKE ALL ON SCHEMA public FROM PUBLIC;
ALTER SCHEMA public OWNER TO app_owner;
GRANT USAGE ON SCHEMA public TO app_rw;
SQL

# 3. pg_restore ----------------------------------------------------------------
echo "==> pg_restore $(basename "$DUMP") -> ${DB_NAME}"
if is_encrypted "$DUMP"; then
    # Streamed: age -d -> pg_restore stdin (no decrypted dump on disk).
    decrypt "$DUMP" | compose exec -T db pg_restore -U postgres -d "$DB_NAME" \
        --exit-on-error --single-transaction
else
    tmp_in_container="/tmp/restore-$$.dump"
    compose cp "$DUMP" "db:${tmp_in_container}"
    trap 'compose exec -T db rm -f "$tmp_in_container" >/dev/null 2>&1 || true' EXIT
    compose exec -T db pg_restore -U postgres -d "$DB_NAME" --exit-on-error --single-transaction \
        "$tmp_in_container"
fi
echo "    tabele: $(psql_db -d "$DB_NAME" -c "SELECT count(*) FROM pg_tables WHERE schemaname = 'public'"), wpisy audytu: $(psql_db -d "$DB_NAME" -c 'SELECT count(*) FROM audit_log')"

# 4. pliki ---------------------------------------------------------------------
if [ -n "$STORAGE" ]; then
    project="$(docker inspect --format '{{index .Config.Labels "com.docker.compose.project"}}' "$db_container")"
    volume="$(docker volume ls -q \
        --filter "label=com.docker.compose.project=${project}" \
        --filter "label=com.docker.compose.volume=storage")"
    if [ -z "$volume" ]; then
        volume="${project}_storage"
        docker volume create \
            --label "com.docker.compose.project=${project}" \
            --label "com.docker.compose.volume=storage" "$volume" >/dev/null
    fi
    db_image="$(docker inspect --format '{{.Config.Image}}' "$db_container")"
    echo "==> odtwarzam pliki do wolumenu ${volume}"
    restore_files='find /data -mindepth 1 -delete && tar -C /data -xzf -'
    if is_encrypted "$STORAGE"; then
        decrypt "$STORAGE" | docker run --rm -i -v "${volume}:/data" "$db_image" sh -c "$restore_files"
    else
        docker run --rm -i -v "${volume}:/data" "$db_image" sh -c "$restore_files" < "$STORAGE"
    fi
fi

# 5. weryfikacja łańcuchów audytu ------------------------------------------------
if [ "$VERIFY" = 1 ]; then
    echo "==> weryfikacja łańcuchów audytu"
    status=0
    verify() {
        # The api image with DATABASE_URL pointed at the restored database (app_rw).
        compose run --rm --no-deps -T -e RESTORE_DB="$DB_NAME" --entrypoint sh api -c \
            'DATABASE_URL="${DATABASE_URL%/*}/${RESTORE_DB}" exec python -m app.cli verify-audit "$@"' \
            verify-audit "$@" || status=1
    }
    verify --global
    for prefix in $(psql_db -d "$DB_NAME" -c "SELECT prefix FROM companies ORDER BY prefix"); do
        verify --company "$prefix"
    done
    if [ "$status" != 0 ]; then
        echo "UWAGA: weryfikacja co najmniej jednego łańcucha nie powiodła się (patrz wyżej)." >&2
        exit 1
    fi
fi

echo "Odtworzenie zakończone. Uruchom aplikację: docker compose up -d"
