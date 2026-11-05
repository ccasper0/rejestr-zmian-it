#!/bin/sh
# Usługa "backup" (docker compose --profile backup up -d backup), ADR 0019 §6.
#
# Codziennie o BACKUP_AT (HH:MM, UTC) wykonuje kopię tak jak scripts/backup.sh:
# pg_dump (format custom, jako postgres - RLS nie ogranicza zrzutu) + archiwum
# wolumenu storage + plik sum SHA-256, z retencją BACKUP_RETENTION_DAYS dni.
# Kopie trafiają do /backups (w compose: katalog ${BACKUP_HOST_DIR:-./backups}).
# Odtworzenie: scripts/restore.sh / scripts/restore.ps1 (docs/deployment.md).
#
# Szyfrowanie (ADR 0019 §10): BACKUP_AGE_RECIPIENT = klucz publiczny age (kilka
# rozdziel przecinkami) -> pliki *.dump.age i *-storage.tar.gz.age szyfrowane
# strumieniowo (pg_dump | age, tar | age), sumy SHA-256 z plików zaszyfrowanych.
# BACKUP_AGE_RECIPIENTS (plik kluczy) działa tylko w scripts/backup.sh|ps1 -
# ścieżka z .env to ścieżka hosta, niewidoczna w kontenerze; usługa odmawia
# startu zamiast po cichu zapisywać kopie bez szyfrowania.
#
# Monitoring (ADR 0019 §11, ISO 27001 A.8.13): po udanej kopii zapisywany jest
# znacznik /backups/.backup-last-success, po nieudanym zaplanowanym uruchomieniu
# /backups/.backup-last-failure (treść: czas epoch UTC + opis). healthcheck.sh
# (healthcheck usługi w compose) zgłasza "unhealthy", gdy ostatnie uruchomienie
# się nie udało albo ostatnia udana kopia jest starsza niż BACKUP_MAX_AGE_HOURS.
set -eu

: "${PGPASSWORD:?PGPASSWORD (POSTGRES_PASSWORD) must be set}"
DB_HOST="${DB_HOST:-db}"
DB_NAME="${POSTGRES_DB:-rejestr}"
BACKUP_AT="${BACKUP_AT:-01:30}"
RETENTION_DAYS="${BACKUP_RETENTION_DAYS:-14}"
OUT=/backups
AGE_RECIPIENTS_FILE=/tmp/age-recipients
SUFFIX=""
SUCCESS_MARKER="${OUT}/.backup-last-success"
FAILURE_MARKER="${OUT}/.backup-last-failure"
STARTED_MARKER=/tmp/backup-loop.started

# $1 = marker file, $2 = description; written atomically (tmp + mv).
write_marker() {
    printf '%s %s\n' "$(date -u +%s)" "$2" > "$1.tmp"
    mv -f "$1.tmp" "$1"
}

setup_encryption() {
    if [ -n "${BACKUP_AGE_RECIPIENTS:-}" ]; then
        echo "backup: usługa nie obsługuje BACKUP_AGE_RECIPIENTS (plik kluczy, ścieżka hosta);" >&2
        echo "backup: użyj BACKUP_AGE_RECIPIENT (klucze publiczne rozdzielone przecinkami)." >&2
        exit 2
    fi
    [ -n "${BACKUP_AGE_RECIPIENT:-}" ] || return 0
    if ! command -v age >/dev/null 2>&1; then
        echo "backup: BACKUP_AGE_RECIPIENT ustawione, ale brak programu age w obrazie" >&2
        echo "backup: (docker compose --profile backup build backup). Kopia NIE powstaje." >&2
        exit 1
    fi
    # One recipient per line for age -R (age1... and ssh-... keys).
    printf '%s\n' "$BACKUP_AGE_RECIPIENT" | tr ',' '\n' \
        | sed -e 's/^[[:space:]]*//' -e 's/[[:space:]]*$//' | grep -v '^$' \
        > "$AGE_RECIPIENTS_FILE" || true
    if [ ! -s "$AGE_RECIPIENTS_FILE" ]; then
        echo "backup: BACKUP_AGE_RECIPIENT nie zawiera żadnego klucza publicznego." >&2
        exit 2
    fi
    if ! age -R "$AGE_RECIPIENTS_FILE" </dev/null >/dev/null; then
        echo "backup: nieprawidłowy klucz publiczny age w BACKUP_AGE_RECIPIENT." >&2
        exit 2
    fi
    SUFFIX=".age"
}

# stdin -> $1: encrypted with age when configured, otherwise as is.
write_out() {
    if [ -n "$SUFFIX" ]; then age -R "$AGE_RECIPIENTS_FILE" -o "$1"; else cat > "$1"; fi
}

backup_once() {
    set -o pipefail
    stamp="$(date -u +%Y%m%dT%H%M%SZ)"
    base="rejestr-${stamp}"
    partial=""
    trap '[ -z "$partial" ] || rm -f "$partial"' EXIT
    echo "backup: ${base} start${SUFFIX:+ (age)}"
    # Streamed: no unencrypted intermediate file when encryption is on; written
    # as *.part and renamed only after the whole pipeline succeeded.
    dump="${base}.dump${SUFFIX}"
    partial="${OUT}/${dump}.part"
    pg_dump -h "$DB_HOST" -U postgres -d "$DB_NAME" --format=custom --compress=6 \
        | write_out "$partial"
    mv "$partial" "${OUT}/${dump}"
    files="${dump}"
    if [ -d /data/storage ]; then
        storage="${base}-storage.tar.gz${SUFFIX}"
        partial="${OUT}/${storage}.part"
        tar -C /data/storage -czf - . | write_out "$partial"
        mv "$partial" "${OUT}/${storage}"
        files="${files} ${storage}"
    fi
    partial=""
    # shellcheck disable=SC2086 # word splitting of the file list is intended
    (cd "$OUT" && sha256sum $files > "${base}.sha256" && sha256sum -c -s "${base}.sha256")
    if [ "$RETENTION_DAYS" -gt 0 ]; then
        # rejestr-* covers *.dump[.age], *-storage.tar.gz[.age], *.sha256, *.part.
        find "$OUT" -maxdepth 1 -type f -name 'rejestr-*' -mtime "+${RETENTION_DAYS}" \
            -print -delete
    fi
    echo "backup: ${base} done"
    LAST_BASE="$base"
}

seconds_until() {
    now="$(date -u +%s)"
    target="$(date -u -d "$(date -u +%Y-%m-%d) ${1}:00" +%s 2>/dev/null \
        || date -u -D '%Y-%m-%d %H:%M:%S' -d "$(date -u +%Y-%m-%d) ${1}:00" +%s)"
    if [ "$target" -le "$now" ]; then
        target=$((target + 86400))
    fi
    echo $((target - now))
}

setup_encryption

if [ "${1:-}" = "--once" ]; then
    # Not inside an if/|| list: "set -e" must stay effective in backup_once. The
    # marker is reached only after a complete, checksum-verified backup.
    LAST_BASE=""
    backup_once
    write_marker "$SUCCESS_MARKER" "$LAST_BASE"
    rm -f "$FAILURE_MARKER"
    exit 0
fi

# Grace period for the healthcheck until the first scheduled backup (container
# filesystem: a restarted container starts a new grace period, an existing
# success marker in /backups still counts).
write_marker "$STARTED_MARKER" "loop started"

echo "backup: daily at ${BACKUP_AT} UTC, retention ${RETENTION_DAYS} days, output ${OUT}${SUFFIX:+, age encryption}"
while true; do
    wait_s="$(seconds_until "$BACKUP_AT")"
    echo "backup: next run in ${wait_s}s"
    sleep "$wait_s"
    # A separate process: "set -e" is ignored inside a function called from an
    # "||" list, so a failed pg_dump would otherwise be checksummed as a backup.
    # A failed run is logged and retried the next day; the service keeps running.
    # The failure marker makes the service unhealthy until the next success.
    if sh "$0" --once; then
        :
    else
        rc=$?
        echo "backup: FAILED (exit ${rc})" >&2
        write_marker "$FAILURE_MARKER" "exit ${rc}" \
            || echo "backup: cannot write ${FAILURE_MARKER}" >&2
    fi
done
