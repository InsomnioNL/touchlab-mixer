#!/usr/bin/env python3
"""Voegt rec-history aan bridge.js toe.

Wijzigingen:
1. Nieuwe functie archiveRecording(slot): kopieert slotN.wav naar
   slotN_<timestamp>.wav en voegt entry toe aan cfg.ttb.slots[N].history
2. Bij 'recording'-event: bewaar recStartTs in samplerState[slot]
3. Bij 'rec-stopped'-event: roep archiveRecording aan
"""
import sys

PATH = sys.argv[1]
MARKER = "REC-HISTORY-V1"

with open(PATH) as f:
    content = f.read()

if MARKER in content:
    print(f"done — {PATH} is al gepatcht ({MARKER})")
    sys.exit(0)

# Nieuwe functie. Plaats vlak voor "// ─── Sampler FUDI" comment-header
NEW_FUNCTION = '''// === REC-HISTORY-V1 ===
// Bij rec-stop: kopieert slotN.wav naar slotN_<timestamp>.wav en voegt
// een history-entry toe aan cfg.ttb.slots[N]. Persisteert sessie via
// saveSessionToDisk. Faalt zacht bij disk-fouten (warning, geen crash).
function archiveRecording(slot) {
  if (!SAMPLER_ENABLED) return;

  const samplesDir = cfg.ttb?.samples_dir || "samples";
  const fullSamplesDir = path.isAbsolute(samplesDir) ? samplesDir : path.join(process.cwd(), samplesDir);
  const srcPath = path.join(fullSamplesDir, `slot${slot}.wav`);

  // Lokale tijd in sortbaar formaat: YYYY-MM-DD-HH-MM-SS
  const d = new Date();
  const pad = n => String(n).padStart(2, "0");
  const ts = `${d.getFullYear()}-${pad(d.getMonth()+1)}-${pad(d.getDate())}-${pad(d.getHours())}-${pad(d.getMinutes())}-${pad(d.getSeconds())}`;
  const archiveName = `slot${slot}_${ts}.wav`;
  const archivePath = path.join(fullSamplesDir, archiveName);

  // Duration: ms verschil tussen recording-start en nu
  const startTs = samplerState[slot]?.recStartTs;
  const durationSec = startTs ? Math.round((Date.now() - startTs) / 100) / 10 : null;

  try {
    fs.copyFileSync(srcPath, archivePath);
  } catch (err) {
    console.warn(`⚠  Kon ${srcPath} niet archiveren: ${err.message}`);
    return;
  }

  // History-entry toevoegen aan cfg.ttb.slots[slot]
  const entry = {
    filename: archiveName,
    recorded_at: d.toISOString(),
  };
  if (durationSec != null) entry.duration_seconds = durationSec;

  const slotEntry = cfg.ttb.slots.find(s => s.slot === slot);
  if (!slotEntry) {
    console.warn(`⚠  archiveRecording: slot ${slot} niet in cfg.ttb.slots (zou niet moeten kunnen na ensureSlotEntries)`);
    return;
  }
  if (!Array.isArray(slotEntry.history)) slotEntry.history = [];
  slotEntry.history.push(entry);

  // Persisteer naar disk
  try {
    saveSessionToDisk(cfg, null);
    console.log(`+  Slot ${slot} archief: ${archiveName}${durationSec != null ? ` (${durationSec}s)` : ""}`);
  } catch (err) {
    console.warn(`⚠  Sessie-save na archive faalde: ${err.message}`);
  }
}

'''

ANCHOR = "// ─── Sampler FUDI"
if ANCHOR not in content:
    print(f"ERROR: kan '{ANCHOR}' niet vinden", file=sys.stderr)
    sys.exit(1)
if content.count(ANCHOR) != 1:
    print(f"ERROR: '{ANCHOR}' komt {content.count(ANCHOR)}x voor", file=sys.stderr)
    sys.exit(1)

idx = content.index(ANCHOR)
line_start = content.rfind("\n", 0, idx) + 1
new_content = content[:line_start] + NEW_FUNCTION + content[line_start:]

# Wijziging 2: bij 'recording'-event start-timestamp opslaan
OLD_REC = '    case "recording":   samplerState[slot].state = "recording"; break;'
NEW_REC = '    case "recording":   samplerState[slot].state = "recording"; samplerState[slot].recStartTs = Date.now(); break;'
if OLD_REC not in new_content:
    print("ERROR: kan 'recording'-case niet vinden", file=sys.stderr)
    sys.exit(1)
if new_content.count(OLD_REC) != 1:
    print(f"ERROR: 'recording'-case komt {new_content.count(OLD_REC)}x voor", file=sys.stderr)
    sys.exit(1)
new_content = new_content.replace(OLD_REC, NEW_REC, 1)

# Wijziging 3: bij 'rec-stopped'-event archiveRecording aanroepen
OLD_STOP = '    case "rec-stopped": samplerState[slot].state = "idle";      break;'
NEW_STOP = '    case "rec-stopped": samplerState[slot].state = "idle"; archiveRecording(slot); break;'
if OLD_STOP not in new_content:
    print("ERROR: kan 'rec-stopped'-case niet vinden", file=sys.stderr)
    sys.exit(1)
if new_content.count(OLD_STOP) != 1:
    print(f"ERROR: 'rec-stopped'-case komt {new_content.count(OLD_STOP)}x voor", file=sys.stderr)
    sys.exit(1)
new_content = new_content.replace(OLD_STOP, NEW_STOP, 1)

with open(PATH, "w") as f:
    f.write(new_content)

print(f"✓ Patched {PATH}")
print("  archiveRecording() function added before sampler FUDI section")
print("  recording-case extended: stores recStartTs")
print("  rec-stopped-case extended: calls archiveRecording")
