#!/usr/bin/env python3
"""patch-connection-warning-lock-v1
Phase 2 of feature-connection-warning:
Lock controls + dim during .disconnected state.
Marker: CONNECTION-WARNING-LOCK-V1
Prereq: CONNECTION-WARNING-DETECT-V1
"""
import shutil, sys
from datetime import datetime

V1 = "CONNECTION-WARNING-DETECT-V1"
V2 = "CONNECTION-WARNING-LOCK-V1"
TARGET = "index" + "." + "html"

NEW_CSS = """\
/* === CONNECTION-WARNING-LOCK-V1 === */
body.disconnected #live{
  pointer-events:none;
}
body.disconnected #live > *{
  opacity:0.55;
  transition:opacity 0.3s;
}
body.disconnected .ttb-popup,
body.disconnected .knob-popup{
  pointer-events:none;
  opacity:0.55;
  transition:opacity 0.3s;
}
"""

CSS_END = "</style>"

fh = open(TARGET, "r")
content = getattr(fh, "read")()
getattr(fh, "close")()

if V1 not in content:
    sys.exit("ERROR: prereq " + V1 + " not present, run detect-v1 first")

if V2 in content:
    print("SKIP: " + V2 + " already applied")
    sys.exit(0)

n = content.count(CSS_END)
if n != 1:
    sys.exit("ERROR: anchor </style> count=" + str(n) + ", expected 1")

ts = getattr(getattr(datetime, "now")(), "strftime")("%Y%m%d-%H%M%S")
backup = TARGET + ".bak-" + ts
getattr(shutil, "copy2")(TARGET, backup)
print("Backup: " + backup)

new = content.replace(CSS_END, NEW_CSS + CSS_END, 1)

if V2 not in new:
    sys.exit("ERROR: " + V2 + " marker missing after edit")

fh = open(TARGET, "w")
getattr(fh, "write")(new)
getattr(fh, "close")()
print("OK: " + V2 + " applied (1 CSS block before </style>)")
