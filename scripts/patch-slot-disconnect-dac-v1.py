#!/usr/bin/env python3
"""patch-slot-disconnect-dac-v1.py

Verwijdert in sampler-slot-1.pd de twee connect-regels die de
master-vol *~ (object 212) verbinden met dac~ (object 97):

    #X connect 212 0 97 0;
    #X connect 212 0 97 1;

Het dac~-object zelf blijft staan als orphan (latere cleanup-pass).
Throw~ ttb-bus-L/R blijven onveranderd (TTB-out-bus naar collega's).

Marker: TTB-MONITOR-SLOT-V1 (idempotent, als comment-text in file).

Na slot-1-patch: roept generate-slots.py aan om slots 2-8 te regenereren.
"""

import shutil, subprocess, sys
from datetime import datetime
from pathlib import Path

V2 = Path.home() / "Documents/Pd/PDMixer/v2"
TARGET = V2 / "sampler-slot-1.pd"
BACKUPS = V2 / "_backups"
MARKER = "TTB-MONITOR-SLOT-V1"
MARKER_LINE = f"#X text 700 785 {MARKER};"

CONNECTS_TO_REMOVE = [
    "#X connect 212 0 97 0;",
    "#X connect 212 0 97 1;",
]

text = TARGET.read_text()

if MARKER in text:
    print(f"Marker {MARKER} reeds aanwezig; geen wijziging.")
    sys.exit(0)

# Verifieer voorstaat: TTB-OUT-SLOT-1-V1 marker moet aanwezig zijn
if "TTB-OUT-SLOT-1-V1" not in text:
    print("ERROR: TTB-OUT-SLOT-1-V1 marker ontbreekt — verkeerde voorstaat. Bail.")
    sys.exit(1)

# Verifieer count==1 voor elke te verwijderen connect
lines = text.splitlines()
for c in CONNECTS_TO_REMOVE:
    n = sum(1 for L in lines if L.strip() == c)
    if n != 1:
        print(f"ERROR: '{c}' niet exact 1x aanwezig (gevonden: {n}) — bail.")
        sys.exit(1)

# Backup
BACKUPS.mkdir(exist_ok=True)
ts = datetime.now().strftime("%Y%m%d-%H%M%S")
backup = BACKUPS / f"sampler-slot-1.pd.{ts}.bak"
shutil.copy(TARGET, backup)
print(f"Backup: {backup}")

# Schrijf nieuwe file: connects weg, marker toegevoegd vóór de eerste #X connect
out = []
marker_inserted = False
for L in lines:
    if L.startswith("#X connect") and not marker_inserted:
        out.append(MARKER_LINE)
        marker_inserted = True
    if L.strip() in CONNECTS_TO_REMOVE:
        continue
    out.append(L)

result = "\n".join(out)
if text.endswith("\n"):
    result += "\n"
TARGET.write_text(result)
print(f"Wrote {TARGET.name}: -{len(CONNECTS_TO_REMOVE)} connects, +1 marker-text")

# Run generate-slots.py
print("\nRunning generate-slots.py to regenerate slots 2-8...")
result = subprocess.run(
    ["python3", str(V2 / "generate-slots.py")],
    capture_output=True, text=True
)
print(result.stdout)
if result.returncode != 0:
    print("STDERR:", result.stderr)
    sys.exit(result.returncode)
