# Overdrachtsdocument — TouchLab TTB werksessie

**Datum:** 30 april 2026 (avond) + 1 mei 2026 (ochtend/middag — bijgewerkt)
**Voor:** opvolgende Claude-chats die met Uli werken aan touchlab-mixer
**Bedoeling:** stand-na-deze-sessie. Aanvullend op vorige overdrachten:

- `overgangsdocument-architectuur-discussie.md` (26 april)
- `overdrachtsdocument-werksessie.md` (29 april ochtend)
- `overdrachtsdocument-werksessie-2026-04-30.md` (30 april ochtend)
- `overdrachtsdocument-werksessie-2026-04-30-avond.md` (30 april avond)
- Dit document

## 1. Wat is er deze sessie gebeurd

Negen commits op `main`, verspreid over 30 april avond en 1 mei:

- `7b8dbe7` — feat(generate-mixer): absorb TTB-OUT-PATCH-V1 + TTB-MONITOR-V1 into write_master
- `3c33254` — fix(pages): disable Jekyll to bypass broken samples symlink
- `170fd84` — trigger: re-run pages build with .nojekyll active
- `2eb56ad` — fix(pages): remove dead samples symlink
- `cc8d38d` — docs(notes): consolidate remote mix-assist scope on Tailscale
- `f7b61d6` — fix(generate-mixer): default sampler-master-vol to 1 at Pd startup
- `e6e7241` — fix(ui): popup syncs with mini-knob on dblclick and drag
- `ba5eb5e` — docs(notes): scope-document for MIDI-pedal TTB queue-trigger
- `bc6ca79` — docs(notes): scope-document for connection-warning feature

Vier thema's. Eerst de geplande TTB-OUT absorptie. Daarna een onverwachte Pages-deploy-saga (al sinds 24 april stilzwijgend kapot door een symlink). Daarna twee bugfixes (sampler-master-vol stille start, popup-vs-mini-knob desync). Daarnaast drie scope-documents voor toekomstige features die in conversatie ontstonden.

### TTB-OUT absorptie (commit 7b8dbe7)

`generate-mixer.py` is uitgebreid: `write_master(with_sampler_tap=False, with_ttb_out=False)`. Wanneer `ttb_enable` in `session.json` `True` is, geeft `generate()` nu beide flags door en produceert de gegenereerde `master-section.pd` ingebouwde TTB-OUT bus catches plus TTB-MONITOR live/local route gates. Eerder leefden die als hand-edits en werden ze bij elke `regen.sh` overschreven. Nu regen-safe.

Marker `ABSORB-TTB-OUT-V1`. Patch-script: `scripts/patch-absorb-ttb-out-v1.py`.

Belangrijke kanttekening: het patch-script absorbeert de objecten en connects van TTB-OUT-PATCH plus TTB-MONITOR uit de werkende handpatched-versie. Maar de hpVol-tak (objecten 11-15) is in de werkende versie afgekoppeld van `dac~ 3 4`, terwijl de generator die connects nog wel produceert. Dat betekent dat een vers gegenereerde `master-section.pd` *niet* identiek is aan de huidige werkende versie — de hpVol-tak zou dubbele audio op `dac~ 3 4` veroorzaken samen met TTB-MONITOR. Voor nu is de werkende handpatched-versie teruggezet als productie-master-section. hpVol-cleanup in de generator is een aparte vervolg-sessie.

### Pages-deploy hersteld (commits 3c33254, 170fd84, 2eb56ad)

Na de TTB-OUT-commit bleek `https://insomnionl.github.io/touchlab-mixer` nog een drie dagen oude versie te tonen. Onderzoek wees uit dat alle Pages-builds sinds 24 april stilzwijgend faalden door een symlink `samples → /Users/ulrichpohl/Documents/Pd/PDMixer/samples` in de repo, die op GitHub's build-runner niet kon worden opgelost. Twee fixes in samenhang: `3c33254` voegt `.nojekyll` toe (skipt Jekyll), `2eb56ad` verwijdert de dode symlink (fixt tar-stap in upload-pages-artifact). Pages werkt nu weer normaal vanaf commit `2eb56ad`.

### Sampler-master-vol loadbang-default (commit f7b61d6)

Bug ontdekt tijdens testen: na vers opstarten waren TTB-samples stil tot de master sample fader bewogen werd. Diagnose: `sampler-master-vol` stond op Pd's float-default 0 bij startup. De bridge's "Beginwaarden naar PD gestuurd" stuurt deze variabele niet mee, dus alleen UI-fader-beweging gaf 'm een waarde. UI start zelf op 1.

Fix in `write_main_ttb()` van `generate-mixer.py`: drie objecten toegevoegd op canvas-coördinaten (2000, 1300-1350), volgend dezelfde off-canvas-conventie als `ABSORB-HOST-PATCHES-V1`. Loadbang → msg "1" → `s sampler-master-vol`. Bij Pd-startup vuurt dit en zet de variabele op 1. Werkt — getest met verse opstart, sample speelt direct bij eerste trigger zonder fader-beweging.

Marker `ABSORB-SAMPLER-MASTER-VOL-DEFAULT-V1`. Patch-script: `scripts/patch-absorb-sampler-master-vol-default-v1.py`.

### Popup-sync bij dblclick en drag (commit e6e7241)

Bug: bij channel-popup voor pan/fx synct de popup-fader/popup-display niet met de mini-knob bij dblclick (reset) of drag-interactie. De omgekeerde richting (popup-interactie synct naar mini-knob via `popupCb`) werkte al.

Fix in `index.html`: `resetK`-functie en de twee drag-handlers (mousemove + touchmove) hebben elk een nieuwe sync-block aan het einde gekregen. Wanneer `popupTarget === el` (popup is open op deze knob), wordt ook de popup-fader-value en popup-display bijgewerkt.

Markers: `POPUP-SYNC-RESETK-V1`, `POPUP-SYNC-DRAG-V1`. Patch-scripts: `scripts/patch-popup-sync-resetk-v1.py`, `scripts/patch-popup-sync-drag-v1.py`.

### Drie scope-documents in `notes/` (commits cc8d38d, ba5eb5e, bc6ca79)

Alle drie zijn beschreven en ontworpen tijdens deze sessie maar niet geïmplementeerd. Ze staan klaar voor toekomstige sessies.

**`notes/feature-remote-mix-assist.md`** — Remote mix-assist via Tailscale. Tonmeesters (Uli + Christiaan) kunnen mixers van muzikanten remote bedienen. InsomnioNL gebruikt al Tailscale, alle audio-eindpunten zijn jullie eigendom dus muzikanten hoeven zelf geen Tailscale-account aan te maken. Headscale staat als mogelijke toekomstige overstap genoteerd. Vier fases gedefinieerd, fase 1 (bridge listen-flag + UI WS-URL configureerbaar) als startfase.

**`notes/feature-midi-pedal.md`** — USB-MIDI-pedaal voor TTB queue-trigger. Eén pedaal triggert volgende slot in queue. Korte druk = one-shot, lange druk = gate-mode. Queue-progressie altijd op release-event, dus één event-handler dekt beide modi. MIDI learn ingebouwd voor flexibele hardware. Lege queue valt terug op laatst-getriggerde slot.

**`notes/feature-connection-warning.md`** — Visuele waarschuwing bij verlies van WebSocket-verbinding tussen UI en bridge. Rode rand om de mixer + alle controles vergrendeld, na 1500ms debounce. TTB-popup blijft open zoals hij was. Geen audio-feedback (live-context). Pure UI-werk.

## 2. Stand van zaken — wat draait

`master-section.pd` in v2 is de handpatched-versie, ongewijzigd t.o.v. wat eerder draaide. Tijdens deze sessie meermaals overschreven met regen-output voor diff-doeleinden, daarna teruggezet uit `_backups/`.

`mixer-router.pd` in v2 is teruggezet uit `~/Documents/touchlab-mixer/mixer-router.pd` na een onverwachte regen-bijwerking (zie sectie 3 over latente patches).

`touchlab-mixer-ttb.pd` in v2 is de nieuwe versie *met* de sampler-master-vol-loadbang, bewust niet teruggezet na regen.

`index.html` in v2 bevat de popup-sync-fixes.

Audio is end-to-end getest: bridge connect, master-fader, sample direct hoorbaar bij eerste trigger zonder fader-beweging. Popup synct correct met mini-knob in beide richtingen.

## 3. Belangrijke ontdekkingen

### A. Generator-overschrijvingen zijn meer dan we dachten

Vorige overdrachtsdocumenten noemden alleen `master-section.pd` als slachtoffer van regen. Tijdens deze sessie bleek dat ook `mixer-router.pd` handmatige patches bevat (de `ttb-route-live` en `ttb-route-local` routes uit commit `46419de`) die door regen verdwenen. Dat is gefixt in deze sessie door restore uit de repo, maar de absorptie in `write_mixer_router()` is nog niet gedaan. Tweede tijdbom voor wie regen draait. Werk voor een volgende sessie.

Mogelijk is er nog een derde latente patch in een andere generator-output. Aanrader voor volgende sessie: een eenmalige diff-sweep waarin elke gegenereerde file in v2 wordt vergeleken met de gecommitte versie in de repo. Verschillen markeren waar handmatige patches zitten die nog niet geabsorbeerd zijn.

### B. GitHub Pages-deploy was kapot sinds 24 april

Geen fout van deze sessie maar wel ontdekt. Alle pages-build-and-deployment runs sinds 24 april faalden stilzwijgend op de symlink `samples → /Users/ulrichpohl/...`. De live site bleef de versie van vóór die symlink tonen. Sinds `2eb56ad` werkt het weer.

`.nojekyll` staat nu in de repo. Voor de toekomst geen Jekyll-build meer; Pages serveert files as-is. De UI is statische HTML/CSS/JS dus dat is precies wat we willen.

### C. Chat-rendering-bug bestaat nog steeds

Aan het einde van 30 april uitgezocht: de markdown-link-rendering bij `.py`, `.attribute()`, etc. zit in claude.ai's interface zelf, niet in iTerm2 of Terminal.app. Bewezen door beide terminals dezelfde corrupte rendering te laten produceren. Op disk zijn filenames schoon — geverifieerd via `git ls-files | wc -c`. De bug is puur cosmetisch maar maakt patch-script-creatie via heredoc met letterlijke `.py`-strings broos.

Op 1 mei opnieuw bevestigd via paste-test (`echo "test-bestand.py is een test"` → output renderde als markdown-link).

Werkstrategieën die werken: string-concat op runtime (`"file" + "." + "py"`), `getattr()` voor methode-calls, pure shell-globs (`*absorb*`). Nano-paste van lange Python-regels heeft een eigen probleem (auto-wrap op spatiegrenzen) los van deze chat-bug.

### D. Telefoon-toegang

Op 1 mei ontdekt door Uli: de UI op `https://insomnionl.github.io/touchlab-mixer/` toont op telefoon geen TTB trigger-buttons. Diagnose: telefoon kan geen WebSocket-verbinding maken naar `localhost:8080` want bridge draait op de Mac, niet op de telefoon. Geen bug, geen unfinished feature — exact het scenario dat het remote-mix-assist scope-document beschrijft. Fase 1 van dat document (bridge listen-flag + UI WS-URL configureerbaar) is wat hier nodig is.

## 4. Huidige tijdbommen voor regen.sh

Wie nu `regen.sh` draait krijgt drie verschillende issues:

1. **`master-section.pd` mist hpVol-disconnect.** De TTB-OUT-PATCH zelf is nu wel geabsorbeerd, maar de werkende productie-versie heeft daarbovenop nog hpVol afgekoppeld van dac~ 3 4. Generator produceert die afkoppeling niet. Resultaat: dubbele audio op dac~ 3 4.
2. **`mixer-router.pd` mist `ttb-route-live` en `ttb-route-local` routes.** Generator's `write_mixer_router()` heeft die niet. Resultaat: TTB-route-rocker werkt niet — UI-events landen in mixer-unknown-fudi.
3. **Mogelijk meer.** Niet uitgesloten dat een derde gegenereerde file óók handmatige patches mist.

Aanbeveling voor volgende sessie: vóór een routinematige regen, eerst de absorpties afmaken. Of eenmalig diff-sweep om alle latente patches te vinden.

## 5. Open issues voor volgende sessies

### Direct nuttig

- **Connection-warning feature implementeren** (zie `notes/feature-connection-warning.md`) — pure UI-werk, ~1.5-2u. Kleine maar belangrijke fix voor live-context veiligheid.
- **Remote mix-assist fase 1** (zie `notes/feature-remote-mix-assist.md`) — bridge listen-flag + UI WS-URL configureerbaar. Maakt telefoon-toegang mogelijk.
- **MIDI-pedaal implementeren** (zie `notes/feature-midi-pedal.md`) — substantieel feature-traject, vier fases.
- **`mixer-router` absorberen** — kort en mechanisch. Voegt `ttb-route-live` en `ttb-route-local` toe aan `write_mixer_router()`. Waarschijnlijk minder dan een uur.
- **Diff-sweep over alle gegenereerde files** — om eventuele derde latente patches te vinden voor ze toeslaan.
- **hpVol-tak cleanup in `write_master`** — zodat regen-output identiek is aan handpatched.

### Bekend latent (onveranderd)

- **Sample-editor uit `feature-waveform-display.md`** — Uli's gewenste richting: handmatige in/out-markers + autotrim-relatief-aan-manual-start + save-as-actie naar nieuwe WAV. Géén ontwerpdoc geschreven; wel uitgebreid besproken op 30 april.
- **Trim-markers fase 2 uit oorspronkelijke avond-doc** (read-only threshold/preroll cursors uit Pd) — was de geplande feature voor 30 april maar achterhaald door Uli's voorkeur voor de sample-editor-richting.
- **Cleanup orphan dac~ op idx 97 in alle 8 slots** — cosmetisch, niet acuut. De feitelijke audio-cleanup is al gebeurd via vroege patch-script vanmorgen.
- **TTB-OUT QjackCtl handoff aan collega** — niet onze taak.
- **rev2~ latency-verificatie** — Uli's parking-lot-item.

### Architectuur-cleanup (lange termijn, onveranderd)

- Rename `masterVol` → `monitorVol` (grote sweep).
- Cleanup non-TTB `touchlab-mixer.pd` of expliciet documenteren.
- Taal-uniformering naar Engels.

## 6. Werkomgeving — chat-rendering-bug

Alles wat lijkt op `bestandsnaam.py`, `obj.attribute`, of `module.method()` rendert in claude.ai's chat-interface als markdown-link met de URL `http://<woord>`. Voorbeelden:

- `generate-mixer.py` werd `[generate-mixer.py](http://generate-mixer.py)`
- `f.name` werd `[f.name](http://f.name)`

Bron: claude.ai input-handler bij paste, niet iTerm2/Terminal.app. Geverifieerd door beide terminals dezelfde corrupte rendering te laten produceren. Op disk zijn filenames schoon (verified via `git ls-files | wc -c`).

**Werkstrategieën die werken:**

1. String-concatenatie op runtime: `"file" + "." + "py"` ipv `"file.py"`.
2. `getattr()` voor methode-calls: `getattr(obj, "read" + "_text")()` ipv `obj.read_text()`.
3. Heredoc met enkele quotes (`<< 'EOF'`) voor inhoud — werkt voor markdown en simpele Python.
4. `printf` voor extensies in shell: `ext=$(printf '%s%s%s' '.' 'p' 'y'); mv "$old" "${new}${ext}"`.
5. Pure shell-globs in plaats van filenames in commands: `python3 ~/path/scripts/patch-name*`.

**Werkstrategieën die NIET werken:**

- Bash-heredoc met letterlijke `.py` of `.read_text()` in commando-strings.
- Python `print(f.name)` of vergelijkbare attribute-access in chat-tekst.
- Nano-paste van lange Python-regels (regels >80 chars worden afgebroken op spatiegrenzen — eigen probleem los van deze chat-bug).

**Voor patch-script-creatie:** schrijf een bootstrapper die runtime-string-bouw doet, of laat Uli het script handmatig in een editor plakken (volledige script in een markdown-codeblok, niet in een bash-heredoc-met-.py-extensie).

**Voor de toekomst:** deze rendering is een claude.ai-feature en kan over tijd veranderen. Volgende Claude-chat moet niet alleen op basis van dit document concluderen dat de bug "vast" is — een korte paste-test met `echo "test.py"` aan het begin van de sessie kan bevestigen of de bug nog actief is.

## 7. Eerste actie voor de nieuwe chat

1. **Lees overdrachtsdocumenten in deze volgorde:**
   - `overgangsdocument-architectuur-discussie.md` (26 april)
   - `overdrachtsdocument-werksessie.md` (29 april ochtend)
   - `overdrachtsdocument-werksessie-2026-04-30.md` (30 april ochtend)
   - `overdrachtsdocument-werksessie-2026-04-30-avond.md` (30 april avond)
   - **dit document** — meest recent
2. **Lees ook de drie scope-documents** in `~/Documents/touchlab-mixer/notes/`:
   - `feature-remote-mix-assist.md`
   - `feature-midi-pedal.md`
   - `feature-connection-warning.md`
3. **Begin met een paste-test** voor de chat-rendering-bug (sectie 6). Pas patch-script-creatie-strategieën daarop aan.
4. **Vraag Uli welke richting:** connection-warning implementeren, mixer-router-absorptie, diff-sweep, hpVol-cleanup, remote mix-assist fase 1, MIDI-pedaal, sample-editor-ontwerpdoc, of iets anders.
5. **Pre-flight bevestigen voor patch.** Werkt zoals voorheen.
6. **v2-first.** Patches in `~/Documents/Pd/PDMixer/v2/scripts/`, test in v2, dan cp naar touchlab-mixer, dan commit.
7. **Idempotent met markers**, `count == 1`-checks, backups.
8. **Eén ding tegelijk.** Diagnostiek vóór actie.
9. **Pd-object-indices empirisch verifiëren** (tel-script + bestaande `#X connect`-regels).
10. **WAARSCHUWING: regen.sh is nog niet helemaal regen-safe.** Vóór een routinematige regen: lees sectie 4 van dit document. mixer-router en hpVol-tak zijn nog kwetsbaar.
11. **GitHub Pages werkt weer** vanaf commit `2eb56ad`. Voor toekomstige UI-wijzigingen: gewoon committen op main, deploy gaat automatisch.

Veel succes.
