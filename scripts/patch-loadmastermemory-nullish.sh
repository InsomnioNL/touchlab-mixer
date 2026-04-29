#!/usr/bin/env bash
# patch-loadmastermemory-nullish.sh
# Doel: || → ?? in loadMasterMemory() zodat opgeslagen 0-waardes
#       niet stilletjes door fallback worden vervangen.
set -euo pipefail

FILE="$HOME/Documents/touchlab-mixer/index.html"
MARKER="LOADMASTER-NULLISH-V1"
OLD='  if(m) return {vol:m.vol||0.8,pan:m.pan||0.5,fxReturn:m.fxReturn||0};'
NEW='  // === LOADMASTER-NULLISH-V1 === ?? ipv || zodat opgeslagen 0 niet door fallback wordt vervangen
  if(m) return {vol:m.vol??0,pan:m.pan??0.5,fxReturn:m.fxReturn??0};'

[ ! -f "$FILE" ] && { echo "ERROR: $FILE niet gevonden"; exit 1; }

# Idempotentie: als marker al aanwezig, niets doen.
if grep -q "$MARKER" "$FILE"; then
  echo "Al gepatcht ($MARKER aanwezig) — niets te doen."
  exit 0
fi

# Veiligheid: oude regel moet exact één keer voorkomen.
COUNT=$(grep -cF "$OLD" "$FILE" || true)
if [ "$COUNT" -ne 1 ]; then
  echo "ERROR: oude regel komt $COUNT keer voor, verwacht: 1. Niets gedaan." >&2
  exit 1
fi

# Backup
cp "$FILE" "$FILE.bak.$(date +%Y%m%d-%H%M%S)"

# Vervanging via python (geen regex-escape-hel, geen runaway-risico)
python3 - "$FILE" "$OLD" "$NEW" << 'PY_EOF'
import sys
path, old, new = sys.argv[1], sys.argv[2], sys.argv[3]
with open(path, 'r') as f:
    content = f.read()
assert content.count(old) == 1, "exact 1 match expected"
content = content.replace(old, new, 1)
with open(path, 'w') as f:
    f.write(content)
PY_EOF

# Verificatie
if grep -q "$MARKER" "$FILE" && ! grep -qF "$OLD" "$FILE"; then
  echo "OK: patch toegepast."
else
  echo "ERROR: patch lijkt niet toegepast." >&2
  exit 1
fi
