#!/usr/bin/env python3
"""Voegt ensureSlotEntries() toe en roept hem aan vóór beide loadTTBSamples-sites."""
import sys

PATH = sys.argv[1]
MARKER = "ENSURE-SLOT-ENTRIES-V1"

with open(PATH) as f:
    content = f.read()

if MARKER in content:
    print(f"done — {PATH} is al gepatcht ({MARKER})")
    sys.exit(0)

NEW_FUNCTION = '''// === ENSURE-SLOT-ENTRIES-V1 ===
// Zorgt dat cfg.ttb.slots voor elke slot 1..SAMPLER_SLOTS een entry heeft.
// Default-entries zijn minimaal: {slot, label, vol, color} - geen 'file'-veld,
// zodat loadTTBSamples ze netjes skipt (geen sampler-load voor lege slots).
// Pas zodra een rec gebeurt en history zich opbouwt, krijgt zo'n slot een file.
function ensureSlotEntries() {
  if (!SAMPLER_ENABLED) return;
  if (!cfg.ttb) cfg.ttb = {};
  if (!Array.isArray(cfg.ttb.slots)) cfg.ttb.slots = [];

  const present = new Set(cfg.ttb.slots.map(s => s.slot).filter(n => typeof n === "number"));
  let added = 0;
  for (let i = 1; i <= SAMPLER_SLOTS; i++) {
    if (!present.has(i)) {
      cfg.ttb.slots.push({
        slot: i,
        label: `SLOT ${i}`,
        vol: 0.8,
        color: "neutral",
      });
      added++;
    }
  }
  if (added > 0) {
    console.log(`+  ${added} slot-entries toegevoegd aan cfg.ttb.slots (default placeholders)`);
  }
}

'''

# Anker 1: insertion-point voor de nieuwe functie.
# Plaats hem vlak vóór de "// ─── TTB sample-loader ───" comment-header.
ANCHOR_HEADER = "// ─── TTB sample-loader ─"
if ANCHOR_HEADER not in content:
    print(f"ERROR: kan '{ANCHOR_HEADER}' niet vinden", file=sys.stderr)
    sys.exit(1)
if content.count(ANCHOR_HEADER) != 1:
    print(f"ERROR: '{ANCHOR_HEADER}' komt {content.count(ANCHOR_HEADER)}x voor", file=sys.stderr)
    sys.exit(1)

# Vind de regel-start van de header
idx = content.index(ANCHOR_HEADER)
line_start = content.rfind("\n", 0, idx) + 1
new_content = content[:line_start] + NEW_FUNCTION + content[line_start:]

# Anker 2: setTimeout-aanroep
OLD1 = "  setTimeout(loadTTBSamples, 300);"
NEW1 = "  ensureSlotEntries();\n  setTimeout(loadTTBSamples, 300);"
if OLD1 not in new_content:
    print(f"ERROR: kan setTimeout-aanroep niet vinden", file=sys.stderr)
    sys.exit(1)
if new_content.count(OLD1) != 1:
    print(f"ERROR: setTimeout-aanroep komt {new_content.count(OLD1)}x voor", file=sys.stderr)
    sys.exit(1)
new_content = new_content.replace(OLD1, NEW1, 1)

# Anker 3: saveSessionToDisk-aanroep
OLD2 = "    if (SAMPLER_ENABLED) loadTTBSamples();"
NEW2 = "    if (SAMPLER_ENABLED) { ensureSlotEntries(); loadTTBSamples(); }"
if OLD2 not in new_content:
    print(f"ERROR: kan saveSession-aanroep niet vinden", file=sys.stderr)
    sys.exit(1)
if new_content.count(OLD2) != 1:
    print(f"ERROR: saveSession-aanroep komt {new_content.count(OLD2)}x voor", file=sys.stderr)
    sys.exit(1)
new_content = new_content.replace(OLD2, NEW2, 1)

with open(PATH, "w") as f:
    f.write(new_content)

print(f"✓ Patched {PATH}")
print("  ensureSlotEntries() function added before loadTTBSamples")
print("  Call inserted before setTimeout(loadTTBSamples, 300)")
print("  Call inserted before SAMPLER_ENABLED loadTTBSamples in saveSessionToDisk")
