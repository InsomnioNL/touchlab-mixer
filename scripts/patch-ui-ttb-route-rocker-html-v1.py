#!/usr/bin/env python3
"""patch-ui-ttb-route-rocker-html-v1.py

Voegt rocker-HTML in de TTB-popup-header toe, direct na de titel
en vóór de bestaande .ttb-mode-twin (PLAY/EDIT).

Marker: TTB-ROUTE-ROCKER-V1 (idempotent).
Anker: de regel met <div class="ttb-mode-twin"> (dat is regel 2502 in huidige file).
"""

import shutil, sys
from datetime import datetime
from pathlib import Path

V2 = Path.home() / "Documents/Pd/PDMixer/v2"
TARGET = V2 / "index.html"
BACKUPS = V2 / "_backups"
MARKER = "TTB-ROUTE-ROCKER-V1"

ANCHOR = '      <div class="ttb-mode-twin">'

INSERT = (
    '      <!-- === TTB-ROUTE-ROCKER-V1 === -->\n'
    '      <div class="ttb-route-twin" id="ttb-route-twin">\n'
    '        <button class="ttb-route-half" id="ttb-route-local-btn" onclick="setTTBRoute(\'local\')">LOCAL</button>\n'
    '        <button class="ttb-route-half active" id="ttb-route-live-btn" onclick="setTTBRoute(\'live\')">LIVE</button>\n'
    '      </div>\n'
)

text = TARGET.read_text()

if MARKER in text:
    print(f"Marker {MARKER} reeds aanwezig; geen wijziging.")
    sys.exit(0)

n = text.count(ANCHOR)
if n != 1:
    print(f"ERROR: anker niet exact 1x gevonden (n={n}). Bail.")
    sys.exit(1)

BACKUPS.mkdir(exist_ok=True)
ts = datetime.now().strftime("%Y%m%d-%H%M%S")
backup = BACKUPS / f"index.html.{ts}.bak"
shutil.copy(TARGET, backup)
print(f"Backup: {backup}")

new_text = text.replace(ANCHOR, INSERT + ANCHOR, 1)
TARGET.write_text(new_text)
print(f"Wrote {TARGET.name}: rocker HTML toegevoegd")
