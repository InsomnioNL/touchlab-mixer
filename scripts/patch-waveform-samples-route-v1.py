#!/usr/bin/env python3
"""patch-waveform-samples-route-v1.py

Fix bij WAVEFORM-FASE1-V1: slot-files leven in samples/, niet in recordings/.

Twee inserts:
  1. bridge.js: extra HTTP-route /samples/<filename> die uit cfg.ttb.samples_dir serveert
  2. index.html: drawWaveform URL-pad /recordings/ -> /samples/

Marker: WAVEFORM-SAMPLES-ROUTE-V1.
"""
import shutil, sys
from datetime import datetime
from pathlib import Path

V2 = Path.home() / "Documents/Pd/PDMixer/v2"
BRIDGE = V2 / "bridge.js"
INDEX = V2 / "index.html"
BACKUPS = V2 / "_backups"
MARKER = "WAVEFORM-SAMPLES-ROUTE-V1"

NL = chr(10)

# --- Bridge: nieuwe HTTP-route /samples/<filename> ---
ANCHOR_BRIDGE = (
    '  if (url.startsWith("/recordings/")) {' + NL
    + '    const filename = decodeURIComponent(url.slice(13));' + NL
    + '    const filepath = path.join(REC_DIR, path.basename(filename));'
)
INSERT_BRIDGE_HEADER = (
    '  // === WAVEFORM-SAMPLES-ROUTE-V1: serve sample-files for waveform display ===' + NL
    + '  if (url.startsWith("/samples/")) {' + NL
    + '    const filename = decodeURIComponent(url.slice(9));' + NL
    + '    const samplesDir = cfg.ttb?.samples_dir || "samples";' + NL
    + '    const fullSamplesDir = path.isAbsolute(samplesDir) ? samplesDir : path.join(process.cwd(), samplesDir);' + NL
    + '    const filepath = path.join(fullSamplesDir, path.basename(filename));' + NL
    + '    if (fs.existsSync(filepath)) {' + NL
    + '      res.writeHead(200, {' + NL
    + '        "Content-Type": "audio/wav",' + NL
    + '        "Access-Control-Allow-Origin": "*",' + NL
    + '        "Content-Length": fs.statSync(filepath).size' + NL
    + '      });' + NL
    + '      fs.createReadStream(filepath).pipe(res);' + NL
    + '    } else {' + NL
    + '      res.writeHead(404); res.end("Sample niet gevonden");' + NL
    + '    }' + NL
    + '    return;' + NL
    + '  }' + NL
)

# --- index.html: drawWaveform URL pad fix ---
ANCHOR_HTML = "var url = \u0027http://localhost:8080/recordings/\u0027 + encodeURIComponent(filename);"
INSERT_HTML = (
    "var url = \u0027http://localhost:8080/samples/\u0027 + encodeURIComponent(filename); /* WAVEFORM-SAMPLES-ROUTE-V1 */"
)

# --- Apply ---
btext = BRIDGE.read_text()
htext = INDEX.read_text()

if MARKER in btext or MARKER in htext:
    print("Marker " + MARKER + " reeds aanwezig; geen wijziging.")
    sys.exit(0)

if btext.count(ANCHOR_BRIDGE) != 1:
    print("ERROR: anker BRIDGE niet exact 1x. Bail.")
    sys.exit(1)
if htext.count(ANCHOR_HTML) != 1:
    print("ERROR: anker HTML niet exact 1x (n=" + str(htext.count(ANCHOR_HTML)) + "). Bail.")
    sys.exit(1)

BACKUPS.mkdir(exist_ok=True)
ts = datetime.now().strftime("%Y%m%d-%H%M%S")
shutil.copy(BRIDGE, BACKUPS / ("bridge.js." + ts + ".bak"))
shutil.copy(INDEX, BACKUPS / ("index.html." + ts + ".bak"))
print("Backups in " + str(BACKUPS))

new_btext = btext.replace(ANCHOR_BRIDGE, INSERT_BRIDGE_HEADER + ANCHOR_BRIDGE, 1)
new_htext = htext.replace(ANCHOR_HTML, INSERT_HTML, 1)

BRIDGE.write_text(new_btext)
INDEX.write_text(new_htext)
print("Wrote bridge.js (samples-route) + index.html (drawWaveform url)")
