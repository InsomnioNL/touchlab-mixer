#!/usr/bin/env python3
"""patch-waveform-fase1-v1.py

Fase 1 van de waveform-feature: statische waveform na opname + bij slot-selectie.

Vier inserts in index.html:
  1. HTML: canvas-element in .ttb-wave-area
  2. CSS: stacking van canvas + empty-placeholder
  3. JS: drawWaveform(filename) + clearWaveform()
  4. Trigger 1: in recStatus-handler na rec-stop met msg.file
  5. Trigger 2: in renderActiveSlotForm bij slot-selectie

Marker: WAVEFORM-FASE1-V1.
Anker-strategy: markers + count==1 checks per insert.

Werking:
- fetch /recordings/<filename> via http://localhost:8080 (CORS toegestaan)
- AudioContext.decodeAudioData
- per-pixel min/max peaks tekenen op canvas (mono summed)
- bij no-file: empty-placeholder zichtbaar; canvas hidden
- bij file: canvas zichtbaar; empty hidden
"""
import shutil, sys
from datetime import datetime
from pathlib import Path

V2 = Path.home() / "Documents/Pd/PDMixer/v2"
TARGET = V2 / "index.html"
BACKUPS = V2 / "_backups"
MARKER = "WAVEFORM-FASE1-V1"

NL = chr(10)

# -- Insert 1: HTML canvas in .ttb-wave-area, naast empty-placeholder --
ANCHOR_HTML = (
    '      <div class="ttb-wave-area" id="ttb-wave-area">' + NL
    + '        <div class="ttb-wave-empty" id="ttb-wave-empty">\u2014 geen sample geselecteerd \u2014</div>' + NL
    + '      </div>'
)
INSERT_HTML = (
    '      <div class="ttb-wave-area" id="ttb-wave-area">' + NL
    + '        <!-- WAVEFORM-FASE1-V1 -->' + NL
    + '        <canvas class="ttb-wave-canvas" id="ttb-wave-canvas" width="600" height="120"></canvas>' + NL
    + '        <div class="ttb-wave-empty" id="ttb-wave-empty">\u2014 geen sample geselecteerd \u2014</div>' + NL
    + '      </div>'
)

# -- Insert 2: CSS voor canvas/empty-stacking --
ANCHOR_CSS = ".ttb-trim-marker.end{right:5%;}"
INSERT_CSS = (
    NL
    + "/* === WAVEFORM-FASE1-V1: canvas + empty stacking === */" + NL
    + ".ttb-wave-area{position:relative;}" + NL
    + ".ttb-wave-canvas{display:none;width:100%;height:100%;}" + NL
    + ".ttb-wave-area.has-sample .ttb-wave-canvas{display:block;}" + NL
    + ".ttb-wave-area.has-sample .ttb-wave-empty{display:none;}"
)

# -- Insert 3: JS drawWaveform + clearWaveform na DOMContentLoaded TTB-route init --
ANCHOR_JS = "// Fader-listener (master volume)"
INSERT_JS = (
    "// === WAVEFORM-FASE1-V1: waveform render ===" + NL
    + "var _waveformAudioCtx = null;" + NL
    + "function _getAudioCtx(){" + NL
    + "  if (!_waveformAudioCtx) {" + NL
    + "    _waveformAudioCtx = new (window.AudioContext || window.webkitAudioContext)();" + NL
    + "  }" + NL
    + "  return _waveformAudioCtx;" + NL
    + "}" + NL
    + "function clearWaveform(){" + NL
    + "  var area = document.getElementById(\u0027ttb-wave-area\u0027);" + NL
    + "  if (area) area.classList.remove(\u0027has-sample\u0027);" + NL
    + "  var canvas = document.getElementById(\u0027ttb-wave-canvas\u0027);" + NL
    + "  if (canvas) {" + NL
    + "    var ctx = canvas.getContext(\u00272d\u0027);" + NL
    + "    ctx.clearRect(0, 0, canvas.width, canvas.height);" + NL
    + "  }" + NL
    + "}" + NL
    + "function drawWaveform(filename){" + NL
    + "  if (!filename) { clearWaveform(); return; }" + NL
    + "  var url = \u0027http://localhost:8080/recordings/\u0027 + encodeURIComponent(filename);" + NL
    + "  fetch(url)" + NL
    + "    .then(function(r){ if (!r.ok) throw new Error(\u0027fetch \u0027 + r.status); return r.arrayBuffer(); })" + NL
    + "    .then(function(buf){ return _getAudioCtx().decodeAudioData(buf); })" + NL
    + "    .then(function(audio){ _renderPeaks(audio); })" + NL
    + "    .catch(function(err){ console.warn(\u0027waveform load failed:\u0027, err); clearWaveform(); });" + NL
    + "}" + NL
    + "function _renderPeaks(audioBuffer){" + NL
    + "  var canvas = document.getElementById(\u0027ttb-wave-canvas\u0027);" + NL
    + "  var area = document.getElementById(\u0027ttb-wave-area\u0027);" + NL
    + "  if (!canvas || !area) return;" + NL
    + "  // Resize canvas to actual display size for crisp rendering" + NL
    + "  var rect = area.getBoundingClientRect();" + NL
    + "  canvas.width = Math.max(100, Math.floor(rect.width));" + NL
    + "  canvas.height = Math.max(60, Math.floor(rect.height));" + NL
    + "  var ctx = canvas.getContext(\u00272d\u0027);" + NL
    + "  var W = canvas.width, H = canvas.height;" + NL
    + "  ctx.clearRect(0, 0, W, H);" + NL
    + "  // Sum channels to mono" + NL
    + "  var ch0 = audioBuffer.getChannelData(0);" + NL
    + "  var ch1 = audioBuffer.numberOfChannels > 1 ? audioBuffer.getChannelData(1) : null;" + NL
    + "  var samplesPerPixel = Math.max(1, Math.floor(audioBuffer.length / W));" + NL
    + "  ctx.strokeStyle = \u0027rgba(176,106,245,0.85)\u0027;" + NL
    + "  ctx.lineWidth = 1;" + NL
    + "  ctx.beginPath();" + NL
    + "  for (var x = 0; x < W; x++) {" + NL
    + "    var start = x * samplesPerPixel;" + NL
    + "    var end = Math.min(start + samplesPerPixel, audioBuffer.length);" + NL
    + "    var min = 1.0, max = -1.0;" + NL
    + "    for (var i = start; i < end; i++) {" + NL
    + "      var v = ch1 ? (ch0[i] + ch1[i]) * 0.5 : ch0[i];" + NL
    + "      if (v < min) min = v;" + NL
    + "      if (v > max) max = v;" + NL
    + "    }" + NL
    + "    var yMin = ((1 - min) * 0.5) * H;" + NL
    + "    var yMax = ((1 - max) * 0.5) * H;" + NL
    + "    ctx.moveTo(x + 0.5, yMin);" + NL
    + "    ctx.lineTo(x + 0.5, yMax);" + NL
    + "  }" + NL
    + "  ctx.stroke();" + NL
    + "  area.classList.add(\u0027has-sample\u0027);" + NL
    + "}" + NL + NL
    + ANCHOR_JS
)

# -- Insert 4: trigger in recStatus-handler na rec-stop met msg.file --
ANCHOR_RECSTOP = (
    "        if(msg.file){" + NL
    + "          recFile=msg.file;"
)
INSERT_RECSTOP = (
    "        if(msg.file){" + NL
    + "          recFile=msg.file;" + NL
    + "          /* WAVEFORM-FASE1-V1: render after rec-stop */" + NL
    + "          drawWaveform(msg.file);"
)
# We need to also handle the duplicate later — since the hook needs to be unique.
# Strategy: replace the original 2 lines with 4 lines, keeping rest intact.
# Therefore use careful match.

# -- Insert 5: trigger in renderActiveSlotForm bij slot-selectie --
ANCHOR_SLOTFORM = "  document.getElementById(\u0027ttb-edit-file\u0027).value = s ? (s.file || \u0027\u0027) : \u0027(leeg)\u0027;"
INSERT_SLOTFORM = (
    ANCHOR_SLOTFORM + NL
    + "  /* WAVEFORM-FASE1-V1: render waveform for selected slot */" + NL
    + "  if (s && s.file) drawWaveform(s.file); else clearWaveform();"
)

text = TARGET.read_text()

if MARKER in text:
    print("Marker " + MARKER + " reeds aanwezig; geen wijziging.")
    sys.exit(0)

for label, anchor in [
    ("HTML", ANCHOR_HTML),
    ("CSS", ANCHOR_CSS),
    ("JS", ANCHOR_JS),
    ("RECSTOP", ANCHOR_RECSTOP),
    ("SLOTFORM", ANCHOR_SLOTFORM),
]:
    n = text.count(anchor)
    if n != 1:
        print("ERROR: anker " + label + " niet exact 1x gevonden (n=" + str(n) + "). Bail.")
        sys.exit(1)

BACKUPS.mkdir(exist_ok=True)
ts = datetime.now().strftime("%Y%m%d-%H%M%S")
backup = BACKUPS / ("index.html." + ts + ".bak")
shutil.copy(TARGET, backup)
print("Backup: " + str(backup))

new_text = text.replace(ANCHOR_HTML, INSERT_HTML, 1)
new_text = new_text.replace(ANCHOR_CSS, ANCHOR_CSS + INSERT_CSS, 1)
new_text = new_text.replace(ANCHOR_JS, INSERT_JS, 1)
new_text = new_text.replace(ANCHOR_RECSTOP, INSERT_RECSTOP, 1)
new_text = new_text.replace(ANCHOR_SLOTFORM, INSERT_SLOTFORM, 1)

TARGET.write_text(new_text)
print("Wrote " + TARGET.name + ": canvas + CSS + JS + 2 triggers (WAVEFORM-FASE1-V1)")
