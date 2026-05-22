#!/bin/sh
set -eu

if [ "${RESTORE_CONFIRM:-}" != "YES" ]; then
  echo "Refusing to restore without confirmation."
  echo "Run with RESTORE_CONFIRM=YES and pass a backup file path."
  exit 1
fi

if [ $# -ne 1 ]; then
  echo "Usage: RESTORE_CONFIRM=YES $0 backups/yixuan_db_YYYYMMDD_HHMMSS.dump"
  exit 1
fi

COMPOSE_FILE="${COMPOSE_FILE:-docker-compose.prod.yml}"
BACKUP_FILE="$1"

if [ ! -f "$BACKUP_FILE" ]; then
  echo "Backup file not found: $BACKUP_FILE"
  exit 1
fi

echo "Restoring database from: $BACKUP_FILE"
cat "$BACKUP_FILE" | docker compose -f "$COMPOSE_FILE" exec -T db pg_restore \
  -U "$POSTGRES_USER" \
  -d "$POSTGRES_DB" \
  --clean \
  --if-exists

echo "Restore complete."
