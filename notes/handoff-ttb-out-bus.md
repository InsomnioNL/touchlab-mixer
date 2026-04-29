# Handoff — TTB-out-bus naar JackTrip via QjackCtl

**Datum:** 29 april 2026
**Voor:** collega die JackTrip/QjackCtl beheert
**Aanleiding:** Pd-kant van TTB-out is af. QjackCtl-kant moet erbij.

## Wat er aan Pd-kant veranderd is

`master-section.pd` heeft nu een nieuwe TTB-out-tak. Beide `dac~`-paren
zijn nu functioneel onderscheiden:

| Pd-bron               | Pd-bestemming | Wat het is                                       |
| --------------------- | ------------- | ------------------------------------------------ |
| Master-mix (mics + binnenkomende JackTrip) | `dac~ 1 2` | Uli's koptelefoon-monitor                        |
| TTB-bus (8 slots gesommeerd)               | `dac~ 3 4` | TTB-uitgang richting collega's via JackTrip-send |

Alle 8 sampler-slots schrijven naar dezelfde gemeenschappelijke
`throw~ ttb-bus-L/R`. Master-section ontvangt op `catch~ ttb-bus-L/R`
en routeert naar `dac~ 3 4`. Bus-sommatie gebeurt automatisch in Pd.

Bestaande functies zijn ongewijzigd:
- Per-slot `dac~` (output 1+2) blijft staan voor lokale monitoring —
  zonder JackTrip-loop is dat de enige manier om af te spelen sample
  zelf te horen.
- `masterVol` regelt nog steeds `dac~ 1 2`-niveau zoals voorheen.
- `sampler-master-vol` regelt globale TTB-uitgangsterkte (vóór de tap
  naar de bus, dus geldt voor zowel de lokale `dac~` als de TTB-out).

## Wat er aan QjackCtl-kant moet gebeuren

In de connections-graph van QjackCtl wijzigingen op `pure_data:output_3`
en `pure_data:output_4`:

- **Voorheen** (vermoedelijk): niet of nauwelijks gewired. De oude tak
  was de `hpVol`-tak — die had geen UI-controle en dus waarschijnlijk
  geen functioneel doel.
- **Voorgestelde nieuwe routing:** `pure_data:output_3` en
  `pure_data:output_4` wiren naar dezelfde JackTrip-send-input(s) waar
  de mic ook al naartoe gaat. Bij collega's komt het binnen als deel
  van Uli's audio-line, samen met de mic.

Geen aparte JackTrip-kanalen voor TTB. TTB lift mee op de mic-stream.

## Verificatie aan jouw kant

Nadat je de routing gewijzigd hebt, kunnen we samen verifiëren:
1. Pd open + bridge draaiend bij Uli
2. Uli speelt een sampler-slot af
3. Een testcollega (of jij via JackTrip-loop) hoort de sample
   binnenkomen op Uli's audio-line, samen met de mic-take

## Open vragen voor jou

Tijdens het architectuur-werk zijn een paar dingen onduidelijk
gebleven die alleen jij kunt verifiëren:

1. **Wat staat er nu op `pure_data:output_3+4`?** Aangewired aan iets,
   of nergens naartoe? Dat bepaalt of we iets bestaands ombuigen of
   een lege output activeren.

2. **Hoe is mic → JackTrip geconfigureerd?** Via Pd (zodat ch1 de mic
   kan tappen) of direct van de audio-interface, of beide? Uli's
   sampler-source-selector heeft `ch1—Bas` als optie en heeft daar
   recentelijk op opgenomen — wat suggereert dat de mic via een
   Jack-loop in Pd binnenkomt op `pure_data:input_1`. Klopt dat?

3. **Is er een Tonmeister-mic-only-stream?** Zo ja: hoe is die
   gerouteerd? Mic dubbel naar twee JackTrip-instances, of een ander
   mechanisme?

## Wat dit níet raakt

- JackTrip-config zelf (bitrate, latency, peers): geen wijziging.
- Bridge / UI / WebSocket: geen wijziging.
- Andere Pd-files dan `master-section.pd` en `sampler-slot-*.pd`:
  geen wijziging.
- Uli's startup-procedure: geen wijziging.

## Rollback indien nodig

In `_backups/` staan de pre-patch versies van `master-section.pd` en
`sampler-slot-1.pd`. Slots 2-8 worden gegenereerd uit slot-1 template
via `generate-slots.py`. Cleane rollback dus mogelijk per file.

## Commits

- `2465b64` — TTB-out-bus in master-section.pd
- `6e4dd6b` — TTB-out-bus tap voor slot-1
- `8ab869f` — TTB-out-bus tap voor slots 2-8

## Vervolgsessies (niet voor jou — voor Uli + Claude)

- Centrale TTB-monitor-toggle (zodat Uli ook zonder JackTrip kan
  testen, en/of de lokale TTB-monitor uit kan zetten)
- Rename `masterVol` → `monitorVol`, `master-section.pd` →
  `monitor-section.pd` (architectuur-cleanup)
- Cleanup orphan hpVol-objecten in master-section.pd
- TTB-OUT-PATCH absorberen in `generate-mixer.py` (zodat `regen.sh`
  niet meer onze patch overschrijft)
