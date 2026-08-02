#!/usr/bin/env bash
# Compact ~/.config/Cursor/User/globalStorage/state.vscdb (often 20G+).
# MUST run with Cursor fully quit (no cursor processes).
set -euo pipefail

DB="$HOME/.config/Cursor/User/globalStorage/state.vscdb"
COMPACT="$DB.compact"
BACKUP="$DB.pre-compact-$(date +%Y%m%d%H%M%S)"

if pgrep -x cursor >/dev/null 2>&1 || pgrep -f '/usr/share/cursor/cursor' >/dev/null 2>&1; then
  echo "ERROR: Cursor is still running. Quit Cursor completely, then re-run:"
  echo "  $0"
  exit 2
fi

if [[ ! -f "$DB" ]]; then
  echo "No state.vscdb at $DB"
  exit 0
fi

before=$(stat -c%s "$DB")
echo "before_bytes=$before ($(numfmt --to=iec "$before"))"
rm -f "$COMPACT"
python3 - <<PY
import sqlite3
src = "$DB"
out = "$COMPACT"
con = sqlite3.connect(src, timeout=60)
con.execute(f"VACUUM INTO '{out}'")
con.close()
print("compact_ok")
PY
after=$(stat -c%s "$COMPACT")
echo "compact_bytes=$after ($(numfmt --to=iec "$after"))"
if (( after >= before )); then
  echo "Compact not smaller; leaving original in place."
  rm -f "$COMPACT"
  exit 0
fi
mv -f "$DB" "$BACKUP"
mv -f "$COMPACT" "$DB"
rm -f "$DB-wal" "$DB-shm" 2>/dev/null || true
echo "Replaced DB. Backup kept at: $BACKUP"
echo "After Cursor starts cleanly for a day, you can delete the backup to reclaim space."
df -h /
