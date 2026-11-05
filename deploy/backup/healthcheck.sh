#!/bin/sh
# Healthcheck usługi "backup" (docker-compose.yml), ADR 0019 §11, ISO 27001 A.8.13.
#
# Znaczniki zapisuje backup-loop.sh w katalogu kopii (/backups):
#   .backup-last-success  - po każdej udanej kopii (także --once)
#   .backup-last-failure  - po nieudanym zaplanowanym uruchomieniu
# Treść znacznika: "<czas epoch UTC> <opis>".
#
# Kod 1 (unhealthy), gdy:
#   - ostatnie uruchomienie się nie udało (znacznik błędu nowszy niż sukcesu),
#   - ostatnia udana kopia jest starsza niż BACKUP_MAX_AGE_HOURS (domyślnie 26),
#   - nie ma żadnej udanej kopii, a pętla działa dłużej niż BACKUP_MAX_AGE_HOURS.
# Wynik (ostatnia linia wyjścia) widać w `docker inspect` (State.Health.Log).
set -u

OUT=/backups
MAX_AGE_HOURS="${BACKUP_MAX_AGE_HOURS:-26}"
SUCCESS_MARKER="${OUT}/.backup-last-success"
FAILURE_MARKER="${OUT}/.backup-last-failure"
STARTED_MARKER=/tmp/backup-loop.started

case "$MAX_AGE_HOURS" in
    '' | *[!0-9]*)
        echo "backup: BACKUP_MAX_AGE_HOURS must be a whole number of hours"
        exit 1
        ;;
esac
max_age_s=$((MAX_AGE_HOURS * 3600))
now="$(date -u +%s)"

# First field of a marker file (epoch seconds), empty when missing/invalid.
marker_time() {
    [ -f "$1" ] || return 0
    value="$(cut -d ' ' -f 1 "$1" 2>/dev/null | head -n 1)"
    case "$value" in
        '' | *[!0-9]*) ;;
        *) echo "$value" ;;
    esac
}

ok_at="$(marker_time "$SUCCESS_MARKER")"
failed_at="$(marker_time "$FAILURE_MARKER")"

if [ -n "$failed_at" ] && { [ -z "$ok_at" ] || [ "$failed_at" -ge "$ok_at" ]; }; then
    echo "backup: UNHEALTHY - last run failed ($(cat "$FAILURE_MARKER"))"
    exit 1
fi

if [ -n "$ok_at" ]; then
    age=$((now - ok_at))
    if [ "$age" -gt "$max_age_s" ]; then
        echo "backup: UNHEALTHY - last successful backup ${age}s ago (> ${MAX_AGE_HOURS} h)"
        exit 1
    fi
    echo "backup: ok - last successful backup ${age}s ago ($(cut -d ' ' -f 2- "$SUCCESS_MARKER"))"
    exit 0
fi

started_at="$(marker_time "$STARTED_MARKER")"
if [ -n "$started_at" ] && [ $((now - started_at)) -le "$max_age_s" ]; then
    echo "backup: ok - waiting for the first backup (loop started $((now - started_at))s ago)"
    exit 0
fi
echo "backup: UNHEALTHY - no successful backup within ${MAX_AGE_HOURS} h"
exit 1
