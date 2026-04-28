#!/usr/bin/env python3
"""
patch-safety-vol-ui.py

=== SAFETY-VOL-UI-V1 ===

Idempotente patch voor index.html: bij browser-opent worden channel-vol
NIET meer geladen vanuit localStorage. Pan/fx/mute/solo blijven wel
geladen (geen volume-risico).

Veiligheidsprincipe: vol komt pas in beeld bij recall of fader-actie.
Visueel toont de UI dus alle faders op 0 bij opent, ongeacht wat in
localStorage staat. localStorage zelf wordt NIET gewist — recall haalt
'm later op.

Master-state in init-handler (regel 968) zet vol al op 0 hardcoded —
geen wijziging nodig daar.

Channel-state via loadChannelMemory: vol-deel verwijderen uit de
property-overschrijving, andere properties (pan/fx/mute/solo) blijven.

Markers: // === SAFETY-VOL-UI-V1 === (JS-comment-syntax in script-blok).

Uitvoering vanuit ~/Documents/Pd/PDMixer/v2/:
    python3 patch-safety-vol-ui.py
"""

import sys
from pathlib import Path

TARGET = Path("index.html")

MARK = "// === SAFETY-VOL-UI-V1 ==="


def die(msg):
    print(f"FOUT: {msg}", file=sys.stderr)
    sys.exit(1)


def already_patched(src):
    return MARK in src


# ---------------------------------------------------------------------------
# Wijziging: in loadChannelMemory de ch.vol=... substring weghalen.
#
# Oud (regel 945, één lange regel):
#   if(m){ch.vol=m.vol!==undefined?m.vol:ch.vol;ch.pan=m.pan!==undefined?m.pan:ch.pan;ch.fx=m.fx!==undefined?m.fx:ch.fx;ch.mute=m.mute!==undefined?m.mute:ch.mute;ch.solo=m.solo!==undefined?m.solo:ch.solo;}
#
# Nieuw: zelfde regel zonder het ch.vol-deel.
# ---------------------------------------------------------------------------

OLD_LINE = "if(m){ch.vol=m.vol!==undefined?m.vol:ch.vol;ch.pan=m.pan!==undefined?m.pan:ch.pan;ch.fx=m.fx!==undefined?m.fx:ch.fx;ch.mute=m.mute!==undefined?m.mute:ch.mute;ch.solo=m.solo!==undefined?m.solo:ch.solo;}"
NEW_LINE = MARK + " vol bewust niet uit localStorage bij opent\n  if(m){ch.pan=m.pan!==undefined?m.pan:ch.pan;ch.fx=m.fx!==undefined?m.fx:ch.fx;ch.mute=m.mute!==undefined?m.mute:ch.mute;ch.solo=m.solo!==undefined?m.solo:ch.solo;}"


def main():
    if not TARGET.exists():
        die(f"{TARGET} niet gevonden in {Path.cwd()}.")

    src = TARGET.read_text()

    if already_patched(src):
        print("Al gepatcht (marker aanwezig). No-op.")
        return

    if OLD_LINE not in src:
        die(f"Anker niet gevonden in {TARGET}:\n  {OLD_LINE[:80]}...")

    src = src.replace(OLD_LINE, NEW_LINE, 1)
    TARGET.write_text(src)
    print(f"  ✓ loadChannelMemory: ch.vol overslaan bij opent")
    print(f"\n{TARGET} gepatcht.")


if __name__ == "__main__":
    main()
