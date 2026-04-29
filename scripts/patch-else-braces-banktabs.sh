#!/usr/bin/env bash
# patch-else-braces-banktabs.sh
# Doel: else zonder accolades op regel 1470 wordt symmetrisch met de if-tak.
set -euo pipefail

FILE="$HOME/Documents/Pd/PDMixer/v2/index.html"
MARKER="ELSE-BRACES-BANKTABS-V1"

[ ! -f "$FILE" ] && { echo "ERROR: $FILE niet gevonden"; exit 1; }

if grep -q "$MARKER" "$FILE"; then
  echo "Al gepatcht ($MARKER aanwezig) — niets te doen."
  exit 0
fi

cp "$FILE" "$FILE.bak.$(date +%Y%m%d-%H%M%S)"

python3 - "$FILE" << 'PY_EOF'
import sys
path = sys.argv[1]
with open(path, 'r') as f:
    content = f.read()

old = "  } else tabs.classList.remove('visible');"
new = """  } else { // === ELSE-BRACES-BANKTABS-V1 === accolades voor symmetrie met if-tak
    tabs.classList.remove('visible');
  }"""

assert content.count(old) == 1, f"verwacht 1 match, kreeg {content.count(old)}"
content = content.replace(old, new, 1)

with open(path, 'w') as f:
    f.write(content)
PY_EOF

COUNT=$(grep -c "$MARKER" "$FILE" || true)
if [ "$COUNT" -eq 1 ]; then
  echo "OK: patch toegepast (marker $COUNT keer aanwezig)."
else
  echo "ERROR: marker $COUNT keer aanwezig, verwacht: 1." >&2
  exit 1
fi
