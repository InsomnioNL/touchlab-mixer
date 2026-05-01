#!/usr/bin/env python3
"""patch-connection-warning-detect-v1b
Intensifies pulse for fase 1: border-alpha animates, shadow 1->36px,
opacity 0.05->0.95, duration 1.2s.
Prereq: V1 applied.
Marker: CONNECTION-WARNING-DETECT-V1B
"""
import shutil, sys
from datetime import datetime

V1 = "CONNECTION-WARNING-DETECT-V1"
V1B = "CONNECTION-WARNING-DETECT-V1B"
TARGET = "index" + "." + "html"

OLD = """/* === CONNECTION-WARNING-DETECT-V1 === */
body.disconnected .view{
  border:2px solid var(--red);
  box-shadow:0 0 14px rgba(224,82,82,0.45);
  animation:connection-warning-pulse 2.0s ease-in-out infinite;
}
@keyframes connection-warning-pulse{
  0%,100%{box-shadow:0 0 10px rgba(224,82,82,0.30);}
  50%{box-shadow:0 0 22px rgba(224,82,82,0.65);}
}
"""

NEW = """/* === CONNECTION-WARNING-DETECT-V1 === */
/* === CONNECTION-WARNING-DETECT-V1B === */
body.disconnected .view{
  border-style:solid;
  border-width:2px;
  animation:connection-warning-pulse 1.2s ease-in-out infinite;
}
@keyframes connection-warning-pulse{
  0%,100%{
    border-color:rgba(224,82,82,0.10);
    box-shadow:0 0 1px rgba(224,82,82,0.05);
  }
  50%{
    border-color:rgba(224,82,82,1.0);
    box-shadow:0 0 36px rgba(224,82,82,0.95);
  }
}
"""

fh = open(TARGET, "r")
content = getattr(fh, "read")()
getattr(fh, "close")()

if V1 not in content:
    sys.exit("ERROR: prereq V1 not present")

if V1B in content:
    print("SKIP: V1B already applied")
    sys.exit(0)

n = content.count(OLD)
if n != 1:
    sys.exit("ERROR: V1 CSS block count=" + str(n) + ", expected 1")

ts = getattr(getattr(datetime, "now")(), "strftime")("%Y%m%d-%H%M%S")
backup = TARGET + ".bak-" + ts
getattr(shutil, "copy2")(TARGET, backup)
print("Backup: " + backup)

new = content.replace(OLD, NEW, 1)

if V1B not in new:
    sys.exit("ERROR: V1B marker missing")

fh = open(TARGET, "w")
getattr(fh, "write")(new)
getattr(fh, "close")()
print("OK: " + V1B + " applied")
