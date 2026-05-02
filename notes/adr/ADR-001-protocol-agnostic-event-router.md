# ADR-001: Protocol-agnostische event-router voor trigger-input

**Status:** Accepted
**Datum:** 2 mei 2026
**Stakeholders:** Uli (lead), Claude (review en implementatie)
**Gerelateerde documenten:** `notes/feature-midi-pedal.md` (revisie 3, 2 mei 2026)

## Context

De trigger-feature ondersteunt input van twee fundamenteel verschillende protocollen:

- **MIDI** — DIY-box (jack→USB), keyboard sustain-pedaal, drumpad, eventueel sustain-pedalen rechtstreeks via een class-compliant USB-MIDI-pedaal
- **OSC** — Glover (van Leap-sensor naar Max of rechtstreeks naar bridge), eventueel andere OSC-bronnen

Beide protocollen verschillen in:

- **Waarde-range**: MIDI is integer 0-127, OSC is typisch float 0.0-1.0 (maar niet gegarandeerd — OSC kent geen range-conventie)
- **Identifier-structuur**: MIDI gebruikt `{type, channel, number}`-tupel, OSC gebruikt een hiërarchisch path met optionele value-arguments
- **Transport**: MIDI via OS-audio-stack (CoreMIDI/ALSA/etc.), OSC via UDP

De feature-eisen vereisen dat een gebruiker meerdere mappings tegelijk actief heeft, mogelijk over beide protocollen heen (bijv. DIY-box CC én Glover-gestures tegelijk). De vraag is: hoe sluit bridge dit architectonisch aan?

## Beslissing

**Bridge wordt een protocol-agnostische event-router**: twee listeners (MIDI, OSC) die normaliseren naar één interne event-vorm, gevolgd door één downstream pipeline (mapping-match → hysterese-state-machine → action-dispatch).

### Interne event-vorm

```
{
  protocol: "midi" | "osc",
  source: <device-name voor MIDI, remote-UDP-address voor OSC>,
  signature: <protocol-specifiek matching-veld>,
  value: <number in eigen waarde-range — niet hernormaliseerd>,
  timestamp: <ms>
}
```

### Mapping-schema heeft protocol-discriminator

Elke mapping bevat een `protocol`-veld (`"midi"` of `"osc"`) en een protocol-specifieke `signature`. Bij elk inkomend event matcht bridge tegen alle mappings via `(event.protocol === mapping.protocol) && signaturesMatch(event.signature, mapping.signature)`.

### Geen waarde-hernormalisatie

Bridge bewaart waarden in hun eigen range. MIDI-waarden blijven 0-127, OSC-waarden blijven hun originele float-range. Hysterese-thresholds in een mapping zijn in dezelfde range als het signaal — `thresholdActive: 70` voor een MIDI-CC, `thresholdActive: 0.55` voor een OSC-float.

Dit voorkomt twee problemen: (1) precisieverlies bij round-trip-conversie, (2) verwarring bij debug-output (gebruiker ziet ruwe waarden zoals zijn bron ze stuurt).

## Consequenties

### Positief

- **Eén pipeline = één plek voor onderhoud.** Bug-fixes, threshold-tuning, dispatch-logica: allemaal op één plek.
- **Toekomstige protocol-uitbreiding zonder herontwerp.** HID, network-controllers, MQTT, OSC-over-WebSocket — elk nieuw protocol kost een nieuwe listener-implementatie en een nieuw `signature`-schema-variant. Pipeline blijft.
- **Heterogene mapping-array werkt direct.** Gebruiker kan DIY-box (MIDI CC) en Glover (OSC path) tegelijk gemapt hebben, bridge handelt beide door dezelfde dispatch-code.
- **Hysterese-logica werkt voor alle protocollen.** Geen aparte state-machines per protocol — verschil zit alleen in welke waarden vergeleken worden tegen welke thresholds.
- **Multi-mapping (v1) en multi-bron-parallel (v2) zijn architectonisch dezelfde uitbreiding.** v2 voegt user-scoping toe aan mappings; pipeline-vorm verandert niet.

### Negatief

- **Iets meer abstractie dan strikt nodig voor v1.** Als we MIDI-only of OSC-only zouden zijn, hadden we geen normalisatie-laag nodig. Verminderbare kost, maar reëel.
- **Range-confusion-risico.** Code die MIDI-waarden tegen OSC-thresholds vergelijkt zonder protocol-check is een latente bug. Mitigatie: thresholds zitten ín de mapping (niet globaal), dus elke vergelijking is impliciet protocol-correct. Code-review moet hier wel op letten.
- **Twee runtime-dependencies** in plaats van één: MIDI-library + OSC-library. Beperkt risico (beide volwassen Node.js-libraries beschikbaar) maar wel meer install-footprint en supply-chain-oppervlak.
- **Source-veld semantisch heterogeen.** Bij MIDI is het een device-name, bij OSC een UDP-address. Voor logging en debug acceptabel, maar mocht source ooit als matching-criterium gebruikt worden (bijv. "alleen events van deze ene Glover-instantie accepteren"), dan wordt de heterogeniteit een ontwerp-uitdaging. Niet in v1-scope.

### Neutraal

- **`pulse-or-gate` duur-threshold werkt protocol-agnostisch.** Held-timer is gewoon `Date.now()`-arithmetic op de event-timestamps — geen protocol-specifieke logica nodig.

## Overwogen alternatieven

### Alternatief 1: MIDI-only in v1, OSC in v2

**Wat:** Bridge luistert alleen op MIDI. OSC wordt v2-feature.

**Waarom verworpen:**
- Hardware-validatie zou pas mogelijk zijn na pedaal-arrival (wachttijd onbekend, mogelijk ≥1 week)
- Glover+Leap is *nu* beschikbaar voor validatie — dat moeten we uitbuiten in v1
- Mapping-schema-uitbreiding na v1-release is een breaking change voor `session.json` (gebruikers met v1-config moeten migreren). Goedkoper om OSC nu meteen mee te ontwerpen.

### Alternatief 2: OSC-only via externe MIDI-naar-OSC-bridge

**Wat:** Bridge luistert alleen op OSC. Gebruikers met MIDI-bronnen installeren een externe tool (ProtoPlug, OSCulator, etc.) om MIDI naar OSC te converteren.

**Waarom verworpen:**
- Externe afhankelijkheid en extra config voor elke MIDI-gebruiker
- DIY-box-gebruikers (zoals Uli) zouden een onnodige extra stap krijgen
- Latency stapelt (USB-MIDI → host → conversie-tool → UDP → bridge)
- TouchLab is een audio-tool die zelf-bevattend zou moeten werken voor de standaard use-cases

### Alternatief 3: Aparte pipelines per protocol

**Wat:** MIDI-pipeline en OSC-pipeline volledig gescheiden, met eigen mapping-storage, eigen hysterese-implementatie, eigen action-dispatch-code. Geen gemeenschappelijke abstractie.

**Waarom verworpen:**
- Code-duplicatie: hysterese-state-machine, action-dispatch, queue-step-logica zouden tweemaal bestaan
- Bug-multiplicatie: elke fix vereist twee plekken
- Cross-protocol mapping-stack onmogelijk: gebruiker zou twee aparte UI's krijgen voor "MIDI-mappings" en "OSC-mappings", en kon ze niet als één lijst zien

### Alternatief 4: Pd-side input-handling via `[notein]`/`[ctlin]`/`[oscparse]`

**Wat:** Pd ontvangt MIDI/OSC direct via native objecten, geen aparte bridge-logica.

**Waarom verworpen:**
- MIDI learn vereist UI-state (gebruikersinteractie tijdens leren), wat niet natuurlijk past in Pd's signaalflow
- Mapping-persistence vereist file-IO of state-objects die in Pd lastiger te beheren zijn dan in Node.js
- Bridge zit al architectonisch tussen UI en Pd; daar past trigger-input ook beter
- Hot-plug-detectie en device-management is in Pd minder volwassen dan in Node.js MIDI-libraries

## Implementatie-notities

- **Normalisatie als eerste stap.** Listeners zetten ruwe events direct om naar interne event-vorm. Downstream code heeft geen protocol-conditionele logica nodig (behalve in `signaturesMatch`, expliciet protocol-bewust).
- **`signature`-veld is per protocol typed.** TypeScript-interface (als bridge TS gebruikt) of duck-typing met runtime-validatie. Beslissen tijdens fase 1 op basis van bestaande bridge-stijl.
- **Source-veld is informatief, niet matching-criterium.** v1 gebruikt source alleen voor logs en UI-display ("event ontvangen van Glover op 192.168.1.42"). v2 mag uitbreiden.
- **Geen globale event-bus.** Bridge dispatcht direct van listener naar mapping-match-functie. Geen pub-sub-tussenlaag — overengineering voor v1.

## Toekomstige ADR's die hier op voortbouwen

- ADR-002 (te schrijven): MIDI-library-keuze
- ADR-003 (te schrijven): OSC-library-keuze
- ADR-004 (mogelijk later): multi-bron-parallel scoping in v2 (user-channels, conflict-resolutie)
