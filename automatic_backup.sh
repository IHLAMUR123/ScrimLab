#!/usr/bin/env bash
# Consistent SQLite backup for ScrimLab.
#
# The database runs in WAL mode, so copying main.sqlite while the bot is
# running can produce a torn backup. This uses SQLite's online backup API,
# which takes a consistent snapshot without stopping the bot.
#
# Usage:
#   ./automatic_backup.sh                 # host: db/main.sqlite
#   ./automatic_backup.sh --docker        # compose: scrimlab service
#   KEEP_DAYS=30 ./automatic_backup.sh    # keep 30 days (default 14)
#
# Output: backups/main-YYYYmmdd-HHMMSS.sqlite.gz
set -euo pipefail

DB_PATH="${DB_PATH:-db/main.sqlite}"
BACKUP_DIR="${BACKUP_DIR:-backups}"
KEEP_DAYS="${KEEP_DAYS:-14}"
SERVICE="${SERVICE:-scrimlab}"
MODE="host"

for arg in "$@"; do
  case "$arg" in
    --docker) MODE="docker" ;;
    -h|--help) sed -n '2,14p' "$0"; exit 0 ;;
    *) echo "Unknown argument: $arg" >&2; exit 2 ;;
  esac
done

mkdir -p "$BACKUP_DIR"
STAMP="$(date +%Y%m%d-%H%M%S)"
NAME="main-$STAMP.sqlite"
OUT="$BACKUP_DIR/$NAME"

if [ "$MODE" = "docker" ]; then
  command -v docker >/dev/null 2>&1 || { echo "docker not found" >&2; exit 1; }
  docker compose exec -T "$SERVICE" python -c "
import sqlite3
src = sqlite3.connect('/app/db/main.sqlite')
dst = sqlite3.connect('/tmp/$NAME')
src.backup(dst)
dst.close()
src.close()
"
  docker compose cp "$SERVICE:/tmp/$NAME" "$OUT"
  docker compose exec -T "$SERVICE" rm -f "/tmp/$NAME"
else
  PYTHON="${PYTHON:-python3}"
  command -v "$PYTHON" >/dev/null 2>&1 || PYTHON=python
  command -v "$PYTHON" >/dev/null 2>&1 || { echo "python not found" >&2; exit 1; }
  [ -f "$DB_PATH" ] || { echo "database not found: $DB_PATH" >&2; exit 1; }
  "$PYTHON" -c "
import sqlite3, sys
src = sqlite3.connect(sys.argv[1])
dst = sqlite3.connect(sys.argv[2])
src.backup(dst)
dst.close()
src.close()
" "$DB_PATH" "$OUT"
fi

gzip -f "$OUT"
echo "Backup written: $OUT.gz"

# Retention: delete snapshots older than KEEP_DAYS (0 disables).
if [ "$KEEP_DAYS" -gt 0 ] 2>/dev/null; then
  find "$BACKUP_DIR" -maxdepth 1 -type f -name 'main-*.sqlite.gz' \
    -mtime +"$KEEP_DAYS" -print -delete
fi
