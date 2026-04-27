"""Stereo VU in master-section: vervangt mono masterVu (via stereo-sum)
door twee aparte masterVuL en masterVuR (per env~ chain).

Object-numbering:
  0-9  : ongewijzigd (catch~, *~, env~, -100, s masterVuL [was masterVu], dac~ 1 2)
  10-21: ongewijzigd (hpVol-chain + loadbang + dac~ 3 4)
  22-24: NIEUW: env~ R, -100, s masterVuR
  25-28: sampler-tap als actief (was 24-27)

Idempotent via marker STEREO-VU-V1.
"""
import sys, re

PATH = "generate-mixer.py"
MARKER = "STEREO-VU-V1"

with open(PATH) as f:
    content = f.read()

if MARKER in content:
    print(f"done — {PATH} al gepatcht ({MARKER})")
    sys.exit(0)

# 1. Vervang complete write_master functie
OLD_FUNCTION_START = 'def write_master(with_sampler_tap=False):'
OLD_FUNCTION_END = '    print(f"  ✓  master-section.pd  (stereo-sum VU{tag})")'

if OLD_FUNCTION_START not in content or OLD_FUNCTION_END not in content:
    print("ERROR: write_master ankers niet gevonden", file=sys.stderr)
    sys.exit(1)

start_idx = content.index(OLD_FUNCTION_START)
end_idx = content.index(OLD_FUNCTION_END) + len(OLD_FUNCTION_END)

NEW_FUNCTION = '''def write_master(with_sampler_tap=False):
    """
    Master section.

    STEREO-VU-V1: twee aparte env~ chains voor masterVuL en masterVuR
    i.p.v. een gesommeerde mono masterVu. Frontend toont stereo-VU
    (twee balkjes met onafhankelijke beweging voor headphone L/R).

    Object map:
        0-9  : base L-chain (catch~ L+R, masterVol → *~ L, *~ R, env~ L,
                 -100, s masterVuL, dac~ 1 2)
        10-21: hpVol-chain + loadbang defaults
        22-24: env~ R + -100 + s masterVuR (NIEUW)
        25-28: sampler-tap chain (if enabled)
    """
    stereo_r_lines = (
        "#X obj 80 190 env~;\\n"        # obj 22: env~ R
        "#X obj 80 210 - 100;\\n"       # obj 23: -100
        "#X obj 80 230 s masterVuR;\\n" # obj 24: s masterVuR
    )
    stereo_r_connects = (
        "#X connect 6 0 22 0;\\n"       # *~ R → env~ R
        "#X connect 22 0 23 0;\\n"      # env~ R → -100
        "#X connect 23 0 24 0;\\n"      # -100 → s masterVuR
    )

    sampler_tap_lines = ""
    sampler_tap_connects = ""
    if with_sampler_tap:
        # Sampler tap nu op indices 25-28 (stereo-VU bezet 22-24).
        sampler_tap_lines = (
            "#X obj 120 200 *~ 0.5;\\n"          # obj 25
            "#X obj 190 200 *~ 0.5;\\n"          # obj 26
            "#X obj 120 230 +~;\\n"              # obj 27
            "#X obj 120 260 send~ sampler-src-master;\\n"  # obj 28
        )
        sampler_tap_connects = (
            "#X connect 5 0 25 0;\\n"
            "#X connect 6 0 26 0;\\n"
            "#X connect 25 0 27 0;\\n"
            "#X connect 26 0 27 1;\\n"
            "#X connect 27 0 28 0;\\n"
        )

    content = f"""\\
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
#X obj 10 230 s masterVuL;
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
{{stereo_r_lines}}{{sampler_tap_lines}}#X connect 0 0 5 0;
#X connect 1 0 6 0;
#X connect 2 0 3 0;
#X connect 3 0 4 0;
#X connect 4 0 5 1;
#X connect 4 0 6 1;
#X connect 5 0 7 0;
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
{{stereo_r_connects}}{{sampler_tap_connects}}"""
    content = content.format(
        stereo_r_lines=stereo_r_lines,
        sampler_tap_lines=sampler_tap_lines,
        stereo_r_connects=stereo_r_connects,
        sampler_tap_connects=sampler_tap_connects,
    )
    with open("master-section.pd", "w") as f:
        f.write(content)
    tag = " +sampler-tap" if with_sampler_tap else ""
    print(f"  ✓  master-section.pd  (stereo VU L/R{tag})")'''

content = content[:start_idx] + NEW_FUNCTION + content[end_idx:]

with open(PATH, "w") as f:
    f.write(content)

print(f"✓ Patched {PATH} ({MARKER})")
print("  write_master volledig vervangen voor stereo VU L/R")
