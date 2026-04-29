#!/usr/bin/env python3
"""
patch-master-section-ttb-out-v1.py — TTB-OUT-PATCH-V1

Wat dit doet (idempotent):
- Verwijdert hpVol -> dac~ 3 4 connections (obj 14 en 15 -> 16)
- Voegt catch~ ttb-bus-L/R toe, direct gewired naar dac~ 3 4 (obj 16)
- Marker als idempotentie-guard

hpVol-objecten (11-15, 20-21) en s hpVol-loadbang-init blijven als orphan
dead code staan. Cleanup is een latere commit, niet nu.

Object-indices na patch: text=32, catch~ ttb-bus-L=33, catch~ ttb-bus-R=34.
"""

import sys
import shutil
from pathlib import Path
from datetime import datetime

PD_FILE = Path.home() / "Documents/Pd/PDMixer/v2/master-section.pd"
BACKUP_DIR = Path.home() / "Documents/Pd/PDMixer/v2/_backups"
MARKER = "TTB-OUT-PATCH-V1"

REMOVE_LINES = [
    "#X connect 14 0 16 0;\n",
    "#X connect 15 0 16 1;\n",
]

NEW_OBJECTS = [
    f"#X text 350 240 {MARKER};\n",
    "#X obj 350 260 catch~ ttb-bus-L;\n",
    "#X obj 350 285 catch~ ttb-bus-R;\n",
]

NEW_CONNECTIONS = [
    "#X connect 33 0 16 0;\n",
    "#X connect 34 0 16 1;\n",
]


def fail(msg):
    print(f"X  {msg}", file=sys.stderr)
    sys.exit(1)


def main():
    if not PD_FILE.exists():
        fail(f"Niet gevonden: {PD_FILE}")

    content = PD_FILE.read_text()

    # Idempotentie-guard
    if MARKER in content:
        print(f"=  Marker '{MARKER}' al aanwezig in {PD_FILE.name} - geen actie")
        return

    lines = content.splitlines(keepends=True)

    # count == 1 check voor elke te verwijderen regel
    for target in REMOVE_LINES:
        n = lines.count(target)
        if n != 1:
            fail(f"Verwacht exact 1 voorkomen van {target.strip()!r}, gevonden {n}")

    # Insertion point: voor eerste #X connect regel
    insert_idx = None
    for i, line in enumerate(lines):
        if line.startswith("#X connect "):
            insert_idx = i
            break
    if insert_idx is None:
        fail("Geen #X connect regels gevonden - file-structuur klopt niet")

    # Backup
    BACKUP_DIR.mkdir(exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    backup = BACKUP_DIR / f"{PD_FILE.name}.{timestamp}.bak"
    shutil.copy2(PD_FILE, backup)
    print(f"~  Backup: {backup}")

    # Filter REMOVE_LINES eruit
    filtered = [ln for ln in lines if ln not in REMOVE_LINES]

    # Hervind insertion point in gefilterde lijst
    new_insert_idx = None
    for i, line in enumerate(filtered):
        if line.startswith("#X connect "):
            new_insert_idx = i
            break
    if new_insert_idx is None:
        fail("Insertion point verloren na filtering")

    # Bouw final: [pre-connect] + NEW_OBJECTS + [connect block] + NEW_CONNECTIONS
    head_plus_objs = filtered[:new_insert_idx] + NEW_OBJECTS + filtered[new_insert_idx:]

    # Zorg dat laatste regel \n eindigt voor we appenden
    if head_plus_objs and not head_plus_objs[-1].endswith("\n"):
        head_plus_objs[-1] = head_plus_objs[-1] + "\n"

    final = head_plus_objs + NEW_CONNECTIONS

    PD_FILE.write_text("".join(final))
    print(f"V  {PD_FILE.name} gepatched met {MARKER}")
    print(f"   - 2 connections verwijderd (14->16, 15->16)")
    print(f"   - 3 objecten toegevoegd (text marker, catch~ L, catch~ R)")
    print(f"   - 2 connections toegevoegd (33->16, 34->16)")


if __name__ == "__main__":
    main()
