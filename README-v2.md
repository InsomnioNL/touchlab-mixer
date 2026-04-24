# TouchLab Sampler — v2 (unverified)

**Status:** werk-in-uitvoering, nog niet geverifieerd in PD.

## Wat is er nieuw in v2

1. **Per-slot autotrim threshold en preroll** — elke slot heeft eigen waarden (was globaal)
2. **Configureerbare input-source per slot** — kies ch1..chN of master (default ch1)
3. **Nieuwe `sampler-router.pd` abstractie** — centraal schakelpunt voor alle input-routing
4. **Nieuwe FUDI-commando's:**
   - `sampler-router-input <slot> <source>` — bv. `sampler-router-input 3 ch2`
   - `sampler-autotrim-threshold <slot> <dB>` — was zonder slot-arg
   - `sampler-autotrim-preroll <slot> <ms>` — was zonder slot-arg

## Let op — voorbehouden

- Ik heb de gegenereerde patches **niet in PD kunnen laden** om te verifiëren dat ze syntactisch correct zijn
- De host-generator had een late fix om connections te bufferen aan het einde (PD-syntax-vereiste)
- Volgende sessie begin ik met een verificatie-run

## Installatie

Kopieer deze hele map naar:
```
/Users/ulrichpohl/Documents/Pd/PDMixer/v2/
```

(naast je bestaande mixer-bestanden — de v1 sampler blijft intact op z'n huidige locatie).

## Eerste test (als je wilt proberen voor de volgende sessie)

1. Stop eventuele draaiende PD:
   ```bash
   pkill -f "Pd-0.55-2"
   ```

2. Open `sampler-host.pd` in v2/ via Finder dubbelklik (let op: mic-permissie)

3. Als 'm zonder errors opent:
   - Check in PD's console of je ziet:
     - 8x `autotrim-threshold-recv: -40`
     - 8x `autotrim-preroll-recv: 50`
   - Geen `error:` regels

4. Als 't mis gaat: **kijk naar welke objecten PD rood markeert** (misgebouwd) — dat is de feedback die ik volgende sessie nodig heb.

## Structuur

```
session.json                    — config (channels + sampler + ttb secties)
sampler-slot-1.pd               — TEMPLATE (hand-geëdit, 5 wijzigingen)
sampler-slot-2..8.pd            — gegenereerd uit template door generate-slots.py
sampler-router.pd               — NIEUW: input router + autotrim dispatcher
sampler-host.pd                 — test-host (met mock adc~ source-taps)
generate-slots.py               — bijgewerkt (kent router, kent sampler-router-input)
generate-router.py              — NIEUW
```

## Volgende stappen (niet in deze v2)

- Integratie in `touchlab-mixer.pd` (update `generate-mixer.py`)
- Bridge.js uitbreiden met sampler-messages
- Frontend: TTB grid + modal

---
*v2 gemaakt in sessie van 24 april 2026, jungle-tijd.*
