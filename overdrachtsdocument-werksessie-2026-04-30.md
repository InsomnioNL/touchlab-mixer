# Overdrachtsdocument — TouchLab TTB werksessie

**Datum:** 30 april 2026 (vervolg op 29 april avond-sessie)
**Voor:** opvolgende Claude-chats die met Uli werken aan touchlab-mixer
**Bedoeling:** stelt een nieuwe chat in staat zonder herontdekken meteen aan de slag te gaan. Aanvullend op `overgangsdocument-architectuur-discussie.md` (26 april) en `overdrachtsdocument-werksessie.md` (29 april ochtend) — die documenten beschrijven respectievelijk de architectuur-context en de plannen-vooraf voor de avond-sessie. Dit document beschrijft wat er die avond is gebeurd en wat de huidige stand is.

---

## 1. Project en context

TouchLab TTB is een Pure Data-mixer voor live jam-sessies tussen muzikanten op verschillende locaties, verbonden via JackTrip. Uli is muzikant en bouwt deze setup voor zichzelf en zijn collega's. De mixer zit op zijn Mac Mini / mini-pc tussen de inkomende JackTrip-streams van collega's en zijn eigen koptelefoon. Hij heeft geen speakers — alle audio gaat naar zijn koptelefoon.

De mixer heeft drie kernfuncties:

1. **Persoonlijke monitor-mixer** voor binnenkomende collega's-audio plus lokaal afgespeelde TTB-samples.

2. **TTB-sampler** (TouchLab Trigger Box): 8 slots, elk met source-selector, autotrim, queue-mode. Sinds 29 april avond ook een **TTB-out-bus** waarmee TTB-output meelift op Uli's mic-stream richting collega's via QjackCtl-routing van `pure_data:output_3+4` naar JackTrip-send.

3. **Opname-functie binnen TTB** — bron-keuze (master/ch1-4), autotrim met threshold + preroll, direct triggerable als sample. Zie `notes/feature-waveform-display.md` voor pending uitbreiding.

Pd draait op het audio-eindpunt (Mac Mini / mini-pc) met `-nogui` voor low-latency-stabiliteit. JackTrip @ 64 samples / 48kHz = 1.33ms buffer-latency. UI draait in browser op een aparte mobiele/tablet — niet op het audio-eindpunt zelf. Bridge (Node.js) verbindt browser-UI via WebSocket met Pd via FUDI/UDP.

JackTrip en QjackCtl worden door een collega beheerd. Voor architectuur-keuzes die QjackCtl raken: breekrisico expliciet flaggen voor handoff aan collega.

---

## 2. Samenwerkingsstijl met Uli

**Hoe Uli wil werken:**

- **Bash-scripts copy/paste-flow.** Uli kopieert bash-blokken integraal naar de terminal. Lever altijd uitvoerbare commando's, niet "voeg deze regel toe in VSCode" of "verander regel X handmatig".
- **Patch-scripts editen files, geen handmatig werk.** File aanpassen = patch-script schrijven dat het idempotent doet. Uli typt zelf geen code en corrigeert zelf geen code.
- **Een ding tegelijk.** Eén commando, wachten op output, dan volgende. Niet drie stappen vooruit plannen. Vooral als er iets onverwachts gebeurt: eerst diagnosticeren, niet doorpatchen.
- **Idempotente patch-scripts met markers.** Standaard: marker-detectie als idempotentie-guard, `count == 1`-check vóór de vervanging. Markers in commentaren in de code (bv. `// === LOADMASTER-NULLISH-V1 ===` of `#X text TTB-OUT-PATCH-V1`) zodat een tweede uitvoering zichzelf detecteert.
- **Commit per fase.** Eén logische wijziging = één commit. Geen mengsels van ongerelateerde fixes in één commit.
- **Test pas valideren als browser-bewijs geleverd is.** Browsers cachen. Hard refresh (Cmd+Shift+R) plus DevTools openen om regel te inspecteren of `view-source:` om te bevestigen dat de gepatchte code daadwerkelijk in de browser zit.

**Anti-patronen om te vermijden:**

1. **Niet doorvragen op werkstructuur aan het begin.** Aannames over paden of tooling kosten uren als ze fout blijken.
2. **Pre-flight overslaan.** Spook-Pd of bridge op de achtergrond geven verwarrende symptomen die op iets anders lijken (geen geluid lijkt audio-pad-issue maar kan poort-conflict zijn).
3. **Patches zonder runaway-bescherming.** Altijd Python met `count == 1`-check, nooit naïef perl/sed voor multi-line replaces met dynamische strings.
4. **Patchen in de "verkeerde" tree.** Workflow is altijd: v2 patchen → testen → cp naar touchlab-mixer → committen. Niet rechtstreeks in touchlab-mixer.
5. **Te snel concluderen "het werkt" zonder verificatie.** Eerst bewijzen dat de browser de nieuwe regel laadt, dan pas gedrag testen.
6. **Te veel stappen tegelijk in één bash-blok.** Voor onbekende of risicovolle wijzigingen: één commando per blok, output bekijken, dan volgende.
7. **Aannemen dat object-indices in Pd-files volgen op visuele turen.** Empirisch verifiëren met script (zie sectie 5).

**Wat Uli waardeert:**

- Diagnostiek vóór actie wanneer iets onverwachts gebeurt
- Eerlijk zijn over onzekerheid in plaats van doorrationaliseren
- Erkennen wanneer ik aannames stapel ipv vragen stel
- Korte, scherpe vragen wanneer er een keuze gemaakt moet worden — niet drie scenario's tegelijk uitleggen voordat hij heeft kunnen kiezen
- Architectonisch meedenken — hij stelt vaak de scherpere vraag dan ik (gisteravond: "is sampler-master-vol niet onze TTB-gain?", "kunnen we de slots niet eerst sommen?")

---

## 3. Werkstructuur

Twee directories, twee rollen, één cp-flow ertussen:

### `~/Documents/Pd/PDMixer/v2/` — runtime/werkdirectory

- Pd draait hieruit (alle `.pd`-files leven hier)
- Bridge draait hier (`node bridge.js session.json`)
- Patch-scripts in `~/Documents/Pd/PDMixer/v2/scripts/`
- `./regen.sh` om Pd-files te genereren via templates
- Backups in `_backups/`
- **Hier wordt eerst getest, voordat iets naar touchlab-mixer gaat**

### `~/Documents/touchlab-mixer/` — git repo + GitHub Pages source

- Origin: `git@github.com:InsomnioNL/touchlab-mixer.git`
- Branch `main` deployt automatisch naar `https://insomnionl.github.io/touchlab-mixer`
- Alleen gevalideerde bestanden komen hier (cp uit v2)
- Patch-scripts ook gekopieerd voor versiebeheer
- `git add` / `commit` / `push` gebeurt hier

### `index.html` heeft drie functies

- Lokaal werkbestand in v2 (bewerk hier)
- Lokaal in browser geopend via `file:///Users/ulrichpohl/Documents/Pd/PDMixer/v2/index.html` tijdens lokale tests
- Op Pages voor sharing met anderen (`https://insomnionl.github.io/touchlab-mixer`)

### Bridge architectuur

Bridge is een Node.js-proces dat luistert op meerdere poorten:

- **9000** — Pd-FUDI receive (bridge → Pd commando's, TCP)
- **9001** — VU-meter UDP (Pd → bridge data)
- **9002** — Sampler cmd UDP (bridge → Pd sampler-commando's)
- **9003** — Sampler status UDP (Pd → bridge sampler-status)
- **8080** — WebSocket (browser ↔ bridge), plus HTTP voor `/recordings/*` endpoint

Browser laadt UI uit een `file://`-pad (lokaal) of van Pages (sharing), maakt vervolgens WS-verbinding naar `ws://localhost:8080` (lokaal-getest) of naar het audio-eindpunt's IP. Bridge zelf serveert geen `index.html`.

### Pd-bestanden

Twee hoofd-Pd-bestanden:

- `touchlab-mixer-ttb.pd` — actieve mixer met TTB-functionaliteit. Dit is wat Uli draait.
- `touchlab-mixer.pd` — non-TTB-variant. Wordt gestart door `start-mixer.sh` regel 113, maar Uli gebruikt dat script niet.

Daarnaast: `master-section.pd`, `ch1.pd` t/m `ch4.pd`, `fx-bus.pd`, `sampler-host.pd`, `sampler-router.pd`, `sampler-slot-1.pd` t/m `sampler-slot-8.pd`, `mic-test.pd`, `panner-test.pd`.

### Workflow per wijziging

1. Patch-script schrijven en in v2 toepassen
2. `./regen.sh` als Pd-templates zijn aangepast — **let op:** regen.sh draait *alle* generators inclusief `generate-mixer.py` die `master-section.pd` overschrijft. Voor enkel slots-werk: gebruik `python3 generate-slots.py` los, plus `python3 patch-sampler-host-rec-path.py` voor de host-post-patch.
3. Live test in v2 (Pd draait, bridge draait, browser ververst)
4. Werkt? → `cp <files> ~/Documents/touchlab-mixer/`
5. `cd ~/Documents/touchlab-mixer && git add ... && git commit && git push`

### Canonical startup-procedure

**Pre-flight (altijd eerst):**
```bash
pkill -9 -f Pd-0.55 ; pkill -9 -f "node bridge" ; sleep 1 ; lsof -i :9000 ; lsof -i :9001 ; lsof -i :8080
```
Output moet leeg zijn op alle drie poorten. Anders draait er iets uit een vorige sessie en eerst opruimen.

**Tab 1 — Pd:**
```bash
cd ~/Documents/Pd/PDMixer/v2 && open touchlab-mixer-ttb.pd
```
Wacht tot Pd-canvas open is. Pd luistert dan op poort 9000 voor FUDI.

**Tab 2 — Bridge:**
```bash
cd ~/Documents/Pd/PDMixer/v2 && node bridge.js session.json
```
Wacht op `✓ Beginwaarden naar PD gestuurd` plus `✓ N TTB-samples geladen`. Bridge luistert nu op WS-poort 8080 en heeft TCP naar Pd op 9000.

**Tab 3 — UI:**
Open `file:///Users/ulrichpohl/Documents/Pd/PDMixer/v2/index.html` in browser (lokale werkversie) of `https://insomnionl.github.io/touchlab-mixer` (Pages-versie). Hard refresh: Cmd+Shift+R.

**Afsluiten:**
```bash
pkill -9 -f Pd-0.55 ; pkill -9 -f "node bridge" ; sleep 1 ; lsof -i :9000 ; lsof -i :9001 ; lsof -i :8080
```

JackTrip en QjackCtl zijn geen onderdeel van bovenstaande. Die worden door een collega beheerd.

---

## 4. Stand van zaken — commits 29 april 2026 (avond)

Vijf commits in de architectuur-track (na de cleanup-track van de ochtend):

- `2465b64` — feat(audio-routing): TTB-out-bus in master-section.pd
- `6e4dd6b` — feat(sampler-slot-1): tap TTB-out-bus naar ttb-bus-L/R
- `8ab869f` — feat(sampler-slots): TTB-out-bus tap voor slots 2-8
- `1d8e59e` — docs: handoff-document voor TTB-out-bus QjackCtl-routing
- `383603b` — docs: feature-design note voor waveform-display

Plus de `fix-master-section-ttb-connects-v1.py` die fout was en via rollback ongedaan is gemaakt — dat script staat nog in `~/Documents/Pd/PDMixer/v2/scripts/` als historisch artefact maar is **niet** in de repo.

**Pilot bewezen werkend:** met env~ + floatatom in master-section toonde de catch~ ttb-bus-L signaal tijdens slot-1 afspelen. Bestaande monitor-route ongestoord.

---

## 5. Lessen geleerd (voor volgende Claude-chats)

### Pd's object-tel-regel — empirisch geverifieerd

Pd telt deze regel-types als objecten: `#X obj`, `#X msg`, `#X floatatom`, `#X symbolatom`, `#X listbox`, `#X text`, en `#N canvas` (subpatches). De **eerste** `#N canvas` regel is de header van de patch zelf en telt **niet** mee.

Verificatie-script:

```python
from pathlib import Path
f = Path("/path/to/file.pd")
lines = f.read_text().splitlines()
found_first_canvas = False
idx = 0
for line in lines:
    if line.startswith("#N canvas") and not found_first_canvas:
        found_first_canvas = True
        continue
    if line.startswith(("#X obj", "#X msg", "#X floatatom",
                        "#X symbolatom", "#X listbox", "#X text",
                        "#N canvas")):
        print(f"index={idx}: {line}")
        idx += 1
```

**Beste praktijk:** verifieer object-indices empirisch via dit script *plus* via bestaande `#X connect`-regels in de file zelf — die laatste is de meest betrouwbare bron, want het is wat Pd zelf gebruikt.

### Verkeerde patch — rollback-procedure

Als een patch-script foute connections schrijft, niet "fix-script bovenop fix-script" stapelen. Gebruik backup-rollback:

```bash
ls -la ~/Documents/Pd/PDMixer/v2/_backups/<file>.*.bak
cp ~/Documents/Pd/PDMixer/v2/_backups/<file>.<timestamp>.bak ~/Documents/Pd/PDMixer/v2/<file>
```

Daarna patch-script corrigeren, opnieuw runnen.

### Pd herlaadt subpatches niet automatisch

Bij wijzigingen in een geïnstantieerde abstraction (bv. `master-section.pd` als child van `touchlab-mixer-ttb.pd`): Cmd+W + heropenen heeft geen effect. Pd moet volledig opnieuw gestart worden om de file vers te laden. Bridge moet dan ook opnieuw — TCP-verbinding op 9000 breekt anders.

### Pd Cmd+S-quirks

Als je in Pd-canvas hand-edits doet (bv. tijdelijke debug-objecten als `env~` + floatatom), niet saven met Cmd+S. "Don't Save" bij sluiten. Anders:
- Canvas-grootte wordt overschreven
- Object-posities kunnen subtiel verschuiven
- Connect-regels worden hergerangschikt

Functioneel meestal harmless, maar geeft cosmetische diff-ruis bij commits.

### `regen.sh` overschrijft master-section.pd

`regen.sh` draait *alle* generators inclusief `generate-mixer.py`, die `master-section.pd` from-scratch herschrijft. Onze TTB-OUT-PATCH-V1 zit handmatig in master-section en wordt overschreven bij regen. Voor enkel slots-werk: gebruik `python3 generate-slots.py` los, plus `python3 patch-sampler-host-rec-path.py`.

**Open verbeterpunt:** TTB-OUT-PATCH absorberen in `generate-mixer.py` zodat regen.sh-safe.

---

## 6. Performance-context (voor inschattingen)

- **Pd draait `-nogui`** — geen Tk-canvas-redraws die x-runs veroorzaken bij lage latency. CPU-load van Pd zelf typisch 5-15% op moderne hardware bij 64 samples.
- **Buffer: 64 samples @ 48kHz** = 1.33ms. Low-latency, gevoelig voor scheduling-spikes en netwerk-jitter.
- **UI draait niet op audio-eindpunt** — browser/tablet, aparte machine, aparte CPU. WAV-decode, canvas-rendering, etc. raken het audio-eindpunt niet.
- **Vergelijking met bestaande tooling:** lichter dan `jackmixer + Teensy + fluidsynth` setup, omdat onze Pd-mixer geen synthese doet — alleen routing, gain, tabread4~ playback. CPU-budget vergelijkbaar of beter.

**Reverb (`fx-bus.pd` gebruikt `rev2~ 100 85 3000 20`):** algoritmische Schroeder-reverb, *geen* blocking-latency. Eerdere latency-pijn bij Uli kwam uit andere context (niet rev2~). rev2~ kan in principe in monitor-pad zonder muzikale problemen, mits CPU-budget toelaat. Niet getest op productie-hardware bij 64 samples.

---

## 7. Open issues voor latere sessies

### Volgende coding-werk (concrete features)

- **Waveform-display in TTB record/edit view** — `notes/feature-waveform-display.md` heeft uitgebreid scope-document. Fase 1 als startpunt: statische waveform na opname, fetch-decode in browser. ~1-2 uur per fase, 4 fases totaal.
- **Centrale TTB-monitor-toggle** — Uli's idee uit gesprek 29 april avond: één globale switch i.p.v. per-slot dac~. Ontwerp: per-slot `dac~` weg, vervangen door `throw~ ttb-monitor-bus`, in master-section een gate-`*~` met `r ttb-monitor-on` die bepaalt of die bus naar `dac~ 1 2` mengt. Vereist UI-toggle + FUDI-route + Pd-template-aanpassing. ~2-3 uur. Geen note geschreven — kan in een aparte sessie ontworpen worden.
- **Popup-sync-bug bij dubbeltap-naar-0 op FX/Pan knobs.** Popup-display synchroniseert niet met de waarde-reset. Lokaal UI-issue, klein, niet acuut.

### Architectuur-cleanup

- Rename `masterVol` → `monitorVol`, `master-section.pd` → `monitor-section.pd`. Grote sweep over veel bestanden, niet urgent.
- Cleanup orphan hpVol-objecten in master-section.pd (na rename of separaat).
- TTB-OUT-PATCH absorberen in `generate-mixer.py` (regen.sh-safe maken).
- Eventuele cleanup van `touchlab-mixer.pd` (de non-TTB-variant) als die werkelijk dood is, of expliciet documenteren waarvoor hij dient.

### Verificatie / handoff

- Collega informeren over TTB-out-bus QjackCtl-routing — `notes/handoff-ttb-out-bus.md` bevat alles wat hij moet weten.
- E2E-test zodra QjackCtl gewired is: speel een sample af, collega hoort het binnenkomen op Uli's audio-line.
- Verifieer aannames over mic-routing en Tonmeister-stream (open vragen in handoff-doc).

### Performance / robustness

- Eventueel meet-protocol opzetten (DSP-load via Pd's CPU-meter, xrun-counter via QjackCtl) op de doel-hardware bij 64 samples.
- rev2~-tests in monitor-pad: muzikaal acceptabel? CPU-headroom ok?

---

## 8. Locatie van overdrachtsdocumenten en notes

In `~/Documents/Pd/PDMixer/v2/`:

- `overgangsdocument-architectuur-discussie.md` (26 april 2026) — architectuur-context
- `overdrachtsdocument-werksessie.md` (29 april ochtend) — plannen-vooraf voor avond-sessie
- `overdrachtsdocument-werksessie-2026-04-30.md` (dit document) — stand na avond-sessie

In `~/Documents/touchlab-mixer/notes/`:

- `code-style.md` — one-liner if-guards stijl-keuze
- `2026-04-27-mixer-fudi-routing-bug.md` — diagnose-notitie
- `2026-04-27-pd-multiplication-diagnosis.md` — diagnose-notitie
- `handoff-ttb-out-bus.md` — voor JackTrip/QjackCtl-collega
- `feature-waveform-display.md` — scope-document waveform-feature

Bij start van een nieuwe chat: minimaal de drie overdrachtsdocumenten uit `v2/` plus de relevante note(s) voor de geplande feature uploaden of plakken.

---

## 9. Eerste actie voor de nieuwe chat

Beste Claude die dit leest:

1. **Lees alle drie de overdrachtsdocumenten volledig** — `overgangsdocument-architectuur-discussie.md`, `overdrachtsdocument-werksessie.md` (29 april ochtend), en dit document. Plus relevante notes voor de geplande feature.
2. **Vat samen wat je hebt begrepen** in 5-10 zinnen, zodat Uli kan corrigeren waar je hem verkeerd interpreteert.
3. **Stel verduidelijkingsvragen** voordat je code schrijft. Vooral over de keuze van wat als volgende feature te doen.
4. **Begin nooit met een patch zonder eerst pre-flight te bevestigen.** Vraag actief: "is Pd open, draait de bridge, is de browser open?" — voordat je een eerste patch-script schrijft.
5. **Werk strikt v2-first.** Patch-scripts in `~/Documents/Pd/PDMixer/v2/scripts/`, test in v2, dan cp naar touchlab-mixer, dan commit.
6. **Idempotent met markers.** Elk patch-script heeft een unieke marker, een marker-detectie als idempotentie-guard, en een `count == 1`-check vóór de vervanging.
7. **Eén ding tegelijk.** Niet drie patches vooruit denken. Eén commando, output bekijken, dan volgende.
8. **Diagnostiek vóór actie als iets onverwachts gebeurt.** Niet doorpatchen — eerst snappen wat er aan de hand is.
9. **Bij Pd-object-indices: verifieer empirisch via tel-script én via bestaande `#X connect`-regels in de file zelf.** Niet door visueel turen of mentaal tellen — die fouten zijn duur.

Veel succes.
