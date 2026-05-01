#!/usr/bin/env python3
"""patch-queue-cue-view-v1
Queue-mode for TTB grid: when ttbQueue.length > 0, grid shows cues from
ttbQueuePos onwards (max ttbVisibleCount), with current cue larger (2fr).
Page-nav buttons step queuePos without playing audio.
Marker: QUEUE-CUE-VIEW-V1
Prereq: QUEUE-ADVANCE-ON-RELEASE-V1
"""
import shutil, sys
from datetime import datetime

MARKER = "QUEUE-CUE-VIEW-V1"
PREREQ = "QUEUE-ADVANCE-ON-RELEASE-V1"
TARGET = "index" + "." + "html"

# --- Edit A: helper toevoegen na renderTTB ---
OLD_A = """function renderTTB(){
  renderCountPills();
  renderQueueNav();
  renderGrid();
  renderQueueDots();
  updateFaderUI();
  updatePageButtons();
}"""

NEW_A = """function renderTTB(){
  renderCountPills();
  renderQueueNav();
  renderGrid();
  renderQueueDots();
  updateFaderUI();
  updatePageButtons();
}

/* === QUEUE-CUE-VIEW-V1: consistente refresh na queue-state-change === */
function refreshAfterQueueChange(){
  renderGrid();
  updateQueueHighlight();
  renderQueueNav();
  renderQueueDots();
  updatePageButtons();
}"""

# --- Edit B: renderGrid met queue-mode tak ---
OLD_B = """function renderGrid(){
  var grid = document.getElementById('ttb-grid');
  if(!grid) return;
  grid.innerHTML = '';
  // Bereken welke slots op huidige pagina horen
  var start = ttbPageIndex * ttbVisibleCount;
  var end   = Math.min(start + ttbVisibleCount, ttbButtonOrder.length);
  var cols  = Math.min(ttbVisibleCount, ttbButtonOrder.length - start);
  if (cols < 1) cols = 1;
  grid.style.gridTemplateColumns = 'repeat(' + cols + ', 1fr)';

  for (var i=start; i<end; i++){
    var slotNum = ttbButtonOrder[i];
    var s = ttbSlots.find(function(x){ return x.slot===slotNum; });
    if (!s) continue;
    var btn = buildTriggerButton(s);
    grid.appendChild(btn);
  }"""

NEW_B = """function renderGrid(){
  var grid = document.getElementById('ttb-grid');
  if(!grid) return;
  grid.innerHTML = '';
  /* === QUEUE-CUE-VIEW-V1: queue-mode tak === */
  if (ttbQueue.length > 0) {
    var qStart = ttbQueuePos;
    var qEnd   = Math.min(qStart + ttbVisibleCount, ttbQueue.length);
    var qCols  = qEnd - qStart;
    if (qCols < 1) qCols = 1;
    var tmpl = '2fr';
    for (var k=1; k<qCols; k++) tmpl += ' 1fr';
    grid.style.gridTemplateColumns = tmpl;
    for (var i=qStart; i<qEnd; i++){
      var slotNum = ttbQueue[i];
      var s = ttbSlots.find(function(x){ return x.slot===slotNum; });
      if (!s) continue;
      var btn = buildTriggerButton(s);
      grid.appendChild(btn);
    }
  } else {
  // Bereken welke slots op huidige pagina horen
  var start = ttbPageIndex * ttbVisibleCount;
  var end   = Math.min(start + ttbVisibleCount, ttbButtonOrder.length);
  var cols  = Math.min(ttbVisibleCount, ttbButtonOrder.length - start);
  if (cols < 1) cols = 1;
  grid.style.gridTemplateColumns = 'repeat(' + cols + ', 1fr)';

  for (var i=start; i<end; i++){
    var slotNum = ttbButtonOrder[i];
    var s = ttbSlots.find(function(x){ return x.slot===slotNum; });
    if (!s) continue;
    var btn = buildTriggerButton(s);
    grid.appendChild(btn);
  }
  }"""

# --- Edit C: pagePrev met queue-mode tak ---
OLD_C = """function pagePrev(){
  if (ttbPageIndex > 0) { ttbPageIndex--; renderGrid(); updatePageButtons(); }
}"""

NEW_C = """function pagePrev(){
  /* === QUEUE-CUE-VIEW-V1 === */
  if (ttbQueue.length > 0) {
    if (ttbQueuePos > 0) { ttbQueuePos--; refreshAfterQueueChange(); }
    return;
  }
  if (ttbPageIndex > 0) { ttbPageIndex--; renderGrid(); updatePageButtons(); }
}"""

# --- Edit D: pageNext met queue-mode tak ---
OLD_D = """function pageNext(){
  var maxPage = Math.floor((ttbButtonOrder.length-1) / ttbVisibleCount);
  if (ttbPageIndex < maxPage) { ttbPageIndex++; renderGrid(); updatePageButtons(); }
}"""

NEW_D = """function pageNext(){
  /* === QUEUE-CUE-VIEW-V1 === */
  if (ttbQueue.length > 0) {
    if (ttbQueuePos < ttbQueue.length - 1) { ttbQueuePos++; refreshAfterQueueChange(); }
    return;
  }
  var maxPage = Math.floor((ttbButtonOrder.length-1) / ttbVisibleCount);
  if (ttbPageIndex < maxPage) { ttbPageIndex++; renderGrid(); updatePageButtons(); }
}"""

# --- Edit E: updatePageButtons met queue-mode tak ---
OLD_E = """function updatePageButtons(){
  var prev = document.getElementById('ttb-page-prev');
  var next = document.getElementById('ttb-page-next');
  if (!prev || !next) return;
  var needed = ttbButtonOrder.length > ttbVisibleCount;"""

NEW_E = """function updatePageButtons(){
  var prev = document.getElementById('ttb-page-prev');
  var next = document.getElementById('ttb-page-next');
  if (!prev || !next) return;
  /* === QUEUE-CUE-VIEW-V1 === */
  if (ttbQueue.length > 0) {
    prev.classList.remove('hidden');
    next.classList.remove('hidden');
    prev.classList.toggle('disabled', ttbQueuePos === 0);
    next.classList.toggle('disabled', ttbQueuePos >= ttbQueue.length - 1);
    return;
  }
  var needed = ttbButtonOrder.length > ttbVisibleCount;"""

# --- Edit F: onRelease (na QUEUE-ADVANCE-ON-RELEASE-V1) ---
OLD_F = """    /* QUEUE-ADVANCE-ON-RELEASE-V1: queue-pos++ hier ipv in pointerdown */
    if (ttbQueue.length && ttbQueue[ttbQueuePos]===s.slot) {
      if (ttbQueuePos < ttbQueue.length - 1) ttbQueuePos++;
      updateQueueHighlight();
      renderQueueNav();
      renderQueueDots();
    }"""

NEW_F = """    /* QUEUE-ADVANCE-ON-RELEASE-V1: queue-pos++ hier ipv in pointerdown */
    /* QUEUE-CUE-VIEW-V1: refreshAfterQueueChange ipv 3 losse calls */
    if (ttbQueue.length && ttbQueue[ttbQueuePos]===s.slot) {
      if (ttbQueuePos < ttbQueue.length - 1) ttbQueuePos++;
      refreshAfterQueueChange();
    }"""

# --- Edit G: queue-dot click handler ---
OLD_G = "    dot.onclick = function(){ ttbQueuePos = i; updateQueueHighlight(); renderQueueNav(); renderQueueDots(); };"
NEW_G = "    dot.onclick = function(){ ttbQueuePos = i; refreshAfterQueueChange(); /* QUEUE-CUE-VIEW-V1 */ };"

# --- Edit H: onQueueInput ---
OLD_H = """  ttbQueue = parts;
  ttbQueuePos = 0;
  // Re-render queue-elementen
  renderQueueNav();
  renderQueueDots();
  updateQueueHighlight();
  markDirty();"""

NEW_H = """  ttbQueue = parts;
  ttbQueuePos = 0;
  /* === QUEUE-CUE-VIEW-V1 === */
  refreshAfterQueueChange();
  markDirty();"""

# --- Edit I: toggleQueueTapping (else-branch) ---
OLD_I = """      ttbQueue = ttbQueueTapBuffer.slice();
      ttbQueuePos = 0;
      renderQueueEditor();
      renderQueueNav();
      renderQueueDots();
      updateQueueHighlight();
      markDirty();"""

NEW_I = """      ttbQueue = ttbQueueTapBuffer.slice();
      ttbQueuePos = 0;
      renderQueueEditor();
      /* === QUEUE-CUE-VIEW-V1 === */
      refreshAfterQueueChange();
      markDirty();"""

fh = open(TARGET, "r")
content = getattr(fh, "read")()
getattr(fh, "close")()

if PREREQ not in content:
    sys.exit("ERROR: prereq " + PREREQ + " not present")

if MARKER in content:
    print("SKIP: " + MARKER + " already present")
    sys.exit(0)

edits = [
    ("A_renderTTB",        OLD_A, NEW_A),
    ("B_renderGrid",       OLD_B, NEW_B),
    ("C_pagePrev",         OLD_C, NEW_C),
    ("D_pageNext",         OLD_D, NEW_D),
    ("E_updatePageButtons",OLD_E, NEW_E),
    ("F_onRelease",        OLD_F, NEW_F),
    ("G_dotClick",         OLD_G, NEW_G),
    ("H_onQueueInput",     OLD_H, NEW_H),
    ("I_toggleQueueTap",   OLD_I, NEW_I),
]

for name, old, _ in edits:
    n = content.count(old)
    if n != 1:
        sys.exit("ERROR: anchor " + name + " count=" + str(n) + ", expected 1")

ts = getattr(getattr(datetime, "now")(), "strftime")("%Y%m%d-%H%M%S")
backup = TARGET + ".bak-" + ts
getattr(shutil, "copy2")(TARGET, backup)
print("Backup: " + backup)

new = content
for name, old, replacement in edits:
    new = new.replace(old, replacement, 1)

cnt = new.count(MARKER)
if cnt < 7:
    sys.exit("ERROR: expected >=7 markers, got " + str(cnt))

fh = open(TARGET, "w")
getattr(fh, "write")(new)
getattr(fh, "close")()
print("OK: " + MARKER + " applied (9 edits, " + str(cnt) + " markers)")
