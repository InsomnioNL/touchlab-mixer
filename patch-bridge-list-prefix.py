#!/usr/bin/env python3
"""Vervangt de markerless list-prefix-strip in bridge.js door een
gemarkeerde versie. Idempotent via LIST-PREFIX-STRIP-V1.

Achtergrond: Pd's [fudiformat] serializeert lists als 'list <items>',
inclusief het 'list'-prefix. Bridge moet dat strippen vóór de
sampler-status-check, anders worden alle status-events gedropt.

Eenmalige migratie - herhaaldelijk draaien is veilig.
"""
import sys

PATH = "bridge.js"
MARKER = "LIST-PREFIX-STRIP-V1"

with open(PATH) as f:
    content = f.read()

if MARKER in content:
    print(f"done — {PATH} is al gepatcht ({MARKER})")
    sys.exit(0)

OLD_LINE = '  if (parts[0] === "list") parts.shift();  // fudiformat prefixt list-messages'
NEW_LINE = '  // === LIST-PREFIX-STRIP-V1 ===\n  // Pd\'s [fudiformat] serializeert Pd-lists als "list <items>" -\n  // het "list"-prefix moet weg vóór de sampler-status-check, anders\n  // worden alle status-events gedropt.\n  if (parts[0] === "list") parts.shift();'

if OLD_LINE not in content:
    print(f"ERROR: huidige list-prefix-strip-regel niet gevonden", file=sys.stderr)
    print(f"  (zoekstring: {OLD_LINE!r})", file=sys.stderr)
    sys.exit(1)

if content.count(OLD_LINE) != 1:
    print(f"ERROR: regel komt {content.count(OLD_LINE)}x voor (verwacht 1)", file=sys.stderr)
    sys.exit(1)

content = content.replace(OLD_LINE, NEW_LINE, 1)

with open(PATH, "w") as f:
    f.write(content)

print(f"✓ Patched {PATH}")
print(f"  Markerless list-prefix-strip vervangen door gemarkeerde versie ({MARKER})")
