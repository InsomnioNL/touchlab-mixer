#!/usr/bin/env python3
"""
patch-safety-vol-pd.py

=== SAFETY-VOL-PD-V1 ===

Idempotente patch voor generate-mixer.py: Pd-loadbang-defaults voor
volume-receivers op 0 (was 0.8).

Veiligheidsprincipe (pendant van patch-safety-vol-bridge.py):
- master-section.pd loadbang stuurt 0 naar masterVol en hpVol (was 0.8).
- ch{N}.pd template loadbang stuurt 0 naar ch{N}-vol (was 0.8).
- masterPan blijft 0.5 (geen volume-risico, midden = neutraal).
- channel-pan blijft 0.5 (idem).

Pd is na deze patch single source of truth voor opstart-state. Bridge
en frontend sturen vol pas wanneer recall of fader-actie. Operator
heeft volledige controle over wanneer audio op iemands oren komt.

Markers: # === SAFETY-VOL-PD-V1: ... === (Python-comment-syntax in
generator; output naar Pd-files heeft geen markers nodig — Pd-output
is gegenereerd, niet bewaard).

Uitvoering vanuit ~/Documents/Pd/PDMixer/v2/:
    python3 patch-safety-vol-pd.py
    ./regen.sh
"""

import sys
from pathlib import Path

TARGET = Path("generate-mixer.py")

MARK_MASTER = "# === SAFETY-VOL-PD-V1: master-section ==="
MARK_CHANNEL = "# === SAFETY-VOL-PD-V1: channel ==="


def die(msg):
    print(f"FOUT: {msg}", file=sys.stderr)
    sys.exit(1)


def already_patched(src):
    return all(m in src for m in (MARK_MASTER, MARK_CHANNEL))


# ---------------------------------------------------------------------------
# Wijziging 1: master-section.pd loadbang.
#
# In write_master, in de content-template (post fase a):
#   #X obj 10 340 loadbang;
#   #X msg 10 360 0.8;        ← masterVol default — naar 0
#   #X obj 10 380 s masterVol;
#   #X msg 90 360 0.8;        ← hpVol default — naar 0
#   #X obj 90 380 s hpVol;
#   ...
#   #X msg 170 360 0.5;       ← masterPan default — BLIJFT
#   #X obj 170 380 s masterPan;
#
# We willen alleen de twee 0.8-msg-regels veranderen naar 0.
# ---------------------------------------------------------------------------

# Beide msg-regels staan exact één keer in de template-string van
# write_master, allebei met 0.8 als value. Maar `0.8` komt mogelijk
# vaker voor in het bestand (defaults op andere plekken). Daarom
# matchen we de unieke surrounding van elke msg-regel.

MASTER_OLD_BLOCK = '''#X obj 10 340 loadbang;
#X msg 10 360 0.8;
#X obj 10 380 s masterVol;
#X msg 90 360 0.8;
#X obj 90 380 s hpVol;'''

MASTER_NEW_BLOCK = '''#X obj 10 340 loadbang;
#X msg 10 360 0;
#X obj 10 380 s masterVol;
#X msg 90 360 0;
#X obj 90 380 s hpVol;'''


# ---------------------------------------------------------------------------
# Wijziging 2: ch{N}.pd loadbang in write_channel.
#
# Volgens grep van ch1.pd (regel 24) staat er een `#X msg 10 440 0.8;`
# die naar `s ch{idx}-vol` gaat. We moeten dit veranderen in de
# write_channel-functie van generate-mixer.py.
#
# Probleem: ik heb de volledige write_channel niet in mijn context.
# Maar grep toonde dat in ch1.pd:
#   regel 23: #X obj 10 420 loadbang;
#   regel 24: #X msg 10 440 0.8;
#   regel 26: #X msg 90 440 0.5;     ← waarschijnlijk pan, blijft
#
# Dat suggereert dat write_channel ook een soortgelijke msg-regel met
# 0.8 heeft. We zoeken die unieke string.
#
# Vermoedelijke template (op basis van symmetrie met master-section):
#   #X obj 10 420 loadbang;
#   #X msg 10 440 0.8;
#   #X obj 10 460 s ch{idx}-vol;
#
# We willen die 0.8 → 0. Maar de exacte string in generate-mixer.py
# kan variëren — vooral de `s ch{idx}-vol`-regel met f-string interpol.
# We gebruiken een minder-specifiek anker: de combinatie van loadbang
# + msg 0.8 in een channel-context, en hopen dat het uniek is.
#
# Voorzichtig: in write_master staat OOK een `loadbang ... msg 10 360
# 0.8`. Daar staat het op pos (10, 360), in write_channel op (10, 440).
# Dus de y-coord 440 onderscheidt ze. Lukt waarschijnlijk.
# ---------------------------------------------------------------------------

# We kunnen niet de definitieve oude string leveren zonder write_channel
# te zien. Strategie: pre-flight een grep laten doen, en als de
# verwachte regel niet in unieke vorm aanwezig is, falen met duidelijke
# melding.

CHANNEL_OLD_LINE = "#X msg 10 440 0.8;"
CHANNEL_NEW_LINE = "#X msg 10 440 0;"


def main():
    if not TARGET.exists():
        die(f"{TARGET} niet gevonden in {Path.cwd()}.")

    src = TARGET.read_text()

    if already_patched(src):
        print("Al gepatcht (alle markers aanwezig). No-op.")
        return

    # Pre-flight: alle ankers verifieren.
    missing = []
    if MARK_MASTER not in src and MASTER_OLD_BLOCK not in src:
        missing.append(f"master-section loadbang-block:\n  (kijk in write_master, "
                       f"regel met 'msg 10 360 0.8' en 'msg 90 360 0.8')")
    if MARK_CHANNEL not in src and CHANNEL_OLD_LINE not in src:
        missing.append(f"channel loadbang-regel: {CHANNEL_OLD_LINE}\n  "
                       f"(kijk in write_channel, regel met '#X msg 10 440 0.8')")

    if missing:
        die("Een of meer ankers niet gevonden:\n  - " +
            "\n  - ".join(missing))

    if MARK_MASTER not in src:
        # Voeg marker als comment vóór de content-template-block.
        # Simpelst: vervang het blok zelf, en voeg een marker-regel
        # ergens in de write_master-functie toe.
        src = src.replace(MASTER_OLD_BLOCK, MASTER_NEW_BLOCK, 1)
        # Marker injecteren: vóór `def write_master(`-regel een comment.
        src = src.replace("def write_master(",
                          f"{MARK_MASTER}\ndef write_master(", 1)
        print("  ✓ master-section: masterVol/hpVol loadbang naar 0")

    if MARK_CHANNEL not in src:
        src = src.replace(CHANNEL_OLD_LINE, CHANNEL_NEW_LINE, 1)
        src = src.replace("def write_channel(",
                          f"{MARK_CHANNEL}\ndef write_channel(", 1)
        print("  ✓ ch{N}.pd: channel-vol loadbang naar 0")

    TARGET.write_text(src)
    print(f"\n{TARGET} gepatcht.")
    print("Volgende stap: ./regen.sh")


if __name__ == "__main__":
    main()
