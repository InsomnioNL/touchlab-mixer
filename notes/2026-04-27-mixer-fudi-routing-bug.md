# Mixer-FUDI routing-bug — diagnose 27 april 2026

## Symptoom
Mixer-controls vanuit de browser (channel-pan, channel-vol, masterVol,
hpVol) lijken te werken op bridge-niveau maar bereiken Pd niet:
- Bridge logt PAN-DBG voor elke knopbeweging.
- Bridge schrijft FUDI-bevelen naar de TCP-socket op poort 9000.
- TCP-verbinding tussen bridge en Pd is ESTABLISHED (geverifieerd
  via lsof).
- Toch triggert geen enkele [r ch1-pan], [r ch1-vol], etc. in Pd.

Deze bug bleef onopgemerkt omdat:
- Master-volume lijkt te werken na bewegen (mogelijk audio-route via
  loadbang-default 0.8, niet via slider-update).
- Sampler-FUDI op poort 9002 werkt prima (heeft fudiparse + route
  keten erachter).
- VU-data van Pd naar bridge werkt (UDP poort 9001, eigen keten).

## Diagnose
Live testen (Pd open, bridge aan, browser pan-knop draaien):
- Bridge stuurt: 'PAN-DBG ch1 pan=0.7' x100+ regels
- ch1.pd debug [print PAN-CH1]: alleen loadbang-default 0.5, geen
  enkele update na browser-actie.
- Direct nc-test naar 9000:
    echo "ch1-pan 0.9" | nc 127.0.0.1 9000        -> niets
    echo "; ch1-pan 0.9;" | nc 127.0.0.1 9000      -> niets
    printf "\\; ch1-pan 0.9;\n" | nc 127.0.0.1 9000 -> niets

netreceive 9000 ontvangt de bytes wel maar genereert geen output.

## Werkelijke oorzaak
netreceive 9000 in touchlab-mixer-ttb.pd (en touchlab-mixer.pd) staat
als losstaand object zonder fudiparse + route-keten erachter. De
aanname dat Pd's netreceive met '; receiver value;'-input automatisch
naar [r receiver] routet was onjuist.

In de eerste versie (commit 0118ff0, 'TouchLab Mixer eerste versie')
stond netreceive 9000 al zonder fudiparse. De keten heeft dus ofwel
nooit gewerkt voor pan/vol-controls, of werkte ooit met een ander
bericht-format dat we sindsdien zijn kwijtgeraakt.

## Werkende referentie
Sampler-FUDI op poort 9002 heeft de juiste structuur:

    netreceive -u -b 9002
        |
    fudiparse
        |
    route sampler-load sampler-play ... sampler-rec-path
        |
    [verschillende s-objecten per route]
    [print sampler-unknown-fudi voor catch-all]

Deze keten werd toegevoegd in commit 8c56358 (rec-path: bridge-driven
write-path injection slot-1) als onderdeel van de TTB-integratie.

## Fix (volgende sessie)
write_main en write_main_ttb in generate-mixer.py uitbreiden met
fudiparse + route-keten na netreceive 9000. Routes nodig (per huidige
sendPD-aanroepen in bridge.js):
- ch1-vol, ch2-vol, ch3-vol, ch4-vol
- ch1-pan, ch2-pan, ch3-pan, ch4-pan
- ch1-gate, ch2-gate, ch3-gate, ch4-gate
- ch1-fx, ch2-fx, ch3-fx, ch4-fx
- masterVol, hpVol, fxReturn

Per route een [s ch{N}-{type}]-object koppelen. Catch-all met [print
mixer-unknown-fudi].

Idempotent patch-script + regen.sh + end-to-end test (browser pan
moet hoorbaar verschil L/R geven met mono-mic).

## Gerelateerde issues
- Master-volume initialisatie bij startup (open issue 3): mogelijk
  zelfde oorzaak. Fader staat ~80% maar audio is stil tot bewegen.
  Met deze fix zou de eerste broadcast vanaf bridge eindelijk de
  line~ in master-section vanuit z'n loadbang-default kunnen wakker
  schudden.

- Stereo VU master-L vs master-R altijd identiek: gevolg van mono-mic
  + pan op midden. Met deze fix zou pan in browser eindelijk hoorbaar
  L/R-verschil opleveren.

## Status
Open issue, hoogste prioriteit voor volgende sessie.
