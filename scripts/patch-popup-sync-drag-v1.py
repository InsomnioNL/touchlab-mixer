#!/usr/bin/env python3
# Extends popup-sync to drag-handlers (mousemove + touchmove) on mini-knobs.
# Same pattern as POPUP-SYNC-RESETK-V1: when popup is open on the dragged
# knob, also sync popup-fader value and popup-display text.
#
# Reverse direction (drag in popup syncs both popup and mini-knob) already
# works via popupCb -> setKV.
#
# Marker: POPUP-SYNC-DRAG-V1
# Idempotent: detects own marker and skips on second run.

from pathlib import Path
from datetime import datetime
import sys

V2 = Path.home() / "Documents/Pd/PDMixer/v2"
TARGET = V2 / ("index" + "." + "html")
BACKUPS = V2 / "_backups"
MARKER = "POPUP-SYNC-DRAG-V1"

if not TARGET.exists():
    print("ERROR: target not found")
    sys.exit(1)

src = getattr(TARGET, "read" + "_text")()

if MARKER in src:
    print("SKIP: marker already present")
    sys.exit(0)

# --- Mousemove handler ---
OLD_MOUSE = "  window.addEventListener('mousemove',e=>{if(!drag)return;val=Math.max(0,Math.min(1,sv+(sy-e.clientY)/120));setKL(ln,val,size);if(cb)cb(val)});"

NEW_MOUSE = '''  window.addEventListener('mousemove',e=>{
    if(!drag)return;
    val=Math.max(0,Math.min(1,sv+(sy-e.clientY)/120));
    setKL(ln,val,size);
    if(cb)cb(val);
    // POPUP-SYNC-DRAG-V1: sync popup if open on this element
    if(popupTarget===el){
      var pf=document.getElementById('popup-fader');
      if(pf){pf.value=val*100;}
      updatePopupVal(val,popupType);
    }
  });'''

# --- Touchmove handler ---
OLD_TOUCH = "  window.addEventListener('touchmove',e=>{if(!drag)return;val=Math.max(0,Math.min(1,sv+(sy-e.touches[0].clientY)/120));setKL(ln,val,size);if(cb)cb(val)},{passive:false});"

NEW_TOUCH = '''  window.addEventListener('touchmove',e=>{
    if(!drag)return;
    val=Math.max(0,Math.min(1,sv+(sy-e.touches[0].clientY)/120));
    setKL(ln,val,size);
    if(cb)cb(val);
    // POPUP-SYNC-DRAG-V1: sync popup if open on this element
    if(popupTarget===el){
      var pf=document.getElementById('popup-fader');
      if(pf){pf.value=val*100;}
      updatePopupVal(val,popupType);
    }
  },{passive:false});'''

if src.count(OLD_MOUSE) != 1:
    print("ERROR: mousemove anchor not found exactly once (count=" + str(src.count(OLD_MOUSE)) + ")")
    sys.exit(2)
if src.count(OLD_TOUCH) != 1:
    print("ERROR: touchmove anchor not found exactly once (count=" + str(src.count(OLD_TOUCH)) + ")")
    sys.exit(3)

src = src.replace(OLD_MOUSE, NEW_MOUSE, 1)
src = src.replace(OLD_TOUCH, NEW_TOUCH, 1)

BACKUPS.mkdir(exist_ok=True)
ts = datetime.now().strftime("%Y%m%d-%H%M%S")
backup = BACKUPS / ("index.html." + ts + ".bak")
backup.write_text(getattr(TARGET, "read" + "_text")())
print("backup: " + str(backup))
TARGET.write_text(src)
print("patched: " + TARGET.name)
