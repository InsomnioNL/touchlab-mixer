# WS-protocol-specificatie — trigger-feature

> **⚠️ Status: ontwerp pre-implementatie**
>
> Dit is een werkdocument geschreven vóórdat de bridge-codebase is geïnspecteerd. Het bevat aannames over bestaande conventies (WS-message-shape, logger-stijl, bestand-organisatie) die **gevalideerd moeten worden tegen de daadwerkelijke bridge-code voordat ze in implementatie worden overgenomen**. Behandel de pseudo-code en JSON-shapes als richtinggevend ontwerp, niet als spec.
>
> Zie de "Open vragen" en "Aannames" secties voor specifieke punten die validatie behoeven. Bij implementatie-sessie deze eerst afwerken.

**Datum:** 2 mei 2026
**Status:** ontwerp, te valideren tegen bestaande bridge-WS-conventie
**Doel:** alle nieuwe WS-message-types definiëren tussen bridge en UI voor de trigger-feature (MIDI/OSC/keyboard-input, learn-flow, mapping-management).

## Aannames (te valideren)

- Bridge gebruikt JavaScript, geen TypeScript
- Bestaande WS-messages volgen ongeveer een `{type: "...", ...payload}`-shape — **te bevestigen door Uli** door één bestaand WS-bericht uit bridge-code te plakken
- Geen versionering in v1 (impliciete versie 1); als bridge ooit versionering nodig heeft voegen we `protocolVersion: 1` toe
- WebSocket-poort 8080 (zoals overdrachtsdoc noemt) — bestaande verbinding, niet een aparte voor trigger-feature
- JSON-encoded messages, geen binary frames

Mocht een aanname niet kloppen, dan herzien we dit document en houden hetzelfde semantische model — de message-namen en payloads kunnen consistent blijven onder een andere wrapper-shape.

## Conventies

- **Naamgeving**: `kebab-case` voor message-types met componenten. Eerste component = onderwerp (`mapping-`, `learn-`, `keyboard-`), tweede = actie/event (`-add`, `-event`, `-complete`).
- **Richting**: per message vermeld of het `bridge → UI`, `UI → bridge`, of beide is.
- **Reply-pattern**: bridge stuurt confirmation-message terug op UI-acties (bijv. `mapping-added` na `mapping-add`-request). UI mag dit gebruiken voor optimistic-UI-confirmation, of negeren.
- **Foutafhandeling**: bridge stuurt `error`-message als fallback bij onbegrepen of ongeldige requests. Geen exception-throwing over WS.

## UI → Bridge messages

### `keyboard-event`

Keystroke vanuit UI-keyboard-listener. UI normaliseert al (`event.repeat` filtering, `event.code` extractie) voordat verzonden.

```json
{
  "type": "keyboard-event",
  "key": "F13",
  "value": 1,
  "timestamp": 1714657890123
}
```

- `key`: `KeyboardEvent.code` (layout-onafhankelijk, bijv. `"F13"`, `"KeyA"`, `"Space"`)
- `value`: `1` voor keydown, `0` voor keyup
- `timestamp`: `Date.now()` op moment van event

Bridge normaliseert naar interne event-vorm met `protocol: "keyboard"`, `source: "ui"`, `signature: { key }`, en routeert naar mapping-match + dispatch.

### `learn-start`

Gebruiker klikt "trigger toevoegen", kiest actie-type, drukt op "leer trigger".

```json
{
  "type": "learn-start",
  "action": "pulse"
}
```

- `action`: één van `"pulse"`, `"gate"`, `"start"`, `"stop"`, `"pulse-or-gate"`

Bridge gaat in learn-mode: eerstvolgende relevante event-stream wordt geanalyseerd voor protocol/signature/polariteit/range. Bridge stuurt `learn-progress` updates en uiteindelijk `learn-complete` of `learn-cancelled` (timeout).

### `learn-cancel`

Gebruiker klikt "annuleren" tijdens learn-flow.

```json
{
  "type": "learn-cancel"
}
```

Bridge verlaat learn-mode zonder mapping op te slaan.

### `mapping-remove`

Gebruiker klikt verwijder-knop op een mapping in de lijst.

```json
{
  "type": "mapping-remove",
  "mappingId": "abc123"
}
```

- `mappingId`: stable identifier per mapping. Door bridge gegenereerd bij `mapping-add` en teruggegeven in `mapping-list`/`mapping-added`. **Open ontwerp-keuze**: UUID, integer-counter, of hash van signature? Voorlopig UUID (`crypto.randomUUID()`).

### `mapping-list-request`

UI vraagt actuele lijst van mappings — typisch bij page-load of na re-connect.

```json
{
  "type": "mapping-list-request"
}
```

Bridge antwoordt met `mapping-list` (alle huidige mappings).

### `osc-port-set`

UI wijzigt OSC-poort-instelling.

```json
{
  "type": "osc-port-set",
  "port": 9100
}
```

Bridge sluit huidige OSC-listener, opent nieuwe op `port`. Bij falen: `error`-message met details.

### `pulse-or-gate-threshold-set`

UI wijzigt globale `pulseOrGateThresholdMs`.

```json
{
  "type": "pulse-or-gate-threshold-set",
  "thresholdMs": 250
}
```

Bridge update interne waarde, gebruikt direct (geen restart nodig).

## Bridge → UI messages

### `event-raw`

Een raw event vanuit een listener (MIDI, OSC, keyboard-from-ui). Alleen verzonden in dev-debug-mode of tijdens learn-flow — niet bij normale dispatch (anders stroomt de WS vol).

```json
{
  "type": "event-raw",
  "protocol": "midi",
  "source": "DIY-Pedal-USB",
  "signature": { "type": "cc", "channel": 1, "number": 64 },
  "value": 127,
  "timestamp": 1714657890123
}
```

UI gebruikt dit voor live-debug-panel en learn-flow-feedback.

### `learn-progress`

Tijdens learn-flow: bridge meldt wat het tot nu toe ziet binnenkomen.

```json
{
  "type": "learn-progress",
  "status": "waiting" | "receiving" | "analyzing",
  "samplesReceived": 3,
  "currentSignaturePreview": { "protocol": "midi", "type": "cc", "channel": 1, "number": 64 }
}
```

UI toont "wachten op input...", "ontvangen: ..." etc.

### `learn-complete`

Bridge heeft alle benodigde info, mapping is opgeslagen.

```json
{
  "type": "learn-complete",
  "mapping": {
    "mappingId": "abc123",
    "action": "pulse",
    "protocol": "midi",
    "signature": { "type": "cc", "channel": 1, "number": 64 },
    "polarity": "normal",
    "thresholdActive": 70,
    "thresholdInactive": 58,
    "valueRange": { "min": 0, "max": 127 }
  }
}
```

UI voegt mapping toe aan lijst-display.

### `learn-cancelled`

Bridge verliet learn-mode zonder voltooide mapping. Reden in payload.

```json
{
  "type": "learn-cancelled",
  "reason": "timeout" | "user-cancel" | "invalid-input"
}
```

`timeout`: bridge wachtte langer dan N seconden zonder genoeg samples (default 30s). `user-cancel`: na `learn-cancel` van UI. `invalid-input`: input was ongeldig (bijv. alleen value-fluctuaties zonder duidelijke active/inactive transitie).

### `mapping-list`

Volledige lijst van geconfigureerde mappings. Antwoord op `mapping-list-request` of pro-actief bij bridge-startup.

```json
{
  "type": "mapping-list",
  "mappings": [
    { "mappingId": "abc123", "action": "pulse", "protocol": "midi", "signature": {...}, "polarity": "normal", "thresholdActive": 70, "thresholdInactive": 58, "valueRange": {...} },
    { "mappingId": "def456", "action": "stop", "protocol": "keyboard", "signature": { "key": "F14" }, "polarity": "normal" }
  ],
  "oscPort": 9100,
  "pulseOrGateThresholdMs": 250
}
```

UI render't lijst opnieuw vanaf scratch.

### `mapping-added`

Confirmation na `learn-complete` (of later bij handmatige add). Functionele duplicaat van `learn-complete` voor consistency met `mapping-removed`. **Mogelijk weglaten als overlapping** — beslissen tijdens implementatie.

### `mapping-removed`

Confirmation na `mapping-remove`-request.

```json
{
  "type": "mapping-removed",
  "mappingId": "abc123"
}
```

UI verwijdert uit lijst-display (of had dat al optimistisch gedaan).

### `mapping-triggered`

Bij elke succesvolle dispatch — bridge informeert UI dat een mapping is getriggerd. Voor visuele feedback (bijv. mapping flashes briefly).

```json
{
  "type": "mapping-triggered",
  "mappingId": "abc123",
  "phase": "activate" | "release",
  "timestamp": 1714657890123
}
```

UI hoeft hier niet op te reageren behalve voor visuele feedback. Als UI deze niet wil, mag bridge'm onder een dev-flag verzenden.

### `osc-port-changed`

Confirmation na `osc-port-set`. Of een failure als de listener niet kon worden gestart.

```json
{
  "type": "osc-port-changed",
  "port": 9100,
  "success": true
}
```

Bij `success: false` ook een `error`-message met `reason`.

### `error`

Generieke fout-message van bridge.

```json
{
  "type": "error",
  "context": "osc-port-set" | "learn-start" | "...",
  "reason": "EADDRINUSE: poort 9100 is al in gebruik",
  "details": { ... }
}
```

`context` is het oorspronkelijke message-type dat de fout veroorzaakte. UI kan dit gebruiken om gerichte foutmeldingen te tonen.

## Sequence-diagram: typische learn-flow

```
UI                                    Bridge
 |                                     |
 |------- learn-start (action) ------> |
 |                                     | (entered learn-mode)
 |<------ learn-progress (waiting) --- |
 |                                     |
 | (gebruiker drukt pedaal)            |
 |                                     |
 |<------ event-raw (cc 64 = 127) ---- |
 |<------ learn-progress (receiving) - |
 |                                     |
 | (gebruiker laat pedaal los)         |
 |                                     |
 |<------ event-raw (cc 64 = 0) ------ |
 |<------ learn-progress (analyzing) - |
 |                                     |
 |<------ learn-complete (mapping) --- |
 |                                     |
```

## Sequence-diagram: typische trigger-flow (na learn)

```
UI/extern bron                Bridge                       Pd
 |                              |                            |
 | (pedaal in)                  |                            |
 |---- MIDI cc 64 = 127 ------->|                            |
 |                              | (mapping-match: "pulse")   |
 |                              | (state: INACTIVE → ACTIVE) |
 |                              |---- samplerPlay slot N --->|
 |<--- mapping-triggered -------|                            |
 |                              |                            |
 | (pedaal uit)                 |                            |
 |---- MIDI cc 64 = 0 --------->|                            |
 |                              | (state: ACTIVE → INACTIVE) |
 |<--- queueAdvance ------------|                            |
 |<--- mapping-triggered -------|                            |
```

`queueAdvance` is een bestaande WS-message van bridge naar UI — UI doet `refreshAfterQueueChange()` zoals nu.

## Open vragen

- **Bestaande WS-message-conventie bevestigen.** Plak één bestaand bridge-WS-bericht zodat ik kan checken of `{type, ...}`-shape correct is, of dat we een wrapper-veld gebruiken (`{event, payload}`, `{message, data}`, etc.).
- **`mapping-added` vs `learn-complete`** — beide bevatten dezelfde info. Eén weglaten? Of beide houden voor message-symmetrie?
- **Throttling van `event-raw`** — bij continuous bronnen (sustain-pedaal, Glover-stream) kan dit honderden events per seconde zijn. Bridge moet throttlen of UI moet aankunnen. Voorstel: bridge stuurt alleen tijdens learn-flow of dev-flag, en bij normale dispatch alleen `mapping-triggered`. Aanvaardbaar?
- **WS-reconnect-behaviour** — UI re-connects naar bridge na netwerk-glitch. Moet bridge bij re-connect automatisch `mapping-list` sturen, of wacht 't tot UI `mapping-list-request` doet? Voorstel: pro-actief sturen — UI hoeft minder logica. Akkoord?
