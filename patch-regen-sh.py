"""Verwijder de geabsorbeerde patch-scripts uit regen.sh.

patch-host-master-vol.py en patch-host-rec-path.py zijn nu overbodig
- write_main_ttb produceert hun output direct (ABSORB-HOST-PATCHES-V1).

patch-sampler-host-rec-path.py blijft - sampler-host.pd is een aparte
file (test-mode), niet geabsorbeerd.
"""
import sys

PATH = "regen.sh"
MARKER = "ABSORB-HOST-PATCHES-REGEN-V1"

with open(PATH) as f:
    content = f.read()

if MARKER in content:
    print(f"done — {PATH} al gepatcht ({MARKER})")
    sys.exit(0)

# 1. Verwijder de twee patch-aanroepen uit de check-loop
OLD_LOOP = '''for script in generate-mixer.py generate-router.py generate-slots.py \\
              patch-host-master-vol.py patch-host-rec-path.py \\
              patch-sampler-host-rec-path.py; do'''

NEW_LOOP = '''# ABSORB-HOST-PATCHES-REGEN-V1: master-vol + rec-path patches voor
# touchlab-mixer-ttb.pd zijn geabsorbeerd in write_main_ttb.
# patch-sampler-host-rec-path.py blijft (sampler-host.pd, test-mode).
for script in generate-mixer.py generate-router.py generate-slots.py \\
              patch-sampler-host-rec-path.py; do'''

if OLD_LOOP not in content:
    print("ERROR: check-loop-anker niet gevonden", file=sys.stderr)
    sys.exit(1)

content = content.replace(OLD_LOOP, NEW_LOOP, 1)

# 2. Verwijder de twee patch-aanroepen uit stap [4/4]
OLD_STEP4 = '''echo "[4/4] Post-regen patches  (master-vol + rec-path injection)"
echo "────────────────────────────────────────────────────────────────"
python3 patch-host-master-vol.py
python3 patch-host-rec-path.py
python3 patch-sampler-host-rec-path.py
echo ""'''

NEW_STEP4 = '''echo "[4/4] Post-regen patches  (sampler-host rec-path injection)"
echo "────────────────────────────────────────────────────────────────"
python3 patch-sampler-host-rec-path.py
echo ""'''

if OLD_STEP4 not in content:
    print("ERROR: step-4-anker niet gevonden", file=sys.stderr)
    sys.exit(1)

content = content.replace(OLD_STEP4, NEW_STEP4, 1)

with open(PATH, "w") as f:
    f.write(content)

print(f"✓ Patched {PATH} ({MARKER})")
print("  Twee geabsorbeerde patches uit regen.sh verwijderd")
