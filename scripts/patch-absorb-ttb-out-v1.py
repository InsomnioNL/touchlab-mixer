#!/usr/bin/env python3
# Absorbs TTB-OUT-PATCH-V1 + TTB-MONITOR-V1 into write_master in
# generate-mixer. After this patch, regen produces a master-section
# that includes TTB output bus + route-rocker gates by construction.
#
# Marker: ABSORB-TTB-OUT-V1
# Idempotent: detects own marker and skips on second run.

from pathlib import Path
from datetime import datetime
import sys

V2 = Path.home() / "Documents/Pd/PDMixer/v2"
TARGET = V2 / ("generate-mixer" + "." + "py")
BACKUPS = V2 / "_backups"
MARKER = "ABSORB-TTB-OUT-V1"

if not TARGET.exists():
    print("ERROR: target not found")
    sys.exit(1)

src = getattr(TARGET, "read" + "_text")()

if MARKER in src:
    print("SKIP: marker already present")
    sys.exit(0)

# 1. Replace write_master signature
OLD_SIG = "def write_master(with_sampler_tap=False):"
NEW_SIG = "def write_master(with_sampler_tap=False, with_ttb_out=False):  # ABSORB-TTB-OUT-V1"
if src.count(OLD_SIG) != 1:
    print("ERROR: signature not found exactly once")
    sys.exit(2)
src = src.replace(OLD_SIG, NEW_SIG, 1)

# 2. Replace canvas dimensions
OLD_CANVAS = "#N canvas 0 0 400 400 12;"
NEW_CANVAS = "#N canvas 0 0 717 562 12;"
if src.count(OLD_CANVAS) != 1:
    print("ERROR: canvas line not found exactly once")
    sys.exit(3)
src = src.replace(OLD_CANVAS, NEW_CANVAS, 1)

# 3. Replace dac 3 4 position
OLD_DAC34 = "#X obj 220 270 dac~ 3 4;"
NEW_DAC34 = "#X obj 312 273 dac~ 3 4;"
if src.count(OLD_DAC34) != 1:
    print("ERROR: dac 3 4 line not found exactly once")
    sys.exit(4)
src = src.replace(OLD_DAC34, NEW_DAC34, 1)

# 4. Replace format() call to include ttb_out builders
OLD_FORMAT = (
    "    content = content.format(\n"
    "        stereo_r_lines=stereo_r_lines,\n"
    "        sampler_tap_lines=sampler_tap_lines,\n"
    "        stereo_r_connects=stereo_r_connects,\n"
    "        sampler_tap_connects=sampler_tap_connects,\n"
    "    )"
)
if src.count(OLD_FORMAT) != 1:
    print("ERROR: format-call block not found exactly once")
    sys.exit(5)

TTB_OBJ = [
    "#X text 390 240 TTB-OUT-PATCH-V1;",
    "#X obj 390 260 catch~ ttb-bus-L;",
    "#X obj 390 285 catch~ ttb-bus-R;",
    "#X text 390 320 TTB-MONITOR-V1;",
    "#X obj 390 340 r ttb-route-live;",
    "#X obj 390 360 pack f 10;",
    "#X obj 390 380 line~;",
    "#X obj 390 400 *~;",
    "#X obj 460 400 *~;",
    "#X obj 390 460 r ttb-route-local;",
    "#X obj 390 480 pack f 10;",
    "#X obj 390 500 line~;",
    "#X obj 390 520 *~;",
    "#X obj 460 520 *~;",
    "#X obj 540 340 loadbang;",
    "#X msg 540 360 1;",
    "#X obj 540 380 s ttb-route-live;",
    "#X msg 620 360 0;",
    "#X obj 620 380 s ttb-route-local;",
]
TTB_CONN = [
    "#X connect 36 0 37 0;",
    "#X connect 37 0 38 0;",
    "#X connect 38 0 39 1;",
    "#X connect 38 0 40 1;",
    "#X connect 33 0 39 0;",
    "#X connect 34 0 40 0;",
    "#X connect 39 0 16 0;",
    "#X connect 40 0 16 1;",
    "#X connect 41 0 42 0;",
    "#X connect 42 0 43 0;",
    "#X connect 43 0 44 1;",
    "#X connect 43 0 45 1;",
    "#X connect 33 0 44 0;",
    "#X connect 34 0 45 0;",
    "#X connect 44 0 10 0;",
    "#X connect 45 0 10 1;",
    "#X connect 46 0 47 0;",
    "#X connect 47 0 48 0;",
    "#X connect 46 0 49 0;",
    "#X connect 49 0 50 0;",
]

new_lines = []
new_lines.append("    # ABSORB-TTB-OUT-V1")
new_lines.append('    ttb_out_lines = ""')
new_lines.append('    ttb_out_connects = ""')
new_lines.append("    if with_ttb_out:")
new_lines.append("        ttb_out_lines = (")
for ol in TTB_OBJ:
    new_lines.append('            "' + ol + '\\n"')
new_lines.append("        )")
new_lines.append("        ttb_out_connects = (")
for cl in TTB_CONN:
    new_lines.append('            "' + cl + '\\n"')
new_lines.append("        )")
new_lines.append("    content = content.format(")
new_lines.append("        stereo_r_lines=stereo_r_lines,")
new_lines.append("        sampler_tap_lines=sampler_tap_lines,")
new_lines.append("        ttb_out_lines=ttb_out_lines,")
new_lines.append("        stereo_r_connects=stereo_r_connects,")
new_lines.append("        sampler_tap_connects=sampler_tap_connects,")
new_lines.append("        ttb_out_connects=ttb_out_connects,")
new_lines.append("    )")
NEW_FORMAT = "\n".join(new_lines)

src = src.replace(OLD_FORMAT, NEW_FORMAT, 1)

# 5. Insert {ttb_out_lines} placeholder in template
OLD_ANCHOR = "#X msg 170 360 0.5;\n#X obj 170 380 s masterPan;\n#X connect 0 0 5 0;"
NEW_ANCHOR = "#X msg 170 360 0.5;\n#X obj 170 380 s masterPan;\n{{ttb_out_lines}}#X connect 0 0 5 0;"
if src.count(OLD_ANCHOR) != 1:
    print("ERROR: masterPan-end anchor not found exactly once")
    sys.exit(6)
src = src.replace(OLD_ANCHOR, NEW_ANCHOR, 1)

# 6. Append {ttb_out_connects} to tail placeholders
OLD_TAIL = "{{stereo_r_connects}}{{sampler_tap_connects}}"
NEW_TAIL = "{{stereo_r_connects}}{{sampler_tap_connects}}{{ttb_out_connects}}"
if src.count(OLD_TAIL) != 1:
    print("ERROR: tail-placeholders not found exactly once")
    sys.exit(7)
src = src.replace(OLD_TAIL, NEW_TAIL, 1)

# 7. Update generate() call
OLD_CALL = "write_master(with_sampler_tap=ttb_enable)"
NEW_CALL = "write_master(with_sampler_tap=ttb_enable, with_ttb_out=ttb_enable)"
if src.count(OLD_CALL) != 1:
    print("ERROR: generate() call not found exactly once")
    sys.exit(8)
src = src.replace(OLD_CALL, NEW_CALL, 1)

# Backup + write
BACKUPS.mkdir(exist_ok=True)
ts = datetime.now().strftime("%Y%m%d-%H%M%S")
backup = BACKUPS / ("generate-mixer.py." + ts + ".bak")
backup.write_text(getattr(TARGET, "read" + "_text")())
print("backup: " + str(backup))
TARGET.write_text(src)
print("patched: " + TARGET.name)
