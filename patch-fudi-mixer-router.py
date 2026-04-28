#!/usr/bin/env python3
"""
patch-fudi-mixer-router.py

=== FUDI-MIXER-ROUTER-V1 ===

Idempotente patch voor generate-mixer.py: voegt write_mixer_router toe,
laat write_main en write_main_ttb een [mixer-router] abstractie spawnen
achter [netreceive 9000], en regelt de generate()-aanroep.

Achtergrond: Pd 0.55-2's [netreceive] in TCP-mode (zonder -b) levert
gedecodeerde FUDI-tokens op de outlet, maar routet niet automatisch
naar [r <selector>]. Daardoor bereikten ch{N}-vol/pan/gate/fx en
masterVol/hpVol/fxReturn van bridge.js Pd niet. Fix: expliciete
[route ...] + sends in een aparte mixer-router.pd abstractie.

Uitvoering:
    cd ~/Documents/Pd/PDMixer/v2
    python3 patch-fudi-mixer-router.py

Tweede aanroep is no-op (idempotent via marker-checks).

Verifieer met:
    diff <(git show HEAD:generate-mixer.py) generate-mixer.py
"""

import re
import sys
from pathlib import Path

TARGET = Path("generate-mixer.py")

# Marker-strings — eerste regel van elk geinjecteerd blok bevat deze tag.
# Aanwezigheid = al gepatcht, sla over.
MARK_FN = "# === FUDI-MIXER-ROUTER-V1: write_mixer_router ==="
MARK_MAIN = "# === FUDI-MIXER-ROUTER-V1: write_main hookup ==="
MARK_TTB = "# === FUDI-MIXER-ROUTER-V1: write_main_ttb hookup ==="
MARK_GEN = "# === FUDI-MIXER-ROUTER-V1: generate() hookup ==="
MARK_FILELIST = "# === FUDI-MIXER-ROUTER-V1: file-list hookup ==="


def die(msg):
    print(f"FOUT: {msg}", file=sys.stderr)
    sys.exit(1)


def already_patched(src):
    return all(m in src for m in (MARK_FN, MARK_MAIN, MARK_TTB, MARK_GEN, MARK_FILELIST))


# ---------------------------------------------------------------------------
# Blok 1: write_mixer_router functie (nieuw, voegen we vóór write_main toe)
# ---------------------------------------------------------------------------

WRITE_MIXER_ROUTER_FN = '''\
{mark}
def write_mixer_router(channels):
    """Schrijf mixer-router.pd: [inlet] -> [route ...] -> {{4N+3}} sends.

    Aangeroepen door generate(). Vervangt impliciete (en in Pd 0.55-2
    gebroken) FUDI auto-routing achter netreceive 9000 door een
    expliciete keten. Het host-patch heeft alleen [mixer-router] nodig
    achter [netreceive 9000].

    Selectors: per kanaal vol/pan/gate/fx, plus masterVol/hpVol/fxReturn.
    Catch-all outlet -> [print mixer-unknown-fudi].

    Layout: sends in een grid van max GRID_COLS kolommen, kolombreedte
    en rijhoogte vast. Schaalt vanzelf met len(channels).
    """
    GRID_COLS = 5
    COL_W = 170
    ROW_H = 28
    Y_INLET = 20
    Y_ROUTE = 60
    Y_SENDS_TOP = 110
    X_LEFT = 20

    selectors = []
    for ch in channels:
        idx = ch["index"]
        selectors += [f"ch{{idx}}-vol", f"ch{{idx}}-pan",
                      f"ch{{idx}}-gate", f"ch{{idx}}-fx"]
    selectors += ["masterVol", "hpVol", "fxReturn"]

    n_outlets = len(selectors)  # zonder catch-all
    rows_needed = (n_outlets + GRID_COLS - 1) // GRID_COLS
    canvas_w = max(450, X_LEFT + GRID_COLS * COL_W + 40)
    canvas_h = Y_SENDS_TOP + (rows_needed + 2) * ROW_H + 40

    lines = [f"#N canvas 0 0 {{canvas_w}} {{canvas_h}} 12;"]
    n = [0]

    def add(l):
        lines.append(l)
        i = n[0]
        n[0] += 1
        return i

    inlet = add(f"#X obj {{X_LEFT}} {{Y_INLET}} inlet;")
    route_args = " ".join(selectors)
    route = add(f"#X obj {{X_LEFT}} {{Y_ROUTE}} route {{route_args}};")
    lines.append(f"#X connect {{inlet}} 0 {{route}} 0;")

    # Sends in grid
    for i, sel in enumerate(selectors):
        col = i % GRID_COLS
        row = i // GRID_COLS
        sx = X_LEFT + col * COL_W
        sy = Y_SENDS_TOP + row * ROW_H
        s = add(f"#X obj {{sx}} {{sy}} s {{sel}};")
        lines.append(f"#X connect {{route}} {{i}} {{s}} 0;")

    # Catch-all op laatste outlet (index n_outlets)
    unk_y = Y_SENDS_TOP + (rows_needed + 1) * ROW_H
    unk = add(f"#X obj {{X_LEFT}} {{unk_y}} print mixer-unknown-fudi;")
    lines.append(f"#X connect {{route}} {{n_outlets}} {{unk}} 0;")

    fname = "mixer-router.pd"
    with open(fname, "w") as f:
        f.write("\\n".join(lines) + "\\n")
    print(f"  ✓ {{fname}} ({{n_outlets}} routes + unknown)")


'''.format(mark=MARK_FN)


# ---------------------------------------------------------------------------
# Blok 2 & 3: hookup in write_main en write_main_ttb
#
# Strategie: we voegen direct na de bestaande netreceive-regel een
# [mixer-router] object toe en connecten netreceive -> mixer-router.
#
# In write_main is netreceive op idx `nr` (variabele bestaat al).
# In write_main_ttb wordt het return-value van add() niet bewaard;
# we moeten de regel dáár ook iets aanpassen om de index te grijpen.
# ---------------------------------------------------------------------------

# Pattern voor write_main hookup. We zoeken een unieke ankerregel in
# write_main: de comment "# Subpatches (als abstracties..." en injecteren
# vlak ervoor. Dit houdt netreceive idx 2 (na lb=0, dsp=1) intact.
WRITE_MAIN_OLD_ANCHOR = '    # Subpatches (als abstracties, zonder \'pd\' prefix)'
WRITE_MAIN_NEW_BLOCK = '''\
    {mark}
    mr = add("#X obj 200 80 mixer-router;")
    lines.append(f"#X connect {{nr}} 0 {{mr}} 0;")
    # Subpatches (als abstracties, zonder \'pd\' prefix)'''.format(
    mark=MARK_MAIN
)

# Pattern voor write_main_ttb. Daar staat:
#     add(f"#X obj 20 80 netreceive {osc_in_port};")
# zonder dat de index wordt gegrepen. We vervangen die regel door iets
# dat 'm wel grijpt + voegen mixer-router + connect toe.
WRITE_TTB_OLD_LINE = '    add(f"#X obj 20 80 netreceive {osc_in_port};")'
WRITE_TTB_NEW_BLOCK = '''\
    {mark}
    mix_nr = add(f"#X obj 20 80 netreceive {{osc_in_port}};")
    mix_mr = add("#X obj 200 80 mixer-router;")
    lines.append(f"#X connect {{mix_nr}} 0 {{mix_mr}} 0;")'''.format(
    mark=MARK_TTB
)

# ---------------------------------------------------------------------------
# Blok 4: generate() hookup — write_mixer_router(channels) aanroep
# We hangen het direct na write_vu_sender(...). Dat is een unieke regel.
# ---------------------------------------------------------------------------

GENERATE_OLD_ANCHOR = '    write_vu_sender(channels, vu_host, vu_port, vu_ms)'
GENERATE_NEW_BLOCK = '''\
    write_vu_sender(channels, vu_host, vu_port, vu_ms)
    {mark}
    write_mixer_router(channels)'''.format(mark=MARK_GEN)

# ---------------------------------------------------------------------------
# Blok 5: file-list in de samenvatting onderaan generate()
# Voegt mixer-router.pd toe aan base_files lijst.
# ---------------------------------------------------------------------------

FILELIST_OLD = '    base_files = ["fx-bus.pd", "master-section.pd", "vu-sender.pd",\n                  "touchlab-mixer.pd"]'
FILELIST_NEW = '''\
    {mark}
    base_files = ["fx-bus.pd", "master-section.pd", "vu-sender.pd",
                  "mixer-router.pd", "touchlab-mixer.pd"]'''.format(
    mark=MARK_FILELIST
)


# ---------------------------------------------------------------------------
# Apply
# ---------------------------------------------------------------------------

def main():
    if not TARGET.exists():
        die(f"{TARGET} niet gevonden in {Path.cwd()}. "
            f"Draai dit script vanuit ~/Documents/Pd/PDMixer/v2/.")

    src = TARGET.read_text()

    if already_patched(src):
        print("Al gepatcht (alle markers aanwezig). No-op.")
        return

    # 1. Inject write_mixer_router functie vóór 'def write_main('
    if MARK_FN not in src:
        anchor = "def write_main(channels, osc_in_port"
        if anchor not in src:
            die(f"Anker '{anchor}' niet gevonden — generate-mixer.py "
                f"is mogelijk substantieel anders dan verwacht. "
                f"Patch handmatig of pas script aan.")
        src = src.replace(anchor, WRITE_MIXER_ROUTER_FN + anchor, 1)
        print("  ✓ write_mixer_router functie geïnjecteerd")

    # 2. write_main hookup
    if MARK_MAIN not in src:
        if WRITE_MAIN_OLD_ANCHOR not in src:
            die(f"write_main anker niet gevonden:\\n  {WRITE_MAIN_OLD_ANCHOR}")
        src = src.replace(WRITE_MAIN_OLD_ANCHOR, WRITE_MAIN_NEW_BLOCK, 1)
        print("  ✓ write_main hookup toegevoegd")

    # 3. write_main_ttb hookup
    if MARK_TTB not in src:
        if WRITE_TTB_OLD_LINE not in src:
            die(f"write_main_ttb netreceive-regel niet gevonden:\\n"
                f"  {WRITE_TTB_OLD_LINE}")
        src = src.replace(WRITE_TTB_OLD_LINE, WRITE_TTB_NEW_BLOCK, 1)
        print("  ✓ write_main_ttb hookup toegevoegd")

    # 4. generate() hookup
    if MARK_GEN not in src:
        if GENERATE_OLD_ANCHOR not in src:
            die(f"generate() anker (write_vu_sender-regel) niet gevonden")
        # We willen die ene regel exact 1x vervangen — gebruik split/join om
        # te garanderen dat we niet meerdere matches raken.
        parts = src.split(GENERATE_OLD_ANCHOR)
        if len(parts) != 2:
            die(f"generate() anker komt {len(parts)-1}x voor, verwacht 1x. "
                f"Niet veilig om automatisch te patchen.")
        src = GENERATE_NEW_BLOCK.join(parts)
        print("  ✓ generate() hookup toegevoegd")

    # 5. file-list
    if MARK_FILELIST not in src:
        if FILELIST_OLD not in src:
            die(f"file-list anker (base_files = ...) niet gevonden in "
                f"de verwachte vorm. Mogelijk handmatig aangepast.")
        src = src.replace(FILELIST_OLD, FILELIST_NEW, 1)
        print("  ✓ file-list hookup toegevoegd")

    TARGET.write_text(src)
    print(f"\\n{TARGET} gepatcht.")
    print("Volgende stap: python3 generate-mixer.py session.json")


if __name__ == "__main__":
    main()
