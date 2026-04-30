#!/usr/bin/env python3
"""patch-bridge-ttb-route-v1.py

Voegt aan bridge.js een WS-handler toe voor ttbRoute-berichten.
Bericht-formaat: {type:"ttbRoute", value:"local"|"live"}.
Stuurt naar Pd:
  ; ttb-route-local 1 ; ttb-route-live 0
of omgekeerd.

Marker: TTB-ROUTE-BRIDGE-V1 (idempotent).
Anker: het bestaande samplerMasterVol-case-blok.
"""

import shutil, sys
from datetime import datetime
from pathlib import Path

V2 = Path.home() / "Documents/Pd/PDMixer/v2"
TARGET = V2 / "bridge.js"
BACKUPS = V2 / "_backups"
MARKER = "TTB-ROUTE-BRIDGE-V1"

ANCHOR = (
    '    case "samplerMasterVol": {\n'
    '      // Master-vol: per slot een eigen [r sampler-master-vol] -> [pack 0 20] -> [line~] -> *~ chain\n'
    '      const v = clamp(msg.value, 0, 1);\n'
    '      sendSampler("sampler-master-vol", v);\n'
    '      broadcast({ type: "samplerMasterVol", value: v });\n'
    '      break;\n'
    '    }'
)

INSERT = (
    '    // === TTB-ROUTE-BRIDGE-V1 ===\n'
    '    case "ttbRoute": {\n'
    '      // value: local | live - mutually exclusive route-switch\n'
    '      const route = (msg.value === "local") ? "local" : "live";\n'
    '      const localOn = (route === "local") ? 1 : 0;\n'
    '      const liveOn  = (route === "live")  ? 1 : 0;\n'
    '      sendPD("ttb-route-local", localOn);\n'
    '      sendPD("ttb-route-live",  liveOn);\n'
    '      broadcast({ type: "ttbRoute", value: route });\n'
    '      break;\n'
    '    }'
)

text = TARGET.read_text()

if MARKER in text:
    print(f"Marker {MARKER} reeds aanwezig; geen wijziging.")
    sys.exit(0)

if text.count(ANCHOR) != 1:
    print(f"ERROR: anker (samplerMasterVol-case) niet exact 1x gevonden ({text.count(ANCHOR)}x). Bail.")
    sys.exit(1)

BACKUPS.mkdir(exist_ok=True)
ts = datetime.now().strftime("%Y%m%d-%H%M%S")
backup = BACKUPS / f"bridge.js.{ts}.bak"
shutil.copy(TARGET, backup)
print(f"Backup: {backup}")

new_text = text.replace(ANCHOR, ANCHOR + "\n" + INSERT, 1)
TARGET.write_text(new_text)
print(f"Wrote {TARGET.name}: WS-handler ttbRoute toegevoegd")
