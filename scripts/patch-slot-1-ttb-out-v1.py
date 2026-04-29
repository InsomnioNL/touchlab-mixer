#!/usr/bin/env python3
"""
patch-slot-1-ttb-out-v1.py — TTB-OUT-SLOT-1-V1

Wat dit doet (idempotent, additief):
- Voegt #X text TTB-OUT-SLOT-1-V1 toe (idempotentie-marker)
- Voegt throw~ ttb-bus-L en throw~ ttb-bus-R toe
- Tap-punt: object 212 (de *~ post sampler-master-vol) outlet 0
- Bestaande connect 212 0 97 0/1 (naar dac~) blijft onaangeroerd

Object-indices na patch:
  222 = #X text TTB-OUT-SLOT-1-V1
  223 = throw~ ttb-bus-L
  224 = throw~ ttb-bus-R
"""

import sys
import shutil
from pathlib import Path
from datetime import datetime

PD_FILE = Path.home() / "Documents/Pd/PDMixer/v2/sampler-slot-1.pd"
BACKUP_DIR = Path.home() / "Documents/Pd/PDMixer/v2/_backups"
MARKER = "TTB-OUT-SLOT-1-V1"

NEW_OBJECTS = [
    f"#X text 900 750 {MARKER};\n",
    "#X obj 900 770 throw~ ttb-bus-L;\n",
    "#X obj 900 790 throw~ ttb-bus-R;\n",
]

NEW_CONNECTIONS = [
    "#X connect 212 0 223 0;\n",
    "#X connect 212 0 224 0;\n",
]

EXPECTED_TAP_REFERENCE = "#X connect 212 0 97 0;\n"


def fail(msg):
    print(f"X  {msg}", file=sys.stderr)
    sys.exit(1)


def count_objects(content):
    """Tel objecten zoals Pd dat doet: obj/msg/atom/listbox/text + #N canvas
    (subpatch), skip eerste #N canvas (header)."""
    found_first_canvas = False
    idx = 0
    for line in content.splitlines():
        if line.startswith("#N canvas") and not found_first_canvas:
            found_first_canvas = True
            continue
        if line.startswith(("#X obj", "#X msg", "#X floatatom",
                            "#X symbolatom", "#X listbox", "#X text",
                            "#N canvas")):
            idx += 1
    return idx


def main():
    if not PD_FILE.exists():
        fail(f"Niet gevonden: {PD_FILE}")

    content = PD_FILE.read_text()

    # Idempotentie-guard
    if MARKER in content:
        print(f"=  Marker '{MARKER}' al aanwezig in {PD_FILE.name} - geen actie")
        return

    # Sanity: tap-punt-referentie moet bestaan (anders is de file niet
    # de verwachte versie en zijn onze indices fout)
    if EXPECTED_TAP_REFERENCE not in content:
        fail(f"Verwachte tap-referentie {EXPECTED_TAP_REFERENCE.strip()!r} niet gevonden - file-staat onverwacht")

    # Sanity: object-aantal moet 222 zijn (voor patch), zodat de nieuwe
    # objecten op index 222/223/224 landen
    obj_count = count_objects(content)
    if obj_count != 222:
        fail(f"Verwacht 222 objecten in {PD_FILE.name}, gevonden {obj_count}")

    lines = content.splitlines(keepends=True)

    # Insertion point voor objecten: vóór eerste #X connect
    insert_idx = None
    for i, line in enumerate(lines):
        if line.startswith("#X connect "):
            insert_idx = i
            break
    if insert_idx is None:
        fail("Geen #X connect regels gevonden")

    # Backup
    BACKUP_DIR.mkdir(exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    backup = BACKUP_DIR / f"{PD_FILE.name}.{timestamp}.bak"
    shutil.copy2(PD_FILE, backup)
    print(f"~  Backup: {backup}")

    # Bouw final
    head = lines[:insert_idx]
    tail = lines[insert_idx:]
    if head and not head[-1].endswith("\n"):
        head[-1] = head[-1] + "\n"

    final = head + NEW_OBJECTS + tail + NEW_CONNECTIONS

    PD_FILE.write_text("".join(final))

    # Verify post-patch obj count = 225
    new_count = count_objects(PD_FILE.read_text())
    if new_count != 225:
        print(f"!  Waarschuwing: na patch verwacht 225 objecten, gevonden {new_count}", file=sys.stderr)

    print(f"V  {PD_FILE.name} gepatched met {MARKER}")
    print(f"   - 3 objecten toegevoegd (text marker @ 222, throw~ L @ 223, throw~ R @ 224)")
    print(f"   - 2 connections toegevoegd (212->223, 212->224)")
    print(f"   - object-aantal: {obj_count} -> {new_count}")


if __name__ == "__main__":
    main()
