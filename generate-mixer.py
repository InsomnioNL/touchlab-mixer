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

def write_channel(idx, name, with_sampler_tap=False):
    """Genereert ch1.pd, ch2.pd etc. — geen $1, alles hardcoded.

    Als with_sampler_tap=True, voegt send~ sampler-src-chN toe (post-fader,
    post-gate, pre-fx, pre-pan) voor de sampler-module.
    """
    # Base pattern: 30 objects (indices 0-29). Sampler tap wordt object 30.
    sampler_tap_line = ""
    sampler_tap_connect = ""
    if with_sampler_tap:
        sampler_tap_line = f"#X obj 400 240 send~ sampler-src-ch{idx};\n"
        # Object 30 (the send~) gets signal from object 8 (post-gate *~)
        sampler_tap_connect = "#X connect 8 0 30 0;\n"

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
{sampler_tap_line}#X connect 0 0 4 0;
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
{sampler_tap_connect}"""
    fname = f"ch{idx}.pd"
    with open(fname, "w") as f:
        f.write(content)
    tag = " +sampler-tap" if with_sampler_tap else ""
    print(f"  ✓  {fname}  ({name}){tag}")


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


def write_master(with_sampler_tap=False):
    """
    Master section.

    VU fix: env~ has only one signal inlet, but the old version tried to
    connect both L and R to it (resulting in a 'connection failed' warning
    at load and an L-only VU in practice).  Here we sum L+R via [+~] and
    halve via [*~ 0.5] before env~, giving a proper stereo-sum VU that
    reads 0 dB for mono content and averages for uncorrelated stereo.

    Object map:
        0-21 : base (catch~, *~, env~, dac~, hp chain, loadbang defaults)
        22-23: VU stereo-sum (+~  and  *~ 0.5) — always present
        24-27: sampler-tap chain (0.5×L, 0.5×R, +~, send~) — if enabled
    """
    # VU stereo-sum — always added, replaces the buggy direct-to-env~ wiring.
    vu_sum_lines = (
        "#X obj 130 150 +~;\n"          # obj 22: L + R
        "#X obj 130 170 *~ 0.5;\n"      # obj 23: halve so mono = 0 dB VU
    )
    vu_sum_connects = (
        "#X connect 5 0 22 0;\n"        # *~ L → sum inlet 0
        "#X connect 6 0 22 1;\n"        # *~ R → sum inlet 1
        "#X connect 22 0 23 0;\n"       # sum → halve
        "#X connect 23 0 7 0;\n"        # halve → env~
    )

    sampler_tap_lines = ""
    sampler_tap_connects = ""
    if with_sampler_tap:
        # Sampler tap now lives at indices 24-27 (VU-sum took 22-23).
        sampler_tap_lines = (
            "#X obj 120 200 *~ 0.5;\n"          # obj 24
            "#X obj 190 200 *~ 0.5;\n"          # obj 25
            "#X obj 120 230 +~;\n"              # obj 26
            "#X obj 120 260 send~ sampler-src-master;\n"  # obj 27
        )
        sampler_tap_connects = (
            "#X connect 5 0 24 0;\n"
            "#X connect 6 0 25 0;\n"
            "#X connect 24 0 26 0;\n"
            "#X connect 25 0 26 1;\n"
            "#X connect 26 0 27 0;\n"
        )

    # NOTE: the old buggy connects "#X connect 5 0 7 0" and
    # "#X connect 6 0 7 1" are removed — env~ now gets its input from
    # the VU-sum chain (obj 23).
    content = f"""\
#N canvas 0 0 400 400 12;
#X obj 10 20 catch~ masterL;
#X obj 80 20 catch~ masterR;
#X obj 10 60 r masterVol;
#X obj 10 80 pack f 10;
#X obj 10 100 line~;
#X obj 10 130 *~;
#X obj 80 130 *~;
#X obj 10 190 env~;
#X obj 10 210 - 100;
#X obj 10 230 s masterVu;
#X obj 10 270 dac~ 1 2;
#X obj 220 60 r hpVol;
#X obj 220 80 pack f 10;
#X obj 220 100 line~;
#X obj 220 130 *~;
#X obj 290 130 *~;
#X obj 220 270 dac~ 3 4;
#X obj 10 340 loadbang;
#X msg 10 360 0.8;
#X obj 10 380 s masterVol;
#X msg 90 360 0.8;
#X obj 90 380 s hpVol;
{vu_sum_lines}{sampler_tap_lines}#X connect 0 0 5 0;
#X connect 1 0 6 0;
#X connect 2 0 3 0;
#X connect 3 0 4 0;
#X connect 4 0 5 1;
#X connect 4 0 6 1;
#X connect 5 0 10 0;
#X connect 5 0 14 0;
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
{vu_sum_connects}{sampler_tap_connects}"""
    with open("master-section.pd", "w") as f:
        f.write(content)
    tag = " +sampler-tap" if with_sampler_tap else ""
    print(f"  ✓  master-section.pd  (stereo-sum VU{tag})")


def write_vu_sender(channels, vu_host, vu_port, vu_ms):
    lines = ["#N canvas 0 0 500 600 12;"]
    n = [0]
    def add(l):
        lines.append(l); i = n[0]; n[0]+=1; return i

    metro  = add(f"#X obj 10 20 metro {vu_ms};")
    lb     = add("#X obj 10 40 loadbang;")
    bang   = add("#X msg 10 60 bang;")
    fmt    = add("#X obj 10 80 fudiformat;")  # VUSENDER-FUDIFORMAT-V1
    ns     = add("#X obj 10 100 netsend -u -b;")  # VUSENDER-CONNECT-MSG-V1
    cm     = add(f"#X msg 10 130 connect {vu_host} {vu_port};")
    router = add("#X obj 200 20 r vu-out;")
    lines.append(f"#X connect {lb} 0 {bang} 0;")
    lines.append(f"#X connect {bang} 0 {metro} 0;")
    lines.append(f"#X connect {router} 0 {fmt} 0;")
    lines.append(f"#X connect {fmt} 0 {ns} 0;")
    lines.append(f"#X connect {lb} 0 {cm} 0;")
    lines.append(f"#X connect {cm} 0 {ns} 0;")

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


def write_main(channels, osc_in_port, with_ttb=False, sampler_cfg=None):
    """Schrijf touchlab-mixer.pd of touchlab-mixer-ttb.pd.

    Als with_ttb=True: voegt sampler-router, sampler-slots, en een tweede
    FUDI-input (UDP 9002) toe voor sampler-commando's.
    """
    N = len(channels)
    suffix = "-ttb" if with_ttb else ""
    lines = ["#N canvas 0 0 1400 900 12;"]
    n = [0]
    def add(l):
        lines.append(l); i = n[0]; n[0]+=1; return i

    # DSP aanzetten
    lb  = add("#X obj 20 20 loadbang;")
    dsp = add("#X msg 20 42 \\; pd dsp 1;")
    lines.append(f"#X connect {lb} 0 {dsp} 0;")

    # OSC ontvangst voor mixer commands (TCP op 9000)
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

    # ------------------------------------------------------------------
    # TTB: sampler-router, sampler slots, sampler FUDI input, status out
    # ------------------------------------------------------------------
    if with_ttb and sampler_cfg:
        slots   = sampler_cfg.get("slots", 8)
        s_port  = sampler_cfg.get("fudi_port", 9002)
        s_stat  = sampler_cfg.get("status_port", 9003)

        yt = 80
        # Sampler UDP netreceive
        s_nr  = add(f"#X obj 900 {yt} netreceive -u -b {s_port};")
        s_fp  = add(f"#X obj 900 {yt+30} fudiparse;")
        s_rt  = add(f"#X obj 900 {yt+60} route sampler-load sampler-play sampler-stop sampler-vol sampler-speed sampler-rec-start sampler-rec-stop sampler-trim sampler-trim-end sampler-autotrim sampler-autotrim-threshold sampler-autotrim-preroll sampler-router-input;")
        lines.append(f"#X connect {s_nr} 0 {s_fp} 0;")
        lines.append(f"#X connect {s_fp} 0 {s_rt} 0;")

        # 13 sends for each route outlet
        send_names = [
            "sampler-load", "sampler-play", "sampler-stop",
            "sampler-vol", "sampler-speed", "sampler-rec-start",
            "sampler-rec-stop", "sampler-trim", "sampler-trim-end",
            "sampler-autotrim", "sampler-autotrim-threshold",
            "sampler-autotrim-preroll", "sampler-router-input",
        ]
        for i, sname in enumerate(send_names):
            sx = 900 + (i % 7) * 100
            sy = yt + 100 + (i // 7) * 30
            s_s = add(f"#X obj {sx} {sy} s {sname};")
            lines.append(f"#X connect {s_rt} {i} {s_s} 0;")

        # unknown-catch
        yt2 = yt + 180
        s_unk = add(f"#X obj 900 {yt2} print sampler-unknown-fudi;")
        lines.append(f"#X connect {s_rt} {len(send_names)} {s_unk} 0;")

        # Status return: UDP out
        yt3 = yt2 + 40
        s_stat_r = add(f"#X obj 900 {yt3} r sampler-status-out;")
        s_fmt    = add(f"#X obj 900 {yt3+25} fudiformat;")  # FUDIFORMAT-PATCH-V1
        s_ns     = add(f"#X obj 900 {yt3+50} netsend -u -b;")
        m_connect = add(f"#X msg 900 {yt3+80} connect 127.0.0.1 {s_stat};")
        lines.append(f"#X connect {s_stat_r} 0 {s_fmt} 0;")
        lines.append(f"#X connect {s_fmt} 0 {s_ns} 0;")
        lines.append(f"#X connect {lb} 0 {m_connect} 0;")
        lines.append(f"#X connect {m_connect} 0 {s_ns} 0;")

        # Router abstraction
        yt4 = yt3 + 120
        s_router = add(f"#X obj 900 {yt4} sampler-router;")

        # Slot abstractions (2 cols x 4 rows)
        for i in range(slots):
            col = i // 4
            row = i % 4
            sx = 1100 + col * 150
            sy = 80 + row * 50
            add(f"#X obj {sx} {sy} sampler-slot-{i + 1};")

    fname = f"touchlab-mixer{suffix}.pd"
    with open(fname, "w") as f:
        f.write("\n".join(lines) + "\n")
    print(f"  ✓  {fname}  ({N} kanalen, TCP poort {osc_in_port}"
          f"{', +TTB sampler' if with_ttb else ''})")


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
      44     print sampler-unknown-fudi (op outlet 13 â master-vol-patch verschuift naar 14)
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
    dsp = add("#X msg 20 42 \\; pd dsp 1;")
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
    s_fmt     = add("#X obj 456 167 fudiformat;")  # FUDIFORMAT-PATCH-V1
    s_ns      = add("#X obj 456 192 netsend -u -b;")
    m_connect = add(f"#X msg 456 217 connect 127.0.0.1 {s_stat};")
    lines.append(f"#X connect {s_stat_r} 0 {s_fmt} 0;")
    lines.append(f"#X connect {s_fmt} 0 {s_ns} 0;")
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
        f.write("\n".join(lines) + "\n")
    print(f"  ✓  {fname}  ({N} kanalen, TCP poort {osc_in_port}, +TTB sampler, cleanup-layout)")



def generate(config_path):
    with open(config_path) as f:
        cfg = json.load(f)

    channels   = cfg["channels"]
    osc_port   = cfg.get("osc_receive_port", 9000)
    vu_host    = cfg.get("vu_send_host", "127.0.0.1")
    vu_port    = cfg.get("vu_send_port", 9001)
    vu_ms      = cfg.get("vu_interval_ms", 50)
    sampler    = cfg.get("sampler", {})
    ttb_enable = sampler.get("enabled", False)

    print(f"TouchLab Mixer — {len(channels)} kanalen"
          f"{' + TTB sampler' if ttb_enable else ''}")
    print("─" * 40)

    # Channels — with or without sampler tap
    for ch in channels:
        write_channel(ch["index"], ch["name"], with_sampler_tap=ttb_enable)

    write_fx_bus()
    write_master(with_sampler_tap=ttb_enable)
    write_vu_sender(channels, vu_host, vu_port, vu_ms)

    # Always write basic mixer
    write_main(channels, osc_port, with_ttb=False)
    # Additionally write ttb variant if enabled
    if ttb_enable:
        write_main_ttb(channels, osc_port, sampler)

    print()
    print("Gegenereerde bestanden:")
    for ch in channels:
        print(f"  ch{ch['index']}.pd")
    base_files = ["fx-bus.pd", "master-section.pd", "vu-sender.pd",
                  "touchlab-mixer.pd"]
    if ttb_enable:
        base_files.append("touchlab-mixer-ttb.pd")
    for f in base_files:
        print(f"  {f}")
    print()
    print("Start:")
    print("  pd -nogui -jack -r 48000 touchlab-mixer.pd          # basic")
    if ttb_enable:
        print("  pd -nogui -jack -r 48000 touchlab-mixer-ttb.pd      # met TTB")
    print()
    print("OSC adressen (via bridge):")
    for ch in channels:
        i = ch["index"]
        print(f"  ch{i}-vol / ch{i}-pan / ch{i}-gate / ch{i}-fx   ({ch['name']})")
    print("  masterVol / hpVol / fxReturn")
    if ttb_enable:
        print()
        print("Sampler (TTB) FUDI:")
        print(f"  UDP {sampler.get('fudi_port', 9002)} in, UDP {sampler.get('status_port', 9003)} out")

if __name__ == "__main__":
    cfg = sys.argv[1] if len(sys.argv) > 1 else "session.json"
    if not os.path.exists(cfg):
        print(f"Fout: {cfg} niet gevonden.")
        sys.exit(1)
    generate(cfg)
