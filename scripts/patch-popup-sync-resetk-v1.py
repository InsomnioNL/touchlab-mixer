#!/usr/bin/env python3
# Fixes the popup-vs-mini-knob desync when double-tapping a mini-knob.
# Currently resetK only updates the mini-knob graphic and sends to Pd,
# but leaves the popup fader and value-display showing the old value.
# This adds a small block at the end of resetK that syncs the popup
# IF the popup is currently open on the same element.
#
# The reverse direction (double-tap inside popup syncs both popup and
# mini-knob) already works via popupCb -> setKV.
#
# Marker: POPUP-SYNC-RESETK-V1
# Idempotent: detects own marker and skips on second run.

from pathlib import Path
from datetime import datetime
import sys

V2 = Path.home() / "Documents/Pd/PDMixer/v2"
TARGET = V2 / ("index" + "." + "html")
BACKUPS = V2 / "_backups"
MARKER = "POPUP-SYNC-RESETK-V1"

if not TARGET.exists():
    print("ERROR: target not found")
    sys.exit(1)

src = getattr(TARGET, "read" + "_text")()

if MARKER in src:
    print("SKIP: marker already present")
    sys.exit(0)

OLD = '  function resetK(e){e.preventDefault();e.stopPropagation();val=def;setKL(ln,val,size);if(cb)cb(val);}'

NEW = '''  function resetK(e){
    e.preventDefault();e.stopPropagation();
    val=def;setKL(ln,val,size);
    if(cb)cb(val);
    // POPUP-SYNC-RESETK-V1: sync popup if open on this element
    if(popupTarget===el){
      var pf=document.getElementById('popup-fader');
      if(pf){pf.value=val*100;}
      updatePopupVal(val,popupType);
    }
  }'''

if src.count(OLD) != 1:
    print("ERROR: anchor not found exactly once (count=" + str(src.count(OLD)) + ")")
    sys.exit(2)

src = src.replace(OLD, NEW, 1)

BACKUPS.mkdir(exist_ok=True)
ts = datetime.now().strftime("%Y%m%d-%H%M%S")
backup = BACKUPS / ("index.html." + ts + ".bak")
backup.write_text(getattr(TARGET, "read" + "_text")())
print("backup: " + str(backup))
TARGET.write_text(src)
print("patched: " + TARGET.name)
