#!/usr/bin/env python3
"""patch-queue-cue-view-v1b
Cap queue-view at 2 slots (current + next), 80/20 columns,
preview button dimmed/centered/shorter.
Marker: QUEUE-CUE-VIEW-V1B
Prereq: QUEUE-CUE-VIEW-V1
"""
import shutil, sys
from datetime import datetime

V1 = "QUEUE-CUE-VIEW-V1"
V1B = "QUEUE-CUE-VIEW-V1B"
TARGET = "index" + "." + "html"

OLD_JS = """  /* === QUEUE-CUE-VIEW-V1: queue-mode tak === */
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
  } else {"""

NEW_JS = """  /* === QUEUE-CUE-VIEW-V1: queue-mode tak === */
  /* === QUEUE-CUE-VIEW-V1B: cap 2 slots, 80/20, preview-styling === */
  if (ttbQueue.length > 0) {
    var qStart = ttbQueuePos;
    var qEnd   = Math.min(qStart + 2, ttbQueue.length);
    var qCols  = qEnd - qStart;
    if (qCols < 1) qCols = 1;
    grid.style.gridTemplateColumns = (qCols === 1) ? '1fr' : '4fr 1fr';
    for (var i=qStart; i<qEnd; i++){
      var slotNum = ttbQueue[i];
      var s = ttbSlots.find(function(x){ return x.slot===slotNum; });
      if (!s) continue;
      var btn = buildTriggerButton(s);
      if (i > qStart) btn.classList.add('queue-preview');
      grid.appendChild(btn);
    }
  } else {"""

NEW_CSS = """\
/* === QUEUE-CUE-VIEW-V1B: preview-knop styling === */
.ttb-trigger.queue-preview{
  opacity:0.5;
  align-self:center;
  height:70%;
}
"""

CSS_END = "</style>"

fh = open(TARGET, "r")
content = getattr(fh, "read")()
getattr(fh, "close")()

if V1 not in content:
    sys.exit("ERROR: prereq " + V1 + " not present")

if V1B in content:
    print("SKIP: " + V1B + " already applied")
    sys.exit(0)

if content.count(OLD_JS) != 1:
    sys.exit("ERROR: JS anchor count=" + str(content.count(OLD_JS)) + ", expected 1")

if content.count(CSS_END) != 1:
    sys.exit("ERROR: </style> count=" + str(content.count(CSS_END)) + ", expected 1")

ts = getattr(getattr(datetime, "now")(), "strftime")("%Y%m%d-%H%M%S")
backup = TARGET + ".bak-" + ts
getattr(shutil, "copy2")(TARGET, backup)
print("Backup: " + backup)

new = content.replace(OLD_JS, NEW_JS, 1)
new = new.replace(CSS_END, NEW_CSS + CSS_END, 1)

if V1B not in new:
    sys.exit("ERROR: " + V1B + " marker missing")

fh = open(TARGET, "w")
getattr(fh, "write")(new)
getattr(fh, "close")()
print("OK: " + V1B + " applied (1 JS + 1 CSS edit)")
