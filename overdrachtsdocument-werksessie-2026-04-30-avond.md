# Overdrachtsdocument — TouchLab TTB werksessie

**Datum:** 30 april 2026 (vervolg op ochtend-sessie van diezelfde dag)
**Voor:** opvolgende Claude-chats die met Uli werken aan touchlab-mixer
**Bedoeling:** stand-na-deze-sessie + concreet startpunt voor volgende sessie. Aanvullend op:
- `overgangsdocument-architectuur-discussie.md` (26 april) — architectuur-context
- `overdrachtsdocument-werksessie.md` (29 april ochtend) — plannen-vooraf
- `overdrachtsdocument-werksessie-2026-04-30.md` (30 april ochtend) — vorige stand
- Dit document — wat is er deze sessie gebeurd

---

## 1. Wat is er deze sessie gebeurd

Vijf commits in `main`, plus eenmalig setup-werk:

### TTB-route rocker (3 commits)
- `e456caa` — feat(audio-routing): TTB-MONITOR gates in master-section
- `418576d` — feat(audio-routing): per-slot dac~ verwijderen
- `46419de` — feat(ui): TTB-route rocker (LOCAL/LIVE switch)

Functioneel: rocker bovenin TTB-popup-header schakelt tussen LIVE (TTB naar collega's via dac~ 3 4) en LOCAL (TTB lokaal naar koptelefoon via dac~ 1 2). Default = live. LOCAL toont rode pulserende rand om popup als visuele waarschuwing dat collega's TTB niet horen. Audio gebruikt line~ 10ms ramps om popping te voorkomen. Mixer-router.pd uitgebreid met routes voor `ttb-route-local` en `ttb-route-live`.

### Waveform display fase 1 (1 commit)
- `e98b977` — feat(ui): waveform display fase 1 + samples-route

Statische waveform na opname + bij slot-selectie. Browser fetcht WAV via nieuwe bridge HTTP-route `/samples/<filename>` (uit `cfg.ttb.samples_dir`), decodeert via `AudioContext.decodeAudioData`, tekent per-pixel min/max peaks. Triggers: `recStatus` na rec-stop met `msg.file`, en `renderActiveSlotForm` bij slot-selectie. Twee markers: `WAVEFORM-FASE1-V1`, `WAVEFORM-SAMPLES-ROUTE-V1`.

**Belangrijke vondst tijdens deze feature:** opnames worden in `samples/` opgeslagen, niet in `recordings/`. De oude `~/recordings/`-map is dood gewicht voor onze use-case. Bridge serveert nu `/samples/` met `Access-Control-Allow-Origin: *` zodat het ook vanuit Pages werkt.

### Waveform playhead cursor (1 commit)
- `c22ec24` — feat(ui): waveform playhead cursor

Witte verticale cursor animeert van links naar rechts over de waveform tijdens playback in EDIT-mode voor het actieve slot. Pure UI met `requestAnimationFrame`, geen Pd of bridge gewijzigd. AudioBuffer wordt gecached om re-render per frame mogelijk te maken zonder fetch-roundtrip. Speed-correctie via lookup in `ttbSlots[i].speed` (valt netjes terug op 1.0). Marker: `WAVEFORM-PLAYHEAD-V1`.

### iTerm2 + shell-integratie (geen commit, alleen tooling)
Brew install van iTerm2, shell-integration script geïnstalleerd. Cmd+Shift+A selecteert nu het laatste output-blok. Enorme productiviteitswinst.

---

## 2. Stand van zaken — totaal vandaag

Inclusief de ochtend-sessie zijn er deze dag **7 commits** op `main`:

| Hash | Wat |
|------|-----|
| `e456caa` | TTB-MONITOR gates in master-section |
| `418576d` | per-slot dac~ verwijderen |
| `46419de` | TTB-route rocker UI |
| `e98b977` | waveform fase 1 + samples-route |
| `c22ec24` | waveform playhead cursor |

(De eerste twee zijn audio-routing voorbereiding voor de rocker, de derde is de UI-laag erop.)

Alles getest en werkend. Pages-deploy automatisch via main-push.

---

## 3. Concreet startpunt voor volgende sessie — trim-markers

**Doel:** twee statische cursors op de waveform die tonen waar Pd écht begint te spelen:
- Threshold-cursor (waar autotrim "hapt", in dB-range -60..0)
- Preroll-cursor (offset ervóór, in ms-range 0..500)

**Architectuur-keuze gemaakt deze sessie:** Pd-side waarheid, niet client-side hercomputatie. Pd weet de exacte trim-start (in samples) en moet die naar de bridge sturen. Reden: client-side scan in JS zou kleine afwijkingen kunnen geven t.o.v. wat Pd echt doet.

**Wat er al is:**
- `slot1-trim-start` is een `value`-object in `sampler-slot-1.pd` dat door autotrim wordt gezet
- Bridge heeft al `samplerState[slot].trimStart` (regel 567), maar dat is een echo-pad — UI stuurt `samplerTrim` (handmatig) en bridge bewaart 'm. Pd stuurt nooit z'n eigen `slot1-trim-start` naar buiten.
- UI heeft `s.autotrimThreshold` en `s.autotrimPreroll` per slot in `ttbSlots`

**Wat er moet:**

1. **Pd:** in `sampler-slot-N.pd`-template een `s sampler-trim-report N <samples>` toevoegen die fired wanneer `slotN-trim-start` verandert (loadbang, na autotrim, na handmatige trim). Iets als `[r slotN-trim-start-in] → [t f] → [pack N f] → [s sampler-trim-report]`. Vereist `generate-slots.py`-aanpassing.

2. **Bridge:** receive-handler voor FUDI `sampler-trim-report` → broadcast als WS-message `trimStartReport` met slot + samples + sampleRate.

3. **UI:** WS-handler voor `trimStartReport` slaat per slot op in `ttbSlots[i].trimStartSamples`. Bij `_renderPeaks`/`_renderPeaksOnly` twee verticale lijnen tekenen:
   - Threshold: x = `(trimStartSamples / audioBuffer.length) * canvas.width`
   - Preroll: x = `((trimStartSamples - prerollSamples) / audioBuffer.length) * canvas.width` waar `prerollSamples = (s.autotrimPreroll / 1000) * audioBuffer.sampleRate`

**Geschatte tijd:** 1.5-2u, met testen. Niet trivial want raakt 4 lagen (Pd-template, generate-slots.py, bridge, UI) en alle 8 slots moeten geregenereerd.

**Risico's:**
- `regen.sh` overschrijft master-section.pd; voor deze feature alleen `python3 generate-slots.py` los draaien
- Pd-object-indices verifieren met tel-script (zie eerdere overdrachtsdocs)

---

## 4. Andere open issues, in volgorde van urgentie

### Direct nuttig
- **Trim-markers fase 2** (zie sectie 3) — logische volgende stap
- **Waveform fase 3+:** zoom/scroll, edit-handles voor handmatige trim, opname-tijd live waveform. Vereist `notes/feature-waveform-display.md` om scope helder te krijgen — die note is nooit aan deze sessies gegeven; staat in `~/Documents/touchlab-mixer/notes/feature-waveform-display.md`. **Bij start volgende sessie: vraag Uli om die te uploaden of plak 'm direct in de chat.**

### Bekende latent
- **Popup-sync-bug bij dubbeltap-naar-0 op FX/Pan knobs.** Niet acuut.
- **Cleanup orphans:** per-slot dac~ in slots 2-8 (alleen slot 1 schoon-getrokken in TTB-route rocker). HpVol-tak in master-section ook nog orphan.
- **TTB-OUT-PATCH absorberen in `generate-mixer.py`** zodat regen.sh-safe.

### Architectuur-cleanup (lange-termijn)
- Rename `masterVol` → `monitorVol`, `master-section.pd` → `monitor-section.pd`. Grote sweep, niet urgent.
- Eventuele cleanup van non-TTB `touchlab-mixer.pd`.
- Taal-uniformering naar Engels (Uli's "gevoelige snaar"): comments, UI-strings, variabel-namen.

### Verificatie / handoff aan derden
- Collega informeren over TTB-out-bus QjackCtl-routing — `notes/handoff-ttb-out-bus.md` is gecommit.
- E2E-test zodra QjackCtl gewired is.

---

## 5. Werkstructuur, samenwerkingsstijl, lessen geleerd

**Onveranderd t.o.v. vorige overdrachtsdocs.** Lees `overdrachtsdocument-werksessie-2026-04-30.md` (ochtend) voor:
- Werkdirs (v2/ en touchlab-mixer/)
- Bridge-poorten (9000-9003 + 8080)
- Workflow per wijziging (v2 patchen → testen → cp → commit)
- Pre-flight (`pkill -9 -f Pd-0.55 ; pkill -9 -f "node bridge" ; sleep 1 ; lsof ...`)
- Pd's object-tel-regel (`#X obj`, `#X msg`, `#X floatatom`, etc.; eerste `#N canvas` telt niet)
- Patch-script-stijl (markers, count==1 checks, idempotent)
- Backup-rollback-procedure
- Pd-quirks (subpatches herladen niet automatisch; Cmd+S niet bij hand-edits)

### Lessen specifiek toegevoegd deze sessie

1. **Heredoc-quoting voor inline patch-scripts.** Outer `<<'PYEOF'` met em-dashes en backslash-escapes is broos. Robuuste werkwijze:
   - Aanmaken via Python-naar-file: outer `<<'PYHEREDOC'`, binnen `content = '...'`
   - In `content`: gebruik `chr(10)` ipv `"\n"`, geen f-strings met `{}`, string-concat met `+`
   - JS single-quotes via `\u0027` om quote-conflicts te vermijden
   - Workflow: aanmaken → `cat` ter verificatie → pas runnen
   - Voor SVG/HTML met em-dashes: gebruik `\u2014` ipv literal em-dash

2. **`sendPD` vs `sendSampler`:**
   - `sendPD(receiver, ...args)` schrijft `;<receiver> <args>;\n` naar TCP 9000 → Pd's netreceive → `mixer-router`
   - `sendSampler` gaat naar UDP 9002 → `sampler-host`
   - Voor `route-*` berichten: via `sendPD`, daarna route in `mixer-router.pd` toevoegen anders krijg je "mixer-unknown-fudi"

3. **Bridge HTTP-routes:** bridge serveerde alleen `/recordings/*`. Voor sample-files (in `samples/`) een aparte route nodig. Configgebruik:
   - `cfg.ttb?.samples_dir` default `"samples"`, kan absolute of relatieve pad
   - Bij relatief: `path.join(process.cwd(), samplesDir)`

4. **Pd-object-indices na nieuwe sends:** als je nieuwe `s`-objecten toevoegt aan `mixer-router.pd`, plaats ze NA bestaande print-objecten zodat bestaande indices behouden blijven (de nieuwe sends krijgen dan idx N+1, N+2). Voorkomt dat catch-all connect "1 N N 0" mis gaat.

5. **Audio-pop-prevention:** bij switching tussen audio-paden altijd `line~ 10` tussen schakel-receive en `*~`-gate. Hard 0/1-toggle ploppt.

---

## 6. Eerste actie voor de nieuwe chat

1. **Lees overdrachtsdocumenten in deze volgorde:**
   - `overgangsdocument-architectuur-discussie.md` (26 april) — context
   - `overdrachtsdocument-werksessie.md` (29 april ochtend) — plannen-vooraf
   - `overdrachtsdocument-werksessie-2026-04-30.md` (30 april ochtend) — eerdere stand
   - **dit document** — meest recent
2. **Vat samen** wat je hebt begrepen in 5-10 zinnen, zodat Uli kan corrigeren.
3. **Vraag actief om `notes/feature-waveform-display.md`** — voor trim-markers en latere fases is die scope-doc relevant.
4. **Vraag welke feature** — trim-markers fase 2 (Pd+bridge+UI), iets uit de cleanup-stapel, of iets dat sinds vandaag opgekomen is.
5. **Begin nooit met een patch zonder pre-flight te bevestigen.**
6. **v2-first.** Patch-scripts in `~/Documents/Pd/PDMixer/v2/scripts/`, test in v2, dan cp naar touchlab-mixer, dan commit.
7. **Idempotent met markers**, count==1-checks, backups.
8. **Eén ding tegelijk.** Eén commando per blok, output bekijken, dan volgende.
9. **Diagnostiek vóór actie** als iets onverwachts gebeurt. Niet doorpatchen.
10. **Pd-object-indices empirisch verifiëren** via tel-script + bestaande `#X connect`-regels.

Veel succes.
