"""Absorbeert master-vol + rec-path post-regen patches in write_main_ttb.

Voegt sampler-master-vol en sampler-rec-path toe aan de route-string
en aan send_specs, zodat de generator ze direct produceert. De
post-regen patch-scripts blijven idempotent (zien hun marker en doen
niets meer).

Idempotent via marker ABSORB-HOST-PATCHES-V1.
"""
import sys

PATH = "generate-mixer.py"
MARKER = "ABSORB-HOST-PATCHES-V1"

with open(PATH) as f:
    content = f.read()

if MARKER in content:
    print(f"done — {PATH} al gepatcht ({MARKER})")
    sys.exit(0)

# 1. Route-string uitbreiden
OLD_ROUTE = '''    s_rt = add("#X obj 633 87 route sampler-load sampler-play sampler-stop "
               "sampler-vol sampler-speed sampler-rec-start sampler-rec-stop "
               "sampler-trim sampler-trim-end sampler-autotrim "
               "sampler-autotrim-threshold sampler-autotrim-preroll "
               "sampler-router-input;")'''

NEW_ROUTE = '''    # ABSORB-HOST-PATCHES-V1: route uitgebreid met sampler-master-vol
    # en sampler-rec-path (voorheen toegevoegd door post-regen patches).
    s_rt = add("#X obj 633 87 route sampler-load sampler-play sampler-stop "
               "sampler-vol sampler-speed sampler-rec-start sampler-rec-stop "
               "sampler-trim sampler-trim-end sampler-autotrim "
               "sampler-autotrim-threshold sampler-autotrim-preroll "
               "sampler-router-input sampler-master-vol sampler-rec-path;")'''

if OLD_ROUTE not in content:
    print("ERROR: route-anker niet gevonden", file=sys.stderr)
    sys.exit(1)

content = content.replace(OLD_ROUTE, NEW_ROUTE, 1)

# 2. send_specs uitbreiden — anker is de regel met sampler-router-input
OLD_LAST_SPEC = '        (965, 218, "sampler-router-input"),\n    ]'
NEW_LAST_SPEC = '''        (965, 218, "sampler-router-input"),
        (900, 230, "sampler-master-vol"),    # ABSORB-HOST-PATCHES-V1
        (2000, 1200, "sampler-rec-path"),    # ABSORB-HOST-PATCHES-V1
    ]'''

if OLD_LAST_SPEC not in content:
    print("ERROR: send_specs-anker niet gevonden", file=sys.stderr)
    sys.exit(1)

content = content.replace(OLD_LAST_SPEC, NEW_LAST_SPEC, 1)

with open(PATH, "w") as f:
    f.write(content)

print(f"✓ Patched {PATH} ({MARKER})")
print("  Route-string uitgebreid (+sampler-master-vol +sampler-rec-path)")
print("  send_specs uitgebreid (+2 entries op staging-coords)")
