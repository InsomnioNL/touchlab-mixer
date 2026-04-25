#!/usr/bin/env python3
"""
Patch touchlab-mixer-ttb.pd: voegt sampler-master-vol toe aan de top-level
FUDI-router.

Strategie:
  - Token toevoegen aan route-regel (14e token)
  - Bestaande connect 'route outlet 13 -> print' verschuiven naar outlet 14
  - Nieuwe objecten + connect HELEMAAL aan het einde van het bestand toevoegen,
    zodat geen bestaande object-indices verschuiven.
"""
import re
import sys
from pathlib import Path

HERE = Path(__file__).parent
HOST = HERE / "touchlab-mixer-ttb.pd"

if not HOST.exists():
    print(f"ERROR: {HOST} niet gevonden")
    sys.exit(1)

content = HOST.read_text()

MARKER = "MASTER-VOL-HOST-PATCH-V1"
if MARKER in content:
    print("done — touchlab-mixer-ttb.pd is al gepatcht")
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
    if "route sampler-load sampler-play" in line and "sampler-router-input" in line:
        route_line_idx = i
        break

if route_line_idx is None:
    print("ERROR: kan route-regel niet vinden")
    sys.exit(1)

if "sampler-master-vol" in lines[route_line_idx]:
    print("ERROR: 'sampler-master-vol' staat al in route-regel maar marker ontbreekt")
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

# Vind connect 'route outlet 13 -> X'
old_connect_pattern = re.compile(rf'^#X connect {route_obj} 13 (\d+) 0;\s*$')
old_connect_idx = None
print_obj = None
for i, l in enumerate(lines):
    m = old_connect_pattern.match(l)
    if m:
        old_connect_idx = i
        print_obj = int(m.group(1))
        break

if old_connect_idx is None:
    print(f"ERROR: kan '#X connect {route_obj} 13 <X> 0;' niet vinden")
    sys.exit(1)

# Verifieer dat dat 'print sampler-unknown-fudi' is
counter = -1
print_line_idx = None
for i, l in enumerate(lines):
    if is_object_line(l):
        counter += 1
        if counter == print_obj:
            print_line_idx = i
            break

if print_line_idx is None or "print sampler-unknown-fudi" not in lines[print_line_idx]:
    print(f"ERROR: object {print_obj} is geen 'print sampler-unknown-fudi'")
    sys.exit(1)

# Totaal objecten = nieuwe object-index voor 's sampler-master-vol'
n_objects = sum(1 for l in lines if is_object_line(l))
new_s_obj = n_objects             # bv. 57
# (text-object voor marker krijgt index n_objects+1, niet relevant voor connects)

# --- Wijzigingen ---

# 1. Token aan route-regel
new_route_line = re.sub(
    r'sampler-router-input;',
    'sampler-router-input sampler-master-vol;',
    lines[route_line_idx],
)
if new_route_line == lines[route_line_idx]:
    print("ERROR: kon 'sampler-router-input;' niet matchen")
    sys.exit(1)
lines[route_line_idx] = new_route_line

# 2. Connect outlet 13 -> print verschuiven naar outlet 14
lines[old_connect_idx] = f"#X connect {route_obj} 14 {print_obj} 0;"

# 3. Nieuwe objecten + connect HELEMAAL achteraan toevoegen
# (verwijder eerst evt. trailing lege regels, append, eindig met newline)
while lines and lines[-1].strip() == "":
    lines.pop()

lines.append(f"#X obj 900 230 s sampler-master-vol;")
lines.append(f"#X text 1100 230 {MARKER};")
lines.append(f"#X connect {route_obj} 13 {new_s_obj} 0;")
lines.append("")  # trailing newline

# Schrijven
new_content = "\n".join(lines)
backup = HOST.with_suffix(".pd.bak-host-mvpatch-v2")
backup.write_text(content)
HOST.write_text(new_content)

print(f"✓ Patched {HOST.name}")
print(f"  Backup:  {backup.name}")
print(f"  Route obj:                       {route_obj}")
print(f"  Print obj:                       {print_obj} (verschoven naar outlet 14)")
print(f"  Nieuwe s sampler-master-vol:     object {new_s_obj}")
print(f"  Wijzigingen achteraan toegevoegd, geen bestaande indices verschoven.")
