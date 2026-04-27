#!/usr/bin/env python3
"""
Patch sampler-host.pd: voegt sampler-rec-path toe aan de host FUDI-router.

Strategie:
  - Token toevoegen aan route-regel (15e token, na sampler-master-vol)
  - Bestaande connect 'route outlet 14 -> X' verschuiven naar outlet 15
  - Nieuwe objecten + connect HELEMAAL aan het einde van het bestand toevoegen,
    zodat geen bestaande object-indices verschuiven.
"""
import re
import sys
from pathlib import Path

HERE = Path(__file__).parent
HOST = HERE / "sampler-host.pd"

if not HOST.exists():
    print(f"ERROR: {HOST} niet gevonden")
    sys.exit(1)

content = HOST.read_text()

MARKER = "REC-PATH-SAMPLER-HOST-PATCH-V1"
if MARKER in content:
    print("done — sampler-host.pd is al gepatcht")
    sys.exit(0)

lines = content.split("\n")

OBJECT_PREFIXES = (
    "#X obj ", "#X msg ", "#X text ", "#X floatatom ",
    "#X symbolatom ", "#X array ",
)

def is_object_line(l):
    return any(l.startswith(p) for p in OBJECT_PREFIXES)

# Vind route-regel
route_line_idx = None
for i, line in enumerate(lines):
    if "route sampler-load sampler-play" in line and "sampler-master-vol" in line:
        route_line_idx = i
        break

if route_line_idx is None:
    print("ERROR: kan route-regel niet vinden (mist 'route sampler-load' of 'sampler-master-vol')")
    sys.exit(1)

if "sampler-rec-path" in lines[route_line_idx]:
    print("ERROR: 'sampler-rec-path' staat al in route-regel maar marker ontbreekt")
    sys.exit(1)

# Object-index van de route bepalen
def pd_index_of_line(line_idx):
    count = -1
    for i, l in enumerate(lines):
        if is_object_line(l):
            count += 1
            if i == line_idx:
                return count
    return None

route_obj = pd_index_of_line(route_line_idx)
if route_obj is None:
    print("ERROR: kan object-index van route niet bepalen")
    sys.exit(1)

# Vind connect 'route outlet 14 -> X' (de unmatched-handler)
old_connect_pattern = re.compile(rf'^#X connect {route_obj} 14 (\d+) 0;\s*$')
old_connect_idx = None
unmatched_obj = None
for i, l in enumerate(lines):
    m = old_connect_pattern.match(l)
    if m:
        old_connect_idx = i
        unmatched_obj = int(m.group(1))
        break

if old_connect_idx is None:
    print(f"ERROR: kan '#X connect {route_obj} 14 <X> 0;' niet vinden")
    sys.exit(1)

# Totaal objecten = nieuwe object-index voor 's sampler-rec-path'
n_objects = sum(1 for l in lines if is_object_line(l))
new_s_obj = n_objects

# --- Wijzigingen ---

# 1. Token aan route-regel
new_route_line = re.sub(
    r'sampler-master-vol;',
    'sampler-master-vol sampler-rec-path;',
    lines[route_line_idx],
)
if new_route_line == lines[route_line_idx]:
    print("ERROR: kon 'sampler-master-vol;' niet matchen op einde route-regel")
    sys.exit(1)
lines[route_line_idx] = new_route_line

# 2. Connect outlet 14 -> X verschuiven naar outlet 15
lines[old_connect_idx] = f"#X connect {route_obj} 15 {unmatched_obj} 0;"

# 3. Nieuwe objecten + connect HELEMAAL achteraan toevoegen
while lines and lines[-1].strip() == "":
    lines.pop()

lines.append("#X obj 900 260 s sampler-rec-path;")
lines.append(f"#X text 1100 260 {MARKER};")
lines.append(f"#X connect {route_obj} 14 {new_s_obj} 0;")
lines.append("")  # trailing newline

# Schrijven (script maakt eigen .bak — analoog aan master-vol script)
new_content = "\n".join(lines)
backup = HOST.with_suffix(".pd.bak-host-recpathpatch-v1")
backup.write_text(content)
HOST.write_text(new_content)

print(f"✓ Patched {HOST.name}")
print(f"  Backup:        {backup.name}")
print(f"  Route obj:     {route_obj}")
print(f"  Unmatched obj: {unmatched_obj} (outlet 14 → 15)")
print(f"  Nieuwe s sampler-rec-path: object {new_s_obj}")
print(f"  Geen bestaande indices verschoven.")
