"""Voegt opts.skipReload parameter toe aan saveSessionToDisk.

Voorkomt overbodige loadTTBSamples-aanroep wanneer interne flows
(zoals archiveRecording) alleen history-state persisteren - de slots
zelf zijn niet veranderd, dus Pd hoeft niets opnieuw te laden.

Idempotent via marker SKIP-RELOAD-V1.
"""
import sys

PATH = "bridge.js"
MARKER = "SKIP-RELOAD-V1"

with open(PATH) as f:
    content = f.read()

if MARKER in content:
    print(f"done — {PATH} al gepatcht ({MARKER})")
    sys.exit(0)

# 1. Functie-signature uitbreiden + skipReload-flag declareren
OLD_SIG = '''function saveSessionToDisk(newConfig, ws) {
  if (!newConfig || typeof newConfig !== "object") {
    if (ws) ws.send(JSON.stringify({type:"saveSessionResult", ok:false, error:"invalid config"}));
    return;
  }'''

NEW_SIG = '''function saveSessionToDisk(newConfig, ws, opts) {
  if (!newConfig || typeof newConfig !== "object") {
    if (ws) ws.send(JSON.stringify({type:"saveSessionResult", ok:false, error:"invalid config"}));
    return;
  }
  // === SKIP-RELOAD-V1 ===
  // Interne aanroepers (archiveRecording) hebben alleen history-state
  // bijgewerkt — Pd hoeft niets opnieuw te laden.
  var skipReload = opts && opts.skipReload === true;'''

if OLD_SIG not in content:
    print("ERROR: signature-anker niet gevonden", file=sys.stderr)
    sys.exit(1)

content = content.replace(OLD_SIG, NEW_SIG, 1)

# 2. Conditionele reload
OLD_RELOAD = '    if (SAMPLER_ENABLED) { ensureSlotEntries(); loadTTBSamples(); }'
NEW_RELOAD = '    if (SAMPLER_ENABLED && !skipReload) { ensureSlotEntries(); loadTTBSamples(); }'

if OLD_RELOAD not in content:
    print("ERROR: reload-anker niet gevonden", file=sys.stderr)
    sys.exit(1)

content = content.replace(OLD_RELOAD, NEW_RELOAD, 1)

# 3. archiveRecording aanroep updaten
OLD_CALL = '    saveSessionToDisk(cfg, null);\n    console.log(`+  Slot ${slot} archief: ${archiveName}'
NEW_CALL = '    saveSessionToDisk(cfg, null, { skipReload: true });\n    console.log(`+  Slot ${slot} archief: ${archiveName}'

if OLD_CALL not in content:
    print("ERROR: archiveRecording call-anker niet gevonden", file=sys.stderr)
    sys.exit(1)

content = content.replace(OLD_CALL, NEW_CALL, 1)

with open(PATH, "w") as f:
    f.write(content)

print(f"✓ Patched {PATH} ({MARKER})")
print("  Signature uitgebreid met opts.skipReload")
print("  Reload conditional gemaakt")
print("  archiveRecording roept aan met skipReload: true")
