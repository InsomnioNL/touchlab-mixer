#!/usr/bin/env python3
"""patch-waveform-playhead-v1.py

Fase 2a van de waveform-feature: afspeelpositie-cursor (playhead) tijdens playback.

Vier inserts in index.html:
  1. JS: cache audioBuffer in _currentAudioBuffer + duration
  2. JS: playhead-functies (start/stop/render-loop)
  3. JS: hook in handleSamplerStatus voor playing/idle-state
  4. JS: clearWaveform() ook stop-playhead aanroepen

Marker: WAVEFORM-PLAYHEAD-V1.

Werking:
- Bij state 'playing' van actieve slot: requestAnimationFrame-loop start
- Elke frame: clear canvas, hertekenen waveform vanuit cache, cursor op huidige pos
- Cursor-positie: elapsed-since-trigger × playSpeed / duration → x-pixel
- Bij state 'idle' of slot-switch: loop stoppen, canvas op statische waveform
"""
import shutil, sys
from datetime import datetime
from pathlib import Path

V2 = Path.home() / "Documents/Pd/PDMixer/v2"
TARGET = V2 / "index.html"
BACKUPS = V2 / "_backups"
MARKER = "WAVEFORM-PLAYHEAD-V1"

NL = chr(10)

# Insert 1: cache audioBuffer in _renderPeaks (modify existing)
ANCHOR_RENDER_START = (
    "function _renderPeaks(audioBuffer){" + NL
    + "  var canvas = document.getElementById(\u0027ttb-wave-canvas\u0027);" + NL
    + "  var area = document.getElementById(\u0027ttb-wave-area\u0027);" + NL
    + "  if (!canvas || !area) return;"
)
INSERT_RENDER_START = (
    "function _renderPeaks(audioBuffer){" + NL
    + "  /* WAVEFORM-PLAYHEAD-V1: cache buffer for re-render during playback */" + NL
    + "  _currentAudioBuffer = audioBuffer;" + NL
    + "  var canvas = document.getElementById(\u0027ttb-wave-canvas\u0027);" + NL
    + "  var area = document.getElementById(\u0027ttb-wave-area\u0027);" + NL
    + "  if (!canvas || !area) return;"
)

# Insert 2: playhead functions + globals, before _renderPeaks
ANCHOR_PLAYHEAD_BLOCK = "function _renderPeaks(audioBuffer){"
INSERT_PLAYHEAD_BLOCK = (
    "// === WAVEFORM-PLAYHEAD-V1: playback cursor ===" + NL
    + "var _currentAudioBuffer = null;" + NL
    + "var _playheadRAF = null;" + NL
    + "var _playheadStartTime = 0;" + NL
    + "var _playheadSlot = null;" + NL
    + "function _getPlaySpeed(){" + NL
    + "  var s = (typeof ttbSlots !== \u0027undefined\u0027 && _playheadSlot != null) ?" + NL
    + "    ttbSlots.find(function(x){ return x.slot === _playheadSlot; }) : null;" + NL
    + "  return (s && s.speed) ? s.speed : 1.0;" + NL
    + "}" + NL
    + "function startPlayhead(slot){" + NL
    + "  if (!_currentAudioBuffer) return;" + NL
    + "  if (_playheadRAF) cancelAnimationFrame(_playheadRAF);" + NL
    + "  _playheadSlot = slot;" + NL
    + "  _playheadStartTime = performance.now();" + NL
    + "  _playheadRAF = requestAnimationFrame(_drawPlayhead);" + NL
    + "}" + NL
    + "function stopPlayhead(){" + NL
    + "  if (_playheadRAF) { cancelAnimationFrame(_playheadRAF); _playheadRAF = null; }" + NL
    + "  _playheadSlot = null;" + NL
    + "  /* Hertekenen zonder cursor */" + NL
    + "  if (_currentAudioBuffer) _renderPeaks(_currentAudioBuffer);" + NL
    + "}" + NL
    + "function _drawPlayhead(){" + NL
    + "  if (!_currentAudioBuffer) { _playheadRAF = null; return; }" + NL
    + "  var canvas = document.getElementById(\u0027ttb-wave-canvas\u0027);" + NL
    + "  if (!canvas) { _playheadRAF = null; return; }" + NL
    + "  /* Re-render statische waveform first */" + NL
    + "  _renderPeaksOnly(_currentAudioBuffer);" + NL
    + "  /* Compute current playback position */" + NL
    + "  var elapsedSec = (performance.now() - _playheadStartTime) / 1000;" + NL
    + "  var speed = _getPlaySpeed();" + NL
    + "  var positionSec = elapsedSec * speed;" + NL
    + "  var duration = _currentAudioBuffer.duration;" + NL
    + "  if (positionSec >= duration) {" + NL
    + "    /* Past end: stop loop, render statisch */" + NL
    + "    _playheadRAF = null;" + NL
    + "    return;" + NL
    + "  }" + NL
    + "  var x = (positionSec / duration) * canvas.width;" + NL
    + "  var ctx = canvas.getContext(\u00272d\u0027);" + NL
    + "  ctx.strokeStyle = \u0027rgba(255,255,255,0.85)\u0027;" + NL
    + "  ctx.lineWidth = 2;" + NL
    + "  ctx.beginPath();" + NL
    + "  ctx.moveTo(x, 0);" + NL
    + "  ctx.lineTo(x, canvas.height);" + NL
    + "  ctx.stroke();" + NL
    + "  _playheadRAF = requestAnimationFrame(_drawPlayhead);" + NL
    + "}" + NL + NL
    + "function _renderPeaks(audioBuffer){"
)

# We need _renderPeaks split into two: a peaks-only version for use inside the loop
# Simpler: extract the body and inline call. But to keep idempotent + minimal-risk,
# add a thin wrapper _renderPeaksOnly that does the same thing without setting cache.
ANCHOR_RENDER_END = (
    "  ctx.stroke();" + NL
    + "  area.classList.add(\u0027has-sample\u0027);" + NL
    + "}"
)
INSERT_RENDER_END = (
    "  ctx.stroke();" + NL
    + "  area.classList.add(\u0027has-sample\u0027);" + NL
    + "}" + NL
    + "/* WAVEFORM-PLAYHEAD-V1: alias zonder cache-side-effects voor render-loop */" + NL
    + "function _renderPeaksOnly(audioBuffer){" + NL
    + "  var canvas = document.getElementById(\u0027ttb-wave-canvas\u0027);" + NL
    + "  var area = document.getElementById(\u0027ttb-wave-area\u0027);" + NL
    + "  if (!canvas || !area) return;" + NL
    + "  var ctx = canvas.getContext(\u00272d\u0027);" + NL
    + "  var W = canvas.width, H = canvas.height;" + NL
    + "  ctx.clearRect(0, 0, W, H);" + NL
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
    + "}"
)

# Insert 3: hook in handleSamplerStatus (only when slot is the active edit slot)
ANCHOR_HSAMPLER = (
    "function handleSamplerStatus(msg){" + NL
    + "  if (msg.state === \u0027playing\u0027 || msg.state === \u0027idle\u0027) {" + NL
    + "    intendedStates[msg.slot] = msg.state;" + NL
    + "  }"
)
INSERT_HSAMPLER = (
    "function handleSamplerStatus(msg){" + NL
    + "  if (msg.state === \u0027playing\u0027 || msg.state === \u0027idle\u0027) {" + NL
    + "    intendedStates[msg.slot] = msg.state;" + NL
    + "  }" + NL
    + "  /* WAVEFORM-PLAYHEAD-V1: animate playhead for active edit slot */" + NL
    + "  if (ttbMode === \u0027edit\u0027 && msg.slot === ttbActiveSlot) {" + NL
    + "    if (msg.state === \u0027playing\u0027) startPlayhead(msg.slot);" + NL
    + "    else if (msg.state === \u0027idle\u0027) stopPlayhead();" + NL
    + "  }"
)

# Insert 4: clearWaveform() also stops the playhead
ANCHOR_CLEAR = (
    "function clearWaveform(){" + NL
    + "  var area = document.getElementById(\u0027ttb-wave-area\u0027);"
)
INSERT_CLEAR = (
    "function clearWaveform(){" + NL
    + "  /* WAVEFORM-PLAYHEAD-V1: stop playhead loop on clear */" + NL
    + "  if (_playheadRAF) { cancelAnimationFrame(_playheadRAF); _playheadRAF = null; }" + NL
    + "  _currentAudioBuffer = null;" + NL
    + "  var area = document.getElementById(\u0027ttb-wave-area\u0027);"
)

# --- Apply ---
text = TARGET.read_text()

if MARKER in text:
    print("Marker " + MARKER + " reeds aanwezig; geen wijziging.")
    sys.exit(0)

for label, anchor in [
    ("RENDER_START", ANCHOR_RENDER_START),
    ("PLAYHEAD_BLOCK", ANCHOR_PLAYHEAD_BLOCK),
    ("RENDER_END", ANCHOR_RENDER_END),
    ("HSAMPLER", ANCHOR_HSAMPLER),
    ("CLEAR", ANCHOR_CLEAR),
]:
    n = text.count(anchor)
    if n != 1:
        print("ERROR: anker " + label + " niet exact 1x (n=" + str(n) + "). Bail.")
        sys.exit(1)

BACKUPS.mkdir(exist_ok=True)
ts = datetime.now().strftime("%Y%m%d-%H%M%S")
backup = BACKUPS / ("index.html." + ts + ".bak")
shutil.copy(TARGET, backup)
print("Backup: " + str(backup))

# Order matters: PLAYHEAD_BLOCK comes BEFORE _renderPeaks, so apply it first
# Then RENDER_START modifies inside _renderPeaks
# Then RENDER_END adds the alias function after _renderPeaks
new_text = text.replace(ANCHOR_PLAYHEAD_BLOCK, INSERT_PLAYHEAD_BLOCK, 1)
new_text = new_text.replace(ANCHOR_RENDER_START, INSERT_RENDER_START, 1)
new_text = new_text.replace(ANCHOR_RENDER_END, INSERT_RENDER_END, 1)
new_text = new_text.replace(ANCHOR_HSAMPLER, INSERT_HSAMPLER, 1)
new_text = new_text.replace(ANCHOR_CLEAR, INSERT_CLEAR, 1)

TARGET.write_text(new_text)
print("Wrote index.html: playhead globals + functions + 2 hooks (WAVEFORM-PLAYHEAD-V1)")
