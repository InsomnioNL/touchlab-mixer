#!/usr/bin/env python3
"""patch-master-section-ttb-monitor-v1.py

Voegt twee gegate taps toe in master-section.pd:
- Live tak:  r ttb-route-live  -> *~ -> dac~ 3 4 (vervangt directe verbinding)
- Local tak: r ttb-route-local -> *~ -> dac~ 1 2 (nieuwe tak, mengt met master)

Defaults bij Pd-start: ttb-route-live=1, ttb-route-local=0.
Marker: TTB-MONITOR-V1 (idempotent).
"""

import shutil, sys
from datetime import datetime
from pathlib import Path

V2 = Path.home() / "Documents/Pd/PDMixer/v2"
TARGET = V2 / "master-section.pd"
BACKUPS = V2 / "_backups"
MARKER = "TTB-MONITOR-V1"

text = TARGET.read_text()

if MARKER in text:
    print(f"Marker {MARKER} reeds aanwezig; geen wijziging.")
    sys.exit(0)

if "TTB-OUT-PATCH-V1" not in text:
    print("ERROR: TTB-OUT-PATCH-V1 marker ontbreekt — verkeerde voorstaat. Bail.")
    sys.exit(1)

to_remove = ["#X connect 33 0 16 0;", "#X connect 34 0 16 1;"]
for c in to_remove:
    if sum(1 for L in text.splitlines() if L.strip() == c) != 1:
        print(f"ERROR: '{c}' niet exact 1x aanwezig — bail.")
        sys.exit(1)

BACKUPS.mkdir(exist_ok=True)
ts = datetime.now().strftime("%Y%m%d-%H%M%S")
backup = BACKUPS / f"master-section.pd.{ts}.bak"
shutil.copy(TARGET, backup)
print(f"Backup: {backup}")

new_objects = [
    "#X text 390 320 TTB-MONITOR-V1;",        # 35  marker
    "#X obj 390 340 r ttb-route-live;",        # 36
    "#X obj 390 360 pack f 10;",               # 37
    "#X obj 390 380 line~;",                   # 38
    "#X obj 390 400 *~;",                      # 39  gate-live-L
    "#X obj 460 400 *~;",                      # 40  gate-live-R
    "#X obj 390 460 r ttb-route-local;",       # 41
    "#X obj 390 480 pack f 10;",               # 42
    "#X obj 390 500 line~;",                   # 43
    "#X obj 390 520 *~;",                      # 44  gate-local-L
    "#X obj 460 520 *~;",                      # 45  gate-local-R
    "#X obj 540 340 loadbang;",                # 46
    "#X msg 540 360 1;",                       # 47
    "#X obj 540 380 s ttb-route-live;",        # 48
    "#X msg 620 360 0;",                       # 49
    "#X obj 620 380 s ttb-route-local;",       # 50
]

new_connects = [
    # Live gate signal path
    "#X connect 36 0 37 0;",
    "#X connect 37 0 38 0;",
    "#X connect 38 0 39 1;",
    "#X connect 38 0 40 1;",
    # Live gate audio path
    "#X connect 33 0 39 0;",
    "#X connect 34 0 40 0;",
    "#X connect 39 0 16 0;",
    "#X connect 40 0 16 1;",
    # Local gate signal path
    "#X connect 41 0 42 0;",
    "#X connect 42 0 43 0;",
    "#X connect 43 0 44 1;",
    "#X connect 43 0 45 1;",
    # Local gate audio path
    "#X connect 33 0 44 0;",
    "#X connect 34 0 45 0;",
    "#X connect 44 0 10 0;",
    "#X connect 45 0 10 1;",
    # Loadbang defaults
    "#X connect 46 0 47 0;",
    "#X connect 47 0 48 0;",
    "#X connect 46 0 49 0;",
    "#X connect 49 0 50 0;",
]

lines = text.splitlines()
out, inserted = [], False
for L in lines:
    if L.startswith("#X connect") and not inserted:
        out.extend(new_objects)
        inserted = True
    if L.strip() in to_remove:
        continue
    out.append(L)
out.extend(new_connects)

result = "\n".join(out)
if text.endswith("\n"):
    result += "\n"
TARGET.write_text(result)
print(f"Wrote {TARGET.name}: +{len(new_objects)} objecten, "
      f"+{len(new_connects)} connects, -{len(to_remove)} oude connects")
