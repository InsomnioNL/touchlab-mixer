#!/usr/bin/env python3
"""patch-queue-advance-on-release-v1
Move queue-pos++ from pointerdown to onRelease in TTB trigger handlers.
Aligns UI-flow with planned MIDI-pedal flow (queue-progression on release event).
Marker: QUEUE-ADVANCE-ON-RELEASE-V1
"""
import shutil, sys
from datetime import datetime

MARKER = "QUEUE-ADVANCE-ON-RELEASE-V1"
TARGET = "index" + "." + "html"

OLD_DOWN = """    } else {
      send({type:'samplerPlay', slot:s.slot});
      intendedStates[s.slot] = 'playing';
      startedPlayback = true;
      // queue-advance: alleen als deze slot de queue-volgende is
      if (ttbQueue.length && ttbQueue[ttbQueuePos]===s.slot) {
        if (ttbQueuePos < ttbQueue.length - 1) ttbQueuePos++;
        updateQueueHighlight();
        renderQueueNav();
        renderQueueDots();
      }
    }"""

NEW_DOWN = """    } else {
      send({type:'samplerPlay', slot:s.slot});
      intendedStates[s.slot] = 'playing';
      startedPlayback = true;
      /* QUEUE-ADVANCE-ON-RELEASE-V1: queue-advance verplaatst naar onRelease */
    }"""

OLD_REL = """  function onRelease(){
    if (!startedPlayback) return;
    var held = Date.now() - pressTime;
    if (held >= PRESS_THRESHOLD) {
      send({type:'samplerStop', slot:s.slot});
      intendedStates[s.slot] = 'idle';
    }
    startedPlayback = false;
  }"""

NEW_REL = """  function onRelease(){
    if (!startedPlayback) return;
    var held = Date.now() - pressTime;
    if (held >= PRESS_THRESHOLD) {
      send({type:'samplerStop', slot:s.slot});
      intendedStates[s.slot] = 'idle';
    }
    /* QUEUE-ADVANCE-ON-RELEASE-V1: queue-pos++ hier ipv in pointerdown */
    if (ttbQueue.length && ttbQueue[ttbQueuePos]===s.slot) {
      if (ttbQueuePos < ttbQueue.length - 1) ttbQueuePos++;
      updateQueueHighlight();
      renderQueueNav();
      renderQueueDots();
    }
    startedPlayback = false;
  }"""

fh = open(TARGET, "r")
content = getattr(fh, "read")()
getattr(fh, "close")()

if MARKER in content:
    print("SKIP: " + MARKER + " already present")
    sys.exit(0)

for name, anchor in [("OLD_DOWN", OLD_DOWN), ("OLD_REL", OLD_REL)]:
    n = content.count(anchor)
    if n != 1:
        sys.exit("ERROR: anchor " + name + " count=" + str(n) + ", expected 1")

ts = getattr(getattr(datetime, "now")(), "strftime")("%Y%m%d-%H%M%S")
backup = TARGET + ".bak-" + ts
getattr(shutil, "copy2")(TARGET, backup)
print("Backup: " + backup)

new = content.replace(OLD_DOWN, NEW_DOWN, 1)
new = new.replace(OLD_REL, NEW_REL, 1)

if new.count(MARKER) != 2:
    sys.exit("ERROR: expected 2 markers, got " + str(new.count(MARKER)))

fh = open(TARGET, "w")
getattr(fh, "write")(new)
getattr(fh, "close")()
print("OK: " + MARKER + " applied (1 pointerdown edit + 1 onRelease edit)")
