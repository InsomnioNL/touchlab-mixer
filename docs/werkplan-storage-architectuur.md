# TouchLab TTB — Werkplan: Storage-architectuur

**Datum opgesteld:** 26 april 2026
**Doel:** rec/load/sample-flow van halve pleisters naar één coherente architectuur
**Verwachte sessies:** 2-3, afhankelijk van hoeveel parallel kan
**Status startpunt:** geen feature commit-bare staat per sessie — we werken zolang het loopt en committen aan einde van een coherent stuk

---

## Wat er nu fout zit (de aanleiding)

Diagnose tijdens de sessie van 26 apr middag:

1. **`sampler-slot-1.pd` regel 171** heeft een hardcoded absoluut pad naar de **legacy-folder** (`/Users/ulrichpohl/Documents/Pd/PDMixer/samples/slot1.wav`, zonder v2). Bestaat niet meer. Opnames belanden dus stilletjes nergens.
2. **Inconsistentie binnen slot-1** zelf: schrijfpad is absoluut (regel 171), leespad is relatief (regel 178). Twee paradigma's in één bestand.
3. **`generate-slots.py` is path-onbewust** — kopieert de slot-1 template inclusief de fout naar slots 2-8.
4. **Geen filename-strategie** — slot1.wav is de enige naam, dus elke nieuwe rec overschrijft de vorige. Geen history mogelijk.
5. **Pd's werkdirectory is impliciet** — als slot-1 ooit relatieve paden krijgt, is hun resolutie afhankelijk van hoe Pd is opgestart. Niet robuust.

Effect: rec-flow werkt al langer niet, niemand had gemerkt. Bestanden in `samples/` zijn allemaal **via de file-picker** geüpload, niet via rec.

---

## Ontwerpprincipe

> **Filename = bridge-bezit. Pd is path-blind.**

Pd-patches bevatten geen letterlijke `samples/` of `/Users/`-strings. Alle paden komen via berichten binnen, gestuurd door de bridge. De bridge is de enige component die weet waar bestanden op disk staan, hoe ze heten, en hoe history zich opbouwt.

**Waarom:** dit maakt eindpunt-distributie straks triviaal (Uli's vraag op 26 apr middag). De bridge wordt natuurlijke owner van filename-state, en kan bestanden aan andere eindpunten doorgeven zonder dat Pd daar partij in is.

---

## Doelarchitectuur

### Pd-laag (slot-template)

- **Schrijfpad** komt binnen via `sampler-rec-path <slot> <abs-pad>`-bericht, vóór rec-start. Slot bewaart het in een `value`-object en gebruikt het in de `list append -wave <pad> slotN`-keten.
- **Leespad** blijft via het bestaande `sampler-load <slot> <pad>`-bericht. Werkt al, geen wijziging nodig.
- **Geen letterlijke paden** meer in de slot-pd files. Hardcoded `/Users/...` weg, hardcoded `samples/...` weg.
- **`generate-slots.py` wordt path-bewust** — de template gebruikt placeholders die door de generator worden gevuld, of werkt volledig path-blind.

### Bridge-laag

- **Bij rec-start:** bridge stuurt `sampler-rec-path <slot> <abs-pad>` met de gewenste write-locatie, dán `sampler-rec-start <slot>`.
- **Bij rec-stop confirmation:** bridge weet dat het bestand klaar is. Volgens history-policy (zie hieronder) maakt hij een gedateerde kopie en houdt het origineel bij voor "actief".
- **Bij load:** bridge stuurt `sampler-load <slot> <abs-pad>` zoals nu — alleen wordt het pad nu door de bridge bepaald, niet meer impliciet door Pd's werkdirectory.
- **Sessie-archief:** uitbreiden met per slot
  - `active_file`: de huidige wav voor dit slot (bv. `slot1.wav` als referentie naar de actieve)
  - `history`: array met objects `{filename, recorded_at, user_name?}` voor metadata zoals user-given names

### Filesystem (samples/)

```
samples/
  slot1.wav                              ← canonieke naam, Pd schrijft hier, Pd leest hier
  slot1_2026-04-26-14-32-15.wav          ← history-kopie 1
  slot1_2026-04-26-14-35-02.wav          ← history-kopie 2
  bach-fuga-take3.wav                    ← user-renamed file (door rename-pass aan einde sessie)
  attenborough.wav                       ← handmatig geüpload, niet aan slot gebonden
```

**Convenant**: `slotN_<timestamp>.wav` is een history-bestand van slot N (filesystem-truth). User-renamed bestanden hebben een arbitraire naam en alleen de sessie-json weet welk slot ze "horen".

---

## Implementatieplan (gefaseerd)

### Fase 1 — Pd path-injection (sessie 1 grootste deel)

**Doel:** slot-template ontvangt write-pad via bericht, geen hardcoded paden meer.

#### 1A-bis. Bewezen architectuur (sessie 26 apr middag)

Tijdens deze sessie is de stitch-architectuur volledig gevalideerd in een serie testbestanden (`test-rec-path.pd`, `test-rec-path-v2.pd`, `test-rec-path-v3.pd`). Het werkt. Hier zijn de bewijzen en de gevallen:

**Bewezen werkend:**

```
[r sampler-rec-path]              ← luistert globaal
       ↓
[route 1]                         ← filter slot-nummer
       ↓ (outlet 0 = match)
[symbol]                          ← cast naar symbol
       ↓
[s slot1-rec-path-sym]            ← bewaar

---

Bij rec-stop, write-keten:

[bng / trigger]
       ↓
[t b b]                           ← splits 2x bang
       ↓ (outlet 0)
[value rec-length]                ← of floatatom — werkt beide
       ↓
[list prepend write -nframes]
       ↓
[list append -wave]
       ↓
[list append] ← [r slot1-rec-path-sym]   ← outlet 1 van [t b b] triggert receive
       ↓
[list append <array-naam>]
       ↓
[list trim]
       ↓
[t a a]                           ← LET OP: t a a, NIET t l l (zie valkuilen)
       ↓ (outlet 0 → soundfiler, outlet 1 → print debug)
[soundfiler]
```

**Bewezen gedrag:**

- **Pad-injection werkt:** symbol uit FUDI-style `; receiver value`-msg komt netjes in de stitch
- **Variabele lengte werkt:** floatatom of `value`-object kan de hardcoded `48000` vervangen, wordt netjes door [t b b] gepasseerd
- **Route filtert correct:** bericht voor slot 2 wordt door `[route 1]` weggefilterd, schrijf-actie blijft bij het oorspronkelijke pad (nooit naar `wrong.wav` geschreven in de test)
- **Init-veiligheid:** als geen pad gezet vóór WRITE → soundfiler faalt luidruchtig met usage-melding, oude bestand niet aangeraakt. Geen halve corruptie. Goeie veiligheidsmarge.

**Belangrijke valkuilen (geleerd, niet opnieuw doen):**

1. **`[t l l]` werkt NIET** als splitter na list-bouw — de soundfiler-msg begint met selector `write`, niet pure list. Pd geeft "trigger: generic messages can only be converted to 'b' or 'a'". **Gebruik `[t a a]`** (anything-anything).

2. **Een msg met `;`-syntax (`#X msg ... \; receiver value;`) heeft geen outlet** — hij verstuurt direct via send/receive. Verbind hem nergens.

3. **`[r ...]`-objecten hebben geen inlet** — ze ontvangen via hun symbol, niet via een wire. Geen connects naar receive-objecten.

4. **`osc~` accepteert geen `bang`** — voor signal-bronnen geldt: DSP aan = continu signaal. Een bang naar osc~ geeft "no method for bang".

5. **`#X floatatom`-syntax voor default-value:** mijn poging `#X floatatom 20 565 7 0 0 0 - - - 48000;` toont 0, niet 48000. De default-positie in Pd's syntax is anders dan ik dacht. **Workaround:** typ de waarde handmatig na openen, of gebruik een `[value rec-length]` met loadbang-init.

6. **Pd's object-numbering in tekst-files is hachelijk te repliceren met handmatige tools.** Subpatches en arrays beïnvloeden de telling op manieren die niet triviaal zijn. **Beste praktijk:** tel vanaf idx=0 (NR=1 is de canvas-header en telt niet mee). En als verifieer dat de connects kloppen: open in Pd. Pd is de bron van waarheid.

#### 1A-ter. Concreet patch-plan voor slot-1

Op basis van de diagnose en de bewezen architectuur is dit het exacte plan voor de echte integratie in `sampler-slot-1.pd`. Indices zijn op de huidige toestand (vóór patch).

**Vervangen — één object eruit, drie er voor in de plaats:**

idx 169 (`list append -wave /Users/.../slot1.wav slot1`) is één object dat drie list-elementen tegelijk toevoegt: het `-wave` flag, het pad, en de array-naam. Voor dynamische injection moeten we dit uit elkaar halen in:

```
oud:  [list append -wave /Users/.../slot1.wav slot1]   (idx 169)

nieuw: [list append -wave]            (vervangt idx 169 op zelfde positie)
            ↓
       [list append] ← [r slot1-rec-path-sym]   (twee nieuwe objecten)
            ↓
       [list append slot1]            (één nieuw object)
            ↓
       [list trim]                    (idx 170 — bestaat al, blijft staan)
```

**Toe te voegen — nieuwe pad-receiver-keten:**

Deze keten luistert op `sampler-rec-path`, filtert op slot 1, en bewaart het pad in een symbol-store voor later gebruik:

```
[r sampler-rec-path]
       ↓
[route 1]
       ↓ (outlet 0)
[symbol]
       ↓
[s slot1-rec-path-sym]
```

Plaats: **helemaal aan het einde van het bestand**, zoals we eerder met master-vol gedaan hebben (zie `patch-host-master-vol.py` voor het patroon). Voorkomt dat bestaande object-indices verschuiven.

**Connects die moeten wijzigen:**

| Oud | Nieuw | Reden |
|---|---|---|
| `connect 168 0 169 0` | blijft | `list prepend write -nframes` → `list append -wave` (zelfde idx) |
| `connect 169 0 170 0` | wordt: laatste-nieuwe-list-append → 170 | `list trim` ontvangt nu output van laatste list-append i.p.v. de oude all-in-one |
| nieuw | `<idx-nieuwe-r-pad-sym> 0 <idx-nieuwe-list-append-met-pad> 1` | symbol-receive injecteert pad in tweede inlet van `list append` |

**Nieuwe connects voor de pad-receiver-keten:**

| Verbinding |
|---|
| `r sampler-rec-path` 0 → `route 1` 0 |
| `route 1` 0 → `symbol` 0 |
| `symbol` 0 → `s slot1-rec-path-sym` 0 |

**Strategie voor de patch:**

Twee opties met verschillende afwegingen:

- **Optie X — Patch-script (zoals master-vol).** Schrijf een idempotente Python-script `patch-slot1-rec-path.py` die het werk doet. Voordeel: reproduceerbaar, idempotent, kan in CI/CD. Nadeel: connect-bedrading is ditmaal complexer dan master-vol (we breken een bestaande connect en herleiden door drie nieuwe objecten heen). Risico op telprobleem zoals we vandaag hebben gezien.
- **Optie Y — Met de hand in Pd.** Open slot-1 in Pd, voeg objecten toe, leg connects, sla op. Voordeel: visueel verifieerbaar terwijl je werkt, Pd genereert correcte indices. Nadeel: niet reproduceerbaar.

**Aanbeveling:** **Optie Y voor de eerste implementatie**. Reden: te veel risico in een script gegeven de telproblematiek van vandaag. Pas wanneer slot-1 visueel werkt en getest is, eventueel achteraf een `patch-slot1-rec-path.py` reverse-engineeren door de diff voor en na te analyseren.

**Pre-flight voor sessie 1:**

```bash
# Alle Pd/bridge instances opruimen
pkill -9 -f "Pd-0.55"
pkill -9 -f "node bridge"
sleep 2

# Werkdirectory + backup verifiëren
cd ~/Documents/Pd/PDMixer/v2
ls -la _backups/sampler-slot-1.pd.bak-pre-storage-fase1   # moet bestaan

# Bridge starten (in één tab)
node bridge.js session.json

# Pd starten (in andere tab) — open slot-1 direct, NIET de host:
open sampler-slot-1.pd
```

Werk **direct in slot-1.pd** (niet in touchlab-mixer-ttb.pd). Slot-1 is template — wat hier werkt, vermenigvuldigt straks via regen.sh naar slots 2-8.

#### 1A. Begrijp de huidige schrijfketen (de diagnose)

Tijdens de sessie van 26 apr middag is de keten in slot-1 helemaal uitgetekend. De relevante objecten zitten in `sampler-slot-1.pd` rond regels 159-173 (idx 157-171):

```
[r sampler-rec-stop] (idx 157)
       ↓
[route 1] (idx 158)         ← filter slot-nummer
       ↓
[t b b b b b b b] (idx 159) ← 7-fold trigger
       ↓
       ├─→ stop
       ├─→ trim-start = 0
       ├─→ trim-end = slot1-length
       └─→ [value slot1-length] (idx 167)
              ↓
           [list prepend write -nframes] (idx 168)
              ↓
           [list append -wave <HARDCODED PAD> slot1] (idx 169) ⚡ HIER
              ↓
           [list trim] (idx 170)
              ↓
           [soundfiler] (idx 171)
```

**Het kritieke punt is idx 169.** Die regel moet vervangen door iets dat het pad uit een
value-object haalt in plaats van het hardcoded te hebben.

#### 1B. Implementatie-keuze: Optie 2 (`makefilename`-stijl)

Drie alternatieven zijn overwogen tijdens de diagnose:

- **Optie 1** — value-object met inline-substitutie via `$1`-trucs
- **Optie 2** — `makefilename` met symbool-list-bouw (gekozen)
- **Optie 3** — bridge stuurt complete soundfiler-cmd

Optie 2 is gekozen omdat:
- Idiomatisch Pd: elk Pd-handboek toont dit patroon
- Houdt soundfiler-syntax binnen Pd (geen lekkende abstractie naar bridge)
- Deterministisch en testbaar

**Wat verworpen werd:** Optie 3 zou betekenen dat de bridge moet weten van Pd's `-nframes`/`-wave`-syntax. Dat verstrengelt de lagen die we juist aan het ontvlechten zijn.

#### 1C. Conceptueel ontwerp van de nieuwe keten

```
Inkomend bericht: "sampler-rec-path 1 /abs/path/slot1.wav"

[r sampler-rec-path]
       ↓
[route 1]                  ← filter op slot-nummer
       ↓
[symbol]                   ← cast naar symbol
       ↓
[s slot1-rec-path-sym]     ← bewaar voor gebruik in rec-stop

---

Bij rec-stop, in de schrijf-keten:

[value slot1-length]
       ↓
[list prepend write -nframes]
       ↓
[<stitch-met-symbol>]      ← nieuw: voegt "-wave <pad-uit-symbol> slotN" toe
       ↓
[list trim] → [soundfiler]
```

De exacte stitching-mechaniek (hoe je een symbol uit een receive-object op het juiste moment in een list-bouw stopt) is wat in sessie 1 het kerndenkwerk wordt.

#### 1D. Stappenplan voor sessie 1

**Stap 1 — Test-eerst-in-apart-bestand (cruciaal!)**

Maak `test-rec-path.pd` aan in v2/ — een minimaal experiment-bestand dat alleen de symbol-stitch test, los van slot-1. Doel: bevestig dat we een symbol uit een receive kunnen plukken en in een soundfiler-write-msg kunnen stitchen die daadwerkelijk een wav schrijft.

```
[bang]
  ↓
[test-trigger]
  ↓
... bouw hier de minimale stitch-keten ...
  ↓
[soundfiler] → schrijf naar /tmp/test-rec-path.wav
```

Pas wanneer dit testbestand een wav produceert op het verwachte pad, is het ontwerp valide en mag het naar slot-1.

**Stap 2 — Slot-1 aanpassen (alleen ná stap 1 succes)**

- Backup bestaat al: `_backups/sampler-slot-1.pd.bak-pre-storage-fase1`
- Voeg nieuwe `r sampler-rec-path` + route + symbol-receive ergens bovenin het bestand toe
- Vervang object idx 169 door de stitch-keten uit stap 1
- **Connect-bedrading is het meest delicate** — zeven outputs van de trigger samenkomen in één write-cmd. Voorzichtig met indices.

**Stap 3 — `generate-slots.py` path-bewust maken**

De huidige generator kopieert slot-1 naar slot-2..8 met `slot1` → `slotN` substitutie. Nieuwe symbol-naam (`slot1-rec-path-sym`) moet ook meegenomen.

**Stap 4 — FUDI-route uitbreiden**

- Top-level `touchlab-mixer-ttb.pd`: `sampler-rec-path` als 15e route-token. Patch-script schrijven (analoog aan `patch-host-master-vol.py`).
- `sampler-host.pd`: idem 15e token + `s sampler-rec-path`. Eveneens via patch-script of regen.

**Stap 5 — Bridge-side message-handler**

```javascript
case "samplerRecPath": {
  const absPath = path.resolve(SAMPLER_DIR, msg.path);
  sendSampler("sampler-rec-path", msg.slot, absPath);
  break;
}
```

En in de bestaande `samplerRecStart`-handler: stuur eerst `sampler-rec-path` met het verwachte schrijfpad, daarna pas `sampler-rec-start`.

**Stap 6 — End-to-end test**

- pkill alles, bridge starten, Pd starten
- TTB rec-knop op slot 1
- Bestand moet verschijnen op het door bridge bepaalde pad in `samples/slot1.wav` (relatief aan v2/)
- Geen schrijf naar legacy-folder, geen "No such file"-error
- Tap slot 1 om af te spelen — moet het zojuist opgenomen geluid teruggeven

**Test-criterium fase 1 voltooid:** rec werkt end-to-end zonder hardcoded paden ergens in slot-1.

### Fase 2 — Bridge history-management (sessie 1 of 2)

**Doel:** elke rec-stop creëert een history-kopie naast `slotN.wav`.

- Bridge ontvangt `rec-stopped` status van Pd (bestaat al — regel 270)
- Op dat moment: `fs.copyFileSync('samples/slot1.wav', 'samples/slot1_<ts>.wav')`
- Sessie-json: history-array bijwerken met `{filename: 'slot1_<ts>.wav', recorded_at: <iso-timestamp>}`

**Test:** opnames in history. `slotN.wav` blijft "actief" (Pd's volgende load werkt zonder wijziging).

### Fase 3 — Frontend history-view (sessie 2)

**Doel:** in EDIT-mode per slot een history-lijst met afspelen, hernoemen, activeren, verwijderen.

- index.html: nieuwe component `slot-history-list`
- API in bridge.js: `getSlotHistory <slot>`, `renameSlotHistoryItem <slot> <oldname> <newname>`, `setSlotActive <slot> <filename>`, `deleteSlotHistoryItem <slot> <filename>`
- "Activeren als slot-bron" doet eigenlijk: kopieer history-bestand naar `slotN.wav` + stuur `sampler-load` naar Pd

**Test:** opname maken → in EDIT-mode zien in history → afspelen → hernoemen → activeer een eerdere take → tap slot → hoor de geactiveerde take.

### Fase 4 — Cleanup van halve dingen (sessie 2-3, parallel met 3)

- Pd-werkdirectory eenduidig maken: `start-mixer.sh` schrijven die altijd vanuit `v2/` opent. Optioneel: ook `start-pd.sh` voor expliciete Pd-start.
- File-picker integreren in nieuwe storage-architectuur: handmatig geüpload bestand wordt automatisch naar `samples/` gekopieerd door bridge, sessie-json onthoudt dat het slot-N's actief is.
- Het `attenborough.wav` patroon (handmatig erin gezet) blijven we ondersteunen. Bridge moet snappen dat zo'n bestand niet bij een specifiek slot hoort tenzij expliciet gekoppeld.

---

## Open vragen voor de volgende sessie

Deze beslissingen zijn nu nog niet definitief; aanvliegen wanneer relevant in implementatie:

1. **Sessie-json schema voor history.** Hoe gestructureerd moeten we metadata bewaren? Minimaal `recorded_at` en optionele `user_name`. Mogelijk ook `duration_seconds` (handig voor UI), `peak_level` (voor waveform-thumbnail later)? Begin minimaal, breid uit op behoefte.

2. **Wat doet "verwijderen" precies?** Hard-delete van het bestand, of soft-delete (verplaatsen naar `samples/.trash/`)? Voor klassieke musici is "weg = weg" mogelijk te eng. Soft-delete met "leegmaken bij sessie-einde" is musisch geruststellender.

3. **Wanneer wordt de FUDI-route met `sampler-rec-path` toegevoegd — vóór of ná de filename-injection?** Volgens fase-1-plan vóór, maar mogelijk willen we eerst alleen het hardcoded-pad-probleem oplossen om snelle progressie te zien. Discussie aan het begin van sessie 1.

4. **Hoe gaan we om met crashes tijdens rec?** Als Pd crasht midden in een opname, hebben we een halve `slotN.wav`. Bridge zou dat moeten detecteren (bv. via `rec-stopped` timeout) en het halve bestand niet als history opnemen.

5. **`sampler-slot-1orig.pd` in legacy folder — opruimen of laten staan?** Hij staat nog op `~/Documents/Pd/PDMixer/sampler-slot-1orig.pd`. Niet kritiek, maar onhygiënisch.

---

## Aandachtspunten voor de uitvoering

### Werkstijl

- **Geen halve fixes meer.** We werken een fase af tot hij echt werkt en getest is voor we de volgende beginnen.
- **Commit per fase** (of per substantiële tussenstap). Pushen na een werkende fase.
- **Tests doen we end-to-end, niet alleen "bestand verschijnt op disk."** We tappen het slot, horen geluid, dat is de echte test.

### Backups vóór we de slot-template aanraken

```bash
cd ~/Documents/Pd/PDMixer/v2
cp sampler-slot-1.pd sampler-slot-1.pd.bak-pre-storage-fase1
```

Slot-1 is de template — als we hem stukmaken zonder backup, raken alle 8 slots stuk na regen.sh. Voorzichtig.

### Pd-werkdirectory tijdens debug

Zorg dat Pd vanuit `v2/` is opgestart, anders zijn relatieve paden onvoorspelbaar. Pre-flight check elke sessie:

```bash
pkill -9 -f "Pd-0.55"  # alle vorige sessies opruimen
cd ~/Documents/Pd/PDMixer/v2
open touchlab-mixer-ttb.pd
```

---

## Wat al gedaan is (vermijdbaar dubbel werk)

Deze dingen zijn al klaar, niet opnieuw doen:

- **TCP reconnect-backoff in bridge.js** (commit `f9be3ae`, 26 apr middag) — `connectToPD` heeft nu exponential backoff, geen dubbele timers, socket cleanup. Maakt Pd-restart-tijdens-bridge-draait stabiel.
- **Master-fader V2** (commit `7e32daa`, 25 apr avond) — werkt hoorbaar, alle 8 slots gepatcht, top-level FUDI-route uitgebreid.
- **Idempotente patch-scripts** (`patch-slot1-master-vol.py`, `patch-host-master-vol.py`) — als template voor nieuwe patch-scripts.
- **Stitch-architectuur gevalideerd** (sessie 26 apr middag/avond) — drie testbestanden bewijzen dat path-injection, variabele lengte, en route-filter allemaal werken zoals ontworpen. Zie sectie 1A-bis hierboven voor de geleerde lessen en valkuilen. Testbestanden: `test-rec-path.pd` (basis-stitch), `test-rec-path-v2.pd` (variabele lengte), `test-rec-path-v3.pd` (route op slot-nummer). Gecommit in `e4f0755` als referentie-artefacten.
- **Slot-1 path-injection — fase 1 deel 1 voltooid** (commit `a69b40a`, 26 apr avond) — visueel in Pd gebouwd. Bevat:
  - Pad-receiver-keten: `[r sampler-rec-path]` → `[route 1]` → `[symbol]` → `[s slot1-rec-path-sym]`
  - Schrijfketen herontworpen: `[list prepend write -nframes]` → `[list append -wave]` → `[list append]` ← `[r slot1-rec-path-sym]` → `[list append slot1]` → `[list trim]` → `[soundfiler]`
  - Hardcoded legacy-pad weggehaald
  - Getest: rec zonder pad-set faalt netjes met soundfiler-usage-melding, geen halve corruptie. ✓

## Open voor fase 1 deel 2 (volgende sessie)

Slot-1 alleen heeft path-injection. Om dit naar end-to-end werkend te krijgen:

1. **Bridge uitbreiden** — `samplerRecPath` message-handler in `bridge.js`. Stuurt vóór elke rec-start: `sampler-rec-path <slot> <abs-pad>`. In de bestaande `samplerRecStart`-flow plakken zodat het automatisch gebeurt (niet als losse aanroep). Format pad: `path.resolve(SAMPLER_DIR, 'slot' + slot + '.wav')`.
2. **FUDI-route uitbreiden in `sampler-host.pd`** — `sampler-rec-path` als 15e route-token (na `sampler-master-vol`). Plus een `s sampler-rec-path` om door te leiden. Patch-script schrijven (analoog aan `patch-host-master-vol.py`) of handmatig in Pd.
3. **FUDI-route uitbreiden in `touchlab-mixer-ttb.pd`** — idem 15e token. Dezelfde aanpak als bij master-vol patch.
4. **`generate-slots.py` aanpassen** zodat slot-2 t/m slot-8 dezelfde wijzigingen krijgen via de generator. Slot-1 is nu de template-bron — generator moet de pad-receiver-keten en schrijfketen-aanpassingen kunnen reproduceren met `slot1` → `slotN` substitutie. **Risico:** generator gebruikt sed-substitutie op slot-1, dus `slot1-rec-path-sym` moet `slotN-rec-path-sym` worden. Verifieer dit zorgvuldig.
5. **regen.sh draaien** — alle slots regenereren. Verifieer dat alle 8 slots de nieuwe keten hebben.
6. **End-to-end test** — bridge stuurt pad → Pd schrijft op verwacht pad. Bestand verschijnt in `samples/slot1.wav`. Tap slot 1, hoor opname terug.

**Aandachtspunt voor sessie:** slot-1 in Pd staat nu correct (in v2/ én repo). Als `generate-slots.py` slot-1 zou herschrijven, raken we onze handmatige wijzigingen kwijt. **Optie:** generator alleen slots 2-8 laten regenereren uit slot-1-als-bron. **Of:** generator zo schrijven dat hij slot-1 idempotent regenereert (kan ingewikkeld zijn). Te beslissen begin van sessie.

---

## Project-context (gelijk aan vorige overdracht)

**Wie:** Ulrich Pohl (Uli), van TouchLab/INSOMNIO. Mac-gebruiker, Nederlandstalig. Werkt met klassieke musici. Filosofie: zo veel mogelijk centraal vanuit TERMINAL aansturen, zo headless mogelijk werken.

**Wat:** TTB ("TapTapBoom") is een audio-broadcast-capability waarbij één eindpunt cue-audio (opmaten, clicktracks, samples) afspeelt via JackTrip naar een subset van musici-koptelefoons.

**Werkmap:** `~/Documents/Pd/PDMixer/v2/` (actief), `~/Documents/Pd/PDMixer/` (legacy v1, leeg op `samples/` na). GitHub: `InsomnioNL/touchlab-mixer`, gekloond op `~/Documents/touchlab-mixer/`. **Belangrijk:** v2/ en touchlab-mixer/ zijn parallelle kopieën die *handmatig* gesynct worden.

**Werkstijl:** Nederlands, prozaïsche uitleg, methodisch debuggen. Geen halve fixes. Beslissingen via meerkeuze-vragen wanneer scope onduidelijk is.
