"""vu-sender.pd: vervang mono r masterVu door twee ketens
(masterVuL en masterVuR), zodat frontend stereo-VU krijgt.

Idempotent via marker VUSENDER-STEREO-V1.
"""
import sys

PATH = "generate-mixer.py"
MARKER = "VUSENDER-STEREO-V1"

with open(PATH) as f:
    content = f.read()

if MARKER in content:
    print(f"done — {PATH} al gepatcht ({MARKER})")
    sys.exit(0)

OLD = '''    rm = add("#X obj 300 120 r masterVu;")
    pm = add("#X obj 300 140 list prepend vu master;")
    sm = add("#X obj 300 160 s vu-out;")
    lines.append(f"#X connect {rm} 0 {pm} 0;")'''

NEW = '''    # === VUSENDER-STEREO-V1 ===
    # Twee ketens voor stereo-VU: masterL en masterR. Frontend mapt
    # die op sg-ml en sg-mr.
    rml = add("#X obj 300 120 r masterVuL;")
    pml = add("#X obj 300 140 list prepend vu masterL;")
    sml = add("#X obj 300 160 s vu-out;")
    lines.append(f"#X connect {rml} 0 {pml} 0;")
    lines.append(f"#X connect {pml} 0 {sml} 0;")
    rmr = add("#X obj 400 120 r masterVuR;")
    pmr = add("#X obj 400 140 list prepend vu masterR;")
    smr = add("#X obj 400 160 s vu-out;")
    lines.append(f"#X connect {rmr} 0 {pmr} 0;")'''

if OLD not in content:
    print("ERROR: anker niet gevonden", file=sys.stderr)
    sys.exit(1)

content = content.replace(OLD, NEW, 1)

# De oude code had een laatste connect-regel onder de [4 regels die we vervangen]:
#   lines.append(f"#X connect {pm} 0 {sm} 0;")
# Die hoort niet meer in de oude vorm. Verwijder de orphan.
ORPHAN = '    lines.append(f"#X connect {pm} 0 {sm} 0;")\n'
if ORPHAN in content:
    content = content.replace(ORPHAN, '', 1)
    print("- orphan connect-regel verwijderd")

with open(PATH, "w") as f:
    f.write(content)

print(f"✓ Patched {PATH} ({MARKER})")
