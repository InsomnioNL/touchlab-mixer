#!/usr/bin/env python3
"""
patch-master-pan-pd.py

=== MASTER-PAN-V1 ===

Idempotente patch voor generate-mixer.py: voegt write_master_pan toe,
laat write_master een [master-pan]-object inserteren tussen de
volume-*~ en de buses, en voegt masterPan toe aan de mixer-router
selectors-lijst.

Achtergrond: master-section.pd had geen pan-implementatie. UI-knop
bestond, frontend bewaarde state in localStorage, maar bridge stuurde
niets naar Pd en Pd had geen pan-keten. Deze fase voegt de Pd-kant
toe (master-pan.pd abstractie + master-section.pd hook + mixer-router
selector). Bridge.js wordt in fase (b) aangepast. Sampler-tap blijft
in deze fase pre-pan; verplaatst in fase (c).

Pan-formule (optie C, mono-folddown-met-bias) voor pan in [0, 1]:
    L_to_L = (pan<=0.5) + (pan>0.5) * (2 - 2*pan)
    R_to_L = (pan<=0.5) * (1 - 2*pan)
    L_to_R = (pan>0.5)  * (2*pan - 1)
    R_to_R = (pan<=0.5) * (2*pan) + (pan>0.5)

    out_L = L * L_to_L + R * R_to_L
    out_R = L * L_to_R + R * R_to_R

Default: 0.5 (midden) via loadbang in master-section.pd.

Gevalideerd met test-master-pan.pd op 28 april 2026.

Uitvoering vanuit ~/Documents/Pd/PDMixer/v2/:
    python3 patch-master-pan-pd.py
    ./regen.sh
"""

import sys
from pathlib import Path

TARGET = Path("generate-mixer.py")

MARK_FN = "# === MASTER-PAN-V1: write_master_pan ==="
MARK_MASTER = "# === MASTER-PAN-V1: write_master hookup ==="
MARK_ROUTER = "# === MASTER-PAN-V1: mixer-router selector ==="
MARK_FILELIST = "# === MASTER-PAN-V1: file-list hookup ==="
MARK_GEN = "# === MASTER-PAN-V1: generate() hookup ==="


def die(msg):
    print(f"FOUT: {msg}", file=sys.stderr)
    sys.exit(1)


def already_patched(src):
    return all(m in src for m in (MARK_FN, MARK_MASTER, MARK_ROUTER,
                                  MARK_FILELIST, MARK_GEN))


# ---------------------------------------------------------------------------
# Blok 1: write_master_pan functie. Schrijft master-pan.pd.
# Object map:
#   0  : inlet~ L
#   1  : inlet~ R
#   2  : r masterPan
#   3  : pack f 10
#   4  : line~
#   5  : expr~ L_to_L
#   6  : expr~ R_to_L
#   7  : expr~ L_to_R
#   8  : expr~ R_to_R
#   9  : *~ (L * L_to_L)
#   10 : *~ (R * R_to_L)
#   11 : *~ (L * L_to_R)
#   12 : *~ (R * R_to_R)
#   13 : +~ (out_L)
#   14 : +~ (out_R)
#   15 : outlet~ L
#   16 : outlet~ R
# ---------------------------------------------------------------------------

WRITE_MASTER_PAN_FN = '''\
{mark}
def write_master_pan():
    """Schrijf master-pan.pd: 2-in 2-out abstractie met masterPan-receive.

    Optie C (mono-folddown-met-bias). Pan in [0, 1]:
      pan=0.0 -> out_L = L+R, out_R = 0       (links: complete mix in L)
      pan=0.5 -> out_L = L,   out_R = R       (midden: ongewijzigde stereo)
      pan=1.0 -> out_L = 0,   out_R = L+R     (rechts: complete mix in R)

    Default-waarde voor masterPan wordt door master-section.pd gezet
    (loadbang 0.5).
    """
    content = """\\
#N canvas 0 0 600 400 12;
#X obj 30 30 inlet~;
#X obj 130 30 inlet~;
#X obj 250 30 r masterPan;
#X obj 250 60 pack f 10;
#X obj 250 80 line~;
#X obj 250 110 expr~ ($v1<=0.5)+(($v1>0.5)*(2-2*$v1));
#X obj 380 110 expr~ ($v1<=0.5)*(1-2*$v1);
#X obj 510 110 expr~ ($v1>0.5)*(2*$v1-1);
#X obj 250 150 expr~ ($v1<=0.5)*(2*$v1)+($v1>0.5);
#X obj 30 200 *~;
#X obj 130 200 *~;
#X obj 230 200 *~;
#X obj 330 200 *~;
#X obj 30 270 +~;
#X obj 230 270 +~;
#X obj 30 320 outlet~;
#X obj 230 320 outlet~;
#X connect 0 0 9 0;
#X connect 0 0 11 0;
#X connect 1 0 10 0;
#X connect 1 0 12 0;
#X connect 2 0 3 0;
#X connect 3 0 4 0;
#X connect 4 0 5 0;
#X connect 4 0 6 0;
#X connect 4 0 7 0;
#X connect 4 0 8 0;
#X connect 5 0 9 1;
#X connect 6 0 10 1;
#X connect 7 0 11 1;
#X connect 8 0 12 1;
#X connect 9 0 13 0;
#X connect 10 0 13 1;
#X connect 11 0 14 0;
#X connect 12 0 14 1;
#X connect 13 0 15 0;
#X connect 14 0 16 0;
"""
    with open("master-pan.pd", "w") as f:
        f.write(content)
    print("  ✓  master-pan.pd")


'''.format(mark=MARK_FN)


# ---------------------------------------------------------------------------
# Blok 2: write_master hookup
#
# We injecteren in write_master:
#   1. Een [master-pan] object op idx 29 (na sampler-tap-block 25-28)
#   2. Een loadbang-default voor masterPan op idx 30-31
#   3. Connects: *~ L (idx 5) en *~ R (idx 6) gaan naar [master-pan] in
#      plaats van naar dac~/env~/sampler. Buses ontvangen van master-pan
#      uitgangen.
#
# Strategie om bestaande sampler-tap (5 0 25 0 / 6 0 26 0) en stereo-VU
# (5 0 7 0 / 6 0 22 0) intact te houden zonder hele structuur op te
# blazen: we wijzigen de connects van *~ L/R van directe verbindingen
# met dac/env/sampler naar verbindingen via [master-pan]. Concreet:
#
# Oude connects (deels):
#   5 0 7 0    *~ L → env~ L
#   5 0 10 0   *~ L → dac~ links
#   5 0 14 0   *~ L → hpVol *~ L
#   5 0 25 0   *~ L → sampler-tap (alleen if with_sampler_tap)
#   6 0 10 1   *~ R → dac~ rechts
#   6 0 15 0   *~ R → hpVol *~ R
#   6 0 22 0   *~ R → env~ R
#   6 0 26 0   *~ R → sampler-tap (alleen if with_sampler_tap)
#
# Nieuwe connects:
#   5 0 29 0   *~ L → master-pan inlet L
#   6 0 29 1   *~ R → master-pan inlet R
#   29 0 7 0   master-pan out L → env~ L
#   29 0 10 0  master-pan out L → dac~ links
#   29 0 14 0  master-pan out L → hpVol *~ L
#   29 0 25 0  master-pan out L → sampler-tap (if with_sampler_tap)
#                                  ^^^ blijft hier in fase (a) — verplaatst
#                                  in fase (c) maar de connect-wijziging
#                                  is dezelfde (post-pan source)
#   29 1 10 1  master-pan out R → dac~ rechts
#   29 1 15 0  master-pan out R → hpVol *~ R
#   29 1 22 0  master-pan out R → env~ R
#   29 1 26 0  master-pan out R → sampler-tap (if with_sampler_tap)
#
# WACHT — dat verplaatst ook de sampler-tap naar post-pan in fase (a),
# wat fase (c)'s werk eigenlijk al zou doen. Goed nieuws: dan is fase
# (c) leeg en kunnen we 'm samenvoegen met (a). Dat is consistent met
# "veiliger" want anders moet ik in fase (a) speciaal de oude sampler-
# connects houden om ze in fase (c) weer te wijzigen — dat is werk om
# bewust een tussenstaat te creëren die niemand wil.
#
# Beslissing: in fase (a) doen we de connect-shift in één keer voor
# alle buses, INCLUSIEF sampler-tap. Fase (c) vervalt.
#
# Loadbang-default toevoegen op idx 30-31.
# ---------------------------------------------------------------------------

# Oude write_master heeft deze content-template. We moeten de connect-
# regels wijzigen en de master-pan-objecten + nieuwe connects + loadbang
# default toevoegen.

WRITE_MASTER_OLD_TEMPLATE_HEAD = '''    content = f"""\\
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
{{stereo_r_connects}}{{sampler_tap_connects}}"""'''


WRITE_MASTER_NEW_TEMPLATE_HEAD = '''    {mark}
    # MASTER-PAN-V1: master-pan op idx 29, loadbang-default op 30-31.
    # *~ L/R (5/6) connecten nu naar master-pan; alle buses (env, dac,
    # hpVol, sampler-tap) ontvangen van master-pan outputs i.p.v.
    # rechtstreeks van *~ L/R.
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
{{{{stereo_r_lines}}}}{{{{sampler_tap_lines}}}}#X obj 45 160 master-pan;
#X msg 170 360 0.5;
#X obj 170 380 s masterPan;
#X connect 0 0 5 0;
#X connect 1 0 6 0;
#X connect 2 0 3 0;
#X connect 3 0 4 0;
#X connect 4 0 5 1;
#X connect 4 0 6 1;
#X connect 5 0 29 0;
#X connect 6 0 29 1;
#X connect 29 0 7 0;
#X connect 29 0 10 0;
#X connect 29 0 14 0;
#X connect 29 1 10 1;
#X connect 29 1 15 0;
#X connect 29 1 22 0;
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
#X connect 17 0 30 0;
#X connect 30 0 31 0;
{{{{stereo_r_connects}}}}{{{{sampler_tap_connects}}}}"""'''.format(mark=MARK_MASTER)


# Oude stereo_r_connects (in regel een tuple van strings; we vervangen
# de letterlijke regel "#X connect 6 0 22 0;" omdat dat nu door
# master-pan moet lopen).
OLD_STEREO_R_CONNECTS = '''    stereo_r_connects = (
        "#X connect 6 0 22 0;\\n"       # *~ R → env~ R
        "#X connect 22 0 23 0;\\n"      # env~ R → -100
        "#X connect 23 0 24 0;\\n"      # -100 → s masterVuR
    )'''

NEW_STEREO_R_CONNECTS = '''    # MASTER-PAN-V1: env~ R krijgt nu master-pan out R (29 1) i.p.v. 6 0
    stereo_r_connects = (
        "#X connect 22 0 23 0;\\n"      # env~ R → -100
        "#X connect 23 0 24 0;\\n"      # -100 → s masterVuR
    )'''


# Oude sampler_tap_connects: connect 5/6 0 25/26 0. We veranderen die
# naar 29 0/1 25/26 0 zodat sampler-tap post-pan tapt. Dit is de
# inhoudelijke wijziging die "fase c" zou zijn.
OLD_SAMPLER_TAP_CONNECTS = '''        sampler_tap_connects = (
            "#X connect 5 0 25 0;\\n"
            "#X connect 6 0 26 0;\\n"
            "#X connect 25 0 27 0;\\n"
            "#X connect 26 0 27 1;\\n"
            "#X connect 27 0 28 0;\\n"
        )'''

NEW_SAMPLER_TAP_CONNECTS = '''        # MASTER-PAN-V1: sampler-tap nu post-master-pan (29 0 / 29 1)
        sampler_tap_connects = (
            "#X connect 29 0 25 0;\\n"
            "#X connect 29 1 26 0;\\n"
            "#X connect 25 0 27 0;\\n"
            "#X connect 26 0 27 1;\\n"
            "#X connect 27 0 28 0;\\n"
        )'''


# ---------------------------------------------------------------------------
# Blok 3: mixer-router selector — voeg 'masterPan' toe aan de
# selectors-lijst in write_mixer_router (zit in generate-mixer.py vanaf
# FUDI-MIXER-ROUTER-V1 patch).
# ---------------------------------------------------------------------------

ROUTER_OLD_LINE = 'selectors += ["masterVol", "hpVol", "fxReturn"]'
ROUTER_NEW_LINE = '''    {mark}
    selectors += ["masterVol", "masterPan", "hpVol", "fxReturn"]'''.format(
    mark=MARK_ROUTER
).lstrip()


# ---------------------------------------------------------------------------
# Blok 4: file-list — voeg master-pan.pd toe aan base_files lijst.
# Past de FUDI-MIXER-ROUTER-V1 file-list aan.
# ---------------------------------------------------------------------------

FILELIST_OLD = '    base_files = ["fx-bus.pd", "master-section.pd", "vu-sender.pd",\n                  "mixer-router.pd", "touchlab-mixer.pd"]'
FILELIST_NEW = '''\
    {mark}
    base_files = ["fx-bus.pd", "master-section.pd", "master-pan.pd",
                  "vu-sender.pd", "mixer-router.pd", "touchlab-mixer.pd"]'''.format(
    mark=MARK_FILELIST
)


# ---------------------------------------------------------------------------
# Blok 5: generate() hookup — write_master_pan() aanroep
# ---------------------------------------------------------------------------

GENERATE_OLD_ANCHOR = '    write_master(with_sampler_tap=ttb_enable)'
GENERATE_NEW_BLOCK = '''    write_master(with_sampler_tap=ttb_enable)
    {mark}
    write_master_pan()'''.format(mark=MARK_GEN)


# ---------------------------------------------------------------------------
# Apply
# ---------------------------------------------------------------------------

def main():
    if not TARGET.exists():
        die(f"{TARGET} niet gevonden in {Path.cwd()}. "
            f"Draai vanuit ~/Documents/Pd/PDMixer/v2/.")

    src = TARGET.read_text()

    if already_patched(src):
        print("Al gepatcht (alle markers aanwezig). No-op.")
        return

    # 1. Inject write_master_pan functie vóór 'def write_main('.
    if MARK_FN not in src:
        anchor = "def write_main(channels, osc_in_port"
        if anchor not in src:
            die(f"Anker '{anchor}' niet gevonden.")
        src = src.replace(anchor, WRITE_MASTER_PAN_FN + anchor, 1)
        print("  ✓ write_master_pan functie geïnjecteerd")

    # 2. write_master template head vervangen
    if MARK_MASTER not in src:
        if WRITE_MASTER_OLD_TEMPLATE_HEAD not in src:
            die("write_master template-head niet gevonden in verwachte vorm. "
                "Mogelijk is de functie sinds GitHub-main veranderd.")
        src = src.replace(WRITE_MASTER_OLD_TEMPLATE_HEAD,
                          WRITE_MASTER_NEW_TEMPLATE_HEAD, 1)
        print("  ✓ write_master template-head bijgewerkt")

    # 2b. stereo_r_connects wijzigen
    if OLD_STEREO_R_CONNECTS not in src:
        die("stereo_r_connects-blok niet gevonden in verwachte vorm.")
    src = src.replace(OLD_STEREO_R_CONNECTS, NEW_STEREO_R_CONNECTS, 1)
    print("  ✓ stereo_r_connects bijgewerkt (env~ R via master-pan)")

    # 2c. sampler_tap_connects wijzigen
    if OLD_SAMPLER_TAP_CONNECTS not in src:
        die("sampler_tap_connects-blok niet gevonden in verwachte vorm.")
    src = src.replace(OLD_SAMPLER_TAP_CONNECTS, NEW_SAMPLER_TAP_CONNECTS, 1)
    print("  ✓ sampler_tap_connects bijgewerkt (post-pan source)")

    # 3. mixer-router selectors
    if MARK_ROUTER not in src:
        if ROUTER_OLD_LINE not in src:
            die(f"router-selectors anker niet gevonden:\\n  {ROUTER_OLD_LINE}")
        src = src.replace(ROUTER_OLD_LINE, ROUTER_NEW_LINE, 1)
        print("  ✓ mixer-router selectors uitgebreid met masterPan")

    # 4. file-list
    if MARK_FILELIST not in src:
        if FILELIST_OLD not in src:
            die("file-list anker niet gevonden in verwachte vorm.")
        src = src.replace(FILELIST_OLD, FILELIST_NEW, 1)
        print("  ✓ file-list uitgebreid met master-pan.pd")

    # 5. generate() hookup
    if MARK_GEN not in src:
        if GENERATE_OLD_ANCHOR not in src:
            die("generate() anker (write_master-aanroep) niet gevonden.")
        parts = src.split(GENERATE_OLD_ANCHOR)
        if len(parts) != 2:
            die(f"generate() anker komt {len(parts)-1}x voor, verwacht 1x.")
        src = GENERATE_NEW_BLOCK.join(parts)
        print("  ✓ generate() hookup toegevoegd")

    TARGET.write_text(src)
    print(f"\\n{TARGET} gepatcht.")
    print("Volgende stap: ./regen.sh")


if __name__ == "__main__":
    main()
