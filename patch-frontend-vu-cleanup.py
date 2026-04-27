"""updateVUs simplified: master-L en master-R passen het standaard
updSG-patroon (zoals channels). Geen dubbele conversie meer.

Idempotent via marker FRONTEND-VU-CLEANUP-V1.
"""
import sys

PATH = "index.html"
MARKER = "FRONTEND-VU-CLEANUP-V1"

with open(PATH) as f:
    content = f.read()

if MARKER in content:
    print(f"done — {PATH} al gepatcht ({MARKER})")
    sys.exit(0)

OLD = """  updSG('ml',dbP(masterVuL||masterVu)/100*60-60);
  updSG('m',masterVu);
  updSG('mr',dbP(masterVuR||masterVu)/100*60-60);"""

NEW = """  // FRONTEND-VU-CLEANUP-V1
  updSG('ml',masterVuL);
  updSG('m',masterVu);
  updSG('mr',masterVuR);"""

if OLD not in content:
    print("ERROR: anker niet gevonden", file=sys.stderr)
    sys.exit(1)

content = content.replace(OLD, NEW, 1)

with open(PATH, "w") as f:
    f.write(content)

print(f"✓ Patched {PATH} ({MARKER})")
