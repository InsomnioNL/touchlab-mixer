#!/usr/bin/env python3
"""
patch-divider-knobs-braces.py

=== DIVIDER-KNOBS-BRACES-V1 ===

Idempotente patch voor index.html: voegt ontbrekende accolades toe
aan de twee if-blokken in initDividerKnobs() voor master-pan en
master-fx.

Bug: door ontbrekende accolades voert de `if` alleen het eerste
statement voorwaardelijk uit. De rest (initK + attachPopup) wordt
altijd uitgevoerd, ook als de SVG-thumb al bestaat. Resultaat: bij
elke aanroep van initDividerKnobs() komt er een extra SVG-thumb bij,
gestapeld op de bestaande knob.

Channel-pan-knoppen hebben dit probleem niet — die worden via een
aparte renderStrips()-pipeline gemaakt, vanaf scratch elke keer.

Fix voor master-pan:
  Oud:  if(mpk&&!mpk.querySelector('svg')) mpk.dataset.default=0.5;
        mpk.dataset.currentVal=master.pan||.5;
            initK(mpk,...);
            attachPopup(mpk,...);

  Nieuw: if(mpk&&!mpk.querySelector('svg')) {
           mpk.dataset.default=0.5;
           mpk.dataset.currentVal=master.pan||.5;
           initK(mpk,...);
           attachPopup(mpk,...);
         }

Idem voor master-fx (mfx-blok).

Markers: // === DIVIDER-KNOBS-BRACES-V1 === (JS-comment-syntax in
script-blok).

Uitvoering vanuit ~/Documents/Pd/PDMixer/v2/:
    python3 patch-divider-knobs-braces.py
"""

import sys
from pathlib import Path

TARGET = Path("index.html")

MARK = "// === DIVIDER-KNOBS-BRACES-V1 ==="


def die(msg):
    print(f"FOUT: {msg}", file=sys.stderr)
    sys.exit(1)


def already_patched(src):
    return MARK in src


# ---------------------------------------------------------------------------
# Twee blokken te patchen, beide met dezelfde structuur. We gebruiken
# de hele oude tekst inclusief de drie regels (if-statement, initK,
# attachPopup) als anker, zodat we precies weten waar we zijn.
# ---------------------------------------------------------------------------

PAN_OLD = """  if(mpk&&!mpk.querySelector('svg')) mpk.dataset.default=0.5;mpk.dataset.currentVal=master.pan||.5;
    initK(mpk,master.pan||.5,26,function(v){master.pan=v;mpk.dataset.currentVal=v;send({type:'masterPan',value:v});saveMaster();},'green');
    attachPopup(mpk,'pan',function(){return parseFloat(mpk.dataset.currentVal||'0.5');},function(v){master.pan=v;mpk.dataset.currentVal=v;var ln2=mpk.querySelector('line');if(ln2)setKL(ln2,v,26);send({type:'masterPan',value:v});saveMaster();});"""

PAN_NEW = """  if(mpk&&!mpk.querySelector('svg')) { """ + MARK + """ braces toegevoegd
    mpk.dataset.default=0.5;mpk.dataset.currentVal=master.pan||.5;
    initK(mpk,master.pan||.5,26,function(v){master.pan=v;mpk.dataset.currentVal=v;send({type:'masterPan',value:v});saveMaster();},'green');
    attachPopup(mpk,'pan',function(){return parseFloat(mpk.dataset.currentVal||'0.5');},function(v){master.pan=v;mpk.dataset.currentVal=v;var ln2=mpk.querySelector('line');if(ln2)setKL(ln2,v,26);send({type:'masterPan',value:v});saveMaster();});
  }"""

FX_OLD = """  if(mfx&&!mfx.querySelector('svg')) mfx.dataset.default=0;mfx.dataset.currentVal=master.fxReturn||0;
    initK(mfx,master.fxReturn||0,26,function(v){master.fxReturn=v;mfx.dataset.currentVal=v;send({type:'fxReturn',value:v});saveMaster();},'purple');
    attachPopup(mfx,'fx',function(){return parseFloat(mfx.dataset.currentVal||'0');},function(v){master.fxReturn=v;mfx.dataset.currentVal=v;var ln2=mfx.querySelector('line');if(ln2)setKL(ln2,v,26);send({type:'fxReturn',value:v});saveMaster();});"""

FX_NEW = """  if(mfx&&!mfx.querySelector('svg')) {
    mfx.dataset.default=0;mfx.dataset.currentVal=master.fxReturn||0;
    initK(mfx,master.fxReturn||0,26,function(v){master.fxReturn=v;mfx.dataset.currentVal=v;send({type:'fxReturn',value:v});saveMaster();},'purple');
    attachPopup(mfx,'fx',function(){return parseFloat(mfx.dataset.currentVal||'0');},function(v){master.fxReturn=v;mfx.dataset.currentVal=v;var ln2=mfx.querySelector('line');if(ln2)setKL(ln2,v,26);send({type:'fxReturn',value:v});saveMaster();});
  }"""


def main():
    if not TARGET.exists():
        die(f"{TARGET} niet gevonden in {Path.cwd()}.")

    src = TARGET.read_text()

    if already_patched(src):
        print("Al gepatcht (marker aanwezig). No-op.")
        return

    # Pre-flight: beide ankers verifiëren vóór één wijziging.
    missing = []
    if PAN_OLD not in src:
        missing.append("master-pan if-blok (kn-m-pan)")
    if FX_OLD not in src:
        missing.append("master-fx if-blok (kn-m-fx)")

    if missing:
        die("Anker(s) niet gevonden:\n  - " + "\n  - ".join(missing))

    src = src.replace(PAN_OLD, PAN_NEW, 1)
    print("  ✓ master-pan if-blok: accolades toegevoegd")

    src = src.replace(FX_OLD, FX_NEW, 1)
    print("  ✓ master-fx if-blok: accolades toegevoegd")

    TARGET.write_text(src)
    print(f"\n{TARGET} gepatcht.")


if __name__ == "__main__":
    main()
