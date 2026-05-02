# Feature scope — MIDI/OSC-trigger voor TTB queue

**Datum:** 2 mei 2026 (revisie 5)
**Status:** scope-document, ontwerp afgerond, implementatie nog niet gestart
**Vorige versies:** 1 mei 2026, 2 mei 2026 revisies 2, 3 en 4
**Doel:** documenteren van het ontwerp voor protocol-agnostische trigger-input (MIDI of OSC) waarmee een muzikant of dirigent TTB-cues uit de queue kan triggeren zonder de tablet te hoeven aanraken.

## Wat veranderd is sinds revisie 4

- **Keyboard als derde first-class protocol in v1.** UI vangt keystrokes op via `keydown`/`keyup`, stuurt ze via WebSocket door naar bridge. Geen externe OS-keymap-tools meer nodig.
- **HID-pedalen (Firefly etc.) ondersteund in v1**, niet meer v2, via de keyboard-protocol-route. BLE-HID-pedaal pairt als BLE-keyboard met de iPad/Mac/etc., browser ontvangt keystrokes, UI routeert door.
- **Multi-functie HID-pedalen**: bij modellen met configureerbare keystrokes per knop (bijv. 4-pedaal Firefly) kunnen sommige knoppen aan bladmuziek-app blijven gemapt en andere aan TouchLab-trigger-acties — zonder cross-app-conflict.
- **OS-keymap-tool-aanpak (Karabiner/AutoHotkey/xdotool) verwijderd uit scope.** Was overcomplexity gegeven dat browsers de keystrokes al direct ontvangen.

## Wat veranderd is sinds revisie 3

- **Bluetooth MIDI-pedalen impliciet ondersteund in v1** via OS-MIDI-stack (CoreMIDI op macOS, ALSA-MIDI op Linux). easymidi ziet ze als gewone MIDI-input zodra OS-niveau-pairing gedaan is. Geen extra implementatie nodig.
- **HID-pedalen (Firefly etc.) naar v2** via OS-keymap-tool-routing — bridge blijft strict MIDI+OSC, geen HID-listener.
- **Bron-keuze MIDI-library**: easymidi (zie ADR-002).
- **Bron-keuze OSC-library**: node-osc (zie ADR-003).

## Wat veranderd is sinds 1 mei versie

- **OSC erbij als first-class protocol** naast MIDI. Bridge wordt protocol-agnostische event-router, niet MIDI-only luisteraar.
- **Vijf expliciete actie-types** (`pulse`, `gate`, `start`, `stop`, `pulse-or-gate`). De eerste vier zijn één-gedrag-per-mapping; `pulse-or-gate` heeft duur-onderscheid (kort=pulse, lang=gate) en hergebruikt de bestaande UI-trigger-duur-logica. Geen andere duur-detectie in v1 — actie-type wordt geleerd, niet afgeleid.
- **Multi-mapping per bron-stack**: gebruiker kan meerdere bron-naar-actie-mappings stapelen, mapping-schema is een array.
- **Hysterese-state-machine** in plaats van simpele binary-threshold-detectie. Vereist door piano sustain-pedalen die continue waarden 0-127 sturen.
- **Multi-sample learn-flow** (druk-houd-release) voor polariteit-detectie en range-bepaling.
- **OSC-poort configureerbaar in UI** met sane default. Geen hardcoded poort.
- **Mock-Pd-bron** als ontwikkel- en validatie-tool, geen hardware-blokker meer.
- **Multi-bron parallel** expliciet naar v2 verschoven (in tegenstelling tot multi-mapping, die wel in v1 zit — verschil zie hieronder).
- **Architectuurvragen 1-3** beantwoord (alle bridge-side).

## Aanleiding

Tijdens een sessie heeft de muzikant beide handen aan zijn instrument. TTB-cues triggeren via de tablet vereist los te laten, vooruit te kijken, te tikken — niet altijd haalbaar binnen de muzikale flow. Een trigger-bron naast het instrument lost dit op voor cues die vooraf gepland zijn in de queue.

Voor de dirigent geldt iets vergelijkbaars: tijdens dirigeren is fysieke tablet-interactie niet praktisch. Een Leap-sensor die handgebaren herkent en via Glover als OSC of MIDI naar bridge stuurt, biedt aanraakvrije bediening.

De feature is bedoeld voor elke gebruiker met een frontend, niet alleen voor Uli. Verschillende gebruikers gebruiken verschillende trigger-bronnen: USB-MIDI-pedalen, keyboards met sustain-pedaal, drumpads, Leap-sensoren via Glover, of BLE-HID-pedalen die als toetsenbord pairen (zoals PageFlip Firefly — vaak al in gebruik voor bladmuziek-apps op iPad). Het systeem moet flexibel kunnen omgaan met de specifieke signalen die elke bron stuurt — vandaar protocol-agnostische learn als onderdeel van v1.

## Mentaal model

Eén of meer trigger-bronnen, elk gemapt aan een specifieke actie. Triggers werken op de queue (volgende slot) of op het huidig spelende slot (stop). Vier actie-types dekken alle gebruiksscenario's tot nu toe.

## Functionele scope v1

### Vijf actie-types

| Actie | Wat doet bridge bij trigger-event | Wat gebeurt bij release-event |
|---|---|---|
| `pulse` | Speel volgende slot uit queue, slot eindigt natuurlijk | Queue stept naar volgende positie |
| `gate` | Speel volgende slot uit queue | Stop slot, queue stept naar volgende positie |
| `start` | Speel volgende slot uit queue, slot blijft actief | (geen actie) |
| `stop` | Stop huidig spelende slot | (geen actie, queue stept hier al) |
| `pulse-or-gate` | Speel volgende slot uit queue | Bij held-duur < threshold: queue stept (pulse-gedrag). Bij held-duur ≥ threshold: stop slot + queue stept (gate-gedrag). |

`pulse` en `gate` verschillen alleen in wat er met de slot gebeurt tijdens de actieve periode — beide steppen de queue op release. `start`/`stop` is een paar voor expliciete play-en-stop-toggle (typisch via twee verschillende Glover-gestures). `pulse-or-gate` combineert pulse en gate op één signaal via duur-meting — bestaande UI-trigger-logica wordt hier hergebruikt.

**Globale duur-threshold voor `pulse-or-gate`**: één instelling voor alle `pulse-or-gate`-mappings, default 250ms (overeenkomstig met UI-trigger), configureerbaar in UI. Niet per-mapping om configuratie te eenvoudig houden.

### Multi-mapping

Gebruiker kan meerdere bron-naar-actie-mappings tegelijk geconfigureerd hebben. Bij elk inkomend event matcht bridge tegen alle mappings; de matchende mapping bepaalt welke actie uitgevoerd wordt.

**Niet hetzelfde als multi-bron-parallel (v2):** v1 staat meerdere mappings toe, maar gaat ervan uit dat één gebruiker tegelijk triggert. Multi-bron-parallel zou betekenen: twee gebruikers (bijv. dirigent + bassist) tegelijk eigen queue-trigger-acties uitvoeren, met conflict-resolutie. Dat is v2.

### Use-case-voorbeelden

- **Eén pedaal, pulse-modus**: muzikant heeft DIY-box (jack→USB MIDI). Eén mapping: CC 64 → `pulse`. Elke trap triggert volgend slot, slot eindigt natuurlijk.
- **Eén pedaal, gate-modus**: muzikant wil sample stoppen op moment van loslaten. Eén mapping: CC 64 → `gate`. Voet erop = sample speelt, voet eraf = sample stopt + queue stept.
- **Eén pedaal, dynamisch (kort vs lang)**: muzikant wil dezelfde pedaal-bediening als de UI-trigger. Eén mapping: CC 64 → `pulse-or-gate`. Korte trap = sample speelt door tot natural end. Lange trap = sample stopt bij loslaten. Hergebruikt bestaande UI-trigger-duur-logica.
- **Glover toggle voor dirigent**: twee gestures, twee mappings. `/glover/fist-1` → `start`, `/glover/fist-2` → `stop`. Eerste vuist start volgend slot, tweede vuist stopt en stept.
- **4-pedaal Firefly gedeeld met forScore**: pedaal 1+2 op default page-up/page-down (forScore vangt deze in eigen app), pedaal 3+4 in PageFlip-config-app op F13/F14 gemapt. TouchLab-UI vangt F13/F14 alleen wanneer focused. Twee mappings: `keyboard F13` → `pulse`, `keyboard F14` → `stop`. Bladmuziek-omslaan en sample-trigger werken simultaan via één gepaird BLE-pedaal.
- **Pedaal + Glover gemixt**: drie mappings actief. CC 64 → `pulse-or-gate` (rappe one-shots of vasthoud-bediening tijdens spel), `/glover/fist-1` → `start`, `/glover/fist-2` → `stop` (langere uitgesponnen samples).

### Lege queue

Voor `pulse`/`gate`/`start`/`pulse-or-gate`: bron triggert het laatst-getriggerde slot opnieuw, met dezelfde modus. Bij eerste sessie-start zonder eerdere triggers: trigger doet niets, visuele feedback in UI dat queue leeg is en geen fallback beschikbaar.

`stop` op lege queue is een no-op (niets om te stoppen).

### UI

Lijst van geconfigureerde mappings, telkens met:
- Actie-label (`pulse`/`gate`/`start`/`stop`/`pulse-or-gate`)
- Bron-info (`MIDI CC 64 op kanaal 1`, `OSC /glover/fist-1`, etc.)
- Verbindings-status (matchend signaal recent gezien?)
- Verwijder-knop

Knop "trigger toevoegen" → dropdown actie-type kiezen (vijf opties) → "druk + houd + laat los op je bron" → mapping toegevoegd. Tijdens learn live preview van wat bridge ziet binnenkomen, zodat gebruiker direct weet of zijn bron wordt opgepikt.

Onder de mappings-lijst: globale instellingen-sectie met OSC-poort en `pulse-or-gate`-duur-threshold (default 250ms). Beide met "wijziging actief na bridge-restart" hint waar relevant — OSC-poort vereist restart, duur-threshold kan live (bridge leest de waarde elke keer dat een release-event verwerkt wordt).

### OSC-poort configureerbaar

Default OSC-poort: 9100 (vermijdt conflict met huidige Leap→Max op 9000 en bridge-Pd-TCP op 9000). UI heeft instelling onder "trigger-instellingen" of vergelijkbaar pad. Wijziging vereist bridge-restart om effect te hebben — UI toont expliciet "wijziging actief na bridge-restart" bij save.

Mapping wordt niet ongeldig bij poort-wijziging — alleen het luister-eindpunt verandert.

## Wat NIET in v1 zit

- **Multi-bron parallel** — twee gebruikers tegelijk eigen mappings, met conflict-resolutie. v2.
- **Configureerbare modifier-acties** — bijv. "spring naar slot N", "skip queue-positie". v1 heeft alleen vijf vaste actie-types.
- **Visuele indicator van laatst-getriggerde slot.**
- **Sessie-specifieke mapping** — één globale mapping-array per gebruiker, in `session.json`.
- **Pad-wildcards voor OSC** (`/leap/finger/*/y`) — v1 vereist exacte match.
- **Typed-value-routing** (verschillende OSC-types verschillende dingen).
- **Conflict-detectie tussen mappings** — bridge waarschuwt niet als gebruiker hetzelfde signaal aan twee acties mapt, of `start` zonder `stop`-tegenhanger configureert. v2.
- **Duur-onderscheid op andere actie-paren** dan pulse↔gate (bijv. start↔stop op één signaal). v1 heeft alleen `pulse-or-gate` als duur-gebaseerde actie. v2 indien nodig.
- **Per-mapping duur-threshold** — één globale waarde voor alle `pulse-or-gate`-mappings.
- **MIDI- of OSC-output** (TouchLab → externe controller).

## Architectuurbeslissingen

### 1. Waar gebeurt input-detectie? → Bridge voor MIDI/OSC, UI voor keyboard

Bridge gebruikt twee server-side listeners:

- **MIDI-listener** via Node.js MIDI-library (zie ADR-002: easymidi).
- **OSC-listener** via Node.js OSC-library (zie ADR-003: node-osc) op UDP-poort, default 9100, configureerbaar via UI.

UI gebruikt één client-side listener:

- **Keyboard-listener** via DOM `keydown`/`keyup`-events op `window`. Filtert `event.repeat` om OS-key-repeat te negeren. Bij relevante keystroke (alle keystrokes tijdens learn-fase, of alleen gemapte keystrokes daarna): `event.preventDefault()` en stuur door naar bridge via WebSocket.

Alle drie listeners normaliseren naar **één interne event-vorm** voor downstream verwerking:

```
{
  protocol: "midi" | "osc" | "keyboard",
  source: <device-name | osc-source-address | "ui">,
  signature: <protocol-specifiek, zie mapping-schema>,
  value: <number, 0..1 voor OSC, 0..127 voor MIDI, 0 of 1 voor keyboard>,
  timestamp: <ms>
}
```

Voor keyboard-events: bridge ontvangt het event via WS van UI (in plaats van direct van een listener). Verder is downstream-behandeling identiek.

Dit faciliteert toekomstige protocol-uitbreiding (HID-direct, network controllers) zonder herontwerp.

### 2. Waar woont de mapping? → Bridge-state in `session.json`

Mapping leeft op het audio-eindpunt zelf. Persistent, beschikbaar voor elke browser die met dat eindpunt verbindt.

**Schema (array van mapping-objecten):**

```json
{
  "triggers": [
    {
      "action": "pulse",
      "protocol": "midi",
      "signature": {
        "type": "cc",
        "channel": 1,
        "number": 64
      },
      "polarity": "normal",
      "thresholdActive": 70,
      "thresholdInactive": 58,
      "valueRange": { "min": 0, "max": 127 }
    },
    {
      "action": "start",
      "protocol": "osc",
      "signature": {
        "path": "/glover/fist-1",
        "valueIndex": 0
      },
      "polarity": "normal",
      "thresholdActive": 0.55,
      "thresholdInactive": 0.45,
      "valueRange": { "min": 0.0, "max": 1.0 }
    },
    {
      "action": "stop",
      "protocol": "osc",
      "signature": {
        "path": "/glover/fist-2",
        "valueIndex": 0
      },
      "polarity": "normal",
      "thresholdActive": 0.55,
      "thresholdInactive": 0.45,
      "valueRange": { "min": 0.0, "max": 1.0 }
    },
    {
      "action": "pulse",
      "protocol": "keyboard",
      "signature": {
        "key": "F13"
      },
      "polarity": "normal"
    }
  ],
  "oscPort": 9100,
  "pulseOrGateThresholdMs": 250
}
```

Voor `protocol: "keyboard"` zijn `thresholdActive`, `thresholdInactive`, `valueRange` weggelaten — keystrokes zijn binair en hebben geen hysterese-tuning nodig. `polarity` blijft formeel aanwezig maar staat altijd op `"normal"` (keystroke = active, geen-keystroke = inactive).

`polarity` is `normal` (active = high) of `inverted` (active = low) — afgeleid tijdens learn.

### 3. Threshold-detectie en hysterese → Bridge

State-machine met twee thresholds, niet één. Voorkomt jitter rond drempel die anders als reeks down/up-events zou worden geïnterpreteerd. Vooral relevant voor:

- Piano sustain-pedalen (Yamaha FC3, Roland DP-10) met continue waarden over de hele pedaal-slag
- Leap-gestures via Glover, waar gesture-confidence als float fluctueert
- Drumpads met velocity-variatie

Voor keyboard-events is hysterese triviaal: `value` is altijd 0 of 1. Bridge passeert direct van INACTIVE naar ACTIVE op keydown (`value: 1`) en terug op keyup (`value: 0`). Geen thresholds gebruikt — voor `protocol: "keyboard"` slaat bridge de hysterese-vergelijking over.

**State-machine per mapping (MIDI/OSC):**

```
state = INACTIVE
on event(value):
  if state == INACTIVE and value >= thresholdActive:
    state = ACTIVE
    dispatch action.activate()   # action-specifiek, zie tabel
  elif state == ACTIVE and value <= thresholdInactive:
    state = INACTIVE
    dispatch action.release()    # action-specifiek
  else:
    # in dode zone, geen state-change
    pass
```

Voor binary-bronnen (DIY-box jack→USB die strict 0/127 stuurt) werkt dit triviaal — beide thresholds liggen in de dode zone tussen 0 en 127, dus elke event triggert state-change.

`action.activate()` en `action.release()` per actie-type:

| Actie | activate() | release() |
|---|---|---|
| `pulse` | `samplerPlay(slot=ttbQueue[ttbQueuePos])` | `queueAdvance` |
| `gate` | `samplerPlay(slot=ttbQueue[ttbQueuePos])` | `samplerStop` + `queueAdvance` |
| `start` | `samplerPlay(slot=ttbQueue[ttbQueuePos])` | (geen) |
| `stop` | `samplerStop(currentlyPlayingSlot)` + `queueAdvance` | (geen) |
| `pulse-or-gate` | `samplerPlay(slot=ttbQueue[ttbQueuePos])`, start held-timer | If held-duur < `pulseOrGateThresholdMs`: `queueAdvance`. Else: `samplerStop` + `queueAdvance`. |

Voor `pulse-or-gate` houdt bridge per active mapping een timestamp bij van het activate-moment, en vergelijkt op release tegen `pulseOrGateThresholdMs` om te beslissen welk release-pad te volgen. Dit is dezelfde logica die de UI-trigger al gebruikt voor finger-push — code-pad hergebruiken indien praktisch.

### 4. Gate-mode in queue-context → al beantwoord

Code-analyse van `buildTriggerButton` bevestigde dat `samplerPlay`/`samplerStop`-events naar bridge slot-gebonden zijn, niet queue-gebonden. Bridge en Pd weten niet of een trigger via queue-tap of directe tap kwam. Conclusie: gate-mode werkt al in queue-context, geen blokker.

UI-flow is in vorige sessie gelijkgetrokken (`QUEUE-ADVANCE-ON-RELEASE-V1`-marker): queue-progressie gebeurt op release-event, consistent met geplande trigger-flow.

### 5. Hot-plug-detectie → buiten v1-validatie-scope

Bij MIDI-IAC-bus en OSC-UDP is hot-plug niet emuleerbaar (poorten zijn altijd present). Bridge implementeert wel device-detection bij startup en hot-plug-handlers, maar **werkelijke validatie wacht op pedaal-arrival**. Markeren als "v1.1 hardware-validatie-pass."

## Bronnen die v1 moet ondersteunen

| Bron | Protocol | Signaal | Polariteit | Validatie |
|---|---|---|---|---|
| DIY-box (jack→USB MIDI) | MIDI | CC binary 0/127 | normal | Pedaal-arrival |
| Piano sustain (FC3, DP-10) | MIDI | CC continuous 0-127 | normal | Pedaal-arrival |
| Keyboard met sustain | MIDI | CC + andere events (filter via mapping) | normal | Hardware-arrival |
| Drumpad | MIDI | Note On/Off met velocity | normal | Hardware-arrival |
| BLE MIDI-pedaal (iRig BlueBoard, AirTurn-MIDI-modus) | MIDI via BLE → CoreMIDI/ALSA | CC of Note On/Off, model-afhankelijk | model-afhankelijk | BLE-pedaal-arrival |
| BLE-HID-pedaal (PageFlip Firefly etc.) | keyboard via BLE | keystroke binary | normal | Pedaal-arrival, mock via gewone toetsenbord-input |
| Glover + Leap | OSC of MIDI | gesture float of CC | normal | **Beschikbaar nu** |
| Mock-Pd-patch | MIDI (IAC) en OSC (UDP) | configureerbaar | beide | **Beschikbaar nu** |

### Bluetooth MIDI in v1

Bluetooth-MIDI-pedalen werken zonder bridge-aanpassingen. Werkwijze voor gebruiker:

1. **macOS**: Audio MIDI Setup → MIDI Studio → Bluetooth Configuration → pedaal koppelen
2. **Linux**: `bluez` + `aseqdump` voor BLE MIDI; soms vereist `bluez-alsa` of vergelijkbare bridge
3. Daarna verschijnt het pedaal als gewone MIDI-input, easymidi pikt het op via `getInputs()`

Geen aanpassingen aan bridge of UI. Standaard learn-flow, standaard mapping. **Latency-caveat:** BLE MIDI is ~10-30ms versus ~1-3ms voor wired USB MIDI; in fase 5 hardware-validatie meten of dat acceptabel is voor onze use-cases.

### BLE-HID-pedalen (Firefly etc.) in v1

BLE-HID-pedalen pairen als BLE-keyboard met het apparaat waar TouchLab-UI op draait (typisch iPad). Browser ontvangt `keydown`/`keyup`-events voor de keystrokes die het pedaal stuurt. UI vangt de events op, stuurt door naar bridge via WebSocket.

**Werkwijze voor gebruiker (Firefly als voorbeeld):**

1. Pedaal pairen met iPad via iOS Bluetooth-instellingen — verschijnt als toetsenbord
2. Optioneel: PageFlip-config-app gebruiken om per pedaal-knop een specifieke keystroke te kiezen. Voor pedalen die ook bladmuziek-app moeten bedienen (forScore, etc.): laat die knoppen op page-up/page-down staan, zet de "extra" knoppen op een keystroke die forScore *niet* gebruikt — F13 t/m F19 zijn veilige keuzes
3. Open TouchLab-UI in Safari op de iPad
4. In TouchLab-mappings-UI: klik "trigger toevoegen" → kies actie → druk pedaal-knop → mapping geleerd

**Co-existence met bladmuziek-apps**: TouchLab-UI doet `event.preventDefault()` op gemapte keystrokes — die gaan dus niet door naar andere keyboard-handlers binnen de browser-tab. Echter: zodra gebruiker naar een andere app schakelt (bijv. forScore), ontvangt TouchLab-UI geen events meer en gaan ze naar de focused app. Dit is precies het gewenste gedrag: tijdens spel staat TouchLab focused, sample-trigger-pedalen werken; tijdens lezen schakelt gebruiker naar forScore, bladmuziek-pedalen werken.

**Multi-functie-pedalen (zoals 4-pedaal Firefly)**: bij modellen waar elke knop een eigen keystroke kan sturen, zijn sommige knoppen aan bladmuziek-app en andere aan TouchLab-trigger gemapt — werkt simultaan zonder conflict mits de keystroke-keuzes uniek zijn.

**Caveats:**

- **UI-focus vereist.** Werkt alleen als TouchLab-tab focus heeft.
- **iPad-Safari-quirks**: niet alle keystrokes worden door Safari aan JS doorgegeven. Te valideren met test-pagina (bijv. `keyjs.dev`) voordat je nieuwe keys mapt.
- **Auto-repeat filteren**: UI gebruikt `if (event.repeat) return;` om OS-niveau-key-repeat te negeren tijdens lange-druk-detectie.

## Mock-Pd-bron

Pd-patch in `~/Documents/Pd/PDMixer/v2/dev-tools/` die fungeert als trigger-emulatie. Drie modi:

1. **Binary CC** — `[ctlout 64 1]` met bang op `127` voor down, `0` voor up. Emuleert DIY-box jack→USB.
2. **Continuous ramp** — `[line~]` of vergelijkbaar van 0→127→0 over instelbare duur (default 200ms). Emuleert piano sustain-pedaal. Valideert hysterese-state-machine.
3. **OSC** — `[netsend]` UDP naar localhost:`<configured-port>`, configureerbaar OSC-path. Emuleert Glover/Leap.

UI: drie momentary `[bng]`s (één per modus) of een tabbladsysteem. Te bepalen tijdens implementatie.

Locatie van mock-patch: aparte folder `dev-tools/`, niet in productie-Pd-pad. Wordt niet door regen.sh of andere build-scripts geraakt.

## Voorgestelde fasering

**Fase 1 — bridge dual-protocol input + UI keyboard-listener + WebSocket-events (~2.5u)**

- Bridge installeert MIDI-library + OSC-library
- Bridge bij startup: detecteer beschikbare MIDI-devices, open OSC UDP-listener op default-poort, log beide
- Bridge bij MIDI- of OSC-input: normaliseer naar interne event-vorm, stuur door als WebSocket-message naar UI
- UI implementeert keyboard-listener op `window`: `keydown`/`keyup` met `event.repeat`-filter, normaliseert naar interne event-vorm, stuurt naar bridge via WS (omgekeerde richting van MIDI/OSC)
- UI heeft live-debug-panel dat alle ruwe events toont (van alle drie protocollen, voor learn-fase)
- Test: mock-Pd MIDI binary → event in UI; mock-Pd OSC → event in UI; gewone toetsenbord-keystroke → event terug naar bridge
- Geen mapping, geen actie-dispatch nog — alleen detectie + transport

**Fase 1.5 — mock-Pd-patch (~1u)**

Kan parallel aan fase 1 of erna. Niet kritisch maar handig voor validatie van fase 1 zonder hardware. Drie modi (zie hierboven). Keyboard-events worden gemockt via gewone toetsenbord-input op de browser-tab — geen aparte mock nodig.

**Fase 2 — protocol-agnostische learn-UI + mapping-storage (~2u)**

- Mappings-lijst-UI: lege state, "+ trigger toevoegen" knop
- Add-flow: kies actie-type uit dropdown → "druk + houd + laat los op je bron" → bridge (of UI voor keyboard) accepteert eerstvolgende event-stream → leidt af: protocol, signature, polariteit, waarde-range, threshold-paar (sane defaults uit range) → mapping toegevoegd aan array
- Voor `protocol: "keyboard"`: minder velden — alleen `signature: { key }`, geen thresholds of range
- Mapping persistent in `session.json` op bridge
- Per mapping: actie-label, bron-info, status-indicator, verwijder-knop
- OSC-poort configuratie-veld onder mappings-lijst, met "wijziging actief na restart" hint

**Fase 3 — actie-dispatch met hysterese (~2u)**

- Bridge implementeert hysterese-state-machine per mapping
- Bij active-event: bridge dispatcht `action.activate()` zoals gespecificeerd in actie-tabel
- Bij release-event: bridge dispatcht `action.release()`
- FUDI naar Pd voor `samplerPlay`/`samplerStop`
- WS naar UI voor `queueAdvance`
- Bij lege queue: laatste-getriggerde slot als fallback-target voor `pulse`/`gate`/`start`
- UI ontvangt `queueAdvance`, doet `refreshAfterQueueChange()`

**Fase 4 — validatie + threshold-tuning (~30 min - 1u)**

- Test elk actie-type (`pulse`, `gate`, `start`, `stop`) met mock-Pd
- Test gate-mode in queue-context met mock-Pd continuous-ramp-modus
- Vind goede default-thresholds voor binary, continuous, en OSC-bronnen
- Test met Glover+Leap voor echte OSC-validatie
- Eventueel UI-config voor advanced threshold-tuning

**Fase 5 (post-pedaal) — hardware-validatie**

- Hot-plug-test met echt pedaal
- Latency-meting fysieke voet → audio-out, separat voor wired USB en BLE MIDI
- Hardware-specifieke quirks documenteren als gevonden
- Inversed-polarity-pedalen testen (DIY-converters)
- Firefly-pairing en multi-knop-mapping valideren met echte hardware

## Wat dit níet doet

- Geen MIDI-output (TouchLab → externe MIDI-controller), alleen input
- Geen OSC-output, alleen input
- Geen MIDI-clock-sync of timing-features
- Geen multi-bron-parallel (v2)
- Geen MIDI-routing voor instrument-MIDI (zoals een keyboard-controller voor noten)
- Geen "ene mapping triggert meerdere acties tegelijk" (v2 als nodig)

## Risico's en valkuilen

- **MIDI-library-keuze.** Verschillende Node.js-MIDI-libraries hebben verschillende cross-platform-eigenaardigheden, vooral bij hot-plug-detectie op Linux. Bij implementatie testen op alle target-OS.
- **OSC-library-keuze.** OSC-stacks verschillen in pattern-matching-completeness en bundel-handling. Voor v1 willen we minimaal: type-tags lezen, eerste argument als value pakken.
- **Hysterese-tuning per bron.** Default thresholds werken voor binary en sustain-pedalen, maar Leap/Glover gestures hebben heel andere ranges. Bij learn moet bridge sane defaults afleiden uit de geziene range — nog niet uitontworpen, te detailleren in fase 2.
- **Race-conditions bij snelle trigger-druk.** Wat als gebruiker drukt, loslaat, drukt voor de queue-step is verwerkt? Mogelijk debounce of queue-event-buffering nodig. Te valideren in fase 3.
- **Multi-mapping conflict.** Gebruiker mapt onbedoeld twee acties op hetzelfde signaal. Bridge dispatch-volgorde dan onbepaald — array-volgorde houden we als de facto regel, maar v1 valideert niet. Documenteren in UI als "let op: meerdere mappings op hetzelfde signaal mogelijk maar niet aanbevolen."
- **Inversed polarity-pedalen.** Sommige fabrikanten en DIY-converters sturen 0 op druk, 127 op release. Learn moet dit detecteren via de samples tijdens druk-houd-release. Falen-modus: gebruiker doet learn niet correct (drukt niet lang genoeg) → polariteit verkeerd geleerd. Mitigatie: learn-UI laat geleerde polariteit zien, gebruiker kan herhalen.
- **Glover-als-bron-kwetsbaarheid.** Glover stuurt continu data, niet discrete events. Voor queue-trigger-doel moet bridge een gesture-confidence-curve interpreteren als binary signaal — werkt prima voor "vuist gebald = active", gebruiker moet wel een gesture kiezen die binary genoeg is. Niet bridge's probleem; gebruiker-config in Glover.
- **OSC-poort-wijziging zonder restart.** Bridge moet UDP-listener netjes sluiten en heropenen. Bij falen blijft mogelijk oude listener actief, of crasht bridge. Te robust testen in fase 2.
- **`pulse-or-gate` duur-threshold-tuning.** Default 250ms is overgenomen van UI-trigger-logica, maar voet-mechaniek is trager dan vinger-touch. Mogelijk verstandig om voor pedaal-bronnen een hogere default te overwegen — kan empirisch afgesteld worden in fase 4 met mock-Pd. Voor v1 één globale waarde, gebruiker stelt zelf bij in UI als nodig.
- **BLE MIDI latency en jitter.** Bluetooth heeft inherent meer latency en variatie dan wired USB. Voor uitgesponnen samples acceptabel; voor strikte timing-bediening (sample op een 16e laten landen) merkbaar. Te valideren in fase 5. Mogelijk advies in documentatie: voor strikte timing wired pedaal gebruiken.
- **Browser-keystroke-quirks (iPad-Safari).** Safari geeft niet alle keystrokes door aan JS — sommige function-keys kunnen door iOS afgevangen worden. F13 t/m F19 zijn relatief veilig op iPad maar te valideren met `keyjs.dev` of vergelijkbare test-pagina voordat een mapping vastgelegd wordt.
- **TouchLab-UI moet focus hebben voor keyboard-events.** Trigger werkt niet als gebruiker naar andere app schakelt. Documenteren als verwacht gedrag — werkt typisch in gebruikers voordeel (bladmuziek-pedalen werken in bladmuziek-app, sample-trigger-pedalen in TouchLab), maar onbekend voor nieuwe gebruikers.
- **Keyboard-mapping-conflicten met andere browser-shortcuts.** Cmd+R, Cmd+T, etc. blijven browser-acties; `event.preventDefault()` kan ze niet onderscheppen. Bij learn-flow waarschuwen als gebruiker een browser-shortcut probeert te mappen.

## Open vragen voor implementatie-sessie

- MIDI-library-keuze (vergelijking opstellen aan begin van fase 1)
- OSC-library-keuze (idem)
- Mock-Pd-patch implementatie-details: welke Pd-objecten voor binary CC en continuous ramp, hoe UI organiseren
- Threshold-defaults bij learn: hoe sane defaults afleiden uit een geobserveerde range? Mogelijk: `thresholdActive = max - 30%`, `thresholdInactive = min + 30%` voor MIDI; voor OSC float: `thresholdActive = max * 0.55`, `thresholdInactive = max * 0.45`. Te valideren.
- UI-locatie van mappings-lijst: nieuwe sectie in main settings, eigen pagina, of modal? Hangt af van bestaande UI-structuur.
- `pulseOrGateThresholdMs` default: overnemen van UI-trigger-waarde (te checken in code) of standaard 250ms? En: live aanpasbaar of restart vereist?
- UI-trigger-duur-detectie-code lokaliseren en bekijken of bridge die letterlijk kan hergebruiken, of dat een eigen implementatie schoner is gegeven dat bridge geen pointerdown/pointerup heeft maar trigger-active/release.

## Volgende sessie startpunt

1. Lees deze note plus het meest recente overdrachtsdocument.
2. Beslis MIDI-library en OSC-library (kort vergelijkings-tabel in chat).
3. Bevestig mock-Pd-patch-locatie (`dev-tools/` voorgesteld) en OSC-default-poort (9100 voorgesteld).
4. Begin met fase 1 — pure detectie en transport, geen mapping nog. Pre-flight nodig (canonical startup, `pwd`-check, v2-first, idempotent met markers, backups).
5. Fase 1.5 (mock-Pd) parallel of erna.

## Verwijzingen

- ADR-001: Protocol-agnostische event-router voor trigger-input — in `notes/adr/`.
- ADR-002: MIDI-library-keuze easymidi — in `notes/adr/`.
- ADR-003: OSC-library-keuze node-osc — in `notes/adr/`.
- ADR-004: Keyboard als derde protocol in event-router — in `notes/adr/`.
- Architectuurvraag E in `overdrachtsdocument-werksessie-2026-05-01-avond.md`, sectie 3 — bevestigde gate-mode-werking in queue-context.
- `QUEUE-ADVANCE-ON-RELEASE-V1`-marker in UI-code — pre-existing alignment voor trigger-flow.
