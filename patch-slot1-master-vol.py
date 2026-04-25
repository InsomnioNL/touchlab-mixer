#!/usr/bin/env python3
"""
Patch sampler-slot-1.pd: voegt een master-vol *~ toe in de signaal-keten.

Origineel:
  tabread4~ slot1 -> *~ (vol) -> *~ (gate) -> dac~

Nieuw:
  tabread4~ slot1 -> *~ (vol) -> *~ (gate) -> *~ (master-vol) -> dac~

Master-vol komt uit [r sampler-master-vol] -> [pack 0 20] -> [line~] -> *~ inlet 1.
Elk slot heeft z'n eigen line~ — geen gedeelde signal-bus. Iets redundant
maar volgt Pd-conventies precies en voorkomt 'r~ no matching send' issues.

Eenmalig draaien:
  python3 patch-slot1-master-vol.py

Daarna ./regen.sh om alle slots te updaten.
"""
import re
import sys
from pathlib import Path

HERE = Path(__file__).parent
SLOT1 = HERE / "sampler-slot-1.pd"

if not SLOT1.exists():
    print(f"ERROR: {SLOT1} niet gevonden")
    sys.exit(1)

content = SLOT1.read_text()

MARKER = "MASTER-VOL-PATCH-V2"
if MARKER in content:
    print("done — slot-1 al gepatcht (V2)")
    sys.exit(0)

if "sampler-master-vol-sig" in content:
    print("OUDE V1-PATCH GEDETECTEERD. Reset slot-1 eerst:")
    print("  cd ~/Documents/Pd/PDMixer/v2 && git checkout sampler-slot-1.pd")
    print("Of restore vanuit een backup, dan dit script opnieuw draaien.")
    sys.exit(1)

lines = content.split("\n")

dac_idx = None
for i, line in enumerate(lines):
    if "dac~" in line and re.match(r'^#X obj \d+ \d+ dac~;\s*$', line):
        dac_idx = i
        break

if dac_idx is None:
    print("ERROR: kan dac~ niet vinden")
    sys.exit(1)

def pd_index(line_idx):
    count = -1
    for i, l in enumerate(lines):
        if (l.startswith("#X obj ") or l.startswith("#X msg ") or
            l.startswith("#X text ") or l.startswith("#X floatatom ") or
            l.startswith("#X symbolatom ") or l.startswith("#X array ")):
            count += 1
            if i == line_idx:
                return count
    return None

n_objects = sum(
    1 for l in lines
    if l.startswith("#X obj ") or l.startswith("#X msg ") or
       l.startswith("#X text ") or l.startswith("#X floatatom ") or
       l.startswith("#X symbolatom ") or l.startswith("#X array ")
)

dac_pd_idx = pd_index(dac_idx)

new_r       = n_objects
new_pack    = n_objects + 1
new_line    = n_objects + 2
new_mul     = n_objects + 3

dac_match = re.match(r'^#X obj (\d+) (\d+) dac~;\s*$', lines[dac_idx])
dac_x = int(dac_match.group(1))
dac_y = int(dac_match.group(2))

new_obj_lines = [
    f"#X obj {dac_x + 200} {dac_y - 120} r sampler-master-vol;",
    f"#X obj {dac_x + 200} {dac_y - 90} pack 0 20;",
    f"#X obj {dac_x + 200} {dac_y - 60} line~;",
    f"#X obj {dac_x + 100} {dac_y - 30} *~;",
    f"#X text {dac_x + 200} {dac_y - 145} {MARKER};",
]

connect_to_dac_pat = re.compile(rf'^#X connect (\d+) (\d+) {dac_pd_idx} (\d+);$')
target_connect_indices = []
upstream_specs = set()
orig_dac_inlets = []
for i, l in enumerate(lines):
    m = connect_to_dac_pat.match(l)
    if m:
        target_connect_indices.append(i)
        upstream_specs.add((int(m.group(1)), int(m.group(2))))
        orig_dac_inlets.append(int(m.group(3)))

if not target_connect_indices:
    print("ERROR: kan connect naar dac~ niet vinden")
    sys.exit(1)

new_connects = [
    f"#X connect {new_r} 0 {new_pack} 0;",
    f"#X connect {new_pack} 0 {new_line} 0;",
    f"#X connect {new_line} 0 {new_mul} 1;",
]
for (src, out) in upstream_specs:
    new_connects.append(f"#X connect {src} {out} {new_mul} 0;")
for inlet in orig_dac_inlets:
    new_connects.append(f"#X connect {new_mul} 0 {dac_pd_idx} {inlet};")

sorted_targets = sorted(target_connect_indices)
to_remove = set(sorted_targets)
first_target = sorted_targets[0]
first_connect_line = next(
    (i for i, l in enumerate(lines) if l.startswith("#X connect ")),
    len(lines)
)

new_file_lines = []
inserted_objs = False
inserted_new_connects = False
for i, l in enumerate(lines):
    if i in to_remove:
        if i == first_target and not inserted_new_connects:
            new_file_lines.extend(new_connects)
            inserted_new_connects = True
        continue
    if i == first_connect_line and not inserted_objs:
        new_file_lines.extend(new_obj_lines)
        inserted_objs = True
    new_file_lines.append(l)

if not inserted_objs:
    new_file_lines.extend(new_obj_lines)

new_content = "\n".join(new_file_lines)
SLOT1.write_text(new_content)

print(f"OK slot-1 gepatcht (V2): master-vol via [r sampler-master-vol] -> [line~] -> *~")
print(f"   Pd-objecten: r={new_r}, pack={new_pack}, line~={new_line}, *~={new_mul}")
print()
print("Draai nu ./regen.sh om alle slots te regenereren.")
