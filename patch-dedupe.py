"""Voegt event-dedupe toe in bridge.js samplerIn-handler.

Zelfde (slot, event) binnen 500ms wordt gedropt. Beschermt tegen
Pd-side broadcast-multiplicatie (open issue: precieze oorzaak nog
niet bekend, gevonden in fase 2-debug 27 apr).

Ook verwijdert de [DEBUG] raw line die we voor diagnose gebruikten.

Idempotent via marker SAMPLER-EVENT-DEDUPE-V1.
"""
import sys

PATH = "bridge.js"
MARKER = "SAMPLER-EVENT-DEDUPE-V1"

with open(PATH) as f:
    content = f.read()

if MARKER in content:
    print(f"done — {PATH} al gepatcht ({MARKER})")
    sys.exit(0)

# Verwijder eerst de DEBUG raw-line van eerder
DEBUG_LINE = '  console.log(`[DEBUG] raw: ${JSON.stringify(line)}`);\n'
if DEBUG_LINE in content:
    content = content.replace(DEBUG_LINE, '', 1)
    print("- DEBUG raw line verwijderd")

# Voeg dedupe-state toe op modul-level. We zoeken een logische plek:
# vlak vóór samplerIn.on("message", ...). De anker is de comment of
# rechtstreeks de "samplerIn.on(\"message\""-regel.
ANCHOR = 'samplerIn.on("message", buf => {'
if ANCHOR not in content:
    print("ERROR: anker samplerIn.on niet gevonden", file=sys.stderr)
    sys.exit(1)

DEDUPE_STATE = '''// === SAMPLER-EVENT-DEDUPE-V1 ===
// Pd dupliceert sommige status-broadcasts (~9x per event); de oorzaak
// zit in de patch-architectuur (open issue). Bridge dedupt hier:
// hetzelfde (slot, event) binnen 500ms wordt slechts 1x verwerkt.
const samplerEventLastSeen = new Map();  // key: "slot:event", value: timestamp
const SAMPLER_EVENT_DEDUPE_MS = 500;

'''

content = content.replace(ANCHOR, DEDUPE_STATE + ANCHOR, 1)

# Voeg de dedupe-check toe vlak vóór de switch in de handler.
SWITCH_ANCHOR = '  // State-machine: mappen van event naar state-veld\n  switch (event) {'
DEDUPE_CHECK = '''  // === SAMPLER-EVENT-DEDUPE-V1 ===
  const dedupeKey = `${slot}:${event}`;
  const now = Date.now();
  const lastSeen = samplerEventLastSeen.get(dedupeKey);
  if (lastSeen && (now - lastSeen) < SAMPLER_EVENT_DEDUPE_MS) {
    return;  // duplicate, drop
  }
  samplerEventLastSeen.set(dedupeKey, now);

  // State-machine: mappen van event naar state-veld
  switch (event) {'''

if SWITCH_ANCHOR not in content:
    print("ERROR: switch-anker niet gevonden", file=sys.stderr)
    sys.exit(1)

content = content.replace(SWITCH_ANCHOR, DEDUPE_CHECK, 1)

with open(PATH, "w") as f:
    f.write(content)

print(f"✓ Patched {PATH}")
print(f"  Dedupe-state toegevoegd vóór samplerIn.on")
print(f"  Dedupe-check toegevoegd vóór switch")
print(f"  Marker: {MARKER}")
