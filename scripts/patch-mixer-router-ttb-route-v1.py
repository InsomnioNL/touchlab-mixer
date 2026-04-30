#!/usr/bin/env python3
"""patch-mixer-router-ttb-route-v1.py

Voegt twee routes toe aan mixer-router.pd zodat
ttb-route-local en ttb-route-live niet meer in de
catch-all (mixer-unknown-fudi) eindigen.

Object-indices na patch:
  0: inlet
  1: route ... (22 routes ipv 20)
  2-21: bestaande sends (ongewijzigd)
  22: print mixer-unknown-fudi (ongewijzigd object, ongewijzigde positie)
  23: s ttb-route-local (NIEUW)
  24: s ttb-route-live (NIEUW)

Connects:
  - bestaande catch-all 1 20 22 0 -> 1 22 22 0
  - nieuw 1 20 23 0 (ttb-route-local)
  - nieuw 1 21 24 0 (ttb-route-live)

Marker: TTB-ROUTE-MIXER-ROUTER-V1.
"""
import shutil, sys
from datetime import datetime
from pathlib import Path

V2 = Path.home() / "Documents/Pd/PDMixer/v2"
TARGET = V2 / "mixer-router.pd"
BACKUPS = V2 / "_backups"
MARKER = "TTB-ROUTE-MIXER-ROUTER-V1"

OLD_ROUTE = "#X obj 20 60 route ch1-vol ch1-pan ch1-gate ch1-fx ch2-vol ch2-pan ch2-gate ch2-fx ch3-vol ch3-pan ch3-gate ch3-fx ch4-vol ch4-pan ch4-gate ch4-fx masterVol masterPan hpVol fxReturn;"
NEW_ROUTE = "#X obj 20 60 route ch1-vol ch1-pan ch1-gate ch1-fx ch2-vol ch2-pan ch2-gate ch2-fx ch3-vol ch3-pan ch3-gate ch3-fx ch4-vol ch4-pan ch4-gate ch4-fx masterVol masterPan hpVol fxReturn ttb-route-local ttb-route-live;"

OLD_CATCH = "#X connect 1 20 22 0;"
NEW_CATCH = "#X connect 1 22 22 0;"

PRINT_LINE = "#X obj 20 250 print mixer-unknown-fudi;"

NL = chr(10)
INSERTED = (
    PRINT_LINE + NL
    + "#X obj 250 280 s ttb-route-local;" + NL
    + "#X connect 1 20 23 0;" + NL
    + "#X obj 480 280 s ttb-route-live;" + NL
    + "#X connect 1 21 24 0;" + NL
    + "#X text 600 20 " + MARKER + ";"
)

text = TARGET.read_text()

if MARKER in text:
    print("Marker " + MARKER + " reeds aanwezig; geen wijziging.")
    sys.exit(0)

for label, needle in [("OLD_ROUTE", OLD_ROUTE), ("OLD_CATCH", OLD_CATCH), ("PRINT_LINE", PRINT_LINE)]:
    if text.count(needle) != 1:
        print("ERROR: " + label + " niet exact 1x gevonden. Bail.")
        sys.exit(1)

BACKUPS.mkdir(exist_ok=True)
ts = datetime.now().strftime("%Y%m%d-%H%M%S")
backup = BACKUPS / ("mixer-router.pd." + ts + ".bak")
shutil.copy(TARGET, backup)
print("Backup: " + str(backup))

new_text = text.replace(OLD_ROUTE, NEW_ROUTE, 1)
new_text = new_text.replace(OLD_CATCH, NEW_CATCH, 1)
new_text = new_text.replace(PRINT_LINE, INSERTED, 1)

TARGET.write_text(new_text)
print("Wrote " + TARGET.name + ": +2 routes, +2 sends, +2 connects, marker")
