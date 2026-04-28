#!/usr/bin/env python3
"""
patch-master-pan-bridge.py

=== MASTER-PAN-BRIDGE-V1 ===

Idempotente patch voor bridge.js: bridge stuurt nu masterPan-berichten
naar Pd in plaats van alleen tussen browser-clients te broadcasten.

Twee wijzigingen:
  1. State-declaratie: masterPan = 0.5 toegevoegd aan de master-state
     declaratie-regel. Bridge moet de variabele bijhouden om later
     binnenkomende clients met de huidige waarde te kunnen
     broadcasten.
  2. Handler: case "masterPan" stuurt nu sendPD bovenop broadcast,
     met clamp en state-update zoals andere master-handlers.

GEEN init-sendPD bij opstart (in tegenstelling tot masterVol). Dat
hoort bij het bredere safety-principe: bridge stuurt bij opstart
niets actief naar Pd voor master/channel volumes; de operator
gebruikt recall om bewust de laatste sessie-waarden te herstellen.
masterPan is geen volume-risico maar volgt dezelfde logica voor
consistentie. Pd's loadbang in master-section zet 0.5 als veilige
default tot recall.

Achtergrond: fase (a) (commit 70c89dc) bracht de Pd-kant. Bridge.js
behield z'n broadcast-only handler waardoor de UI-knop in browsers
synchroniseerde maar Pd niets ontving. Deze patch sluit de loop.

Markers: // === MASTER-PAN-BRIDGE-V1: ... === (JS-comment-syntax).

Uitvoering vanuit ~/Documents/Pd/PDMixer/v2/:
    python3 patch-master-pan-bridge.py
"""

import sys
from pathlib import Path

TARGET = Path("bridge.js")

MARK_DECL = "// === MASTER-PAN-BRIDGE-V1: state ==="
MARK_HANDLER = "// === MASTER-PAN-BRIDGE-V1: handler ==="


def die(msg):
    print(f"FOUT: {msg}", file=sys.stderr)
    sys.exit(1)


def already_patched(src):
    return all(m in src for m in (MARK_DECL, MARK_HANDLER))


# ---------------------------------------------------------------------------
# Wijziging 1: state-declaratie. Voeg 'masterPan = 0.5' toe.
#
# Oude regel 73:
#   let masterVol = 0.8, hpVol = 0.8, fxReturn = 0.0, masterVu = -100, masterVuL = -100, masterVuR = -100;
# ---------------------------------------------------------------------------

DECL_OLD = "let masterVol = 0.8, hpVol = 0.8, fxReturn = 0.0, masterVu = -100, masterVuL = -100, masterVuR = -100;"
DECL_NEW = f"{MARK_DECL}\nlet masterVol = 0.8, hpVol = 0.8, masterPan = 0.5, fxReturn = 0.0, masterVu = -100, masterVuL = -100, masterVuR = -100;"


# ---------------------------------------------------------------------------
# Wijziging 2: handler - case "masterPan" wordt full-functional.
#
# Oud:
#   case "masterPan":  { broadcast({type:"masterPan",value}); break; }
#
# Nieuw:
#   case "masterPan":  { masterPan=clamp(value,0,1); sendPD("masterPan",masterPan); broadcast({type:"masterPan",value:masterPan}); break; } // === MASTER-PAN-BRIDGE-V1: handler ===
# ---------------------------------------------------------------------------

HANDLER_OLD = 'case "masterPan":  { broadcast({type:"masterPan",value}); break; }'
HANDLER_NEW = f'case "masterPan":  {{ masterPan=clamp(value,0,1); sendPD("masterPan",masterPan); broadcast({{type:"masterPan",value:masterPan}}); break; }} {MARK_HANDLER}'


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

    # Pre-flight: verifieer alle ankers vóór we iets schrijven.
    # Zo voorkomen we half-patches.
    missing = []
    if MARK_DECL not in src:
        if DECL_OLD not in src:
            missing.append(f"state-declaratie:\n  {DECL_OLD}")
    if MARK_HANDLER not in src:
        if HANDLER_OLD not in src:
            missing.append(f"handler:\n  {HANDLER_OLD}")

    if missing:
        die("Een of meer ankers niet gevonden:\n  - " +
            "\n  - ".join(missing))

    # Alle ankers zijn aanwezig. Nu mogen we patchen.
    if MARK_DECL not in src:
        src = src.replace(DECL_OLD, DECL_NEW, 1)
        print("  ✓ state-declaratie bijgewerkt (masterPan = 0.5)")

    if MARK_HANDLER not in src:
        src = src.replace(HANDLER_OLD, HANDLER_NEW, 1)
        print("  ✓ case 'masterPan' handler full-functional")

    TARGET.write_text(src)
    print(f"\n{TARGET} gepatcht.")
    print("Volgende stap: bridge herstarten (node bridge.js session.json).")


if __name__ == "__main__":
    main()
