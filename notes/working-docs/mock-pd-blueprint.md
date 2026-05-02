# Mock-Pd-patch-blueprint — trigger-bron-emulatie

> **⚠️ Status: ontwerp pre-implementatie**
>
> Dit is een werkdocument geschreven vóórdat de Pd-codebase van TouchLab is geïnspecteerd. Het beschrijft objecten, signaalstroom en GUI-layout op basis van standaard Pd-vanilla-conventies. Specifieke object-namen (`[ctlout]`, `[netsend]`, etc.) zijn correcte vanilla-Pd-objecten — die zijn niet "aanname". Wat wel aanname is: passende GUI-layout-stijl voor TouchLab, en consistentie met bestaande dev-tools-patches in `~/Documents/Pd/PDMixer/v2/`.
>
> Bij implementatie: eerst een bestaande Pd-patch in v2 bekijken voor stijl-conventies (kleuren, font-size, label-conventie), dan dit document volgen voor structuur en dan één-op-één bouwen.

**Datum:** 2 mei 2026
**Doel:** specificatie van een mock-Pd-patch die fungeert als trigger-bron-emulatie tijdens fase 1-4 ontwikkeling, voordat een fysiek pedaal beschikbaar is. Kan ook later als regression-test-tool dienen.

## Functionele scope

De mock-patch emuleert drie soorten trigger-bronnen, elk met een eigen test-modus:

1. **Binary CC** — emuleert DIY-box jack→USB MIDI-pedaal (direct 0/127 toggle)
2. **Continuous CC ramp** — emuleert piano sustain-pedaal (geleidelijk 0→127→0 over korte tijd)
3. **OSC** — emuleert Glover/Leap (UDP-bericht naar bridge)

Elk modus heeft een eigen "trigger"-knop en eigen instellingen. De patch is bedoeld voor de ontwikkelaar, niet voor productie-gebruik — UI hoeft dus niet super-glanzend, alleen functioneel duidelijk.

## Locatie en filename

```
~/Documents/Pd/PDMixer/v2/dev-tools/trigger-mock.pd
```

Folder `dev-tools/` is nieuw — wordt door build-scripts (regen.sh) niet aangeraakt, blijft buiten productie-Pd-paden. Ook in repo committen onder `dev-tools/trigger-mock.pd` zodat de mock vindbaar is voor toekomstige sessies.

Eventueel later een `dev-tools/README.md` toevoegen die de mock-patch en eventuele andere dev-tools beschrijft. Niet kritisch voor v1.

## Pd-objecten en signaalstroom

### Modus 1: Binary CC

```
       [bng] "Trigger DOWN"          [bng] "Trigger UP"
          |                               |
       [127]                           [0]
          |                               |
          +---------+---------------------+
                    |
              [ctlout 64 1]
              (controller=64, channel=1)
```

**Werking:** klik DOWN-knop → stuurt CC 64 op kanaal 1 met value 127. Klik UP-knop → stuurt CC 64 met value 0.

**Voor TouchLab-bridge integratie:** Pd's MIDI-output gaat naar het systeem-MIDI-bus (CoreMIDI op macOS). Bridge moet kunnen luisteren op een input-bus die deze output ontvangt. Standaard-aanpak op macOS: gebruik **IAC Driver Bus 1** (een virtuele MIDI-loopback). Pd output → IAC Bus 1 → bridge input via easymidi.

**Configuratie nodig in macOS Audio MIDI Setup:** IAC Driver enabled, één bus (default Bus 1). Eenmalige setup, dan werkt het tussen alle Pd-instances en alle MIDI-input-applicaties.

**Configuratie nodig in Pd:** Pd-preferences → MIDI → output device → "IAC Driver Bus 1". Vereist herstart van Pd na wijziging. **Open vraag voor Uli:** is IAC al geconfigureerd in jouw Pd-setup? Mogelijk ja, omdat je MIDI-werk doet.

### Modus 2: Continuous CC ramp

```
   [bng] "Send ramp"
      |
      |     [hsl] "Duration ms" [50, 1000, default 200]
      |       |
      |     [t f f]------+
      |       |          |
      +-->[t b b]         |
              |  |        |
              |  +-->[$1, 127 $1, 0(   ← message: ramp 0→127 in N ms, dan 127→0 in N ms
              |          |
              |       [line]            ← fixed-point ramp generator
              |          |
              |       [int]             ← convert float to int 0-127
              |          |
              +-->     [ctlout 64 1]
              |
              [delay 0]                 ← optionele guard
```

**Werking:** klik "Send ramp" → Pd genereert CC-waarden van 0 oplopend tot 127, dan terug naar 0, totale duur instelbaar via slider (default 200ms). Bridge moet hysterese-state-machine correct activeren bij de stijgende flank en deactiveren bij de dalende flank.

**Compactere implementatie alternatief** met `[line]`:

```
   [bng]
    |
   [t b b]
   |  |
   |  [0 0( ← reset eerst
   |   |
   |   [line]
   |
   [127 100, 0 100( ← naar 127 in 100ms, dan naar 0 in 100ms (totaal 200ms)
    |
   [line]
    |
   [int]
    |
   [ctlout 64 1]
```

**Validatie-criteria:** continuous-ramp-modus is succesvol als bridge **één** activate-event en **één** release-event detecteert tijdens de ramp, niet meerdere flips door drempel-jitter. Dat is de hele reden waarom we hysterese gebruiken.

### Modus 3: OSC

```
       [bng] "OSC trigger DOWN"        [bng] "OSC trigger UP"
          |                                  |
        [127]                              [0]
          |                                  |
          +-------+--------------------------+
                  |
                  | (value)
                  |
       [pack /test/path 127]    ← message: OSC-path + value
                  |
       [list trim]              ← strip list-prefix indien nodig
                  |
       [oscformat]              ← format als OSC-binary blob (vanilla-Pd)
                  |
       [list]                   ← convert to byte-list
                  |
       [netsend -u -b 127.0.0.1 9100]   ← UDP broadcast naar localhost:9100
```

**Of**, met externals (`mrpeach/[udpsend]` als die in jouw Pd-installatie zit):

```
       [bng] DOWN                       [bng] UP
          |                                  |
        [127]                              [0]
          |                                  |
          +----------+-----------------------+
                     |
              [send /test/path $1(    ← OSC-message met value
                     |
              [oscformat]
                     |
              [udpsend 127.0.0.1 9100]
```

**Open vraag voor Uli:** welke OSC-objecten zijn beschikbaar in jouw Pd-installatie? Standaard vanilla-Pd heeft `[oscformat]` en `[oscparse]`. Externals zoals `mrpeach` voegen `[udpsend]` toe wat ergonomisch handiger is. Als geen externals, dan met `[netsend -u]` werken.

**Configureerbaar OSC-pad** zou nice-to-have zijn — een `[symbolatom]` waar je een path kunt typen, gevolgd door `[pack /<path> <value>]` met dynamische pad-substitutie. Voor v1 hardcoded `/test/path` is voldoende, en eventueel later een tweede knop met `/glover/fist-1` voor Glover-emulatie.

## GUI-layout

Geen complexe layout nodig. Drie horizontale secties verticaal gestapeld:

```
+------------------------------------+
| ── Modus 1: Binary CC ──           |
| [DOWN] [UP]   Channel: 1  CC: 64  |
+------------------------------------+
| ── Modus 2: Continuous CC ramp ── |
| [Send ramp]  Duration: ──○── 200  |
+------------------------------------+
| ── Modus 3: OSC ──                |
| [DOWN] [UP]   Path: /test/path    |
| Target: 127.0.0.1 : 9100          |
+------------------------------------+
| Status: laatste event om HH:MM:SS |
+------------------------------------+
```

Comments (gebruikmakend van Pd's comment-objecten) als headers per sectie. Bang-knoppen (`[bng]`) als trigger-buttons. Slider (`[hsl]`) voor duration. Number boxes voor channel/CC-nummer (configureerbaar voor flexibiliteit).

**Aanbeveling voor stijl:** kijk eerst naar bestaande Pd-patches in `~/Documents/Pd/PDMixer/v2/` om consistentie te behouden — kleuren, font-grootte, label-positie. Mocht er een styleguide zijn (zelfs informeel), volg die.

## Test-procedure (na fase 1 implementatie)

Met fase 1 bridge actief en mock-patch geopend:

1. **Test modus 1**: klik DOWN-knop in mock-patch → bridge logt MIDI-event → UI debug-panel toont `[midi] IAC Driver Bus 1 {"type":"cc","channel":1,"number":64} = 127`. Klik UP → zelfde maar `= 0`.
2. **Test modus 2**: klik "Send ramp" → UI debug-panel toont een **stortvloed** van events (mogelijk 50-100 binnen 200ms). Dit is verwacht en valideert dat bridge geen events filtert (filtering komt in fase 3 via mapping-match).
3. **Test modus 3**: klik OSC DOWN → UI debug-panel toont `[osc] 127.0.0.1:port {"path":"/test/path","valueIndex":0} = 127`. Idem UP met `= 0`.
4. **Stress-test**: snel achterelkaar klikken op meerdere knoppen → events arriveren in juiste volgorde, geen drops.

Als alle vier slagen, mock-Pd is functioneel.

## Wat de mock NIET hoeft te doen in v1

- **Multiple devices emuleren tegelijk** — één instance van Pd, één virtual MIDI-port, één OSC-port. Voor v1 voldoende.
- **Hardware-pedaal-quirks emuleren** (inversed polarity, half-pedaal-states, weird BLE timing) — die valideren we pas met echte hardware in fase 5.
- **Auto-trigger** (bijv. "elke 1 seconde een binary toggle"). Mocht handig zijn voor langlopende stress-tests, maar v1 doet manuele clicks.
- **Visuele feedback** wanneer bridge een event ontvangt. Mock-Pd weet niet wat bridge doet — dat zien we in TouchLab-UI debug-panel.
- **Mock van keyboard-protocol** — niet nodig, gewone toetsenbord-keystroke in browser-tab werkt al perfect als mock.

## Open vragen voor implementatie

- **IAC Driver geconfigureerd in jouw setup?** Mogelijk al — je werkt regelmatig met MIDI.
- **Welke OSC-externals beschikbaar in jouw Pd?** Vanilla heeft `[oscformat]`/`[oscparse]`/`[netsend -u]`. Mrpeach heeft `[udpsend]` (compacter). Speciale Pd-distros (Pd-l2ork, Purr Data) hebben uitgebreidere sets.
- **Pd-patch-stijl-conventie van TouchLab?** Bestaat een styleguide voor TouchLab-Pd-patches (kleuren, fonts, label-positie)? Zo nee, gewoon vanilla-Pd-defaults.
- **Mock in repo of niet?** Voorstel: ja, in `dev-tools/trigger-mock.pd`. Klein bestand (paar KB), helpt toekomstige sessies. Tegen-argument: dev-tools horen niet in productie-repo. Geen sterke voorkeur — Uli beslist.
- **Eén mock-patch met drie modi vs drie aparte patches?** Voorgesteld: één patch met alle drie modi (compacter, één window). Drie aparte zou minder gemixte signalen geven (geen kans dat je per ongeluk OSC stuurt terwijl je MIDI test). Voor v1 één patch lijkt voldoende.

## Implementatie-volgorde

Bij eventuele fase 1.5 implementatie-sessie:

1. **Open Pd, maak nieuwe patch**: `~/Documents/Pd/PDMixer/v2/dev-tools/trigger-mock.pd`
2. **Bouw modus 1 eerst** (simpelste). Test direct dat `[ctlout]` MIDI uitstuurt naar IAC Bus 1, en dat een MIDI-monitor (bijvoorbeeld macOS Audio MIDI Setup → MIDI Studio → MIDI Monitor, of de gratis "MIDI Monitor.app") het oppikt. Dit is **vóór** bridge-fase-1-implementatie — zorgt dat het MIDI-pad onafhankelijk gevalideerd is.
3. **Bouw modus 3** (OSC). Test met een OSC-monitor (`oscdump 9100` op de command line via `liblo`-tools, of een Pd-test-receiver). Idem onafhankelijk valideren.
4. **Bouw modus 2** (continuous ramp). Iets complexer met `[line]` of vergelijkbaar — maar vereist niet meer dan modus 1 om te testen.
5. **GUI-layout polijsten**: comments toevoegen, knoppen netjes uitlijnen, sectie-headers.
6. **Save en commit** naar repo.

## Verwijzingen

- `notes/feature-midi-pedal.md` revisie 5, sectie "Mock-Pd-bron"
- `notes/working-docs/fase-1-blueprint.md` voor bridge-zijde van de validatie
- Pd-vanilla-documentatie: `[ctlout]`, `[oscformat]`, `[netsend]`, `[line]`
- macOS IAC Driver setup: Audio MIDI Setup → MIDI Studio → IAC Driver → "Device is online"
