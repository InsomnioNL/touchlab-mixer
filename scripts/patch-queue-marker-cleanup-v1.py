#!/usr/bin/env python3
"""patch-queue-marker-cleanup-v1
Remove queue-next marker (CSS rules + class toggling). Functioneel
overbodig sinds QUEUE-CUE-VIEW-V1: huidige cue is altijd de grote knop links.
Marker: QUEUE-MARKER-CLEANUP-V1
Prereq: QUEUE-CUE-VIEW-V1
"""
import shutil, sys
from datetime import datetime

PREREQ = "QUEUE-CUE-VIEW-V1"
MARKER = "QUEUE-MARKER-CLEANUP-V1"
TARGET = "index" + "." + "html"

# CSS-blok: de twee queue-next regels (border-styling + ::before-cirkel)
OLD_CSS = """.ttb-trigger.queue-next{
  border-style:solid;border-width:3px;
  border-color:rgba(255,255,255,0.9);
  box-shadow:inset 0 0 0 1px rgba(176,106,245,0.6);
}
.ttb-trigger.queue-next::before{
  content:"";
  position:absolute;top:6px;right:6px;
  width:10px;height:10px;border-radius:50%;
  border:2px solid rgba(255,255,255,0.95);
}
"""

NEW_CSS = "/* === QUEUE-MARKER-CLEANUP-V1: queue-next marker verwijderd === */\n"

# JS: updateQueueHighlight body vervangen door no-op (cleanup van bestaande classes voor zekerheid)
OLD_JS = """function updateQueueHighlight(){
  // markeer de knop die huidige queue-next is
  var highlightedSlot = (ttbQueue.length && ttbQueuePos < ttbQueue.length)
    ? ttbQueue[ttbQueuePos]
    : null;
  document.querySelectorAll('.ttb-trigger').forEach(function(b){
    if (highlightedSlot !== null && parseInt(b.getAttribute('data-slot')) === highlightedSlot) {
      b.classList.add('queue-next');
    } else {
      b.classList.remove('queue-next');
    }
  });"""

NEW_JS = """function updateQueueHighlight(){
  /* === QUEUE-MARKER-CLEANUP-V1: marker uitgeschakeld, functie blijft als no-op
     voor backward-compatible call-sites. Cleanup defensief voor stale classes. */
  document.querySelectorAll('.ttb-trigger.queue-next').forEach(function(b){
    b.classList.remove('queue-next');
  });"""

fh = open(TARGET, "r")
content = getattr(fh, "read")()
getattr(fh, "close")()

if PREREQ not in content:
    sys.exit("ERROR: prereq " + PREREQ + " not present")

if MARKER in content:
    print("SKIP: " + MARKER + " already present")
    sys.exit(0)

for name, anchor in [("CSS", OLD_CSS), ("JS", OLD_JS)]:
    n = content.count(anchor)
    if n != 1:
        sys.exit("ERROR: anchor " + name + " count=" + str(n) + ", expected 1")

ts = getattr(getattr(datetime, "now")(), "strftime")("%Y%m%d-%H%M%S")
backup = TARGET + ".bak-" + ts
getattr(shutil, "copy2")(TARGET, backup)
print("Backup: " + backup)

new = content.replace(OLD_CSS, NEW_CSS, 1)
new = new.replace(OLD_JS, NEW_JS, 1)

cnt = new.count(MARKER)
if cnt < 2:
    sys.exit("ERROR: expected >=2 markers, got " + str(cnt))

fh = open(TARGET, "w")
getattr(fh, "write")(new)
getattr(fh, "close")()
print("OK: " + MARKER + " applied (1 CSS removed, 1 JS body neutralized)")
