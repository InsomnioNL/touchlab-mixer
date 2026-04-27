"""Voegt fudiformat toe in write_vu_sender. Idempotent via marker."""
import sys

PATH = "generate-mixer.py"
MARKER = "VUSENDER-FUDIFORMAT-V1"

with open(PATH) as f:
    content = f.read()

if MARKER in content:
    print(f"done — {PATH} al gepatcht ({MARKER})")
    sys.exit(0)

# In write_vu_sender:
#   ns     = add(f"#X obj 10 80 netsend -u -b {vu_host} {vu_port};")
# moet worden:
#   fmt    = add("#X obj 10 80 fudiformat;")
#   ns     = add(f"#X obj 10 100 netsend -u -b {vu_host} {vu_port};")
# en de connect router → ns moet via fmt.

OLD_NS = '''    bang   = add("#X msg 10 60 bang;")
    ns     = add(f"#X obj 10 80 netsend -u -b {vu_host} {vu_port};")
    router = add("#X obj 200 20 r vu-out;")
    lines.append(f"#X connect {lb} 0 {bang} 0;")
    lines.append(f"#X connect {bang} 0 {metro} 0;")
    lines.append(f"#X connect {router} 0 {ns} 0;")'''

NEW_NS = '''    bang   = add("#X msg 10 60 bang;")
    fmt    = add("#X obj 10 80 fudiformat;")  # VUSENDER-FUDIFORMAT-V1
    ns     = add(f"#X obj 10 100 netsend -u -b {vu_host} {vu_port};")
    router = add("#X obj 200 20 r vu-out;")
    lines.append(f"#X connect {lb} 0 {bang} 0;")
    lines.append(f"#X connect {bang} 0 {metro} 0;")
    lines.append(f"#X connect {router} 0 {fmt} 0;")
    lines.append(f"#X connect {fmt} 0 {ns} 0;")'''

if OLD_NS not in content:
    print("ERROR: anker niet gevonden", file=sys.stderr)
    sys.exit(1)

content = content.replace(OLD_NS, NEW_NS, 1)

with open(PATH, "w") as f:
    f.write(content)

print(f"✓ Patched {PATH}")
print(f"  fudiformat ingevoegd in write_vu_sender ({MARKER})")
