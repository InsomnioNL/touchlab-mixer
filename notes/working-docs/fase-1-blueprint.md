# Fase 1 implementatie-blueprint — bridge dual-protocol input + UI keyboard-listener

> **⚠️ Status: ontwerp pre-implementatie**
>
> Dit is een werkdocument geschreven vóórdat de bridge-codebase is geïnspecteerd. Pseudo-code, bestand-organisatie en library-integratie zijn voorstellen op basis van algemene conventies, niet op basis van de daadwerkelijke bridge-code. **Valideer de aannames-sectie tegen de bridge-code voordat je dit document letterlijk volgt** — pseudo-code-stijl, WS-call-syntax, en folder-structuur passen mogelijk niet bij wat er nu staat.
>
> De test-checklist en architectuur-blokken (welke modules, welke verantwoordelijkheden) zijn waarschijnlijk wel direct bruikbaar. Aanpassingen verwacht op het syntax-niveau, niet conceptueel.

**Datum:** 2 mei 2026
**Status:** ontwerp-blueprint, geen final code
**Doel:** concrete pseudo-code en bestandsorganisatie voor fase 1 van de trigger-feature, zodat de implementatie-sessie kan starten zonder conceptuele beslissingen te nemen.
**Scope:** alleen detectie + transport (MIDI/OSC in bridge, keyboard in UI). Geen mapping-match, geen action-dispatch — die zitten in fase 2/3.

## Aannames

- Bridge is JavaScript (ES2020+, async/await), draait via Node.js
- UI is HTML+JavaScript, draait in browser (Safari op iPad als primaire target)
- WS-verbinding tussen UI en bridge bestaat al (poort 8080) en heeft eigen send/receive-functies — ik gebruik die abstract als `bridge.sendToUI(msg)` en `bridge.onUIMessage(cb)` zonder hun exacte implementatie aan te nemen
- Bridge gebruikt al een logger (uit overdrachtsdoc: `✓ Beginwaarden naar PD gestuurd`-stijl) — ik gebruik abstract `log.info()`, `log.warn()`, `log.error()`

## Bestand-organisatie (voorstel)

Niet bindend — pas aan op bridge's bestaande conventie. Idee is **één file per protocol-listener** zodat ze onafhankelijk te onderhouden zijn:

```
bridge/
  ├── index.js                    (bestaand — entry point)
  ├── ws-server.js                (bestaand — WS naar UI)
  ├── pd-fudi.js                  (bestaand — TCP naar Pd)
  ├── trigger/                    (NIEUW)
  │   ├── index.js                (orchestrator: laadt listeners, mapping-store)
  │   ├── normalize.js            (interne event-vorm, normalisatie-functies per protocol)
  │   ├── midi-listener.js        (easymidi-wrapper)
  │   ├── osc-listener.js         (node-osc-wrapper)
  │   ├── keyboard-handler.js     (ontvangt keyboard-events van UI via WS)
  │   └── debug-tap.js            (debug-events naar UI sturen tijdens learn/dev-mode)
```

Elk listener-bestand exporteert:
- `start(config, eventHandler)` — opent listener, registreert callback
- `stop()` — sluit listener netjes
- (optioneel) `getStatus()` — voor diagnostiek

Voor fase 1 hoeft `trigger/index.js` nog geen mapping-store te hebben — alleen listener-orchestratie + debug-tap.

## `normalize.js` — interne event-vorm

```js
// Interne event-vorm zoals gespecificeerd in ADR-001 + ADR-004:
// {
//   protocol: "midi" | "osc" | "keyboard",
//   source: <string>,
//   signature: <protocol-specifiek object>,
//   value: <number>,
//   timestamp: <number, ms>
// }

function normalizeMidi(deviceName, msg) {
  // msg is van easymidi: { _type: "cc"|"noteon"|..., channel, ...}
  // We mappen alleen cc, noteon, noteoff in v1.
  if (msg._type === 'cc') {
    return {
      protocol: 'midi',
      source: deviceName,
      signature: { type: 'cc', channel: msg.channel, number: msg.controller },
      value: msg.value,
      timestamp: Date.now()
    };
  }
  if (msg._type === 'noteon') {
    return {
      protocol: 'midi',
      source: deviceName,
      signature: { type: 'note', channel: msg.channel, note: msg.note },
      value: msg.velocity,
      timestamp: Date.now()
    };
  }
  if (msg._type === 'noteoff') {
    return {
      protocol: 'midi',
      source: deviceName,
      signature: { type: 'note', channel: msg.channel, note: msg.note },
      value: 0,
      timestamp: Date.now()
    };
  }
  return null; // andere types negeren in v1
}

function normalizeOsc(remoteAddr, msg) {
  // msg is van node-osc: [path, ...args]
  const [path, ...args] = msg;
  return {
    protocol: 'osc',
    source: remoteAddr,
    signature: { path, valueIndex: 0 },
    value: typeof args[0] === 'number' ? args[0] : 0,
    timestamp: Date.now()
  };
}

function normalizeKeyboard(uiPayload) {
  // uiPayload is wat UI over WS stuurde: { key, value, timestamp }
  return {
    protocol: 'keyboard',
    source: 'ui',
    signature: { key: uiPayload.key },
    value: uiPayload.value,
    timestamp: uiPayload.timestamp || Date.now()
  };
}

module.exports = { normalizeMidi, normalizeOsc, normalizeKeyboard };
```

## `midi-listener.js`

```js
const easymidi = require('easymidi');
const { normalizeMidi } = require('./normalize');

let inputs = []; // Active easymidi.Input instances

function start(config, eventHandler) {
  const deviceNames = easymidi.getInputs();
  log.info(`MIDI: ${deviceNames.length} input devices found: ${deviceNames.join(', ')}`);

  for (const name of deviceNames) {
    try {
      const input = new easymidi.Input(name);

      const onMessage = (type) => (msg) => {
        const normalized = normalizeMidi(name, { ...msg, _type: type });
        if (normalized) eventHandler(normalized);
      };

      input.on('cc', onMessage('cc'));
      input.on('noteon', onMessage('noteon'));
      input.on('noteoff', onMessage('noteoff'));

      inputs.push(input);
      log.info(`MIDI: listening on ${name}`);
    } catch (err) {
      log.error(`MIDI: failed to open ${name}: ${err.message}`);
    }
  }
}

function stop() {
  for (const input of inputs) {
    try { input.close(); } catch (_) {}
  }
  inputs = [];
}

module.exports = { start, stop };
```

**Open punt voor fase 1**: hot-plug van MIDI-devices. easymidi/`@julusian/midi` documenteren niet expliciet of er device-add-events zijn. Voor v1 alleen detectie bij startup; v1.1 een polling-loop (`setInterval(refreshDevices, 5000)`) als fallback.

## `osc-listener.js`

```js
const { Server } = require('node-osc');
const { normalizeOsc } = require('./normalize');

let server = null;

function start(config, eventHandler) {
  const port = config.oscPort || 9100;
  server = new Server(port, '0.0.0.0', () => {
    log.info(`OSC: listening on UDP port ${port}`);
  });

  server.on('message', (msg, rinfo) => {
    const remoteAddr = rinfo ? `${rinfo.address}:${rinfo.port}` : 'unknown';
    const normalized = normalizeOsc(remoteAddr, msg);
    eventHandler(normalized);
  });

  server.on('error', (err) => {
    log.error(`OSC server error: ${err.message}`);
  });
}

async function stop() {
  if (server) {
    await server.close();
    server = null;
  }
}

async function restart(config, eventHandler) {
  await stop();
  start(config, eventHandler);
}

module.exports = { start, stop, restart };
```

`restart` wordt later (fase 2) gebruikt door `osc-port-set`-handler.

## `keyboard-handler.js`

Geen listener — bridge ontvangt keyboard-events via WS van UI. Dit bestand bevat alleen de handler.

```js
const { normalizeKeyboard } = require('./normalize');

function handleUIKeyboardEvent(uiPayload, eventHandler) {
  // uiPayload: { key: "F13", value: 1, timestamp: 1714... }
  if (typeof uiPayload.key !== 'string') {
    log.warn('keyboard-event: missing or invalid key field');
    return;
  }
  if (uiPayload.value !== 0 && uiPayload.value !== 1) {
    log.warn(`keyboard-event: invalid value ${uiPayload.value}, expected 0 or 1`);
    return;
  }

  const normalized = normalizeKeyboard(uiPayload);
  eventHandler(normalized);
}

module.exports = { handleUIKeyboardEvent };
```

`ws-server.js` (bestaand) krijgt een nieuwe message-handler:

```js
// In bestaande ws-server.js, bij de handler voor inkomende UI-messages:
if (msg.type === 'keyboard-event') {
  handleUIKeyboardEvent(msg, /* eventHandler from trigger/index.js */);
}
```

## `trigger/index.js` — orchestrator

```js
const midiListener = require('./midi-listener');
const oscListener = require('./osc-listener');
const debugTap = require('./debug-tap');

let currentConfig = {
  oscPort: 9100,
  pulseOrGateThresholdMs: 250,
  // mappings: [...] — fase 2
};

function eventHandler(normalizedEvent) {
  // Fase 1: alleen debug-tap. Fase 2/3 voegt mapping-match + dispatch toe.
  debugTap.maybeForward(normalizedEvent);
}

function start(config) {
  currentConfig = { ...currentConfig, ...config };
  midiListener.start(currentConfig, eventHandler);
  oscListener.start(currentConfig, eventHandler);
  // Keyboard-handler is gekoppeld via ws-server.js, niet hier.
}

async function stop() {
  midiListener.stop();
  await oscListener.stop();
}

module.exports = { start, stop, eventHandler };
```

## `debug-tap.js`

In fase 1: stuurt elk genormaliseerd event naar UI via WS, voor live-debug-panel. In fase 2 wordt dit conditional — alleen tijdens learn-flow of bij dev-flag.

```js
let debugEnabled = true; // fase 1: altijd aan. Fase 2: configureerbaar.

function maybeForward(normalizedEvent) {
  if (!debugEnabled) return;
  bridge.sendToUI({
    type: 'event-raw',
    ...normalizedEvent
  });
}

function setDebugEnabled(value) {
  debugEnabled = !!value;
}

module.exports = { maybeForward, setDebugEnabled };
```

## UI: keyboard-listener

Toe te voegen aan UI-init-code (locatie tbd op basis van bestaande UI-organisatie):

```js
function initKeyboardListener() {
  window.addEventListener('keydown', (event) => {
    if (event.repeat) return; // ignore OS-key-repeat

    // Voor v1: stuur alle non-modifier keystrokes door, bridge filtert via mapping.
    // Mocht dit teveel WS-traffic geven, hier een whitelist invoeren.
    if (isModifierOnly(event)) return;

    bridge.sendKeyboardEvent({
      key: event.code,
      value: 1,
      timestamp: Date.now()
    });

    // Note: preventDefault() pas in fase 2 gebruiken, alleen voor gemapte keys.
    // Tijdens fase 1 willen we geen browser-shortcuts blokkeren.
  });

  window.addEventListener('keyup', (event) => {
    if (isModifierOnly(event)) return;
    bridge.sendKeyboardEvent({
      key: event.code,
      value: 0,
      timestamp: Date.now()
    });
  });
}

function isModifierOnly(event) {
  // Cmd, Ctrl, Alt, Shift on hun eigen — niet doorsturen
  return ['MetaLeft', 'MetaRight', 'ControlLeft', 'ControlRight',
          'AltLeft', 'AltRight', 'ShiftLeft', 'ShiftRight'].includes(event.code);
}

function sendKeyboardEvent(payload) {
  ws.send(JSON.stringify({ type: 'keyboard-event', ...payload }));
}
```

## UI: live-debug-panel (fase 1)

Eenvoudige toevoeging aan UI. Visueel: paneel onderaan scherm met scrollende event-lijst (laatste 50 events).

```js
function initDebugPanel() {
  const panel = document.getElementById('debug-panel');
  ws.on('message', (raw) => {
    const msg = JSON.parse(raw);
    if (msg.type !== 'event-raw') return;
    appendDebugLine(panel, formatEvent(msg));
  });
}

function formatEvent(evt) {
  const time = new Date(evt.timestamp).toISOString().slice(11, 23);
  const sig = JSON.stringify(evt.signature);
  return `${time} [${evt.protocol}] ${evt.source} ${sig} = ${evt.value}`;
}

function appendDebugLine(panel, line) {
  const div = document.createElement('div');
  div.textContent = line;
  panel.appendChild(div);
  while (panel.childElementCount > 50) panel.firstChild.remove();
  panel.scrollTop = panel.scrollHeight;
}
```

In fase 2 wordt het debug-panel verborgen achter een dev-toggle.

## Test-checklist voor fase 1

Aan het einde van fase 1 moet het volgende werken — zonder mappings, zonder dispatch, alleen detectie + transport:

1. **Bridge startup** logt: `MIDI: N input devices found: ...` en `OSC: listening on UDP port 9100`
2. **MIDI-input zichtbaar in UI debug-panel**: gewoon MIDI-toetsenbord aansluiten, een toets indrukken — line verschijnt met `[midi] <devicename> {"type":"cc","channel":1,"number":...}`
3. **OSC-input zichtbaar in UI debug-panel**: vanuit Pd of een test-tool een OSC-bericht naar `localhost:9100` sturen — line verschijnt met `[osc] 127.0.0.1:port /test/path = value`
4. **Keyboard zichtbaar in UI debug-panel**: focus op TouchLab-tab, druk een toets — line verschijnt met `[keyboard] ui {"key":"F13"} = 1`, en bij loslaten `= 0`
5. **Geen crash** als geen MIDI-devices aangesloten zijn (logs `0 input devices found`, OSC-listener werkt nog wel)
6. **Geen crash** als OSC-poort al in gebruik is — logs een error, MIDI-listener werkt nog wel

## Wat NIET in fase 1 zit

- Mapping-match: events stromen wel naar UI debug-panel maar triggeren geen actie. Fase 2/3.
- `learn-flow`: nog geen "trigger toevoegen" UI. Fase 2.
- Hysterese-state-machine: nog niet geïmplementeerd. Fase 3.
- `event.preventDefault()` in UI-keyboard-listener: alleen toegevoegd in fase 2 voor gemapte keys.
- Mock-Pd-patch: aparte deliverable, niet onderdeel van bridge-fase 1.

## Open vragen

- **WS-message-wrapper-shape**: ik gebruik `{ type: "...", ...payload }` direct. Is dat consistent met bestaande bridge-WS-conventie? Plak één bestaand bericht als sanity-check.
- **Bridge-bestand-organisatie**: voorstel is `bridge/trigger/`-subfolder. Past dat bij bestaande structuur, of leeft alles momenteel in een paar grote files in de bridge-root?
- **Logger-conventie**: ik gebruik abstract `log.info` etc. Welke logger draait bridge nu? `console.log` direct, of een wrapper als `pino`/`winston`/eigen module?
- **`ws.on('message', ...)` style in bestaande UI** — gebruikt UI native WebSocket of een wrapper-library (socket.io, etc.)? Mocht UI socket.io gebruiken, dan past `bridge.sendKeyboardEvent` in mijn UI-blueprint niet 1-op-1 — herschrijven naar `socket.emit('keyboard-event', payload)` ofzo.

Geen van deze blokkeert de blueprint conceptueel; het zijn aanpassingen op de plek waar bridge-code wordt geraakt.
