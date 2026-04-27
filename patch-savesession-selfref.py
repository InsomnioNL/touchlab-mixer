"""Fix in saveSessionToDisk: detect self-reference (newConfig === cfg) en
deep-copy in dat geval. Voorkomt data-loss als gevolg van het
delete-then-reassign-patroon op regel 590-591.

Idempotent via marker SAVESESSION-SELFREF-V1.
"""
import sys

PATH = "bridge.js"
MARKER = "SAVESESSION-SELFREF-V1"

with open(PATH) as f:
    content = f.read()

if MARKER in content:
    print(f"done — {PATH} al gepatcht ({MARKER})")
    sys.exit(0)

OLD = '''    var fullConfig;
    if (newConfig.__ttb_only && newConfig.ttb) {
      fullConfig = JSON.parse(JSON.stringify(cfg));
      fullConfig.ttb = newConfig.ttb;
    } else {
      fullConfig = newConfig;
    }'''

NEW = '''    // === SAVESESSION-SELFREF-V1 ===
    // Als newConfig === cfg (zelf-referentie vanuit interne aanroepers
    // zoals archiveRecording), deep-copy om data-loss te voorkomen bij
    // de delete-then-reassign-cyclus hieronder.
    var fullConfig;
    if (newConfig === cfg) {
      fullConfig = JSON.parse(JSON.stringify(cfg));
    } else if (newConfig.__ttb_only && newConfig.ttb) {
      fullConfig = JSON.parse(JSON.stringify(cfg));
      fullConfig.ttb = newConfig.ttb;
    } else {
      fullConfig = newConfig;
    }'''

if OLD not in content:
    print("ERROR: anker niet exact gevonden", file=sys.stderr)
    sys.exit(1)

content = content.replace(OLD, NEW, 1)

with open(PATH, "w") as f:
    f.write(content)

print(f"✓ Patched {PATH}")
print(f"  Self-reference branch toegevoegd ({MARKER})")
