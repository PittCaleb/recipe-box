#!/bin/sh
# Pull a fresh copy of the live recipes data from the NAS into ./data (and the
# source PDFs into ./pdf) so you can test against real data locally.
#
#   scripts/pull-live-data.sh
#
# Nothing on the NAS is changed except a temporary snapshot file in its
# tmp/ folder, which is removed afterwards. The database is copied with
# SQLite's backup API inside the container, so it's consistent even while
# someone is using the app. Your current local database is kept in
# data/backups/ before it's replaced.
#
# Local only: changes you make to this copy never go back to the NAS.
set -eu

NAS="${RECIPES_NAS:-cohenc@mockingnas.local}"
NAS_DIR=/share/Container/mockingnas
REMOTE_DATA="$NAS_DIR/data/recipes"
SNAPSHOT=pull-snapshot.db

cd "$(dirname "$0")/.."
LOCAL_DATA=./data

port="${RECIPES_PORT:-5052}"
if lsof -nP -iTCP:"$port" -sTCP:LISTEN >/dev/null 2>&1; then
    echo "Something is running on port $port (the local app?). Stop it first, then run this again." >&2
    exit 1
fi

echo "Taking a snapshot of the live database..."
ssh "$NAS" "$NAS_DIR/dc.sh exec -T recipes python -c \"import sqlite3; sqlite3.connect('/data/recipes.db').backup(sqlite3.connect('/data/tmp/$SNAPSHOT'))\""
# The container wrote the snapshot, so it has to be the one to remove it.
trap 'ssh "$NAS" "$NAS_DIR/dc.sh exec -T recipes rm -f /data/tmp/$SNAPSHOT" || true' EXIT

mkdir -p "$LOCAL_DATA/backups" "$LOCAL_DATA/tmp" ./pdf
rsync -t "$NAS:$REMOTE_DATA/tmp/$SNAPSHOT" "$LOCAL_DATA/tmp/$SNAPSHOT"

if [ -f "$LOCAL_DATA/recipes.db" ]; then
    keep="$LOCAL_DATA/backups/recipes-local-$(date +%Y%m%d-%H%M%S).db"
    mv "$LOCAL_DATA/recipes.db" "$keep"
    echo "Kept your old local database as $keep"
fi
rm -f "$LOCAL_DATA/recipes.db-wal" "$LOCAL_DATA/recipes.db-shm"
mv "$LOCAL_DATA/tmp/$SNAPSHOT" "$LOCAL_DATA/recipes.db"

# Photos, scans and import files must match the database, so stale local
# ones are removed. Source PDFs are only ever added to.
echo "Copying photos, scans and import files..."
for d in images scans import; do
    mkdir -p "$LOCAL_DATA/$d"
    rsync -a --delete "$NAS:$REMOTE_DATA/$d/" "$LOCAL_DATA/$d/"
done
rsync -a "$NAS:$REMOTE_DATA/pdf/" ./pdf/

recipes=$(.venv/bin/python -c "import sqlite3; print(sqlite3.connect('$LOCAL_DATA/recipes.db').execute('select count(*) from recipes').fetchone()[0])")
echo "Done: $recipes recipes, $(ls "$LOCAL_DATA/images" | wc -l | tr -d ' ') image files. Start the app with .venv/bin/python run.py"
