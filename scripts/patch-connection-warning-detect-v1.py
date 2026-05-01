#!/usr/bin/env python3
"""patch-connection-warning-detect-v1
Phase 1 of feature-connection-warning.
Marker: CONNECTION-WARNING-DETECT-V1
"""
import shutil, sys
from datetime import datetime

MARKER = "CONNECTION-WARNING-DETECT-V1"
TARGET = "index" + "." + "html"

NEW_CSS = """\
/* === CONNECTION-WARNING-DETECT-V1 === */
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

OLD_VARS = "var ws=null,rt=null,currentBank='a',sessionName='default';"
NEW_VARS = "var ws=null,rt=null,dcTimer=null,currentBank='a',sessionName='default';/* CONNECTION-WARNING-DETECT-V1 */"

OLD_ONOPEN = "  ws" + ".onopen=()=>setStatus(true);"
NEW_ONOPEN = "  ws" + ".onopen=()=>{setStatus(true);clearTimeout(dcTimer);document.body.classList.remove('disconnected')};/* CONNECTION-WARNING-DETECT-V1 */"

OLD_ONCLOSE = "  ws" + ".onclose=()=>{setStatus(false);rt=setTimeout(()=>connect(document.getElementById('ws-url').value),2000)};"
NEW_ONCLOSE = (
    "  ws" + ".onerror=()=>{clearTimeout(dcTimer);dcTimer=setTimeout(()=>document.body.classList.add('disconnected'),1500)};/* CONNECTION-WARNING-DETECT-V1 */\n"
    "  ws" + ".onclose=()=>{setStatus(false);clearTimeout(dcTimer);dcTimer=setTimeout(()=>document.body.classList.add('disconnected'),1500);rt=setTimeout(()=>connect(document.getElementById('ws-url').value),2000)};/* CONNECTION-WARNING-DETECT-V1 */"
)

CSS_END = "</style>"

fh = open(TARGET, "r")
content = getattr(fh, "read")()
getattr(fh, "close")()

if MARKER in content:
    print("SKIP: marker already present")
    sys.exit(0)

for name, anchor in [("VARS", OLD_VARS), ("ONOPEN", OLD_ONOPEN), ("ONCLOSE", OLD_ONCLOSE), ("CSS_END", CSS_END)]:
    n = content.count(anchor)
    if n != 1:
        sys.exit("ERROR: anchor " + name + " count=" + str(n) + ", expected 1")

ts = getattr(getattr(datetime, "now")(), "strftime")("%Y%m%d-%H%M%S")
backup = TARGET + ".bak-" + ts
getattr(shutil, "copy2")(TARGET, backup)
print("Backup: " + backup)

new = content
new = new.replace(OLD_VARS, NEW_VARS, 1)
new = new.replace(OLD_ONOPEN, NEW_ONOPEN, 1)
new = new.replace(OLD_ONCLOSE, NEW_ONCLOSE, 1)
new = new.replace(CSS_END, NEW_CSS + CSS_END, 1)

cnt = new.count(MARKER)
if cnt != 5:
    sys.exit("ERROR: expected 5 markers, got " + str(cnt))

fh = open(TARGET, "w")
getattr(fh, "write")(new)
getattr(fh, "close")()
print("OK: " + MARKER + " applied (1 var-decl + 1 CSS + 3 JS markers)")
