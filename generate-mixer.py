#!/usr/bin/env python3
"""
TouchLab Mixer Generator
Leest session.json en genereert alle benodigde PD patches.

Gebruik:
  python3 generate-mixer.py [session.json]

Start:
  pd -nogui -jack -r 48000 touchlab-mixer.pd
"""
import json, sys, os

def write_channel(idx, name):
    """Genereert ch1.pd, ch2.pd etc. — geen $1, alles hardcoded."""
    content = f"""\
#N canvas 0 0 450 520 12;
#X obj 10 20 catch~ ch{idx};
#X obj 10 60 r ch{idx}-vol;
#X obj 10 80 pack f 10;
#X obj 10 100 line~;
#X obj 10 130 *~;
#X obj 10 170 r ch{idx}-gate;
#X obj 10 190 pack f 5;
#X obj 10 210 line~;
#X obj 10 240 *~;
#X obj 200 170 r ch{idx}-fx;
#X obj 200 190 pack f 10;
#X obj 200 210 line~;
#X obj 200 240 *~;
#X obj 200 270 throw~ fx;
#X obj 10 300 r ch{idx}-pan;
#X obj 10 330 panner;
#X obj 10 370 throw~ masterL;
#X obj 50 370 throw~ masterR;
#X obj 320 240 env~;
#X obj 320 260 - 100;
#X obj 320 280 s ch{idx}-vu;
#X obj 10 420 loadbang;
#X msg 10 440 0.8;
#X obj 10 460 s ch{idx}-vol;
#X msg 90 440 0.5;
#X obj 90 460 s ch{idx}-pan;
#X msg 170 440 1;
#X obj 170 460 s ch{idx}-gate;
#X msg 250 440 0;
#X obj 250 460 s ch{idx}-fx;
#X connect 0 0 4 0;
#X connect 1 0 2 0;
#X connect 2 0 3 0;
#X connect 3 0 4 1;
#X connect 4 0 8 0;
#X connect 5 0 6 0;
#X connect 6 0 7 0;
#X connect 7 0 8 1;
#X connect 8 0 12 0;
#X connect 8 0 15 0;
#X connect 8 0 18 0;
#X connect 9 0 10 0;
#X connect 10 0 11 0;
#X connect 11 0 12 1;
#X connect 12 0 13 0;
#X connect 14 0 15 1;
#X connect 15 0 16 0;
#X connect 15 1 17 0;
#X connect 18 0 19 0;
#X connect 19 0 20 0;
#X connect 21 0 22 0;
#X connect 21 0 24 0;
#X connect 21 0 26 0;
#X connect 21 0 28 0;
#X connect 22 0 23 0;
#X connect 24 0 25 0;
#X connect 26 0 27 0;
#X connect 28 0 29 0;
"""
    fname = f"ch{idx}.pd"
    with open(fname, "w") as f:
        f.write(content)
    print(f"  ✓  {fname}  ({name})")


def write_fx_bus():
    content = """\
#N canvas 0 0 300 340 12;
#X obj 10 20 catch~ fx;
#X obj 10 60 rev2~ 100 85 3000 20;
#X obj 10 110 r fxReturn;
#X obj 10 130 pack f 10;
#X obj 10 150 line~;
#X obj 10 180 *~;
#X obj 60 180 *~;
#X obj 10 220 throw~ masterL;
#X obj 60 220 throw~ masterR;
#X obj 10 270 loadbang;
#X msg 10 290 0;
#X obj 10 310 s fxReturn;
#X connect 0 0 1 0;
#X connect 1 0 5 0;
#X connect 1 1 6 0;
#X connect 2 0 3 0;
#X connect 3 0 4 0;
#X connect 4 0 5 1;
#X connect 4 0 6 1;
#X connect 5 0 7 0;
#X connect 6 0 8 0;
#X connect 9 0 10 0;
#X connect 10 0 11 0;
"""
    with open("fx-bus.pd", "w") as f:
        f.write(content)
    print("  ✓  fx-bus.pd")


def write_master():
    content = """\
#N canvas 0 0 400 400 12;
#X obj 10 20 catch~ masterL;
#X obj 80 20 catch~ masterR;
#X obj 10 60 r masterVol;
#X obj 10 80 pack f 10;
#X obj 10 100 line~;
#X obj 10 130 *~;
#X obj 80 130 *~;
#X obj 10 170 env~;
#X obj 10 190 - 100;
#X obj 10 210 s masterVu;
#X obj 10 240 dac~ 1 2;
#X obj 220 60 r hpVol;
#X obj 220 80 pack f 10;
#X obj 220 100 line~;
#X obj 220 130 *~;
#X obj 290 130 *~;
#X obj 220 240 dac~ 3 4;
#X obj 10 310 loadbang;
#X msg 10 330 0.8;
#X obj 10 350 s masterVol;
#X msg 90 330 0.8;
#X obj 90 350 s hpVol;
#X connect 0 0 5 0;
#X connect 1 0 6 0;
#X connect 2 0 3 0;
#X connect 3 0 4 0;
#X connect 4 0 5 1;
#X connect 4 0 6 1;
#X connect 5 0 7 0;
#X connect 5 0 10 0;
#X connect 5 0 14 0;
#X connect 6 0 7 1;
#X connect 6 0 10 1;
#X connect 6 0 15 0;
#X connect 7 0 8 0;
#X connect 8 0 9 0;
#X connect 11 0 12 0;
#X connect 12 0 13 0;
#X connect 13 0 14 1;
#X connect 13 0 15 1;
#X connect 14 0 16 0;
#X connect 15 0 16 1;
#X connect 17 0 18 0;
#X connect 17 0 20 0;
#X connect 18 0 19 0;
#X connect 20 0 21 0;
"""
    with open("master-section.pd", "w") as f:
        f.write(content)
    print("  ✓  master-section.pd")


def write_vu_sender(channels, vu_host, vu_port, vu_ms):
    lines = ["#N canvas 0 0 500 600 12;"]
    n = [0]
    def add(l):
        lines.append(l); i = n[0]; n[0]+=1; return i

    metro  = add(f"#X obj 10 20 metro {vu_ms};")
    lb     = add("#X obj 10 40 loadbang;")
    bang   = add("#X msg 10 60 bang;")
    ns     = add(f"#X obj 10 80 netsend -u -b {vu_host} {vu_port};")
    router = add("#X obj 200 20 r vu-out;")
    lines.append(f"#X connect {lb} 0 {bang} 0;")
    lines.append(f"#X connect {bang} 0 {metro} 0;")
    lines.append(f"#X connect {router} 0 {ns} 0;")

    y = 120
    for ch in channels:
        idx = ch["index"]
        r  = add(f"#X obj 10 {y} r ch{idx}-vu;")
        p  = add(f"#X obj 10 {y+20} list prepend vu {idx};")
        s  = add(f"#X obj 10 {y+40} s vu-out;")
        lines.append(f"#X connect {r} 0 {p} 0;")
        lines.append(f"#X connect {p} 0 {s} 0;")
        y += 80

    rm = add("#X obj 300 120 r masterVu;")
    pm = add("#X obj 300 140 list prepend vu master;")
    sm = add("#X obj 300 160 s vu-out;")
    lines.append(f"#X connect {rm} 0 {pm} 0;")
    lines.append(f"#X connect {pm} 0 {sm} 0;")

    with open("vu-sender.pd", "w") as f:
        f.write("\n".join(lines) + "\n")
    print("  ✓  vu-sender.pd")


def write_main(channels, osc_in_port):
    N = len(channels)
    lines = ["#N canvas 0 0 900 800 12;"]
    n = [0]
    def add(l):
        lines.append(l); i = n[0]; n[0]+=1; return i

    # DSP aanzetten
    lb  = add("#X obj 20 20 loadbang;")
    dsp = add("#X msg 20 42 \\; pd dsp 1;")
    lines.append(f"#X connect {lb} 0 {dsp} 0;")

    # OSC ontvangst (TCP — PD luistert als server)
    nr  = add(f"#X obj 20 80 netreceive {osc_in_port};")

    # Subpatches (als abstracties, zonder 'pd' prefix)
    fxb = add("#X obj 20 130 fx-bus;")
    ms  = add("#X obj 20 160 master-section;")
    vus = add("#X obj 20 190 vu-sender;")

    # JACK inputs: adc~ N → throw~ chN
    y = 240
    for ch in channels:
        idx = ch["index"]
        adc = add(f"#X obj 20 {y} adc~ {idx};")
        thr = add(f"#X obj 20 {y+22} throw~ ch{idx};")
        lines.append(f"#X connect {adc} 0 {thr} 0;")
        y += 60

    # Kanaalpatches (ch1, ch2, ... — aparte bestanden per kanaal)
    y2 = 240 + N * 60 + 20
    for ch in channels:
        idx   = ch["index"]
        strip = add(f"#X obj 20 {y2} ch{idx};")
        y2 += 30

    # Kanaalnamen bij opstart → mixer-info
    y3 = y2 + 20
    for ch in channels:
        idx  = ch["index"]
        name = ch["name"]
        m    = add(f"#X msg 400 {y3} set-name {idx} {name};")
        s    = add(f"#X obj 400 {y3+20} s mixer-info;")
        lines.append(f"#X connect {lb} 0 {m} 0;")
        lines.append(f"#X connect {m} 0 {s} 0;")
        y3 += 44

    cm = add(f"#X msg 650 240 channel-count {N};")
    cs = add(f"#X obj 650 260 s mixer-info;")
    lines.append(f"#X connect {lb} 0 {cm} 0;")
    lines.append(f"#X connect {cm} 0 {cs} 0;")

    with open("touchlab-mixer.pd", "w") as f:
        f.write("\n".join(lines) + "\n")
    print(f"  ✓  touchlab-mixer.pd  ({N} kanalen, TCP poort {osc_in_port})")


def generate(config_path):
    with open(config_path) as f:
        cfg = json.load(f)

    channels   = cfg["channels"]
    osc_port   = cfg.get("osc_receive_port", 9000)
    vu_host    = cfg.get("vu_send_host", "127.0.0.1")
    vu_port    = cfg.get("vu_send_port", 9001)
    vu_ms      = cfg.get("vu_interval_ms", 50)

    print(f"TouchLab Mixer — {len(channels)} kanalen")
    print("─" * 40)

    for ch in channels:
        write_channel(ch["index"], ch["name"])

    write_fx_bus()
    write_master()
    write_vu_sender(channels, vu_host, vu_port, vu_ms)
    write_main(channels, osc_port)

    print()
    print("Gegenereerde bestanden:")
    for ch in channels:
        print(f"  ch{ch['index']}.pd")
    for f in ["fx-bus.pd","master-section.pd","vu-sender.pd","touchlab-mixer.pd"]:
        print(f"  {f}")
    print()
    print("Start:")
    print("  pd -nogui -jack -r 48000 touchlab-mixer.pd")
    print()
    print("OSC adressen (via bridge):")
    for ch in channels:
        i = ch["index"]
        print(f"  ch{i}-vol / ch{i}-pan / ch{i}-gate / ch{i}-fx   ({ch['name']})")
    print("  masterVol / hpVol / fxReturn")

if __name__ == "__main__":
    cfg = sys.argv[1] if len(sys.argv) > 1 else "session.json"
    if not os.path.exists(cfg):
        print(f"Fout: {cfg} niet gevonden.")
        sys.exit(1)
    generate(cfg)
