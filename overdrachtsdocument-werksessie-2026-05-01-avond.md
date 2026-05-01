Wacht op `✓ Beginwaarden naar PD gestuurd`. Bridge luistert nu op WS-poort 8080 en heeft TCP naar Pd op 9000.

**Tab 3 — UI:** `file:///Users/ulrichpohl/Documents/Pd/PDMixer/v2/index.html` of `https://insomnionl.github.io/touchlab-mixer/`. Hard refresh: Cmd+Shift+R.

**Cleanup:** zelfde pkill-regel als pre-flight.

JackTrip en QjackCtl zijn geen onderdeel van bovenstaande — door collega beheerd.

## 3. Belangrijke ontdekkingen

### A. Sloppy-mode-undeclared-variable bug bij dcTimer

Eerste fase 1 patch faalde stil: vingerafdruk werkte (setStatus(false) liep), maar rode rand kwam niet. Console toonde geen error op disconnect-moment. `ws.onclose.toString()` in DevTools toonde wel de nieuwe handler.

Oorzaak: `dcTimer` was niet gedeclareerd. In JavaScript sloppy mode (geen `'use strict'`) kun je impliciet **schrijven** naar een undeclared variable (`dcTimer = setTimeout(...)`), maar **lezen** ervan (zoals `clearTimeout(dcTimer)` doet) gooit `ReferenceError`. De error werd in de bestaande code wel zichtbaar maar niet als console-log — werd geslikt door het arrow-function execution model voor ws-event-handlers in sommige browsers.

Fix: dcTimer toegevoegd aan bestaande `var ws=null,rt=null,...` declaratie. Lesson voor toekomstige patches: alle nieuwe globale state-variabelen expliciet declareren in een `var`/`let` regel, niet impliciet via eerste assignment.

### B. Patch-script cwd-verwarring

Eerste run van het fase-1 patch-script werd geëxecuteerd terwijl `pwd` `~/Documents/touchlab-mixer` was, niet `~/Documents/Pd/PDMixer/v2/`. Het script schreef succesvol naar de repo-versie, maar v2 bleef ongepatcht. Browser laadt v2 → geen rode rand → diagnostiek leek op een JS-bug terwijl het feitelijk een file-locatie-bug was.

Diagnose: `find` op de naam van de backup-file die het script had gemaakt (de timestamp was uniek). Daaruit bleek de werkelijke locatie van de patch.

Aanbevolen werkwijze voor toekomstige bash-blokken die patches draaien: altijd `pwd` als sanity-output direct na de `cd`, vóór de `python3 ...` regel. Of het patch-script zelf een `os.getcwd()` check laten doen tegen verwachte directory-naam.

### C. DevTools insertRule met duplicate keyframe-naam

Tijdens fase 1b live tweaking: `document.styleSheets[0].insertRule('@keyframes connection-warning-pulse {...}')` had geen effect — de rode rand bleef pulseren met de oude keyframe-curve. Browser kiest bij duplicate keyframe-namen één van de definities, vaak de eerste in de stylesheet, ongeacht welke later is ingevoegd.

Workaround voor live experimenteren: hernoem de keyframe (`-v2`-suffix) en voeg een nieuwe regel toe die naar de hernoemde keyframe verwijst, met `!important` voor specificity. Of beter: edit direct in DevTools Elements panel via de bestaande rule.

Bij vastlegging op disk dezelfde naam houden — dat geeft geen probleem want er is dan maar één definitie.

### D. README startup-instructies komen niet overeen met canonical procedure

README in repo beschrijft een Jack-startup met `jackd -d alsa` etc. Uli werkt sinds eind april zonder Jack — Pd start gewoon als macOS GUI-app via `open touchlab-mixer-ttb.pd`, audio gaat via macOS' eigen audio-routing. De canonical procedure staat wel in de overdrachtsdocumenten (zie sectie 2 hierboven of sectie 3 van 29-april-doc) maar niet in README. Te documenteren in een toekomstige sessie als low-priority cleanup.

### E. Architectuurvraag 4 MIDI-pedaal beantwoord zonder pedaal-hardware

Code-analyse van `buildTriggerButton` (rond regel 1900): de `samplerPlay`/`samplerStop`-events naar bridge zijn slot-gebonden, niet queue-gebonden. Bridge en Pd weten niet eens of een trigger via queue-tap of directe tap kwam. **Conclusie: gate-mode werkt al in queue-context, geen blokker voor MIDI-pedaal fase 3.**

Bijvangst: oude UI-code deed queue-pos++ op `pointerdown`, maar het MIDI-pedaal-scope-document zegt expliciet "queue-progressie altijd op release-event". Discrepantie. Daarom in deze sessie de UI gelijkgetrokken (`QUEUE-ADVANCE-ON-RELEASE-V1`). Pedaal-flow en UI-flow zijn nu consistent.

Voor MIDI-pedaal fase 3 implementatie (toekomstige sessie): bridge moet eigen pedaal-down/pedaal-up handlers hebben, niet de UI-events doorsturen. Drie events:
- pedaal-down → `samplerPlay` (slot = `ttbQueue[ttbQueuePos]`)
- pedaal-up + held < threshold → niets extra (slot loopt natuurlijk uit)
- pedaal-up + held >= threshold → `samplerStop`
- in beide release-paden: bridge increment't queue-positie en stuurt `queueAdvance` naar UI

UI ontvangt `queueAdvance` via WebSocket, doet hetzelfde als `refreshAfterQueueChange()` doet bij UI-trigger.

## 4. Huidige tijdbommen voor regen.sh (onveranderd)

Drie issues uit vorige overdrachtsdoc, zie sectie 4 daar:

1. `master-section.pd` mist hpVol-disconnect.
2. `mixer-router.pd` mist `ttb-route-live` en `ttb-route-local` routes.
3. Mogelijk derde latente patch in een andere generator-output — diff-sweep nog niet gedaan.

Geen verandering deze sessie, omdat we niet in de generator-pipeline hebben gewerkt.

## 5. Open issues voor volgende sessies

### Direct nuttig

- **MIDI-pedaal implementeren** (zie `notes/feature-midi-pedal.md`) — wacht op pedaal-aanschaf voor hardware-validatie. Architectuurvraag 4 al beantwoord (zie ontdekking E). Eerste sessie-startpunt: pedaal aansluiten + welk model + welke MIDI-message stuurt het.
- **Remote mix-assist fase 1** (zie `notes/feature-remote-mix-assist.md`) — bridge listen-flag + UI WS-URL configureerbaar. Maakt telefoon-toegang mogelijk.
- **`mixer-router` absorberen** — kort en mechanisch, ~1u.
- **Diff-sweep over alle gegenereerde files** — om eventuele derde latente patches te vinden.
- **hpVol-tak cleanup in `write_master`**.

### Nieuwe items uit deze sessie

- **README startup-procedure synchroniseren** met canonical procedure in sectie 2 (zie ontdekking D). Low-priority.
- **Open ontwerpvraag**: wat doen de count-pills (1/2/4/6/8) tijdens queue-mode? Zijn nu effectief inactief (queue-mode cap't op 2). Optie: pills verbergen tijdens queue, of laten staan voor wanneer queue leeg wordt.

### Bekend latent (onveranderd)

- Sample-editor uit `feature-waveform-display.md`.
- Trim-markers fase 2 uit oorspronkelijke avond-doc.
- Cleanup orphan dac~ op idx 97 in alle 8 slots.
- TTB-OUT QjackCtl handoff aan collega.
- rev2~ latency-verificatie.

### Architectuur-cleanup (lange termijn, onveranderd)

- Rename `masterVol` → `monitorVol` (grote sweep).
- Cleanup non-TTB `touchlab-mixer.pd` of expliciet documenteren.
- Taal-uniformering naar Engels.

## 6. Werkomgeving — chat-rendering-bug

Onveranderd t.o.v. vorige sessie. Bug nog actief, geverifieerd via paste-test (`echo "test.py"` → markdown-link). Werkstrategieën uit sectie 6 van vorige overdrachtsdoc nog steeds geldig:

1. Single-quoted heredoc (`<< 'EOF'`) voor patch-script-inhoud — bewezen safe deze sessie via 8 succesvolle patch-runs.
2. `getattr(obj, "name")()` ipv directe attribuut-access in commando-regels.
3. Runtime string-concat voor extensies: `EXT=$(printf '%s%s%s' '.' 'p' 'y')`.
4. Pure shell-globs: `python3 scripts/patch-name*` ipv expliciete extensie.
5. Markdown code-blocks (triple-backtick) zijn safe voor inhoud-delivery.

Toevoeging deze sessie: `command not found: #` shell-comments in chat-paste. Kosmetisch, niet kritisch — bash-comments in een gepaste blok worden door zsh-interactive als unknown commando's geïnterpreteerd. Mogelijk in toekomst comments inline aan eind van regel zetten of weglaten.

## 7. Eerste actie voor de nieuwe chat

1. **Lees overdrachtsdocumenten in deze volgorde:**
   - `overgangsdocument-architectuur-discussie.md` (26 april)
   - `overdrachtsdocument-werksessie.md` (29 april ochtend) — bevat de canonical startup-procedure en samenwerkingsstijl-anti-patronen
   - `overdrachtsdocument-werksessie-2026-04-30.md` (30 april ochtend)
   - `overdrachtsdocument-werksessie-2026-04-30-avond.md` (30 april avond)
   - `overdrachtsdocument-werksessie-2026-04-30-late-avond.md` (30 april + 1 mei middag)
   - **dit document** — meest recent
2. **Lees scope-documents** in `notes/`:
   - `feature-remote-mix-assist.md`
   - `feature-midi-pedal.md` — MIDI-pedaal scope
   - `feature-connection-warning.md` — geïmplementeerd, maar nog steeds nuttig als referentie
3. **Begin met paste-test** voor de chat-rendering-bug (sectie 6).
4. **Vraag Uli welke richting:** MIDI-pedaal (mits pedaal aanwezig), remote mix-assist fase 1, mixer-router-absorptie, diff-sweep, hpVol-cleanup, sample-editor-ontwerpdoc, README-update, of iets anders.
5. **Pre-flight bevestigen voor patch.** Inclusief `pwd`-check vóór patch-runs (zie ontdekking B).
6. **v2-first.** Patches in `~/Documents/Pd/PDMixer/v2/scripts/`, test in v2, dan cp naar touchlab-mixer, dan commit.
7. **Idempotent met markers**, `count == 1`-checks, backups.
8. **Eén ding tegelijk.** Diagnostiek vóór actie.
9. **Pd-object-indices empirisch verifiëren** (tel-script + bestaande `#X connect`-regels), als we weer in de Pd-pipeline werken.
10. **WAARSCHUWING: regen.sh is nog niet helemaal regen-safe.** Vóór een routinematige regen: lees sectie 4 van vorige overdrachtsdoc. mixer-router en hpVol-tak nog kwetsbaar.
11. **GitHub Pages werkt** vanaf commit `2eb56ad`. Voor toekomstige UI-wijzigingen: gewoon committen op main, deploy gaat automatisch.

Veel succes.
