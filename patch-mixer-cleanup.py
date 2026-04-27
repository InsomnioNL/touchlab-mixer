#!/usr/bin/env python3
"""
Eenmalig patch-script voor generate-mixer.py — voegt een nieuwe functie
write_main_ttb toe (met opgeruimde TTB-layout) en verlegt de TTB-aanroep
in generate() daarheen.

Idempotent (marker-check). Alleen draaien op generate-mixer.py:
    python3 patch-mixer-cleanup.py [path/to/generate-mixer.py]

write_main blijft ongewijzigd — wordt nog gebruikt voor de basic
touchlab-mixer.pd. De if-with_ttb-tak in write_main blijft aanwezig
maar wordt niet meer aangeroepen (dode code; opruimen kan later).

Object-volgorde van write_main_ttb is identiek aan die van
write_main(with_ttb=True), zodat post-regen patch-scripts (master-vol,
rec-path) dezelfde object-indices kunnen blijven verwachten.
"""
import re
import sys
from pathlib import Path

PATH = Path(sys.argv[1] if len(sys.argv) > 1 else "generate-mixer.py")

if not PATH.exists():
    print(f"ERROR: {PATH} niet gevonden", file=sys.stderr)
    sys.exit(1)

content = PATH.read_text()

MARKER = "MIXER-CLEANUP-PATCH-V1"
if MARKER in content:
    print(f"done — {PATH.name} is al gepatcht ({MARKER})")
    sys.exit(0)

# --- Nieuwe functie als raw string. f-strings worden door Python uitgevoerd
# --- ZODRA generate-mixer.py wordt geïmporteerd/gedraaid, niet door dit script.
NEW_FUNCTION = '''
# === MIXER-CLEANUP-PATCH-V1 ===
def write_main_ttb(channels, osc_in_port, sampler_cfg):
    """Schrijf touchlab-mixer-ttb.pd met opgeruimde layout (cleanup-coords).

    Object-volgorde is identiek aan write_main(with_ttb=True), zodat de
    post-regen patch-scripts (master-vol, rec-path) dezelfde indices
    blijven verwachten:
      0..1   loadbang, dsp
      2      netreceive (mixer-cmds, TCP)
      3..5   fx-bus, master-section, vu-sender
      6..13  4x (adc~, throw~)
      14..17 4x ch{N}
      18..25 4x (set-name msg, s mixer-info)
      26..27 channel-count msg + s mixer-info
      28..30 sampler netreceive, fudiparse, route (13 tokens)
      31..43 13 sends voor route-outlets 0..12
      44     print sampler-unknown-fudi (op outlet 13 \xe2\x80\x94 master-vol-patch verschuift naar 14)
      45..47 status return: r sampler-status-out, netsend, connect msg
      48     sampler-router
      49..   sampler-slot-N
    """
    N = len(channels)
    lines = ["#N canvas 0 0 1400 803 12;"]
    n = [0]
    def add(l):
        lines.append(l); i = n[0]; n[0] += 1; return i

    lb  = add("#X obj 20 20 loadbang;")
    dsp = add("#X msg 20 42 \\\\; pd dsp 1;")
    lines.append(f"#X connect {lb} 0 {dsp} 0;")

    add(f"#X obj 20 80 netreceive {osc_in_port};")
    add("#X obj 20 130 fx-bus;")
    add("#X obj 20 160 master-section;")
    add("#X obj 20 190 vu-sender;")

    y = 240
    for ch in channels:
        idx = ch["index"]
        adc = add(f"#X obj 20 {y} adc~ {idx};")
        thr = add(f"#X obj 20 {y+22} throw~ ch{idx};")
        lines.append(f"#X connect {adc} 0 {thr} 0;")
        y += 60

    y2 = 500
    for ch in channels:
        idx = ch["index"]
        add(f"#X obj 20 {y2} ch{idx};")
        y2 += 30

    y3 = 272
    for ch in channels:
        idx = ch["index"]
        name = ch["name"]
        m = add(f"#X msg 268 {y3} set-name {idx} {name};")
        s = add(f"#X obj 268 {y3+20} s mixer-info;")
        lines.append(f"#X connect {lb} 0 {m} 0;")
        lines.append(f"#X connect {m} 0 {s} 0;")
        y3 += 44

    cm = add(f"#X msg 460 91 channel-count {N};")
    cs = add(f"#X obj 460 111 s mixer-info;")
    lines.append(f"#X connect {lb} 0 {cm} 0;")
    lines.append(f"#X connect {cm} 0 {cs} 0;")

    s_port = sampler_cfg.get("fudi_port", 9002)
    s_stat = sampler_cfg.get("status_port", 9003)
    slots  = sampler_cfg.get("slots", 8)

    s_nr = add(f"#X obj 633 27 netreceive -u -b {s_port};")
    s_fp = add("#X obj 633 57 fudiparse;")
    s_rt = add("#X obj 633 87 route sampler-load sampler-play sampler-stop "
               "sampler-vol sampler-speed sampler-rec-start sampler-rec-stop "
               "sampler-trim sampler-trim-end sampler-autotrim "
               "sampler-autotrim-threshold sampler-autotrim-preroll "
               "sampler-router-input;")
    lines.append(f"#X connect {s_nr} 0 {s_fp} 0;")
    lines.append(f"#X connect {s_fp} 0 {s_rt} 0;")

    send_specs = [
        (638, 530, "sampler-load"),
        (664, 503, "sampler-play"),
        (688, 472, "sampler-stop"),
        (715, 446, "sampler-vol"),
        (742, 419, "sampler-speed"),
        (769, 394, "sampler-rec-start"),
        (798, 365, "sampler-rec-stop"),
        (826, 340, "sampler-trim"),
        (855, 316, "sampler-trim-end"),
        (882, 293, "sampler-autotrim"),
        (910, 268, "sampler-autotrim-threshold"),
        (936, 243, "sampler-autotrim-preroll"),
        (965, 218, "sampler-router-input"),
    ]
    for i, (sx, sy, sname) in enumerate(send_specs):
        s_s = add(f"#X obj {sx} {sy} s {sname};")
        lines.append(f"#X connect {s_rt} {i} {s_s} 0;")

    s_unk = add("#X obj 1022 173 print sampler-unknown-fudi;")
    lines.append(f"#X connect {s_rt} {len(send_specs)} {s_unk} 0;")

    s_stat_r  = add("#X obj 456 142 r sampler-status-out;")
    s_ns      = add("#X obj 456 172 netsend -u -b;")
    m_connect = add(f"#X msg 456 202 connect 127.0.0.1 {s_stat};")
    lines.append(f"#X connect {s_stat_r} 0 {s_ns} 0;")
    lines.append(f"#X connect {lb} 0 {m_connect} 0;")
    lines.append(f"#X connect {m_connect} 0 {s_ns} 0;")

    add("#X obj 461 229 sampler-router;")

    slot_specs = [
        (462, 262), (462, 285), (463, 309), (463, 332),
        (463, 355), (463, 379), (463, 404), (463, 428),
    ]
    for i in range(slots):
        if i < len(slot_specs):
            sx, sy = slot_specs[i]
        else:
            sx, sy = 463, 428 + (i - 7) * 23
        add(f"#X obj {sx} {sy} sampler-slot-{i + 1};")

    fname = "touchlab-mixer-ttb.pd"
    with open(fname, "w") as f:
        f.write("\\n".join(lines) + "\\n")
    print(f"  \u2713  {fname}  ({N} kanalen, TCP poort {osc_in_port}, +TTB sampler, cleanup-layout)")

'''

OLD_CALL = "write_main(channels, osc_port, with_ttb=True, sampler_cfg=sampler)"
NEW_CALL = "write_main_ttb(channels, osc_port, sampler)"

if OLD_CALL not in content:
    print(f"ERROR: aanroep '{OLD_CALL}' niet gevonden in {PATH.name}", file=sys.stderr)
    sys.exit(1)

if content.count(OLD_CALL) != 1:
    print(f"ERROR: aanroep komt {content.count(OLD_CALL)}x voor (verwachtte 1)", file=sys.stderr)
    sys.exit(1)

# Insertion point: vlak vóór 'def generate('
m = re.search(r'\n\ndef generate\(', content)
if not m:
    print("ERROR: kan 'def generate(' niet vinden", file=sys.stderr)
    sys.exit(1)

new_content = content[:m.start()] + "\n" + NEW_FUNCTION + content[m.start():]
new_content = new_content.replace(OLD_CALL, NEW_CALL)

backup = PATH.with_suffix(".py.bak-mixer-cleanup")
backup.write_text(content)
PATH.write_text(new_content)

print(f"\u2713 Patched {PATH.name}")
print(f"  Backup:                          {backup.name}")
print(f"  write_main_ttb function added before 'def generate('")
print(f"  Call in generate() updated: write_main \u2192 write_main_ttb")
