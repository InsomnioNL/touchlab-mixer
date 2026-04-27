#!/usr/bin/env python3
"""Voegt fudiformat in tussen 'r sampler-status-out' en netsend in
beide generators. Maakt UDP-tekst-FUDI uitgaand mogelijk zodat bridge
sampler-status events kan ontvangen.

Patches:
1. generate-slots.py / build_host: TCP netsend → UDP-binary met fudiformat
2. generate-mixer.py / write_main_ttb: UDP-binary → fudiformat ervoor
3. generate-mixer.py / write_main (basic-tak): idem
"""
import sys

MARKER = "FUDIFORMAT-PATCH-V1"

# ─── generate-slots.py ─────────────────────────────────────────────────
SLOTS_PATH = "generate-slots.py"
with open(SLOTS_PATH) as f:
    slots = f.read()

if MARKER in slots:
    print(f"done — {SLOTS_PATH} al gepatcht")
else:
    OLD_SLOTS = '''    r_stat = pd.obj(20, 340, "r sampler-status-out")
    ns = pd.obj(20, 365, "netsend 1")'''
    NEW_SLOTS = '''    r_stat = pd.obj(20, 340, "r sampler-status-out")
    fmt    = pd.obj(20, 365, "fudiformat")  # FUDIFORMAT-PATCH-V1
    ns     = pd.obj(20, 390, "netsend -u -b")'''

    if OLD_SLOTS not in slots:
        print(f"ERROR: kan generate-slots r_stat-block niet vinden", file=sys.stderr)
        sys.exit(1)
    slots = slots.replace(OLD_SLOTS, NEW_SLOTS, 1)

    # Connect-fix: r_stat → fmt → ns en m_connect → ns blijft
    OLD_CON = "    pd.connect(m_connect, 0, ns, 0)    # connect msg → netsend left inlet"
    NEW_CON = """    pd.connect(r_stat, 0, fmt, 0)      # r → fudiformat (FUDIFORMAT-PATCH-V1)
    pd.connect(fmt, 0, ns, 0)          # fudiformat → netsend
    pd.connect(m_connect, 0, ns, 0)    # connect msg → netsend left inlet"""

    if OLD_CON not in slots:
        print(f"ERROR: kan generate-slots connect-block niet vinden", file=sys.stderr)
        sys.exit(1)
    slots = slots.replace(OLD_CON, NEW_CON, 1)

    with open(SLOTS_PATH, "w") as f:
        f.write(slots)
    print(f"✓ Patched {SLOTS_PATH}")

# ─── generate-mixer.py / write_main_ttb ──────────────────────────────
MIXER_PATH = "generate-mixer.py"
with open(MIXER_PATH) as f:
    mixer = f.read()

if MARKER in mixer:
    print(f"done — {MIXER_PATH} al gepatcht")
else:
    # write_main_ttb: regel 487-489
    OLD_TTB = '''    s_stat_r  = add("#X obj 456 142 r sampler-status-out;")
    s_ns      = add("#X obj 456 172 netsend -u -b;")
    m_connect = add(f"#X msg 456 202 connect 127.0.0.1 {s_stat};")
    lines.append(f"#X connect {s_stat_r} 0 {s_ns} 0;")'''
    NEW_TTB = '''    s_stat_r  = add("#X obj 456 142 r sampler-status-out;")
    s_fmt     = add("#X obj 456 167 fudiformat;")  # FUDIFORMAT-PATCH-V1
    s_ns      = add("#X obj 456 192 netsend -u -b;")
    m_connect = add(f"#X msg 456 217 connect 127.0.0.1 {s_stat};")
    lines.append(f"#X connect {s_stat_r} 0 {s_fmt} 0;")
    lines.append(f"#X connect {s_fmt} 0 {s_ns} 0;")'''

    if OLD_TTB not in mixer:
        print(f"ERROR: kan write_main_ttb status-block niet vinden", file=sys.stderr)
        sys.exit(1)
    mixer = mixer.replace(OLD_TTB, NEW_TTB, 1)

    # write_main (basic): regel 359-363
    OLD_BASIC = '''        yt3 = yt2 + 40
        s_stat_r = add(f"#X obj 900 {yt3} r sampler-status-out;")
        s_ns     = add(f"#X obj 900 {yt3+30} netsend -u -b;")
        m_connect = add(f"#X msg 900 {yt3+60} connect 127.0.0.1 {s_stat};")
        lines.append(f"#X connect {s_stat_r} 0 {s_ns} 0;")'''
    NEW_BASIC = '''        yt3 = yt2 + 40
        s_stat_r = add(f"#X obj 900 {yt3} r sampler-status-out;")
        s_fmt    = add(f"#X obj 900 {yt3+25} fudiformat;")  # FUDIFORMAT-PATCH-V1
        s_ns     = add(f"#X obj 900 {yt3+50} netsend -u -b;")
        m_connect = add(f"#X msg 900 {yt3+80} connect 127.0.0.1 {s_stat};")
        lines.append(f"#X connect {s_stat_r} 0 {s_fmt} 0;")
        lines.append(f"#X connect {s_fmt} 0 {s_ns} 0;")'''

    if OLD_BASIC not in mixer:
        print(f"ERROR: kan write_main basic status-block niet vinden", file=sys.stderr)
        sys.exit(1)
    mixer = mixer.replace(OLD_BASIC, NEW_BASIC, 1)

    with open(MIXER_PATH, "w") as f:
        f.write(mixer)
    print(f"✓ Patched {MIXER_PATH}")
