"""Voegt de ontbrekende {pmr} → {smr} connect toe aan write_vu_sender.

Idempotent via marker VUSENDER-STEREO-FIX-V1.
"""
import sys

PATH = "generate-mixer.py"
MARKER = "VUSENDER-STEREO-FIX-V1"

with open(PATH) as f:
    content = f.read()

if MARKER in content:
    print(f"done — {PATH} al gepatcht ({MARKER})")
    sys.exit(0)

OLD = '''    rmr = add("#X obj 400 120 r masterVuR;")
    pmr = add("#X obj 400 140 list prepend vu masterR;")
    smr = add("#X obj 400 160 s vu-out;")
    lines.append(f"#X connect {rmr} 0 {pmr} 0;")'''

NEW = '''    rmr = add("#X obj 400 120 r masterVuR;")
    pmr = add("#X obj 400 140 list prepend vu masterR;")
    smr = add("#X obj 400 160 s vu-out;")
    lines.append(f"#X connect {rmr} 0 {pmr} 0;")
    lines.append(f"#X connect {pmr} 0 {smr} 0;")  # VUSENDER-STEREO-FIX-V1'''

if OLD not in content:
    print("ERROR: anker niet gevonden", file=sys.stderr)
    sys.exit(1)

content = content.replace(OLD, NEW, 1)

with open(PATH, "w") as f:
    f.write(content)

print(f"✓ Patched {PATH}")
