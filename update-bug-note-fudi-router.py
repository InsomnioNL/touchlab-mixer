#!/usr/bin/env python3
"""
update-bug-note-fudi-router.py

=== FUDI-MIXER-ROUTER-V1 ===

Werkt notes/2026-04-27-mixer-fudi-routing-bug.md bij met de
fix-bevindingen van 28 april 2026.

Idempotent: als de marker FIX-BEVINDING-V1 al in het bestand staat,
gebeurt er niets.

Strategie: vervangt de complete '## Status'-sectie aan het einde van
het bestand door een uitgebreid blok dat status, fix-bevinding,
implementatie, verificatie en bijgevangen open issues bevat.

Uitvoering vanuit de werkdir of de repo-root:
    python3 update-bug-note-fudi-router.py
"""

import sys
from pathlib import Path

# Probeer beide locaties (werkdir en repo) — pak de eerste die bestaat.
CANDIDATES = [
    Path("notes/2026-04-27-mixer-fudi-routing-bug.md"),
    Path.home() / "Documents/touchlab-mixer/notes/2026-04-27-mixer-fudi-routing-bug.md",
    Path.home() / "Documents/Pd/PDMixer/v2/notes/2026-04-27-mixer-fudi-routing-bug.md",
]

MARKER = "<!-- FIX-BEVINDING-V1 -->"

NEW_TAIL = f'''\
## Status
**Opgelost 28 april 2026.**

{MARKER}

## Fix-bevinding (28 april 2026)
Live-test met minimale Pd-patch (`[netreceive 9000]` → `[print TCP-RAW]`)
bevestigde:

- TCP komt prima binnen.
- Pd 0.55-2 decodeert FUDI-tokens al op de outlet (geen `-b` flag, geen
  `fudiparse` nodig — bericht `; ch1-pan 0.9;` komt eruit als lijst
  `ch1-pan 0.9`).
- Auto-routing naar `[r <selector>]` is dood in Pd 0.55-2. Vandaar dat
  geen enkele `[r ch1-pan]` triggerde ondanks correcte FUDI-input.

Origineel plan in deze notitie noemde `fudiparse + route`. Werkelijke
fix is alleen `route` — `fudiparse` is niet nodig op pre-decoded input
van TCP-netreceive zonder `-b`.

## Fix-implementatie
Nieuwe abstractie `mixer-router.pd` met `[inlet] → [route ...] → 4N+3
sends + catch-all-print`. Host-patches (`touchlab-mixer.pd`,
`touchlab-mixer-ttb.pd`) krijgen alleen `[netreceive 9000] →
[mixer-router]` — één extra object, geen index-verschuiving voor
bestaande post-regen patch-scripts.

Schaalt voor N=1 t/m N=20+ via grid-layout (5 kolommen).

Patch: `patch-fudi-mixer-router.py` (idempotent, markers
`# === FUDI-MIXER-ROUTER-V1: ... ===`).

## Verificatie (28 april 2026)
End-to-end getest met N=4 kanalen, sampler.enabled=true:
- ch{{1..4}}-vol/pan/gate/fx werken — VU L/R reageert onafhankelijk
- masterVol, hpVol, fxReturn werken
- `mixer-unknown-fudi` print bleef stil tijdens normale frontend-acties
- tcpdump op poort 9000 bevestigde alle 19 selectors correct
  geformatteerd door bridge

## Open issues bijgevangen
- Master-mute: bridge stuurt geen FUDI bij master-mute (tcpdump
  bevestigt: niets gaat over de wire). Geen routing-bug, vermoedelijk
  ontbrekende handler in `bridge.js` of frontend-event mismatch. Nieuwe
  notitie aanmaken voor opvolging.
- Sampler-pan werkt niet — andere FUDI-keten (UDP 9002), aparte
  diagnose nodig in volgende sessie.
'''


def find_target():
    for p in CANDIDATES:
        if p.exists():
            return p
    print("FOUT: bug-notitie niet gevonden in:", file=sys.stderr)
    for p in CANDIDATES:
        print(f"  - {p}", file=sys.stderr)
    sys.exit(1)


def main():
    target = find_target()
    src = target.read_text()

    if MARKER in src:
        print(f"Al bijgewerkt (marker aanwezig in {target}). No-op.")
        return

    # Knip alles vanaf de eerste '## Status' regel af. Vervang door
    # NEW_TAIL.
    anchor = "## Status"
    if anchor not in src:
        print(f"FOUT: '## Status'-sectie niet gevonden in {target}. "
              f"Handmatig bijwerken.", file=sys.stderr)
        sys.exit(1)

    head = src.split(anchor, 1)[0].rstrip() + "\n\n"
    new_src = head + NEW_TAIL

    target.write_text(new_src)
    print(f"  ✓ {target} bijgewerkt")


if __name__ == "__main__":
    main()
