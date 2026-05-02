# ADR-004: Keyboard als derde protocol in de event-router

**Status:** Accepted
**Datum:** 2 mei 2026
**Stakeholders:** Uli (lead), Claude (review en implementatie)
**Verhouding tot eerdere ADRs:** breidt ADR-001 uit van twee-protocol- naar drie-protocol-router. Vervangt de v2-aanpak voor HID-pedalen die in `notes/feature-midi-pedal.md` revisies 4 stond.
**Gerelateerde documenten:** `notes/feature-midi-pedal.md` (revisie 5), `notes/adr/ADR-001-protocol-agnostic-event-router.md`

## Context

ADR-001 vastgesteld dat bridge een protocol-agnostische event-router heeft met twee listeners (MIDI, OSC). Tijdens uitwerking kwam HID-pedaal-ondersteuning ter sprake — specifiek voor BLE-HID-pedalen zoals PageFlip Firefly, die als BLE-keyboard pairen en keystrokes sturen.

Eerste voorstel in scope-doc revisie 4: externe OS-keymap-tools (Karabiner / AutoHotkey / xdotool) detecteren de keystrokes en sturen OSC naar bridge. Bridge blijft strict MIDI+OSC.

Bij latere iteratie werd ingezien dat de **TouchLab-UI zelf de keystrokes al ontvangt** — het is een browser-app, BLE-pedaal-pairing met de iPad maakt het pedaal een gewoon toetsenbord, en `window.addEventListener('keydown', ...)` werkt out-of-the-box. Externe tool overbodig.

De vraag: hoe integreren we deze derde event-bron in de architectuur?

## Beslissing

**Keyboard wordt third first-class protocol in de event-router**, met de listener in de UI in plaats van bridge. UI vangt `keydown`/`keyup`-events op `window`, filtert OS-key-repeat, normaliseert naar de interne event-vorm uit ADR-001, en stuurt over WebSocket naar bridge. Bridge handelt het event identiek aan MIDI/OSC events: mapping-match → state-machine (overgeslagen voor binary keystrokes) → action-dispatch.

### Interne event-vorm (uitbreiding van ADR-001)

```
{
  protocol: "midi" | "osc" | "keyboard",
  source: "ui" voor keyboard-events,
  signature: { key: <KeyboardEvent.key | KeyboardEvent.code> },
  value: 0 of 1,
  timestamp: <ms>
}
```

Mapping-schema krijgt `protocol: "keyboard"` als derde optie naast de bestaande twee. Voor keyboard-mappings zijn `thresholdActive`, `thresholdInactive`, `valueRange` weggelaten — niet zinvol voor binary signalen.

## Consequenties

### Positief

- **BLE-HID-pedalen (Firefly etc.) ondersteund in v1.** Geen Karabiner/AutoHotkey/xdotool installatie nodig, geen OSC-tussenroute. Enige user-action: pedaal pairen via iPad-Bluetooth.
- **Multi-functie-pedalen werken simultaan met bladmuziek-apps.** Bij modellen met configureerbare keystrokes per knop kunnen sommige knoppen aan forScore en andere aan TouchLab gemapt zijn — werkt zonder cross-app-conflict mits de keystroke-keuzes uniek zijn.
- **Cross-platform via browser.** Browser-event-API werkt op macOS, Linux, Windows, iPadOS, Android — overal waar TouchLab-UI draait. Geen platform-specifieke implementaties.
- **Eenvoudiger code-pad voor keyboard.** Hysterese-state-machine wordt overgeslagen — keydown=active, keyup=inactive, geen tuning. Held-duur-meting (voor `pulse-or-gate`) werkt identiek aan andere protocollen.
- **Mock-validatie triviaal.** Een gewone toetsenbord-keystroke in dezelfde browser-tab simuleert pedaal-input perfect — geen apart mock-apparaat nodig voor keyboard-pad-tests.

### Negatief

- **UI-focus vereist voor keystroke-detectie.** Andere protocollen (MIDI/OSC) ontvangen events ongeacht UI-focus, want bridge-side. Voor keyboard moet TouchLab-UI focus hebben. In praktijk gewenst gedrag (bladmuziek-pedalen werken in bladmuziek-app, sample-trigger-pedalen in TouchLab), maar wel asymmetrie tussen protocollen die documentatie moet noemen.
- **iPad-Safari-keystroke-quirks.** Niet alle keystrokes worden door Safari aan JS doorgegeven — sommige function-keys kunnen door iOS afgevangen worden. F13–F19 relatief veilig maar te valideren per-key tegen test-pagina (`keyjs.dev` of vergelijkbaar) voordat een mapping wordt vastgelegd.
- **Browser-shortcuts kunnen niet worden onderschept.** Cmd+R (reload), Cmd+T (new tab), etc. blijven browser-acties; `event.preventDefault()` kan deze niet blokkeren. Learn-flow moet waarschuwen als gebruiker een browser-shortcut als mapping-target probeert.
- **Listener-locatie asymmetrisch.** MIDI/OSC in bridge, keyboard in UI. Niet ideaal voor uniformiteit van code-organisatie, maar onvermijdelijk: keystrokes komen alleen via browser binnen.

### Neutraal

- **Interne event-vorm consistent.** Downstream code (matching, dispatch, action-table) is identiek over alle drie protocollen. Asymmetrie zit alleen in de detectie-laag.
- **WS-bandbreedte triviaal hoger.** Een paar extra events per minuut over een al-bestaande WS-verbinding. Geen meetbaar effect.

## Overwogen alternatieven

### Alternatief 1: HID-listener in bridge via `node-hid`

- **Wat:** Bridge opent HID-device direct (BLE-HID-pedaal als HID-device leest), leest raw HID-reports, normaliseert naar interne event-vorm.
- **Waarom verworpen:**
  - Vereist HID-permission-prompts op macOS bij eerste gebruik
  - Cross-platform HID-codes verschillen — extra abstractie-laag nodig
  - BT-pairing moet alsnog via OS — geen voordeel boven keyboard-aanpak
  - Extra C++ binding (`node-hid`), meer install-complexiteit
  - Werkt alleen op het apparaat waar bridge draait — niet op iPad als TouchLab-UI op iPad draait en bridge op Mac

### Alternatief 2: OS-keymap-tool (Karabiner / AutoHotkey / xdotool)

- **Wat:** Externe tool detecteert keystrokes en stuurt OSC naar bridge. Bridge blijft strict MIDI+OSC.
- **Waarom verworpen:**
  - Externe tool-installatie en -configuratie voor elke gebruiker
  - Drie verschillende tools afhankelijk van OS — fragmentatie van docs en supportlast
  - Extra latency-laag (keystroke → tool → OSC → bridge)
  - Configuratie-fragiliteit: bij OS-update of tool-update kan de mapping breken
  - Dubbele config (Firefly-config-app + Karabiner-config) — verwarrend voor gebruikers

### Alternatief 3: Geen HID-pedaal-support in v1

- **Wat:** Status quo zoals in scope-doc revisie 4 — HID-pedalen zijn v2 met OS-keymap-tool.
- **Waarom verworpen:**
  - Veel TouchLab-gebruikers hebben BLE-HID-pedalen al in gebruik voor bladmuziek
  - Met de keyboard-protocol-aanpak is implementatie-overhead minimaal (~30 minuten code)
  - "Werkt direct met je bestaande pedaal" is een sterk product-signal voor adoption

## Implementatie-notities

- UI-listener: `window.addEventListener('keydown', handler)` en `keyup`, niet op specifiek element — pedaal-keystrokes kunnen vanuit elk focus-element komen
- Filter `event.repeat === true` om OS-key-repeat tijdens vasthouden te negeren — alleen eerste keydown telt
- Op gemapte keys: `event.preventDefault()` blokkeert browser-default-actie en propagatie naar andere handlers
- WS-message-formaat van UI naar bridge:
  ```
  { type: "keyboard-event", key: "F13", value: 1, timestamp: 1714657890123 }
  ```
- Bridge ontvangt, normaliseert naar interne event-vorm met `protocol: "keyboard"`, `source: "ui"`, `signature: { key }`, en routeert door zoals elk ander event
- Voor `signature.key` aanbeveling: gebruik `KeyboardEvent.code` (`"F13"`, `"KeyA"`) i.p.v. `key` (`"F13"`, `"a"`/`"A"`) — `code` is layout-onafhankelijk en case-insensitive
- Hysterese-state-machine in bridge: detecteer `protocol === "keyboard"`, sla state-machine over, ga direct van keydown→ACTIVE→keyup→INACTIVE
- `pulse-or-gate` voor keyboard: bridge meet held-duur tussen niet-repeat-keydown en keyup, vergelijkt met `pulseOrGateThresholdMs` zoals voor andere protocollen

## Verwijzingen

- ADR-001 (origineel twee-protocol-design, blijft geldig — dit ADR is een uitbreiding)
- `notes/feature-midi-pedal.md` revisie 5 — bevat de Firefly-use-case en BLE-HID-sectie
- MDN docs over `KeyboardEvent.code`: https://developer.mozilla.org/en-US/docs/Web/API/KeyboardEvent/code
