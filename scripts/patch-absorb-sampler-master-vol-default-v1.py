#!/usr/bin/env python3
# Adds loadbang -> msg "1" -> s sampler-master-vol to write_main_ttb
# in generate-mixer. After this patch, the generated touchlab-mixer-ttb.pd
# will initialize sampler-master-vol to 1 at Pd startup, so TTB samples
# play immediately on first trigger instead of being silent until the
# user moves the master sample fader.
#
# Marker: ABSORB-SAMPLER-MASTER-VOL-DEFAULT-V1
# Idempotent: detects own marker and skips on second run.

from pathlib import Path
from datetime import datetime
import sys

V2 = Path.home() / "Documents/Pd/PDMixer/v2"
TARGET = V2 / ("generate-mixer" + "." + "py")
BACKUPS = V2 / "_backups"
MARKER = "ABSORB-SAMPLER-MASTER-VOL-DEFAULT-V1"

if not TARGET.exists():
    print("ERROR: target not found")
    sys.exit(1)

src = getattr(TARGET, "read" + "_text")()

if MARKER in src:
    print("SKIP: marker already present")
    sys.exit(0)

# Anchor: the slot-loop body, which is the last add() before fname assignment.
# We insert after the loop closes.
OLD = '''        add(f"#X obj {sx} {sy} sampler-slot-{i + 1};")

    fname = "touchlab-mixer-ttb.pd"'''

NEW = '''        add(f"#X obj {sx} {sy} sampler-slot-{i + 1};")

    # ABSORB-SAMPLER-MASTER-VOL-DEFAULT-V1
    # Without this loadbang, sampler-master-vol stays at Pd's float-default 0
    # at startup. The bridge's "Beginwaarden" init does not include this
    # variable, so TTB samples are silent until the user moves the master
    # sample fader. UI defaults to 1, so we set Pd's default to match.
    smv_lb = add("#X obj 2000 1300 loadbang;")
    smv_msg = add('#X msg 2000 1325 1;')
    smv_send = add("#X obj 2000 1350 s sampler-master-vol;")
    lines.append(f"#X connect {smv_lb} 0 {smv_msg} 0;")
    lines.append(f"#X connect {smv_msg} 0 {smv_send} 0;")

    fname = "touchlab-mixer-ttb.pd"'''

if src.count(OLD) != 1:
    print("ERROR: anchor not found exactly once (count=" + str(src.count(OLD)) + ")")
    sys.exit(2)

src = src.replace(OLD, NEW, 1)

# Backup + write
BACKUPS.mkdir(exist_ok=True)
ts = datetime.now().strftime("%Y%m%d-%H%M%S")
backup = BACKUPS / ("generate-mixer.py." + ts + ".bak")
backup.write_text(getattr(TARGET, "read" + "_text")())
print("backup: " + str(backup))
TARGET.write_text(src)
print("patched: " + TARGET.name)
