#!/usr/bin/env python3
"""patch-ui-ttb-route-rocker-css-js-v1.py

Fase 3c: CSS + JS voor de TTB-route-rocker.

Drie inserts in index.html:
  1. CSS voor .ttb-route-twin / .ttb-route-half / .ttb-popup.route-local
     (kopie van mode-twin styling + rode rand-pulse als route=local)
  2. JS-functie setTTBRoute(route) na setTTBMode
  3. DOMContentLoaded init die default route op live zet

Marker: TTB-ROUTE-RC-V1 (idempotent).
Drie ankers, drie inserts, een script.
"""

import shutil, sys
from datetime import datetime
from pathlib import Path

V2 = Path.home() / "Documents/Pd/PDMixer/v2"
TARGET = V2 / "index.html"
BACKUPS = V2 / "_backups"
MARKER = "TTB-ROUTE-RC-V1"

# Anker 1: einde van .ttb-mode-half.active block
ANCHOR_CSS = (
    ".ttb-mode-half.active{\n"
    "  background:rgba(240,185,58,0.3);\n"
    "  color:rgba(255,255,255,0.95);\n"
    "  cursor:default;\n"
    "}"
)

INSERT_CSS = """
/* === TTB-ROUTE-RC-V1: rocker styling === */
.ttb-route-twin{
  display:flex;
  border-radius:4px;overflow:hidden;
  border:1px solid rgba(176,106,245,0.3);
  flex-shrink:0;
}
.ttb-route-half{
  background:rgba(176,106,245,0.05);
  color:rgba(176,106,245,0.5);
  font-size:10px;font-family:var(--mono);letter-spacing:.1em;
  cursor:pointer;padding:3px 9px;line-height:1;
  border:0;
  transition:all .15s;
}
.ttb-route-half:not(.active):hover{
  background:rgba(176,106,245,0.15);
  color:rgba(176,106,245,0.9);
}
.ttb-route-half.active{
  background:rgba(240,185,58,0.3);
  color:rgba(255,255,255,0.95);
  cursor:default;
}
.ttb-popup.route-local{
  border:2px solid var(--red);
  box-shadow:0 0 12px rgba(224,82,82,0.4);
  animation:ttb-route-local-pulse 3.5s ease-in-out infinite;
}
@keyframes ttb-route-local-pulse{
  0%,100%{box-shadow:0 0 8px rgba(224,82,82,0.25);}
  50%{box-shadow:0 0 18px rgba(224,82,82,0.55);}
}
"""

# Anker 2: einde van setTTBMode-functie + de toggleTTBMode wrapper erna
ANCHOR_JS = (
    "// Backwards-compat \u2014 sommige flows roepen toggleTTBMode aan\n"
    "function toggleTTBMode(){\n"
    "  setTTBMode(ttbMode === 'perf' ? 'edit' : 'perf');\n"
    "}"
)

INSERT_JS = """

// === TTB-ROUTE-RC-V1: rocker JS ===
var ttbRoute = 'live'; // 'local' | 'live'
function setTTBRoute(newRoute){
  if (newRoute !== 'local' && newRoute !== 'live') return;
  if (newRoute === ttbRoute) return;
  ttbRoute = newRoute;
  var pop = document.getElementById('ttb-popup');
  if (pop) pop.classList.toggle('route-local', ttbRoute === 'local');
  var btnLocal = document.getElementById('ttb-route-local-btn');
  var btnLive  = document.getElementById('ttb-route-live-btn');
  if (btnLocal) btnLocal.classList.toggle('active', ttbRoute === 'local');
  if (btnLive)  btnLive.classList.toggle('active',  ttbRoute === 'live');
  send({type:'ttbRoute', value:ttbRoute});
}"""

# Anker 3: bestaande DOMContentLoaded met de TTB-fader-listener als bovenste haakje
ANCHOR_INIT = (
    "// Fader-listener (master volume)\n"
    "document.addEventListener('DOMContentLoaded', function(){"
)

INSERT_INIT = (
    "// === TTB-ROUTE-RC-V1: init ===\n"
    "document.addEventListener('DOMContentLoaded', function(){\n"
    "  // Stuur default route 'live' naar bridge bij UI-load.\n"
    "  // Bridge stuurt dat door als ttb-route-live=1, ttb-route-local=0.\n"
    "  // Pd's loadbang zet dezelfde state al, dus geen audio-effect.\n"
    "  var trySend = function(){\n"
    "    if (ws && ws.readyState === 1) {\n"
    "      send({type:'ttbRoute', value:ttbRoute});\n"
    "    } else {\n"
    "      setTimeout(trySend, 200);\n"
    "    }\n"
    "  };\n"
    "  setTimeout(trySend, 500);\n"
    "});\n\n"
)

text = TARGET.read_text()

if MARKER in text:
    print(f"Marker {MARKER} reeds aanwezig; geen wijziging.")
    sys.exit(0)

for name, anchor in [("CSS", ANCHOR_CSS), ("JS", ANCHOR_JS), ("INIT", ANCHOR_INIT)]:
    n = text.count(anchor)
    if n != 1:
        print(f"ERROR: anker {name} niet exact 1x gevonden (n={n}). Bail.")
        sys.exit(1)

BACKUPS.mkdir(exist_ok=True)
ts = datetime.now().strftime("%Y%m%d-%H%M%S")
backup = BACKUPS / f"index.html.{ts}.bak"
shutil.copy(TARGET, backup)
print(f"Backup: {backup}")

new_text = text.replace(ANCHOR_CSS, ANCHOR_CSS + INSERT_CSS, 1)
new_text = new_text.replace(ANCHOR_JS, ANCHOR_JS + INSERT_JS, 1)
new_text = new_text.replace(ANCHOR_INIT, INSERT_INIT + ANCHOR_INIT, 1)

TARGET.write_text(new_text)
print(f"Wrote {TARGET.name}: CSS + JS + init toegevoegd")
