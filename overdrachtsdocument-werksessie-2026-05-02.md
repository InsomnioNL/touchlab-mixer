# Overdrachtsdocument werksessie 2 mei 2026

**Datum:** zaterdag 2 mei 2026 (versie 2 — uitgebreid na avond-sessie)
**Voorgaande sessie:** `overdrachtsdocument-werksessie-2026-05-01-avond.md`
**Hoofdthema:** trigger-feature ontwerp + fase-1-implementatie (MIDI/OSC/keyboard input-detectie) + fase-2-skeleton (mapping-store, match, persistence, hysterese-state-machine)
**Status aan einde van sessie:** fase 1 compleet, fase 2-skeleton met persistence en hysterese werkend, binary-pad-hysterese gevalideerd; continuous-pad-hysterese en action-dispatch nog niet

## 1. Lees-volgorde voor context

Voor een snelle herstart, lees in deze volgorde:

1. **Dit document eerst** — sectie 2 (canonical startup), sectie 6 (chat-rendering-bug strategieën, met updates uit deze sessie), sectie 7 (eerste-actie-lijst).
2. **Vorig overdrachtsdocument** (`overdrachtsdocument-werksessie-2026-05-01-avond.md`) voor architectuur-context van vóór de trigger-feature.
3. **Eerder overdrachtsdocumenten** indien dieper context nodig is.

Voor diep duiken in de trigger-feature specifiek:
1. `notes/feature-midi-pedal.md` (revisie 5) — volledige scope-doc, vier of vijf actie-types beschrijving, mapping-schema
2. `notes/adr/ADR-001-protocol-agnostic-event-router.md` — kernarchitectuur
3. `notes/adr/ADR-004-keyboard-as-third-protocol.md` — uitbreiding op ADR-001
4. `notes/adr/ADR-002-midi-library-easymidi.md` — library-keuze
5. `notes/adr/ADR-003-osc-library-node-osc.md` — library-keuze
6. `notes/working-docs/` — vier werkdocumenten met `⚠️ pre-implementatie`-disclaimer; mogelijk gedeeltelijk overruled door wat we daadwerkelijk geïmplementeerd hebben

## 2. Canonical startup-procedure

Onveranderd t.o.v. vorige sessie. Drie tabs (Pd, bridge, UI), pkill-cleanup vooraf, Pd start als macOS GUI-app, geen Jack. Bevestig dat alles draait vóór je iets nieuws aanpakt.

Bridge gebruikt nu **`easymidi`** en **`node-osc`** als nieuwe dependencies bovenop `ws`. Deze zijn al geïnstalleerd in `~/Documents/Pd/PDMixer/node_modules` (oude conventie, één niveau boven `v2/`) **én** in `~/Documents/touchlab-mixer/node_modules` (repo, sinds deze sessie). Bij een fresh clone of restore: `npm install` draaien in beide directories — of in repo als je vanaf de repo werkt.

## 3. Wat in deze sessie is gebeurd

### 3.1 Volledige scope-doc-evolutie van de trigger-feature

Begonnen met scope-doc revisie 1 (van vorige sessie), in deze sessie geëvolueerd via revisies 2 t/m 5:

- **rev 2**: vier actie-types (`pulse`, `gate`, `start`, `stop`), multi-mapping, OSC erbij, hysterese-state-machine, configureerbare OSC-poort
- **rev 3**: vijfde actie-type `pulse-or-gate` met duur-onderscheid; hergebruikt UI-trigger-duur-logica
- **rev 4**: BLE MIDI impliciet ondersteund in v1; HID-pedalen (Firefly) initieel naar v2 verschoven via OS-keymap-tools
- **rev 5**: keyboard als third first-class protocol; HID-pedalen weer naar v1; v2-OS-keymap-tool-aanpak verwijderd

### 3.2 Vier ADR's geschreven en gepusht

- **ADR-001**: Protocol-agnostische event-router. Bridge wordt drie-protocol-router (MIDI/OSC + UI keyboard).
- **ADR-002**: easymidi als MIDI-library. Native compile via `@julusian/midi`. BLE MIDI gratis bonus.
- **ADR-003**: node-osc als OSC-library. LGPL-3.0 acceptabel voor server-side gebruik.
- **ADR-004**: Keyboard als third protocol. UI vangt `keydown`/`keyup`, stuurt via WS. Vervangt eerdere v2-aanpak via OS-keymap-tools.

### 3.3 Vier werkdocumenten geschreven en gepusht (met disclaimer)

In `notes/working-docs/`:
- `ws-protocol-spec.md` — alle WS-message-types ontworpen
- `fase-1-blueprint.md` — pseudo-code voor bridge-modules en UI-listener
- `preflight-fase-1.md` — sanity checks vóór implementatie
- `mock-pd-blueprint.md` — mock-Pd-patch-ontwerp (niet meer kritisch nodig — Glover dekt MIDI/OSC validatie)

**Belangrijk:** deze werkdocumenten zijn **gedeeltelijk overruled** door wat we daadwerkelijk gebouwd hebben. Specifiek:
- Bestand-organisatie: blueprint stelde `bridge/trigger/`-subfolder voor, daadwerkelijk gekozen: één `trigger.js`-file naast `bridge.js`
- WS-message-shape blueprint had `{type, ...payload}` als aanname; bevestigd correct toen `handleFrontendMessage(msg)` werd geanalyseerd
- Logger-conventie blueprint was abstract `log.info`, daadwerkelijk gebruikt: `console.log("[trigger] ...")`
- Het kleyboard-listener voorstel in blueprint heeft nu concrete locatie: na `function send()` in `index.html`

### 3.4 Fase-1-implementatie compleet

**Drie protocollen geïmplementeerd, allemaal live gevalideerd:**

#### MIDI (commit 3fea5db)
- `trigger.js` met `easymidi`-listener
- Logt op startup beschikbare MIDI-devices
- Per device handlers voor `cc`, `noteon`, `noteoff`
- Live gevalideerd: Glover stuurt `CC 88` op channel 0 (MIDI-spec-channel 1) met value 0/100

#### OSC (commit c2efe7f)
- `node-osc.Server` op UDP 9100
- Logt path en args per message
- Live gevalideerd: Glover stuurt diverse paths (`/posLR`, `/hit`, `/up`, `/pitch`, `/yaw`, `/block1`, `/unblock1`)
- **Ontdekking**: Glover stuurt zowel pulse-style (argumentloos: `/hit`, `/yaw`) als continuous (`/posLR` met value)

#### Keyboard (commit 757ba43)
- UI-listener in `index.html` na `send()`-helper, `window.addEventListener('keydown'/'keyup')`
- Filtert `event.repeat`, modifier-only-keys, en input/textarea-focus
- Stuurt via bestaande `send()`-helper als `{type: "keyboard-event", key, value, timestamp}`
- Bridge-handler in `handleFrontendMessage`-switch op regel 608
- Live gevalideerd: Mac-toetsenbord-input wordt door bridge ontvangen en gelogd

### 3.5 Hygiëne-verbeteringen

- **`.gitignore` uitgebreid met `node_modules/`** (hygiëne-commit 0df67f0)
- **20 ws-files uit git-tracking gehaald** — die waren historisch gecommit door ontbrekende ignore. -5575 regels.
- **Dual package.json setup ontdekt:** `~/Documents/Pd/PDMixer/package.json` (oud, voor v2-runtime) én nu ook `~/Documents/touchlab-mixer/package.json` (repo). Beide hebben nu `easymidi` + `node-osc` + `ws`.

### 3.6 Fase-2-skeleton geïmplementeerd

Na fase 1 is in dezelfde sessie een fase-2-skeleton gebouwd met vier bouwlagen:

#### Mapping-store (commit 52f5dfd)
- Nieuwe file `triggerStore.js` met in-memory state
- Functions: `load(cfg)`, `getAll()`, `add(mapping)`, `remove(id)`, `matchEvent(evt)`
- `load()` valt netjes terug op lege array als `cfg.triggers` ontbreekt
- Ids worden auto-toegekend met counter, na load gesynchroniseerd op hoogste bestaande id
- Matching gebeurt via `signaturesMatch()` — alle keys in mapping.signature moeten exact matchen met event.signature (subset-match)

#### Centrale event-handler (commit da3f1a8)
- `trigger.js` refactor: alle protocollen normaliseren naar interne event-vorm en roepen `onEvent(evt)` aan
- Drie normalize-helpers: `normalizeMidiCc`, `normalizeMidiNote`, `normalizeOsc`
- Keyboard normalize loopt via nieuwe export `handleKeyboardEvent(uiPayload)` die bridge.js aanroept vanuit ws-handler
- `onEvent` matcht events tegen alle mappings, logt event en eventuele matches
- `bridge.js` `keyboard-event`-case roept nu `trigger.handleKeyboardEvent(msg)` aan
- Drie nieuwe test-WS-handlers: `mapping-add-test`, `mapping-list-test`, `mapping-remove-test` — bedoeld voor handmatige tests via DevTools-console, vervangen door real UI in latere fase

#### Persistence (commit ceea360)
- `mapping-add-test`/`mapping-remove-test`-handlers schrijven `cfg.triggers = triggerStore.getAll()` en triggeren `saveSessionToDisk(cfg, null, {skipReload: true})`
- `skipReload` voorkomt onnodige TTB-sample-reload bij elke mapping-wijziging
- Mappings overleven bridge-restart — bevestigd via test: mapping toegevoegd → bridge stop → bridge start → match werkt zonder re-add

#### Hysterese-state-machine (commit e0ab1d7)
- `triggerStore` krijgt `applyThresholdDefaults()` bij add — defaults afhankelijk van protocol (MIDI: 64/32, OSC: 0.5/0.3, keyboard: geen)
- Runtime state-Map `stateById` in triggerStore — niet gepersisteerd, reset bij bridge-restart (bewust)
- `onEvent` evalueert per match `evaluateHysteresis(mapping, value)` met return `"activate" | "release" | "no-change"`
- Voor binary-mappings (geen thresholds): value > 0 → activate, value === 0 → release
- Voor continuous (met thresholds): standaard hysterese-state-machine met dode zone tussen thresholds
- Logging onderscheidt nu `TRANSITION=ACTIVATE`, `TRANSITION=RELEASE`, en `(no state change)`
- **Binary-pad gevalideerd** met keyboard-mapping (KeyZ aan/uit-cyclus produceert correct ACTIVATE/RELEASE)
- **Continuous-pad NIET gevalideerd** — vereist Leap-bron of mock-Pd-patch die we deze sessie niet meer gedaan hebben

## 4. Veertien commits gepusht in deze sessie

```
ce69f1f  Update MIDI-pedal scope (rev 3) + ADR-001 protocol-agnostic event-router
4494243  Update MIDI-pedal scope (rev 4) + ADR-002 easymidi + ADR-003 node-osc
9b129da  Update MIDI-pedal scope (rev 5) + ADR-004 keyboard as third protocol
ecd1108  Add trigger-feature working docs (WS-protocol, fase-1-blueprint, preflight) - pre-implementation
abd7141  Add mock-Pd-blueprint working doc - pre-implementation
0df67f0  Hygiene: ignore node_modules/ and remove from tracking
3fea5db  Add trigger.js: minimal MIDI listener (fase 1, MIDI-only)
c2efe7f  trigger.js: add OSC listener on UDP 9100 (validated with Glover)
757ba43  Fase 1 compleet: keyboard-listener UI->bridge (validated with Mac keyboard)
dc671ef  Add overdrachtsdocument werksessie 2026-05-02 - fase 1 trigger-feature compleet
52f5dfd  Add triggerStore.js: in-memory mapping-store skeleton (loaded from cfg.triggers)
da3f1a8  trigger.js refactor: central onEvent + mapping-match (validated with Glover OSC)
ceea360  Mappings persistent via cfg.triggers + saveSessionToDisk (skipReload)
e0ab1d7  Hysteresis state-machine in trigger.js + threshold defaults in triggerStore (binary path validated)
```

(Het overdrachtsdocument-commit `dc671ef` was geschreven na fase 1, vóórdat het fase-2-skeleton-werk was uitgevoerd. Dit document is daarna bijgewerkt met de extra context — versie 2 — maar als losse "v2"-update niet apart gecommit, wordt onderdeel van de volgende commit.)

## 5. Belangrijke ontdekkingen tijdens deze sessie

### Ontdekking F: bridge.js draait vanuit niveau-hoger dependencies

Bridge-code zit in `~/Documents/Pd/PDMixer/v2/bridge.js`, maar `package.json` + `node_modules` zitten één niveau hoger in `~/Documents/Pd/PDMixer/`. Node's module-resolution zoekt automatisch parent-directories voor `node_modules` — daardoor werkt dit. Bij `npm install` voor v2-werk: cd naar `~/Documents/Pd/PDMixer/`, niet `v2/`.

**Echter**: voor de repo (`~/Documents/touchlab-mixer/`) hebben we nu een eigen `package.json` met dezelfde dependencies. Dit is de juiste plek voor toekomstige fresh clones.

### Ontdekking G: WS-message-shape conventie

Bridge gebruikt `handleFrontendMessage(msg, ws)` met destructuring `const { type, channel, value } = msg;` en een `switch (type)`-statement. Nieuwe message-types worden toegevoegd als case in die switch, vóór `default:`. Onze `keyboard-event`-handler volgt dit patroon.

### Ontdekking H: pre-emptive toggle in UI-trigger-logica

UI's `buildTriggerButton` heeft een **pre-emptive toggle**: als je een tweede keer drukt op een al spelende slot, stopt het slot. Dit is **niet hetzelfde** als onze ontworpen `start`/`stop`-paar. Voor fase 3 implementatie: bridge moet ofwel deze semantiek overnemen, ofwel via UI-proxy-pad (optie 1b uit chat-discussie) zodat UI's bestaande logica gewoon werkt.

**Beslissing genomen tijdens sessie**: pad X met optie 1b — bridge stuurt `triggerActivate`/`triggerRelease` naar UI zonder slot, UI bepaalt zelf `ttbQueue[ttbQueuePos]`. Dit raakt UI-code minimaal en hergebruikt bestaande logica.

### Ontdekking I: Glover OSC heeft pulse en continuous

Glover stuurt zowel argumentloze pulse-events (`/hit`, `/yaw`) als continuous-value-events (`/posLR`, `/pitch`). Mapping-schema in fase 2 moet hier rekening mee houden:
- Argumentloos = puls-event, geen hysterese, instantane trigger
- Continuous = state-machine met thresholds zoals MIDI CC

### Ontdekking J: Glover stuurt verschillende source-poorten per OSC-bericht

Bij elke OSC-bericht heeft Glover een nieuwe UDP source-poort. Niet relevant voor v1 (we matchen op path, niet source), maar wel iets om bewust te zijn als source-matching ooit overwogen wordt.

### Ontdekking K: BLE-HID-pedalen werken via browser-keyboard-events

Eerder dachten we dat HID-pedalen (Firefly) externe OS-keymap-tools nodig hadden om naar bridge te routen. Realisatie: TouchLab-UI is een browser-app, browser ontvangt keystrokes al van BLE-keyboards. UI-listener vangt 'm op, stuurt naar bridge. Veel eenvoudiger architectuur, hele OS-keymap-tool-laag verdwijnt.

### Ontdekking L: argumentloze OSC-events triggeren state-machine fout

Glover stuurt sommige OSC-paths argumentloos (`/hit`, `/yaw`, `/block1`, `/unblock1`). Onze `normalizeOsc()` zet `value: 0` als geen arg aanwezig. Dat botst met de hysterese-state-machine: een argumentloze pulse zou een instantane trigger moeten zijn, maar wordt nu altijd geïnterpreteerd als `value=0` → blijft INACTIVE → geen ACTIVATE. **Latente bug**, te fixen in volgende sessie. Mogelijke aanpak: speciale "pulse-mode" voor argumentloze paths, of `value: undefined` als geen arg en die afzonderlijk afhandelen.

### Ontdekking M: Glover heeft geen toggle-button voor handmatige tests

Tijdens hysterese-validatie wilden we OSC `/up` triggeren met val=0 voor RELEASE-pad. Glover heeft alleen "Send Value"-push als handmatige actie, geen toggle. Dat maakt continuous-pad-validatie zonder Leap-hardware lastig. **Voor volgende sessie**: Leap aansluiten, of mock-Pd-patch bouwen die continuous ramps stuurt.

### Ontdekking N: bestaande mappings krijgen geen retro-actieve thresholds

Een mapping toegevoegd vóór de hysterese-patch heeft geen `thresholdActive`/`thresholdInactive`. Bij `load()` blijft die zonder thresholds — wordt door bridge geïnterpreteerd als binary-mode. **Niet kritiek nu** want we hebben de oude mapping handmatig verwijderd, maar als idempotent migration-pad ooit nodig is, voeg dan defaults toe in `load()` ook (niet alleen in `add()`).

### Ontdekking O: state-Map is bewust niet-persistent

`stateById` in triggerStore is in-memory only. Bij bridge-restart begint elke mapping op INACTIVE, ongeacht of de fysieke bron nog actief is. Dit voorkomt "hangende" state na restart, en is in de meeste gevallen wenselijk — fysieke bronnen zoals pedalen zijn typisch niet ingedrukt tijdens een bridge-restart. **Documenteren in fase 3** indien nodig.

## 6. Chat-rendering-bug — strategieën update

### Bevinding deze sessie: ook in code-blocks niet veilig

**Strategie 5 uit vorige sessie was niet volledig betrouwbaar.** Triple-backtick-code-blocks beschermen niet tegen rendering van `bestand.md`-patronen — de bug transformeert ze ook binnen blocks. Voorbeelden van wat we zagen:

- `git status`-output toonde `notes/[feature-midi-pedal.md](http://feature-midi-pedal.md)` in plaats van `notes/feature-midi-pedal.md`
- `ls -lT` filenames werden ook geraakt
- `[main 9b129da]`-output van `git commit` werd beïnvloed

**Effectieve strategieën in deze sessie:**

1. **Shell-globs** (strategie 4 uit vorige sessie) — `feature-midi-pedal*` ontwijkt de bug omdat de extensie wegvalt. **Werkt ook op klein-schaal voor cp-commando's** in deze sessie.
2. **Heredoc met single-quoted EOF-marker** — `cat > file.js << 'TRIGGER_EOF'` werkt voor file-creation zonder dat zsh interne content interpreteert.
3. **Python3-patch-scripts** — voor multi-line patches betrouwbaarder dan sed/heredoc, en niet onderhevig aan shell-quote-issues. Idempotent via marker-checks.

### Bevinding deze sessie: `(1)`-suffix download-valstrik

Browser dedupliceert downloads niet — bij meerdere downloads van dezelfde filename krijgt elke nieuwe `(1)`, `(2)`, etc. suffix. **Bij meerdere revisies in één sessie**: oude downloads in `~/Downloads` weggooien voordat nieuwe downloads gehaald worden, anders wordt de glob `cp ~/Downloads/feature-midi-pedal*` niet eenduidig.

**Diagnostische workflow bij verwarring:**

```
md5 ~/Downloads/feature-midi-pedal*    # zien welke versies er zijn
ls -lT ~/Downloads/feature-midi-pedal*  # zien wanneer ze gedownload zijn
head -3 ~/Downloads/feature-midi-pedal* # zien welke revisie de header zegt
```

Hiermee zien we file-staat, tijdstempels, en revisie-headers. Dat is genoeg om eenduidig te bepalen welke versie de juiste is.

## 7. Status van repo aan einde van sessie

Repo `~/Documents/touchlab-mixer/`:

```
notes/
├── feature-midi-pedal.md (rev 5)
├── adr/
│   ├── ADR-001-protocol-agnostic-event-router.md
│   ├── ADR-002-midi-library-easymidi.md
│   ├── ADR-003-osc-library-node-osc.md
│   └── ADR-004-keyboard-as-third-protocol.md
└── working-docs/
    ├── ws-protocol-spec.md           (gedeeltelijk overruled — zie sectie 3.3)
    ├── fase-1-blueprint.md           (gedeeltelijk overruled — zie sectie 3.3)
    ├── preflight-fase-1.md           (uitgevoerd — kan weg of bewaard)
    └── mock-pd-blueprint.md          (niet meer kritisch — Glover dekt validatie)

bridge.js                  (markers: TRIGGER-FEATURE-V1, TRIGGER-STORE-V1, TRIGGER-START-V1,
                            TRIGGER-KEYBOARD-V2, TRIGGER-MAPPING-TEST-V1, TRIGGER-PERSIST-V1)
trigger.js                 (markers: TRIGGER-FEATURE-V1, TRIGGER-OSC-V1, TRIGGER-NORMALIZE-V1, TRIGGER-HYSTERESE-V1)
triggerStore.js            (markers: TRIGGER-STORE-V1, TRIGGER-HYSTERESE-V1)
index.html                 (markers: TRIGGER-KEYBOARD-V1)
package.json               (met easymidi, node-osc, ws)
package-lock.json
.gitignore                 (met node_modules/)
```

V2-werkomgeving `~/Documents/Pd/PDMixer/v2/`:
- `bridge.js`, `trigger.js`, `triggerStore.js`, `index.html` identiek aan repo
- `bridge.js.backup-2026-05-02-fase1` — backup vóór fase-1-patches
- `trigger.js.backup-2026-05-02-fase2A` — backup vóór hysterese-refactor
- `session.json` heeft één live mapping (id=2: OSC `/up` → pulse, met thresholds 0.5/0.3)

## 8. Open vragen voor volgende sessie

### 8.1 Action-dispatch (de volgende grote stap)

Mapping-match werkt en hysterese werkt. Volgende fase: **bij TRANSITION=ACTIVATE/RELEASE een actie uitvoeren** (zoals `samplerPlay`/`samplerStop`/`queueAdvance`). Beslissing van vorige sessie was **pad X / optie 1b**: bridge stuurt `triggerActivate`/`triggerRelease` naar UI zonder slot, UI bepaalt zelf `ttbQueue[ttbQueuePos]` en routeert naar bestaande `buildTriggerButton`-logica.

Concrete taken:
- WS-message-types `triggerActivate` en `triggerRelease` definiëren
- Bridge-side: bij hysterese-transitie WS-message broadcasten
- UI-side: handler die action-dispatch doet via interne `handleTriggerAction(slot, phase)`-functie (refactor van bestaande pointerdown/pointerup-logica)
- Validatie: keyboard-mapping op `pulse`-actie → echte sample speelt af in TouchLab

### 8.2 Argumentloze OSC fix (latente bug, ontdekking L)

Glover's `/hit`, `/yaw`, `/block1`, `/unblock1` worden nu altijd `value=0` → blijven INACTIVE. Fix-aanpak voorstellen tijdens implementatie. Mogelijke oplossingen:
- Speciale "puls-mode" voor argumentloze paths (één event = één activate+release)
- `value: undefined` als geen arg en die afzonderlijk afhandelen in evaluateHysteresis
- Een nieuw mapping-type `pulse-instant` dat geen state-machine gebruikt

### 8.3 Continuous-pad-validatie (uitgesteld vanwege ontdekking M)

Hysterese-state-machine voor continuous bronnen is ontworpen en geïmplementeerd, maar niet gevalideerd met live continuous data. Twee opties voor validatie:
- Leap aansluiten + Glover-OSC-streaming-mode → echte continuous floats
- Mock-Pd-patch bouwen (zie `notes/working-docs/mock-pd-blueprint.md`)

### 8.4 UI voor mapping-beheer

Nu mappings via DevTools-console worden toegevoegd, niet via UI. Voor productie-gebruik nodig:
- Mapping-lijst in UI (zien wat er gemapt staat)
- Add-knop met learn-flow (druk-houd-release detection)
- Verwijder-knop per mapping
- Eventueel: live-debug-panel voor binnenkomende events tijdens learn

### 8.5 Andere open punten

- **MIDI channel-indexing.** easymidi gebruikt 0-based, MIDI-spec is 1-based. Voor `session.json` kies één conventie en converteer in normalize-laag. Voorstel: 1-based opslaan (mensvriendelijker, MIDI-spec-conform).
- **`pulse-or-gate` duur-threshold global vs per-mapping.** Scope-doc zegt globaal. Bij echt-pedaal-validatie kan blijken dat per-mapping nuttig is. Niet kritisch nu.
- **Backward compat in `triggerStore.load()`.** Mappings zonder thresholds krijgen ze nu niet retro-actief. Tijdens deze sessie was dat geen probleem (handmatig opgeruimd), maar als ooit een complete migration nodig is, defaults ook in `load()` toepassen.
- **`event.preventDefault()` op gemapte keys in UI.** Nu sturen we keystrokes naar bridge, maar browser-default acties blijven werken (toets type-events naar focused input, etc.). Bij gemapte keys zou preventDefault gewenst zijn — maar UI weet pas via bridge welke keys gemapt zijn. Mogelijk oplossing: bridge stuurt mapping-list naar UI bij init, UI past preventDefault toe.

## 9. Werkstrategieën die effectief waren

- **Diagnose-vóór-actie**: meerdere keren tijdens sessie dingen gestopt om eerst staat te valideren (bijv. download-`(1)`-verwarring, `connectToPD()` count-mismatch, `node_modules`-tracking-issue). Voorkomde elk een grotere foutslag.
- **Tussen-commits**: na MIDI werkte → commit. Na OSC werkte → commit. Na keyboard werkte → commit. Drie aparte commits in plaats van één grote. Maakt rollback en troubleshooting later veel makkelijker.
- **Idempotente python3-patches met markers**: voor elke wijziging aan bestaande files (`bridge.js`, `index.html`) gebruikten we een patch-script dat eerst checkt of de marker al aanwezig is, en dan de needle telt op exact 1. Voorkomt dubbel-toepassen en geeft duidelijke errors.
- **Plak-één-output-per-keer-policy**: zsh raakt verstrikt als meerdere commando's tegelijk worden geplakt waarvan één gefaalde wordt. Eén commando per plak voorkomt dit.

## 10. Wat de volgende sessie zou moeten doen

In volgorde van prioriteit:

1. **Lees deze overdracht en `notes/feature-midi-pedal.md` revisie 5.**
2. **Pre-flight kort**: bevestig baseline draait (canonical startup), bridge logt nog steeds drie protocollen + `[trigger-store] loaded N mapping(s)` bij startup. Test eventueel of bestaande mapping (id=2: OSC `/up` → pulse) nog matcht.
3. **Eerste reparatie**: argumentloze OSC-bug fixen (ontdekking L) — kleine fix, opent het pad voor `/hit`-style triggers.
4. **Action-dispatch (fase 3 begin)**: kies kleinste deelstap. Voorstel: alleen `pulse`-actie laten werken via WS-message naar UI, UI proxiet naar bestaande logica. Continuous bronnen kunnen wachten tot continuous-validatie (Leap of mock-Pd) beschikbaar is.
5. **Continuous-pad-validatie**: ofwel Leap aansluiten ofwel mock-Pd-patch bouwen.
6. **Pas dan UI voor mapping-beheer** — laagste prioriteit gegeven dat we nu via DevTools-console verder kunnen.

Inschatting fase 3 + UI: 4-6 uur, gespreid over meerdere sessies.

## 11. Cross-referenties

- **Vorig overdrachtsdoc**: `overdrachtsdocument-werksessie-2026-05-01-avond.md` (canonical startup, eerdere ontdekkingen A t/m E, queue-feature-architectuur)
- **Scope-doc trigger-feature**: `notes/feature-midi-pedal.md` revisie 5
- **ADR-reeks trigger-feature**: `notes/adr/ADR-001` t/m `ADR-004`
- **Werkdocumenten trigger-feature**: `notes/working-docs/` (vier files, met disclaimer)
- **Markers in code voor trigger-feature**:
  - `TRIGGER-FEATURE-V1` (bridge.js regel 12, trigger.js regel 1)
  - `TRIGGER-START-V1` (bridge.js regel 706)
  - `TRIGGER-STORE-V1` (bridge.js regels 13 en 49, triggerStore.js)
  - `TRIGGER-OSC-V1` (trigger.js regels 5, 34)
  - `TRIGGER-NORMALIZE-V1` (trigger.js — central onEvent)
  - `TRIGGER-KEYBOARD-V1` (index.html regel 1113)
  - `TRIGGER-KEYBOARD-V2` (bridge.js regel 610 — geüpgraded van V1)
  - `TRIGGER-MAPPING-TEST-V1` (bridge.js regel 614)
  - `TRIGGER-PERSIST-V1` (bridge.js regels 615, 626)
  - `TRIGGER-HYSTERESE-V1` (trigger.js + triggerStore.js)
