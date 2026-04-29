#!/usr/bin/env bash
# patch-masterfader-digit.sh
# Doel: %-readout op de master-fader thumb (zelfde patroon als channel-faders).
set -euo pipefail

FILE="$HOME/Documents/Pd/PDMixer/v2/index.html"
MARKER="MASTERFADER-DIGIT-V1"

[ ! -f "$FILE" ] && { echo "ERROR: $FILE niet gevonden"; exit 1; }

if grep -q "$MARKER" "$FILE"; then
  echo "Al gepatcht ($MARKER aanwezig) — niets te doen."
  exit 0
fi

# Backup
cp "$FILE" "$FILE.bak.$(date +%Y%m%d-%H%M%S)"

python3 - "$FILE" << 'PY_EOF'
import sys
path = sys.argv[1]
with open(path, 'r') as f:
    content = f.read()

# === Stap 1: digit-element aanmaken in buildMasterFader, na thumb-creatie ===
old1 = '''  var thumb=document.createElement('div');thumb.className='fvu-thumb';thumb.id='th-m';
  var line=document.createElement('div');line.className='fvu-line';thumb.appendChild(line);
  thumb.style.top=((1-master.vol)*R+PAD+6.5)+'px';'''

new1 = '''  var thumb=document.createElement('div');thumb.className='fvu-thumb';thumb.id='th-m';
  var line=document.createElement('div');line.className='fvu-line';thumb.appendChild(line);
  // === MASTERFADER-DIGIT-V1 === %-readout op master-thumb (channel-fader patroon)
  var digit=document.createElement('div');digit.className='fvu-digit';digit.id='dig-m';
  digit.textContent=Math.round(master.vol*100)+'%';
  digit.style.top=master.vol>0.85?'18px':'-16px';
  thumb.appendChild(digit);
  thumb.style.top=((1-master.vol)*R+PAD+6.5)+'px';'''

assert content.count(old1) == 1, f"stap 1: verwacht 1 match, kreeg {content.count(old1)}"
content = content.replace(old1, new1, 1)

# === Stap 2: digit bijwerken in drag-handler ===
old2 = "  function mv(y){if(!drag)return;var v=Math.max(0,Math.min(1,sv+(sy-y)/R));thumb.style.top=((1-v)*R+PAD+6.5)+'px';master.vol=v;send({type:'masterVol',value:v});saveMaster();}"

new2 = "  function mv(y){if(!drag)return;var v=Math.max(0,Math.min(1,sv+(sy-y)/R));thumb.style.top=((1-v)*R+PAD+6.5)+'px';var d=document.getElementById('dig-m');if(d){d.textContent=Math.round(v*100)+'%';d.style.top=v>0.85?'18px':'-16px';}master.vol=v;send({type:'masterVol',value:v});saveMaster();}"

assert content.count(old2) == 1, f"stap 2: verwacht 1 match, kreeg {content.count(old2)}"
content = content.replace(old2, new2, 1)

with open(path, 'w') as f:
    f.write(content)
PY_EOF

# Verificatie
COUNT=$(grep -c "$MARKER" "$FILE" || true)
if [ "$COUNT" -eq 1 ]; then
  echo "OK: patch toegepast (marker $COUNT keer aanwezig)."
else
  echo "ERROR: marker $COUNT keer aanwezig, verwacht: 1." >&2
  exit 1
fi
