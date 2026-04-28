#!/usr/bin/env python3
"""
patch-safety-vol-bridge.py

=== SAFETY-VOL-V1 ===

Idempotente patch voor bridge.js: vol-state op 0 bij opstart, en
vol-related sendPD-aanroepen verwijderd uit het opstart-block.

Veiligheidsprincipe: bridge stuurt bij opstart geen vol-data naar Pd.
Pd's loadbang is single source of truth voor opstart-state (post fase
c-2: ook 0 in de generator). Browser stuurt vol-state niet bij opent
(geverifieerd: alleen via recall/fader-handlers). Pas wanneer een
user op recall drukt of een fader beweegt komt er volume.

Drie wijzigingen in bridge.js:
  1. State-default `vol: 0.8` → `vol: 0` (channel-state factory).
  2. `let masterVol = 0.8, hpVol = 0.8` → `0, 0`. (masterPan op 0.5
     blijft, geen volume-risico; fxReturn = 0.0 was al veilig.)
  3. Opstart-`sendPD`-block: `ch${i}-vol`/`masterVol`/`hpVol`-aanroepen
     weghalen. `ch${i}-pan/gate/fx`/`fxReturn` blijven (geen risico).

Markers: // === SAFETY-VOL-V1: ... === (JS-comment-syntax).

Uitvoering:
    python3 patch-safety-vol-bridge.py
"""

import sys
from pathlib import Path

TARGET = Path("bridge.js")

MARK_STATE = "// === SAFETY-VOL-V1: state ==="
MARK_DECL = "// === SAFETY-VOL-V1: master-decl ==="
MARK_INIT = "// === SAFETY-VOL-V1: init ==="


def die(msg):
    print(f"FOUT: {msg}", file=sys.stderr)
    sys.exit(1)


def already_patched(src):
    return all(m in src for m in (MARK_STATE, MARK_DECL, MARK_INIT))


# ---------------------------------------------------------------------------
# Wijziging 1: channel-state factory. Default vol op 0.
#
# Oud regel 71 (ongeveer):
#   state[ch.index] = { name: ch.name, vol: 0.8, pan: 0.5, mute: false, solo: false, fx: 0.0, vu: -100 };
# ---------------------------------------------------------------------------

STATE_OLD = "state[ch.index] = { name: ch.name, vol: 0.8, pan: 0.5, mute: false, solo: false, fx: 0.0, vu: -100 };"
STATE_NEW = f"""{MARK_STATE}
    state[ch.index] = {{ name: ch.name, vol: 0, pan: 0.5, mute: false, solo: false, fx: 0.0, vu: -100 }};"""


# ---------------------------------------------------------------------------
# Wijziging 2: master-state declaratie.
#
# Oud regel 73:
#   let masterVol = 0.8, hpVol = 0.8, masterPan = 0.5, fxReturn = 0.0, ...
# (na fase b is masterPan al toegevoegd. We laten markers van fase b intact.)
# ---------------------------------------------------------------------------

DECL_OLD = "let masterVol = 0.8, hpVol = 0.8, masterPan = 0.5, fxReturn = 0.0, masterVu = -100, masterVuL = -100, masterVuR = -100;"
DECL_NEW = f"""{MARK_DECL}
let masterVol = 0, hpVol = 0, masterPan = 0.5, fxReturn = 0.0, masterVu = -100, masterVuL = -100, masterVuR = -100;"""


# ---------------------------------------------------------------------------
# Wijziging 3: opstart-block. Vol-related sendPD-regels verwijderen.
#
# Oud (regel ~225-234):
#     const s = state[ch.index];
#     sendPD(`ch${ch.index}-vol`, s.vol);
#     sendPD(`ch${ch.index}-pan`, s.pan);
#     sendPD(`ch${ch.index}-gate`, computeGate(ch.index));
#     sendPD(`ch${ch.index}-fx`, s.fx);
#   });
#   sendPD("masterVol", masterVol);
#   sendPD("hpVol", hpVol);
#   sendPD("fxReturn", fxReturn);
#
# Nieuw:
#     const s = state[ch.index];
#     // === SAFETY-VOL-V1: init ===
#     // ch${i}-vol weggehaald: vol komt pas bij recall/fader-actie.
#     sendPD(`ch${ch.index}-pan`, s.pan);
#     sendPD(`ch${ch.index}-gate`, computeGate(ch.index));
#     sendPD(`ch${ch.index}-fx`, s.fx);
#   });
#   // masterVol + hpVol weggehaald om dezelfde reden.
#   sendPD("fxReturn", fxReturn);
# ---------------------------------------------------------------------------

# We knippen het opstart-block in een redelijk-uniek anker.
INIT_OLD = '''    const s = state[ch.index];
    sendPD(`ch${ch.index}-vol`, s.vol);
    sendPD(`ch${ch.index}-pan`, s.pan);
    sendPD(`ch${ch.index}-gate`, computeGate(ch.index));
    sendPD(`ch${ch.index}-fx`, s.fx);
  });
  sendPD("masterVol", masterVol);
  sendPD("hpVol", hpVol);
  sendPD("fxReturn", fxReturn);'''

INIT_NEW = f'''    const s = state[ch.index];
    {MARK_INIT}
    // ch${{ch.index}}-vol/masterVol/hpVol weggehaald: komen pas bij recall.
    sendPD(`ch${{ch.index}}-pan`, s.pan);
    sendPD(`ch${{ch.index}}-gate`, computeGate(ch.index));
    sendPD(`ch${{ch.index}}-fx`, s.fx);
  }});
  sendPD("fxReturn", fxReturn);'''


def main():
    if not TARGET.exists():
        die(f"{TARGET} niet gevonden in {Path.cwd()}.")

    src = TARGET.read_text()

    if already_patched(src):
        print("Al gepatcht (alle markers aanwezig). No-op.")
        return

    # Pre-flight: alle ankers verifiëren vóór één wijziging.
    missing = []
    if MARK_STATE not in src and STATE_OLD not in src:
        missing.append(f"channel-state factory:\n  {STATE_OLD}")
    if MARK_DECL not in src and DECL_OLD not in src:
        missing.append(f"master-state declaratie:\n  {DECL_OLD}")
    if MARK_INIT not in src and INIT_OLD not in src:
        missing.append("opstart-block (zie INIT_OLD in script)")

    if missing:
        die("Een of meer ankers niet gevonden:\n  - " +
            "\n  - ".join(missing))

    if MARK_STATE not in src:
        src = src.replace(STATE_OLD, STATE_NEW, 1)
        print("  ✓ channel-state default vol = 0")

    if MARK_DECL not in src:
        src = src.replace(DECL_OLD, DECL_NEW, 1)
        print("  ✓ master/hp default vol = 0 (masterPan/fxReturn ongewijzigd)")

    if MARK_INIT not in src:
        src = src.replace(INIT_OLD, INIT_NEW, 1)
        print("  ✓ opstart-block: vol-related sendPD weggehaald")

    TARGET.write_text(src)
    print(f"\n{TARGET} gepatcht.")


if __name__ == "__main__":
    main()
