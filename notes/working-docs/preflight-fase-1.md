# Pre-flight checklist — fase 1 trigger-feature

> **⚠️ Status: ontwerp pre-implementatie**
>
> Dit is een werkdocument geschreven vóórdat de bridge-codebase is geïnspecteerd. De checklist beschrijft een algemene veilige startup-procedure plus fase-1-specifieke checks, maar **de concrete patch-instructies (welke files, welke markers) gaan uit van de blueprint die nog gevalideerd moet worden**.
>
> De canonical startup-procedure (sectie 1) en de Node/build-tools checks (5, 6) zijn protocol-onafhankelijk en blijven correct. De implementatie-volgorde-stappen vereisen herziening zodra bridge-conventies bekend zijn.

**Datum:** 2 mei 2026
**Status:** voorlopige checklist, te bevestigen aan begin van implementatie-sessie
**Doel:** voorkomen dat we tijdens fase 1 implementatie tegen voorzienbare problemen aanlopen — alle checks aan het begin van de sessie afwerken.

## Vóór de eerste patch — sanity checks

### 1. Canonical startup geverifieerd

Volg de canonical startup-procedure uit het overdrachtsdocument (sectie 2 van `overdrachtsdocument-werksessie-2026-05-01-avond.md`). Drie tabs (Pd, bridge, UI), pkill-cleanup vooraf, geen Jack — Pd start als macOS GUI-app via `open touchlab-mixer-ttb.pd`.

Bevestig dat alles draait **vóór** we aan code beginnen. Als de baseline niet werkt, zien we niet of latere problemen door onze code komen of door pre-existing issues.

### 2. `pwd`-check (ontdekking B uit overdrachtsdoc)

Patches gaan naar `~/Documents/Pd/PDMixer/v2/` (v2-first). Niet naar `~/Documents/touchlab-mixer/` direct — dat is repo-staging na test in v2.

```
cd ~/Documents/Pd/PDMixer/v2/
pwd
```

Verwacht: `/Users/ulrichpohl/Documents/Pd/PDMixer/v2`. Als iets anders → corrigeer voordat je verder gaat.

### 3. Git-status schoon

```
cd ~/Documents/touchlab-mixer
git status
```

Verwacht: `nothing to commit, working tree clean` (afgezien van `.DS_Store`-modificaties die we negeren). Als er staged changes hangen die niet van deze sessie zijn → eerst die afronden of stash'en.

### 4. Backup van bridge

Vóór elke aanpassing aan bestaande bridge-files: backup naar timestamped folder.

```
cp -r ~/Documents/Pd/PDMixer/v2/bridge ~/Documents/Pd/PDMixer/v2/bridge.backup-2026-05-02-fase1
```

Pad-naam met datum + fase, zodat bij meerdere sessies op één dag de backups niet overschrijven.

### 5. Node-versie check

`easymidi` vereist Node ≥14.15. `node-osc` v11+ vereist Node ≥18 (te bevestigen).

```
node --version
```

Als <18 → upgrade overwegen vóór install. Geen blokker als 14-17, dan even `node-osc` versie-eis valideren.

### 6. Build-tools voor `easymidi` native compile

`easymidi` → `@julusian/midi` is C++ binding, vereist build-tools.

```
xcode-select -p
```

Verwacht: een pad naar Xcode of Command Line Tools (`/Library/Developer/CommandLineTools` of `/Applications/Xcode.app/...`). Geen pad → installeer met `xcode-select --install` voordat je `npm install` doet.

## Pre-flight vragen aan Uli (te beantwoorden voor de eerste regel code)

Ik (Claude) kan deze niet zelf beantwoorden, jij wel:

- **WS-message-wrapper-shape bestaande bridge** — plak één voorbeeld zodat blueprints kunnen aansluiten
- **Bridge-bestand-organisatie** — past `bridge/trigger/` als nieuwe subfolder, of zit alles in één file?
- **Logger-conventie** — `console.log`, of een wrapper-module?
- **UI WebSocket — native of wrapper?** — `new WebSocket()` of socket.io?
- **`session.json` huidige locatie en schema** — fase 2 voegt mappings hieraan toe; fase 1 raakt 'm niet, maar handig om vast te weten waar 't leeft

## Implementatie-volgorde fase 1

Eén ding tegelijk. Diagnose vóór actie. Niet alle stappen tegelijk:

### Stap A: dependencies installeren (geen code-wijzigingen nog)

```
cd ~/Documents/Pd/PDMixer/v2/bridge
npm install easymidi node-osc
```

Verwacht: install slaagt zonder native-compile-errors. Bij errors → controleer Xcode CLT, plak de error in chat voor diagnose.

Direct daarna:

```
git status  # in repo
```

Verwacht: `package.json` en `package-lock.json` als modified. Nog niet committen — eerst werkende fase 1.

### Stap B: nieuwe bestanden in `bridge/trigger/`

Volgorde, één voor één testen na elke:

1. `bridge/trigger/normalize.js` — pure functies, kan getest worden via een mini-script of node-REPL
2. `bridge/trigger/midi-listener.js` — start in isolatie via test-script (`node -e "require('./bridge/trigger/midi-listener').start({}, console.log)"`)
3. `bridge/trigger/osc-listener.js` — idem, test door OSC vanuit Pd te sturen
4. `bridge/trigger/keyboard-handler.js` — pure functies, geen runtime-test nodig in deze stap
5. `bridge/trigger/debug-tap.js` — vereist WS-koppeling, kan pas getest worden in stap C
6. `bridge/trigger/index.js` — orchestrator

Geen patch-script nodig voor deze stap — het zijn nieuwe files in een nieuwe folder. Maakt geen bestaande code stuk.

### Stap C: bestaande bridge-files aanpassen

**Hier wel patch-scripts gebruiken** met markers en backups, zoals overdrachtsdoc voorschrijft.

1. `bridge/index.js` — laad `trigger/index.js`, roep `start(config)` aan na bestaande init
   - Marker: `// TRIGGER-FEATURE-INIT-V1`
   - Backup van bridge/index.js voor de wijziging
   - `count == 1`-check op marker (mag niet al bestaan)

2. `bridge/ws-server.js` — handler voor `keyboard-event` toevoegen
   - Marker: `// TRIGGER-KEYBOARD-HANDLER-V1`
   - Backup
   - `count == 1`-check

### Stap D: UI-aanpassingen

Te doen in `~/Documents/Pd/PDMixer/v2/index.html` (of waar de UI-init-code zit). Eerst lokaliseren waar de WS-init en bestaande event-handlers staan.

1. Keyboard-listener-functie toevoegen
   - Marker: `// TRIGGER-KEYBOARD-LISTENER-V1`
   - Backup van index.html

2. Live-debug-panel toevoegen
   - Marker: `<!-- TRIGGER-DEBUG-PANEL-V1 -->`
   - HTML + JS toevoegen
   - Backup

3. WS-message-handler voor `event-raw` (toevoegen aan bestaande WS-receive-switch)
   - Marker: `// TRIGGER-EVENT-RAW-HANDLER-V1`

### Stap E: integratie-test

Volg "Test-checklist voor fase 1" uit blueprint-document. Zes punten, één voor één afvinken.

### Stap F: v2 → repo-staging

Na succesvolle integratie-test in v2:

```
cp -r ~/Documents/Pd/PDMixer/v2/bridge/trigger ~/Documents/touchlab-mixer/bridge/trigger
cp ~/Documents/Pd/PDMixer/v2/bridge/index.js ~/Documents/touchlab-mixer/bridge/index.js
cp ~/Documents/Pd/PDMixer/v2/bridge/ws-server.js ~/Documents/touchlab-mixer/bridge/ws-server.js
cp ~/Documents/Pd/PDMixer/v2/bridge/package.json ~/Documents/touchlab-mixer/bridge/package.json
cp ~/Documents/Pd/PDMixer/v2/bridge/package-lock.json ~/Documents/touchlab-mixer/bridge/package-lock.json
cp ~/Documents/Pd/PDMixer/v2/index.html ~/Documents/touchlab-mixer/index.html
```

Daarna `cd ~/Documents/touchlab-mixer && git status` om te zien wat we committen. Selectief `git add` (geen `.DS_Store`).

Commit-message-voorstel: `Implement trigger-feature fase 1: MIDI/OSC/keyboard input detection`

## Rollback-strategie

Als iets misloopt en bridge crasht of UI breekt:

1. `cp -r bridge.backup-2026-05-02-fase1/* bridge/` — restore alle bestaande files
2. `rm -rf bridge/trigger` — verwijder nieuwe folder
3. `git checkout -- bridge/package.json bridge/package-lock.json` (in repo, niet v2) — als nog niet gecommit
4. Restart canonical startup — verifieer dat baseline weer werkt

Backups blijven staan tot fase 1 succesvol afgerond is. Bij commit van succesvolle fase 1: backups mogen weg, of laten staan tot fase 2 startpunt.

## Bekende risico's voor fase 1

- **`@julusian/midi` install-failure** door ontbrekende build-tools. Mitigatie: stap 6 hierboven.
- **OSC-poort 9100 al in gebruik** door iets onverwachts (Glover-config? andere tool?). Mitigatie: bij `EADDRINUSE`-error, check `lsof -i UDP:9100`, kies andere default zoals 9101 indien nodig.
- **Bestaande WS-message-handler in bridge breekt** door onze toevoeging. Mitigatie: marker-based patch met backup, eerst alleen lezen om huidige handler te begrijpen, dan toevoegen via clean idempotent edit.
- **iPad-Safari blokkeert sommige keystrokes** (bijv. F-keys gemapt aan iOS-system-shortcuts). Mitigatie: tijdens fase 1 gebruik je gewone toetsen om listener te valideren (bijv. spatie); F-keys-mapping pas valideren in fase 2 met echt pedaal.
- **chat-rendering-bug-impact**: alle bash-commando's in deze sessie via shell-globs schrijven, niet via expliciete `.js`-extensies. Bijv. `cp normalize* trigger/` ipv `cp normalize.js trigger/`.

## Wanneer dit document weggaat

Na succesvolle fase 1 commit kan dit pre-flight-document weggegooid worden, of bewaard als template voor fase 2/3 pre-flight (aanpassen op die fase). Niet committen naar repo — dit is een werkdocument voor één sessie, geen scope-doc.
