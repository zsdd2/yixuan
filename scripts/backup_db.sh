#!/bin/sh
set -eu

COMPOSE_FILE="${COMPOSE_FILE:-docker-compose.prod.yml}"
BACKUP_DIR="${BACKUP_DIR:-backups}"
STAMP="$(date +%Y%m%d_%H%M%S)"
OUT_FILE="${BACKUP_DIR}/yixuan_db_${STAMP}.dump"

mkdir -p "$BACKUP_DIR"

echo "Creating database backup: $OUT_FILE"
docker compose -f "$COMPOSE_FILE" exec -T db pg_dump \
  -U "$POSTGRES_USER" \
  -d "$POSTGRES_DB" \
  -Fc > "$OUT_FILE"

echo "Backup complete: $OUT_FILE"
