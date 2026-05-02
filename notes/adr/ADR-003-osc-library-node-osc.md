# ADR-003: node-osc als OSC-library voor bridge

**Status:** Accepted
**Datum:** 2 mei 2026
**Stakeholders:** Uli (lead), Claude (review en implementatie)
**Gerelateerde documenten:** `notes/feature-midi-pedal.md` (revisie 4), `notes/adr/ADR-001-protocol-agnostic-event-router.md`

## Context

ADR-001 vastgesteld dat bridge een OSC-listener heeft als onderdeel van de protocol-agnostische event-router. Voor implementatie hebben we een Node.js OSC-library nodig die:

- OSC-input ontvangt over UDP op een configureerbare poort
- Eenvoudige API biedt voor `path` + `args` parsing
- Recent onderhouden is
- Cross-platform werkt (macOS minimaal)
- Compatible is met Glover-output (OSC 1.0-spec)

Niet vereist:
- Pattern matching met wildcards (`/leap/*`) — v1-scope vereist exacte match
- Bundle-handling met timetag-magie — Glover stuurt typisch losse messages
- WebSocket-transport — UI praat al via WS naar bridge, OSC-bron is een aparte UDP-stream
- TCP/SLIP — niet gebruikt door onze bronnen
- Browser-shared code — bridge is server-only
- OSC-output (TouchLab stuurt geen OSC uit, alleen in)

## Beslissing

**`node-osc` (versie 11.2.2+).**

Eenvoudige Server/Client API, gebaseerd op pyOSC's design:

```js
const { Server } = require('node-osc');
const oscServer = new Server(port, '0.0.0.0', () => {
  console.log('OSC Server is listening');
});
oscServer.on('message', (msg) => {
  // msg is array: [path, ...args]
  const [path, ...args] = msg;
});
```

Past direct op bridge's normalisatie-stap: each `message` event wordt geconverteerd naar de interne event-vorm uit ADR-001 met `signature: { path, valueIndex }` en `value: args[valueIndex]`.

## Consequenties

### Positief

- **Recente activiteit.** Versie 11.2.2 gepubliceerd ~1 maand geleden (per april 2026). Actief onderhouden.
- **Built-in TypeScript types.** `.d.mts`-types worden automatisch gegenereerd uit JSDoc, werkt voor zowel ESM als CommonJS. Geen `@types/`-pakket nodig. Toekomstig nuttig als bridge naar TS migreert.
- **Pure JavaScript.** Geen native compile-stap, geen build-tools-vereiste bij install.
- **Simpele Server/Client-abstractie.** Geen Plugin-architectuur of Port-classes — direct `new Server(port, host, cb)` en `.on('message', cb)`.
- **Bundle-support indien nodig.** Voor toekomstige features die Glover-bundles willen ondersteunen, niet voor v1.
- **32 dependents op npm** — bewezen adoption in publieke projecten.
- **Snyk health-score 79/100** — hoogste van de drie OSC-kandidaten.

### Negatief

- **LGPL-3.0 licentie.** Moet bewust geaccepteerd worden door TouchLab. Voor server-side npm-import (geen statische linking) is LGPL-compliance automatisch — gebruikers van TouchLab kunnen de library theoretisch vervangen door een eigen versie via npm. In de praktijk geen issue voor TouchLab's deployment-model, maar als TouchLab ooit als gesloten binary uitgeleverd zou worden (Electron-bundle, etc.) is een herbeoordeling nodig. Nu acceptabel; te heroverwegen bij toekomstige distributie-veranderingen.
- **Geen pattern-matching uit de box.** `osc-js` heeft `osc.on('/foo/{a,b}/*', cb)` met wildcards; node-osc doet dat niet. Voor v1 niet nodig (scope-doc vereist exacte match), maar als pattern-matching ooit gewenst wordt, zelf implementeren.
- **Geen multi-transport.** Alleen UDP. Voor TouchLab voldoende, maar geen toekomstige WebSocket-OSC-bron-mogelijkheid zonder library-wissel.

### Neutraal

- **Server bindt op IPv4 / wildcard host (`0.0.0.0`)** — accepteert verbindingen van LAN-IPs. Voor remote-mix-assist scenario's ooit relevant; voor v1 prima default.

## Overwogen alternatieven

### Alternatief 1: `osc.js` (de library van Colin Clark)

- **Wat:** Comprehensive OSC-library, OSC 1.0 + 1.1 spec-compliant, browser + Node, multi-transport (UDP/TCP/Serial/WebSocket).
- **Waarom verworpen:**
  - Laatste release ~2 jaar geleden — geen recente activiteit
  - Comprehensive feature-set (Ports-abstraction, SLIP framing, multi-transport) is overkill voor onze single-UDP-listener-use-case
  - Geen built-in TypeScript types
  - Hoogste adoption van de drie (60 dependents) compenseert niet voor staleness

### Alternatief 2: `osc-js` (van adzialocha)

- **Wat:** OSC-library met Plugin-API voor UDP/WebSocket/bridge, address-pattern-matching met wildcards.
- **Waarom verworpen:**
  - Laatste release ~2 jaar geleden — geen recente activiteit
  - Plugin-architectuur is niet nodig voor onze single-transport-use-case
  - Wildcard-pattern-matching nice-to-have die we expliciet uit v1 hebben gehouden
  - Lagere adoption (12 dependents)

### Alternatief 3: Eigen UDP-parser via `dgram` (Node built-in)

- **Wat:** Geen library — UDP-socket via Node's built-in `dgram` module, OSC-binary handmatig parsen.
- **Waarom verworpen:**
  - OSC-binary-format heeft padding-rules en type-tag-parsing die niet-triviaal zijn om correct te implementeren
  - Bug-risico in self-implemented parser hoger dan in een gevestigde library
  - Tijdwinst marginaal — node-osc's API is al minimaal

## Implementatie-notities

- Installatie: `npm install node-osc`. Pure JavaScript, geen native compile.
- Bij bridge startup: `new Server(oscPort, '0.0.0.0', cb)` waar `oscPort` uit `session.json` komt (default 9100, configureerbaar via UI per scope-doc).
- `server.on('message', (msg) => ...)` waar `msg` een array is `[path, arg1, arg2, ...]`. Voor onze normalisatie: `signature: { path: msg[0], valueIndex: 0 }`, `value: msg[1]`. Hogere `valueIndex` als gebruiker wil — voor v1 alleen index 0.
- Bij poort-wijziging via UI: `await oldServer.close()` + `new Server(newPort, ...)`. Bridge moet robuust zijn tegen close-failure (eventueel kort delay + retry).
- Geen pattern-matching in v1 — bridge matcht zelf op exacte string-equality van path tegen mappings.

## Verwijzingen

- npm: https://www.npmjs.com/package/node-osc
- GitHub: https://github.com/MylesBorins/node-osc
- License: LGPL-3.0 (https://opensource.org/licenses/LGPL-3.0)
