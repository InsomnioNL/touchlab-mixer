#!/usr/bin/env python3
"""patch-queue-input-digits-v1
Queue-input parser: each digit = one slot (1-8), all non-digits ignored.
Replaces previous comma-separated parser.
Marker: QUEUE-INPUT-DIGITS-V1
"""
import shutil, sys
from datetime import datetime

MARKER = "QUEUE-INPUT-DIGITS-V1"
TARGET = "index" + "." + "html"

OLD = """  var input = document.getElementById('ttb-queue-input');
  var raw = input.value;
  // Parse: getallen gescheiden door komma's
  var parts = raw.split(',').map(function(p){return parseInt(p.trim());}).filter(function(n){return !isNaN(n) && n>=1 && n<=8;});"""

NEW = """  var input = document.getElementById('ttb-queue-input');
  var raw = input.value;
  /* === QUEUE-INPUT-DIGITS-V1: elk cijfer = 1 slot, non-digits genegeerd === */
  var parts = raw.split('').map(function(c){return parseInt(c);}).filter(function(n){return !isNaN(n) && n>=1 && n<=8;});"""

fh = open(TARGET, "r")
content = getattr(fh, "read")()
getattr(fh, "close")()

if MARKER in content:
    print("SKIP: " + MARKER + " already present")
    sys.exit(0)

n = content.count(OLD)
if n != 1:
    sys.exit("ERROR: anchor count=" + str(n) + ", expected 1")

ts = getattr(getattr(datetime, "now")(), "strftime")("%Y%m%d-%H%M%S")
backup = TARGET + ".bak-" + ts
getattr(shutil, "copy2")(TARGET, backup)
print("Backup: " + backup)

new = content.replace(OLD, NEW, 1)

if MARKER not in new:
    sys.exit("ERROR: marker missing after edit")

fh = open(TARGET, "w")
getattr(fh, "write")(new)
getattr(fh, "close")()
print("OK: " + MARKER + " applied")
