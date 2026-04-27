# Pd status-broadcast multiplicatie — diagnose 27 april 2026

## Symptoom
Tijdens fase 2-implementatie zagen we sampler-status events 9 maal binnenkomen
op bridge per actie. Een recording-event leidde tot 9 archief-kopieen
(zelfde timestamp, zelfde file, history-array groeide met 9 entries).

## Initiele hypothese
"Pd-architectuur dupliceert broadcasts." 9 = 1 router + 8 slot-instances.
We bouwden een dedupe in bridge (SAMPLER-EVENT-DEDUPE-V1, commit a025979)
om er tegen te beschermen. Onderzoek naar de werkelijke oorzaak werd
genoteerd als open issue.

## Onderzoek (deze sessie)
- Status-broadcasts in slot-N.pd: een keten per file, geen fanout.
- r sampler-status-out slechts 1 maal in actief-toplevel-bestand
  (touchlab-mixer-ttb.pd). sampler-host.pd heeft er ook een maar wordt
  niet geinstantieerd.
- Geen netsend in slot of router abstractions; alle UDP-uitgang
  zit in top-level patch.
- Geen fanout in upstream walks vanaf de list append recording-broadcast.

## Werkelijke oorzaak
Geen Pd-architectuur-bug. Multiplicatie was een artefact van Pd-state
ophoping in long-running Pd-instances: wanneer Pd lange tijd openstond
en de connect-msg-box meermaals werd geklikt (of patches herladen),
hoopte de netsend-keten state op zodat een broadcast effectief meerdere
keren werd verzonden.

## Verificatie
Na pkill Pd-0.55 + open touchlab-mixer-ttb.pd (verse start) zagen we
exact 5 events per rec, geen duplicaten: input ch1, autotrim-done,
recording, autotrim-done, rec-stopped.

## Conclusies
- Bridge-side dedupe blijft nuttig als verdedigingslaag tegen long-running
  Pd-state-bagage. Geen workaround voor architectuur-bug; gewoon
  defensief programmeren.
- Werkadvies: Pd herstarten na langdurige debug-sessies. Vermijd
  meermaals klikken op connect-msg-boxen; een keer is genoeg.
- Open issue 1 is hierbij gesloten.
