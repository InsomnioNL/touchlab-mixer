# Feature-design — Waveform-display in TTB record/edit view

**Datum:** 29 april 2026 (avond)
**Status:** scope-document, nog niet gestart

## Aanleiding

In de TTB record/edit view (rechterkolom van de UI) zit al een
`.ttb-wave-area` met daarbinnen een `.ttb-wave-canvas` element en
twee `.ttb-trim-marker`-elementen (start/end). De canvas wordt nu
niet beschilderd — er is alleen een lege `.ttb-wave-empty`-tekst.

De infrastructuur staat dus al klaar. Wat ontbreekt is het tekenen
van de daadwerkelijke audio-waveform op de canvas.

## Bestaande haakpunten (geverifieerd in index.html)

- **Regel 599-622:** CSS voor `.ttb-wave-area`, `.ttb-wave-canvas`,
  `.ttb-wave-empty`, `.ttb-trim-marker.start`, `.ttb-trim-marker.end`.
  De markers zijn `position:absolute` met `cursor:ew-resize` — ze
  zijn al voorbereid om verschuifbaar te zijn over de canvas heen.
- **Regel 1713:** UI heeft al `/recordings/${recFile}`-URL voor
  download. Bridge serveert WAV-files via HTTP op poort 8080.
- **Regel 1003:** WS ontvangt `sampleList`-bericht — vermoedelijk
  per slot info over geladen sample (naam, lengte, etc).
- **Regel 1835:** `recordQueueTap` triggert opname; opnamestatus
  komt waarschijnlijk via `samplerStatus`-bericht (regel 1002).

## Open ontwerpvragen

1. **Datapad: WAV ophalen of peaks-array via bridge?**
   - **A)** Browser fetcht `/recordings/slotN.wav`, decodet via
     Web Audio API's `decodeAudioData`, berekent peaks zelf.
     Voordeel: geen bridge-aanpassing. Nadeel: hele WAV over de wire,
     CPU-spike bij decode op grote samples.
   - **B)** Bridge berekent peaks-array (bv. 1024 of 2048 samples)
     en serveert via `/recordings/slotN.peaks` of via WS-bericht.
     Voordeel: lichter dataverkeer, snellere render. Nadeel:
     bridge-werk, peaks-cache-management.
   - **Voorkeur tbd:** start met A (eenvoud, niet meteen bridge
     aanraken), B als optimisatie als A te traag blijkt.

2. **Real-time tijdens opnemen?** Of pas wanneer opname klaar is?
   - Real-time is veel werk (Pd → bridge → UI streaming van
     peaks-data). Niet doen in eerste versie.
   - Eerste versie: lege canvas tijdens opname, render zodra
     opname klaar (status `rec-stopped` ontvangen).

3. **Trim-markers koppelen aan waveform-coördinaten.** De markers
   staan nu op `5%` en `95%` als CSS-default. Bij echte
   functionaliteit moeten ze:
   - Initieel op `slotN-trim-start` en `slotN-trim-end` (in samples)
     gepositioneerd worden, geconverteerd naar pixels op canvas.
   - Bij drag updaten ze de `samplerTrim`/`samplerTrimEnd` waarden
     via WS richting Pd.
   - Bij wijziging vanuit Pd-kant (bv. autotrim doet z'n werk)
     bewegen ze visueel mee.

4. **Welke waveform-stijl?** Mono mid-line met peaks omhoog/omlaag,
   of separate L/R-tracks gestapeld? Onze samples zijn mono
   (slot-array is 1-kanaal), dus enkele track met +/- peaks om de
   middenlijn is voldoende.

5. **Resolutie/peaks-berekening.** Voor een 60s sample @ 48kHz =
   2.88M samples, op een canvas van ~600px breed = ~4800
   samples-per-pixel. Per pixel min/max berekenen geeft een
   scherpe waveform. Standaard aanpak.

## Voorgestelde fasering

**Fase 1 — Statische waveform na opname (~1-2 uur)**

- Pas `index.html` aan: na ontvangst van `sampleList` (of na
  `rec-stopped` status) fetch `/recordings/slotN.wav`, decode met
  Web Audio, render peaks op `.ttb-wave-canvas`.
- Patch-script structuur: marker `WAVEFORM-RENDER-V1`, idempotent.
- Test: neem een sample op, slot opent, waveform verschijnt.
- Edge cases: mono vs stereo WAV, lege/korte samples, decode-errors.

**Fase 2 — Trim-markers koppelen aan canvas-coördinaten (~1-2 uur)**

- `.ttb-trim-marker.start` en `.end` positie omrekenen op basis van
  `slot-trim-start` en `slot-trim-end` in samples → percentage
  van waveform-lengte.
- Drag-handlers zodat verschuiven van een marker een nieuwe
  trim-waarde naar Pd stuurt via WS (`samplerTrim` /
  `samplerTrimEnd`-berichten bestaan al).
- Bij update van trim-waarden vanuit Pd (bv. autotrim) markers
  visueel mee laten bewegen.

**Fase 3 — Visuele highlight van het getrimde gebied (~30 min)**

- Tussen start- en end-marker een lichte overlay tekenen die het
  "actief afgespeelde" gebied aangeeft. CSS-only is voldoende.
- Buiten de markers: gedimde waveform (lichte transparant overlay).

**Fase 4 — Real-time playback-positie tijdens afspelen (optioneel)**

- Tijdens afspelen: een verticale lijn die meebeweegt met de
  huidige play-positie. Vereist dat Pd of bridge de positie
  doorgeeft (of we interpoleren clientside obv start-tijd +
  speed-factor).
- Niet kritiek voor v1, kan later.

## Wat dit níet raakt

- Pd-files: **geen wijziging** nodig in fase 1-3.
- Bridge: **geen wijziging** in fase 1 (pad A). Wel bij pad B
  (peaks-API), of bij real-time playback-positie (fase 4).
- Audio-routing / TTB-out-bus: volledig orthogonaal.

## Risico's en valkuilen

- **Decode-performance van grote WAV's.** Sampler-array is 60s @
  48kHz mono = ~5MB raw. Decoderen kan 100-500ms duren. Niet
  blokkerend (Web Audio is async), maar UI moet "loading"-state
  tonen tijdens decode.
- **Resolution-mismatch tussen Pd-array en weergegeven WAV.**
  Pd's slot-array is 60s, maar een opname kan korter zijn.
  Trim-end-waarde geeft de werkelijke lengte. We moeten de
  WAV-lengte uit de file zelf afleiden, niet uit de array-grootte.
- **Race-condition bij snel achterelkaar opnemen + slot-switch.**
  Render-trigger moet idempotent zijn — niet renderen als de
  active-slot ondertussen al gewijzigd is.

## Volgende sessie startpunt

1. Lees deze note en het overdrachtsdocument.
2. Bevestig fase 1 als startfase, pad A als data-pad.
3. Schrijf patch-script `patch-waveform-render-v1.py` dat
   `index.html` patcht met de render-functie en de fetch-trigger.
4. Test in v2 (Pd + bridge + browser), cp naar touchlab-mixer,
   commit als één logische wijziging.
