"""Bridge accepteert masterL en masterR VU-events apart, en stuurt ze
mee in de WebSocket-broadcast.

Idempotent via marker BRIDGE-STEREO-VU-V1.
"""
import sys

PATH = "bridge.js"
MARKER = "BRIDGE-STEREO-VU-V1"

with open(PATH) as f:
    content = f.read()

if MARKER in content:
    print(f"done — {PATH} al gepatcht ({MARKER})")
    sys.exit(0)

# 1. State: voeg masterVuL en masterVuR toe naast masterVu
OLD_STATE = 'let masterVol = 0.8, hpVol = 0.8, fxReturn = 0.0, masterVu = -100;'
NEW_STATE = 'let masterVol = 0.8, hpVol = 0.8, fxReturn = 0.0, masterVu = -100, masterVuL = -100, masterVuR = -100;'

if OLD_STATE not in content:
    print("ERROR: state-anker niet gevonden", file=sys.stderr)
    sys.exit(1)
content = content.replace(OLD_STATE, NEW_STATE, 1)

# 2. Handler: masterL en masterR apart, plus oude master als alias
OLD_HANDLER = '  if (who === "master") masterVu = val;\n  else { const idx = parseInt(who); if (state[idx]) state[idx].vu = val; }'
NEW_HANDLER = '''  // === BRIDGE-STEREO-VU-V1 ===
  if (who === "masterL") { masterVuL = val; masterVu = (masterVuL + masterVuR) / 2; }
  else if (who === "masterR") { masterVuR = val; masterVu = (masterVuL + masterVuR) / 2; }
  else if (who === "master") masterVu = val;  // backward compat
  else { const idx = parseInt(who); if (state[idx]) state[idx].vu = val; }'''

if OLD_HANDLER not in content:
    print("ERROR: handler-anker niet gevonden", file=sys.stderr)
    sys.exit(1)
content = content.replace(OLD_HANDLER, NEW_HANDLER, 1)

# 3. Broadcast: voeg masterVuL en masterVuR toe
OLD_BCAST = '  broadcast({ type: "vu", channels: CHANNELS.map(ch => ({ index: ch.index, vu: state[ch.index].vu })), masterVu });'
NEW_BCAST = '  broadcast({ type: "vu", channels: CHANNELS.map(ch => ({ index: ch.index, vu: state[ch.index].vu })), masterVu, masterVuL, masterVuR });'

if OLD_BCAST not in content:
    print("ERROR: broadcast-anker niet gevonden", file=sys.stderr)
    sys.exit(1)
content = content.replace(OLD_BCAST, NEW_BCAST, 1)

with open(PATH, "w") as f:
    f.write(content)

print(f"✓ Patched {PATH} ({MARKER})")
print("  State, handler, broadcast bijgewerkt")
