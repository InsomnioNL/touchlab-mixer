"""Frontend leest masterVuL en masterVuR uit WebSocket-message
(bridge stuurt ze nu apart). Idempotent via FRONTEND-STEREO-VU-V1.
"""
import sys

PATH = "index.html"
MARKER = "FRONTEND-STEREO-VU-V1"

with open(PATH) as f:
    content = f.read()

if MARKER in content:
    print(f"done — {PATH} al gepatcht ({MARKER})")
    sys.exit(0)

OLD = "if(msg.type==='vu'){masterVu=msg.masterVu||-60;(msg.channels||[]).forEach(u=>{var c=channels.find(x=>x.index===u.index);if(c)c.vu=u.vu});updateVUs();return}"
NEW = "if(msg.type==='vu'){/*FRONTEND-STEREO-VU-V1*/masterVu=msg.masterVu||-60;masterVuL=(typeof msg.masterVuL==='number')?msg.masterVuL:masterVu;masterVuR=(typeof msg.masterVuR==='number')?msg.masterVuR:masterVu;(msg.channels||[]).forEach(u=>{var c=channels.find(x=>x.index===u.index);if(c)c.vu=u.vu});updateVUs();return}"

if OLD not in content:
    print("ERROR: anker niet gevonden", file=sys.stderr)
    sys.exit(1)

content = content.replace(OLD, NEW, 1)

with open(PATH, "w") as f:
    f.write(content)

print(f"✓ Patched {PATH} ({MARKER})")
