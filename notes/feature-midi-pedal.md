# Feature scope — MIDI-voetpedaal voor TTB queue-trigger

**Datum:** 1 mei 2026
**Status:** scope-document, nog niet gestart
**Doel:** documenteren van het ontwerp voor MIDI-voetpedaal-ondersteuning waarmee een muzikant TTB-cues uit de queue kan triggeren zonder de tablet te hoeven aanraken.

## Aanleiding

Tijdens een sessie heeft de muzikant beide handen aan zijn instrument. TTB-cues triggeren via de tablet vereist los te laten, vooruit te kijken, te tikken — niet altijd haalbaar binnen de muzikale flow. Een voetpedaal naast het instrument lost dit op voor cues die vooraf gepland zijn in de queue.

De feature is bedoeld voor elke muzikant met een frontend, niet alleen voor Uli. Verschillende muzikanten kunnen verschillende USB-MIDI-pedalen gebruiken, dus het systeem moet flexibel kunnen omgaan met de specifieke MIDI-messages die hun pedaal stuurt — vandaar MIDI learn als onderdeel van v1.

## Mentaal model

Eén pedaal naast je voet, je triggert cues uit een vooraf opgebouwde queue. Hetzelfde gedrag dat de tablet biedt voor finger-push (kort = one-shot, lang = gate-mode), maar dan via voetbediening en gericht op het volgende slot in de queue.

## Functionele scope v1

**Pedaal triggert het volgende slot in de queue.**

- **Korte druk** (< threshold): one-shot mode. Slot speelt af tot trim-end of natural sample-end. Bij release stept de queue door naar het volgende slot.
- **Lange druk** (> threshold): gate-mode. Slot speelt zolang het pedaal ingetrapt is. Bij release stopt het slot, en stept de queue door naar het volgende.

In beide modi is de queue-progressie gekoppeld aan **release** (pedaal omhoog). Dit unificeert de logica: één event triggert de queue-step, ongeacht of de druk lang of kort was. Het verschil tussen one-shot en gate zit uitsluitend in wat er met de huidige slot gebeurt tijdens de druk — niet in queue-gedrag.

**Threshold-tijd voor lang vs kort**: configureerbaar, default mogelijk hoger dan voor finger-push omdat voetpedaal-mechaniek trager is. Te bepalen tijdens testen.

**Lege queue**: pedaal triggert het laatst-getriggerde slot opnieuw, met dezelfde modus-detectie (kort = one-shot, lang = gate). Bij eerste sessie-start zonder eerdere triggers: pedaal-druk doet niets (visuele feedback in UI dat queue leeg is en geen fallback beschikbaar). Dit gedrag is identiek aan wat we voor de gewone queue-stepper hadden bedacht.

**MIDI learn**: in v1 ingebouwd. UI-flow: gebruiker klikt op "MIDI pedaal koppelen", drukt eenmaal op pedaal, UI vangt de inkomende MIDI-message op en slaat 'm op. Vanaf dat moment werkt elke pedaal-druk die dezelfde message stuurt.

**UI-feedback**: status van pedaal-verbinding in de UI ("pedaal verbonden" / "pedaal niet verbonden"). Geen aparte preview van "wat is het volgende slot" — die bestaat al via de queue-preview die de UI heeft. Geen aparte indicator voor "laatst-getriggerde slot".

## Wat NIET in v1 zit

- Tweede of meerdere pedalen — uitbreiding voor v2
- Configureerbare actie per pedaal — pedaal heeft één vaste functie (queue-trigger met fallback)
- Visuele indicator van laatst-getriggerde slot
- Pedaal-mapping per sessie — één globale mapping per gebruiker, in browser-state of session.json (zie open vraag)
- Meerdere triggers per pedaal (lang vs kort = automatisch op druk-duur, niet via dubbele klik of vergelijkbare patronen)

## Architectuurvragen

### 1. Waar gebeurt MIDI-input-detectie?

Twee plekken mogelijk:

**A. Bridge (Node.js).** Bridge gebruikt een MIDI-library zoals `easymidi` of `webmidi-node`, leest USB-MIDI van het audio-eindpunt, stuurt events door naar de UI via WebSocket, en/of rechtstreeks naar Pd via FUDI. Bridge heeft al de rol van vertaler tussen UI-state en Pd-state, dus het past architectonisch.

**B. Pd zelf.** Pd heeft `[notein]`, `[ctlin]`, `[pgmin]` etc. native objecten voor MIDI. Geen extra dependency, MIDI-events landen direct in Pd's signaalflow. Maar Pd heeft minder flexibele logica voor "stuur de specifieke MIDI-message terug naar UI voor MIDI learn".

**Voorkeur tbd:** bridge. MIDI learn vereist UI-state (de mapping wordt door de gebruiker gemaakt), en bridge zit dichter bij de UI. Plus: de bridge kan dezelfde event ook doorsturen naar Pd voor immediate audio-trigger.

### 2. Waar woont de MIDI-mapping?

Twee opties:

**A. Browser-localStorage.** Mapping per browser, per gebruiker. Werkt direct, geen bridge-aanpassing voor opslag. Nadeel: mapping gaat verloren bij browser-cache-wis, en is niet beschikbaar voor remote-mix-assist (waar een tonmeester de UI op een ander apparaat opent).

**B. Bridge-state, in `session.json` of een aparte file.** Mapping leeft op het audio-eindpunt zelf. Persistent, beschikbaar voor elke browser die met dat eindpunt verbindt. Betere route gegeven het remote-mix-assist scope-document waarin meerdere apparaten op hetzelfde eindpunt verbinden.

**Voorkeur tbd:** B, voor consistentie met het bredere ontwerp. Mapping is intrinsiek aan het eindpunt (waar het pedaal fysiek aan vastzit), niet aan de browser.

### 3. Threshold-detectie: bridge of UI?

Wie meet "is dit een korte of lange druk"? Bridge ziet de raw MIDI-events binnenkomen (down + up), kan daar een timer op zetten en dan een logische `samplerPlay` of `samplerGate`-event sturen. Of UI kan zelf de raw events binnenkrijgen en de logica daar doen.

**Voorkeur tbd:** bridge. Latency is lager als bridge direct beslist, en de logica past bij bridge's bestaande rol als event-vertaler. UI hoeft alleen het uiteindelijke event te ontvangen ("slot N gestart in gate-mode") voor visuele feedback.

### 4. Gate-mode: hoe zeker weten we dat dit werkt voor queue-getriggerde slots?

TouchLab heeft bestaand gate-mode-gedrag voor finger-push op een specifiek slot. Wat nog niet getest is: of dat gedrag ook werkt wanneer de slot via queue-progressie als "het volgende" wordt aangewezen, niet via directe slot-selectie.

**Te onderzoeken in implementatie-fase:** speel een queue-getriggerd slot in gate-mode af (vinger lang ingedrukt op queue-trigger-knop), en kijk of het stop-gedrag werkt zoals bij directe slot-selectie. Mogelijk vereist dit kleine aanpassingen aan de Pd-kant of aan de bridge's queue-logica.

### 5. USB-MIDI-detectie op verschillende OS

Class-compliant USB-MIDI-pedalen werken plug-and-play op macOS en Linux. Bridge moet:

- Bij startup beschikbare MIDI-devices detecteren
- Reageren op hot-plug (pedaal aansluiten tijdens runtime)
- Status-events sturen naar UI bij verbinden/loskoppelen

Standaardgedrag voor Node.js MIDI-libraries — geen complexe issue, wel nodig om te implementeren.

## Voorgestelde fasering

**Fase 1 — bridge MIDI-input + WebSocket-events naar UI (~1.5u)**

- Bridge installeert MIDI-library (te kiezen tijdens implementatie)
- Bij startup detecteert bridge beschikbare MIDI-devices, logt ze
- Bij MIDI-input: bridge stuurt raw event als WebSocket-message naar UI
- Test: pedaal indrukken, controleren dat event in UI aankomt
- Geen functionaliteit gekoppeld aan event nog — alleen detectie + transport

**Fase 2 — MIDI learn-UI (~1u)**

- Knop in UI "MIDI pedaal koppelen"
- Klik → next incoming MIDI-event wordt gemapt op pedaal-actie
- Mapping persistent op bridge-kant (session.json of aparte file)
- Status-indicator "pedaal verbonden / pedaal niet verbonden"

**Fase 3 — pedaal-actie: queue-trigger met fallback (~1.5u)**

- Bridge implementeert threshold-detectie (kort/lang)
- Bridge dispatcht juiste event naar Pd: queue's volgende slot triggeren in juiste modus
- Bij release: queue stept naar volgende, ongeacht modus
- Bij lege queue: laatste-getriggerde slot als fallback-target

**Fase 4 — gate-mode validatie + threshold-tuning (~30 min)**

- Test gate-mode in queue-context (zie architectuurvraag 4)
- Vind goede default-threshold voor pedaal vs vinger
- Eventueel UI-config voor threshold

## Wat dit níet doet

- Geen MIDI-output (TouchLab → MIDI-controller), alleen input
- Geen MIDI-clock-sync of vergelijkbare timing-features
- Geen multi-pedaal mapping (één pedaal-mapping in v1)
- Geen MIDI-routing voor instrument-MIDI (zoals een keyboard-controller)

## Risico's en valkuilen

- **MIDI-library-keuze.** Verschillende Node.js-MIDI-libraries hebben verschillende cross-platform-eigenaardigheden, vooral bij hot-plug-detectie op Linux. Bij implementatie testen op alle target-OS.
- **Threshold-tuning.** Pedaal-mechaniek varieert sterk tussen modellen — een lichte sustain-pedaal-actie verschilt van een zware voetschakelaar. Default-threshold mogelijk per pedaal te configureren in v2.
- **Race-conditions bij snelle pedaal-druk.** Wat als gebruiker drukt, loslaat, drukt voor de queue-step is verwerkt? Mogelijk debounce of queue-event-buffering nodig.
- **Gate-mode + queue-step op release-event.** De combinatie is niet getest in TouchLab. Onverwacht gedrag mogelijk waar bridge en Pd een race-condition krijgen tussen "stop slot" en "step queue + start volgende slot".

## Volgende sessie startpunt

1. Lees deze note plus het algemene overdrachtsdocument.
2. Beslis architectuurvragen 1-3 (waarschijnlijk: bridge-side voor alle drie).
3. Onderzoek architectuurvraag 4 als eerste experiment (kan gate-mode in queue-context).
4. Kies MIDI-library voor Node.js, installeer, test detectie.
5. Begin met fase 1 — pure detectie en transport, geen functionaliteit gekoppeld nog.
