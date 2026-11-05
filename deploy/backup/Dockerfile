# Image of the optional "backup" service (ADR 0019 §6, §10): the same PostgreSQL
# client as the db service + age for encrypting backups (BACKUP_AGE_RECIPIENT).
FROM postgres:16-alpine
RUN apk add --no-cache age
