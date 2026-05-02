# ADR-002: easymidi als MIDI-library voor bridge

**Status:** Accepted
**Datum:** 2 mei 2026
**Stakeholders:** Uli (lead), Claude (review en implementatie)
**Gerelateerde documenten:** `notes/feature-midi-pedal.md` (revisie 4), `notes/adr/ADR-001-protocol-agnostic-event-router.md`

## Context

ADR-001 vastgesteld dat bridge een MIDI-listener heeft als onderdeel van de protocol-agnostische event-router. Voor implementatie hebben we een Node.js MIDI-library nodig die:

- MIDI-input ontvangt (CC, Note On/Off, primair voor pedaal-/keyboard-/drumpad-bronnen)
- Cross-platform werkt (macOS minimaal, Linux/Windows wenselijk voor toekomstige deployment-flexibiliteit)
- Hot-plug-detectie aankan (v1.1, niet kritisch voor v1 maar lib mag het niet uitsluiten)
- Event-based API biedt die direct in bridge's bestaande architectuur past
- Recent onderhouden is (geen dood project)

Niet vereist:
- MIDI-output (TouchLab stuurt geen MIDI uit, alleen in)
- MIDI 2.0 ondersteuning (gebruiken alleen MIDI 1.0 CC/Note)
- SysEx of geavanceerde gear-detectie
- Browser-shared code (bridge is server-side Node)

## Beslissing

**`easymidi` (versie 3.2.0+).**

Eenvoudige event-based wrapper rond `@julusian/midi` (gemaintainede fork van het oudere `node-midi`). API-pattern:

```js
const easymidi = require('easymidi');
const inputs = easymidi.getInputs();
inputs.forEach(name => {
  const input = new easymidi.Input(name);
  input.on('cc', msg => { /* {channel, controller, value} */ });
  input.on('noteon', msg => { /* {channel, note, velocity} */ });
});
```

Past 1-op-1 op bridge's normalisatie-stap: each `cc` of `noteon` event wordt direct geconverteerd naar de interne event-vorm uit ADR-001.

## Consequenties

### Positief

- **Zero-overhead API.** Geen Web-MIDI-API-emulatie, geen chaining-syntax — direct naar event-handlers.
- **Recente activiteit.** Versie 3.2.0 gepubliceerd ~2 maanden geleden (per maart 2026).
- **MIT-licentie.** Geen license-vragen voor TouchLab.
- **Bewezen track record.** Gebruikt door monome-grid (een bekende open-source MIDI-controller-library) en andere productieve projecten.
- **BLE MIDI gratis.** Op macOS verschijnen BLE-MIDI-pedalen (na OS-pairing via Audio MIDI Setup) als gewone CoreMIDI-inputs. easymidi pikt ze op via `getInputs()` zonder code-aanpassing. Dat dekt de "iRig BlueBoard / AirTurn-MIDI"-use-case in v1 zonder extra werk.
- **Onderhouden via @julusian/midi.** De underlying binding is een actief gemaintainede fork (na het verwaarlozen van het originele node-midi).

### Negatief

- **Native compile vereist.** `@julusian/midi` is een C++ binding tegen platform-MIDI-stacks (CoreMIDI/ALSA/WinMM). Bij `npm install` moet de gebruiker build-tools hebben (Xcode CLT op macOS, build-essential op Linux, Windows-build-tools op Windows). Voor TouchLab's deployment-context (lokaal op Mac) acceptabel, maar latente kost als we ooit naar een container of statische binary gaan.
- **Geen MIDI 2.0.** Als TouchLab ooit MIDI 2.0 messages wil ontvangen of zenden, moet er gemigreerd worden naar een andere library (jzz, MIDIVal). Niet relevant voor v1-scope of huidige hardware.
- **Geen built-in TypeScript types.** Bridge gebruikt momenteel JavaScript, dus geen direct issue, maar als bridge ooit naar TS migreert moeten types via `@types/easymidi` of handmatige declarations komen.

### Neutraal

- **Hot-plug op @julusian/midi.** Niet uit easymidi-documentatie te bevestigen of er een event komt bij device-add/remove. Te valideren in fase 1; valt onder v1.1-validatie als bridge moet pollen of inherent reageren.

## Overwogen alternatieven

### Alternatief 1: jzz

- **Wat:** Web-MIDI-API-style library van jazz-soft, ondersteunt MIDI 1.0 + 2.0, browser + Node.
- **Waarom verworpen:**
  - Web-MIDI-API-stijl (`navigator.requestMIDIAccess()`, chaining `.openMidiIn().connect(cb)`) is een dikkere abstractie dan we nodig hebben voor server-side gebruik
  - MIDI 2.0 niet vereist
  - Browser-shared-code-voordeel niet relevant (bridge is Node-only)
  - Iets meer dependency-footprint (jazz-soft heeft een familie van pakketten)

### Alternatief 2: `@julusian/midi` direct (zonder easymidi-wrapper)

- **Wat:** De underlying C++ binding gebruiken zonder easymidi's event-wrapper.
- **Waarom verworpen:**
  - We zouden zelf MIDI-byte-parsing moeten doen (status-bytes naar event-types vertalen)
  - easymidi's `cc`/`noteon`/etc. event-types zijn precies de abstractie die we willen
  - Geen meetbaar performance-voordeel verwacht voor onze event-volumes (sub-100Hz)

### Alternatief 3: MIDIVal

- **Wat:** Modernere abstraction-laag (`@midival/core` + platform-adapters).
- **Waarom verworpen:**
  - Voegt indirection toe zonder duidelijke feature-winst voor onze use-case
  - Recentere community-adoption maar minder track record dan easymidi
  - Opt-in TypeScript niet onmiddellijk relevant voor JS-bridge

## Implementatie-notities

- Installatie: `npm install easymidi`. Zorg dat `@julusian/midi` zonder errors compileert; op macOS vereist dat Xcode Command Line Tools.
- Bij bridge startup: `easymidi.getInputs()` enumeert beschikbare devices, log de lijst voor diagnostiek.
- Voor elk device: `new easymidi.Input(name)` en bind handlers voor `cc`, `noteon`, `noteoff` (en eventueel `pitch`, `program` later — niet voor v1).
- Bij MIDI-event: normaliseer naar interne event-vorm (zie ADR-001) met `signature: { type: "cc", channel, number }` of vergelijkbaar voor noteon/noteoff.
- BLE MIDI vereist geen aparte handling — verschijnt als gewoon device na OS-pairing.
- Hot-plug: te onderzoeken of @julusian/midi events stuurt bij device-changes; zo niet, een korte poll (`getInputs()` elke ~5s vergelijken) als fallback. Niet in fase 1 — v1.1.

## Verwijzingen

- npm: https://www.npmjs.com/package/easymidi
- GitHub: https://github.com/dinchak/node-easymidi
- Underlying binding: https://www.npmjs.com/package/@julusian/midi
