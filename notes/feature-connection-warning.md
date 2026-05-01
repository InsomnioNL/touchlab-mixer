# Feature scope — Verbroken-verbinding-waarschuwing

**Datum:** 1 mei 2026
**Status:** scope-document, nog niet gestart
**Doel:** documenteren van het ontwerp voor een visuele waarschuwing wanneer de UI structureel de WebSocket-verbinding met de bridge verliest.

## Aanleiding

De TouchLab UI praat met de bridge via WebSocket op `ws://localhost:8080` (of straks via Tailscale-tunnel). Als die verbinding wegvalt — bridge crasht, netwerk hapert, USB-Ethernet trekt eruit — kan de UI niets meer naar Pd sturen. Faders bewegen, maar audio reageert niet. Dat is een ernstige stille faal: de muzikant denkt dat alles werkt en blijft door-werken terwijl niets binnenkomt.

Voor live-gebruik (concerten, repetities) is dat onacceptabel. Er moet een onmiskenbaar visueel signaal zijn wanneer de verbinding weg is, en bovendien moeten de controles vergrendeld worden zodat ongecontroleerde state niet bij reconnect ineens naar Pd gaat.

## Mentaal model

Twee soorten verbindings-status, elk met eigen visuele signaal:

- **Verbinding goed**: bestaande groene pulserende vingerafdruk-indicator. Subtiel, "alles in orde".
- **Verbinding weg**: rode rand om de hele mixer. Onmiskenbaar, "probleem".

De twee zijn complementair: vingerafdruk is positief signaal, rode rand is negatief. Bij verbroken verbinding gaat de groene vingerafdruk uit (zou anders liegen).

## Functionele scope v1

**Detectie van verbroken verbinding.**

WebSocket heeft `onclose` en `onerror` events. Bij triggering daarvan start een timer van 1500ms. Als de timer afloopt zonder reconnect, gaat de UI in "disconnected" modus. Bij reconnect binnen die 1500ms gebeurt visueel niets — flikker wordt genegeerd.

**Visuele signalen tijdens "disconnected"**:

- Rode rand om de hele mixer (statisch of pulserend, te bepalen tijdens implementatie). Stijl te aligneren met de bestaande TTB-LOCAL-rode-rand voor consistentie.
- Groene vingerafdruk-indicator gaat uit of verandert van kleur (rood, of grijs).
- Eventueel een kleine tekst-melding "Geen verbinding met bridge" — te beslissen tijdens implementatie of dat extra waarde heeft naast de rode rand.

**Controles vergrendeld tijdens "disconnected"**:

- Alle faders, knobs, buttons reageren niet op input. Visueel grijs of dimmed.
- Reden: voorkomt dat ongecontroleerde state-veranderingen (master-fader per ongeluk omhoog gedraaid tijdens disconnect) bij reconnect naar Pd gaan en een audio-piek veroorzaken.
- Dit is veilig omdat Pd's interne master-vol bij startup op 0 staat en de bridge bij re-init niet automatisch hoge waardes pusht.

**TTB-popup blijft open** tijdens disconnect indien hij dat al was. Inputs erin worden ook vergrendeld, maar de popup zelf hoeft niet gesloten en geopend te worden bij reconnect. Spaart de gebruiker werk in een moment van potentieel haast.

**Geen geluid.** Geen audio-feedback bij verbroken verbinding. Dat zou in een live-context catastrofaal zijn (onbedoeld geluid tijdens een concert).

**Reconnect**: bij succesvol herstellen van WebSocket-verbinding gaan rode rand uit, vingerafdruk weer groen, controles weer reageerbaar. UI's bestaande sync-logica neemt het over voor state-restoratie.

## Wat NIET in v1 zit

- **Auto-reconnect-logica.** Bij disconnect wordt geen actieve poging gedaan opnieuw te verbinden. Mogelijk later v2-feature. Voor v1 vertrouwt het systeem op de browser's standaard WebSocket-reconnect-gedrag (wat afhankelijk van implementatie variabel is).
- **Onderscheid tussen verschillende disconnect-redenen.** Bridge-crash, netwerk-hapering, of expliciete bridge-shutdown krijgen allemaal hetzelfde visuele signaal.
- **Detectie van JackTrip-uitval.** Verbinding tussen muzikanten via JackTrip is een aparte component. Dat wordt door dit feature niet gedetecteerd. Te overwegen voor latere uitbreiding maar architectuur-anders (vereist extern monitoring van JackTrip).
- **Detectie van internet-uitval voor Pages-deploy.** UI is statisch en blijft werken na laden, dus internet voor browser->Pages is na initiële load irrelevant.

## Architectuurvragen

### 1. Waar zit de WebSocket-handler in de UI nu?

Te onderzoeken in implementatie-fase: waar in `index.html` worden `onopen`, `onmessage` events afgehandeld? Daar komen `onclose` en `onerror` bij. Vermoedelijk in een centrale `connect()` of `setupWebSocket()`-functie.

### 2. Hoe lock je alle inputs efficient?

Twee opties:

**A. CSS-class op een wrapper-element.** Body of een wrapper krijgt class `.disconnected`, alle inputs in die scope krijgen `pointer-events: none` en visuele dim. Eén CSS-regel, geen JavaScript-werk per input.

**B. JavaScript-lock per element.** Elk input-element krijgt expliciet `disabled = true`. Werkt voor `<input>` en `<button>` natively; voor custom-knobs zou je extra logica nodig hebben (negeer click-events terwijl in disconnected-state).

**Voorkeur tbd:** A. Veel minder code, makkelijker te garanderen dat *alle* controls vergrendeld zijn, makkelijker te testen.

### 3. Reconnect-detectie zonder auto-reconnect

Browsers' standaard WebSocket-gedrag bij disconnect varieert. Sommige browsers proberen niet automatisch opnieuw, andere wel. Voor v1: de UI poogt geen actieve reconnect, maar wanneer de browser zelf een nieuwe `onopen`-event genereert (bv. bij refresh of automatische browser-retry), pakt de UI dat op en gaat terug naar verbonden-modus.

In de praktijk betekent dit dat de gebruiker mogelijk de pagina handmatig moet refreshen na een disconnect. Voor v2 kunnen we expliciete reconnect-attempts inbouwen.

### 4. Vingerafdruk-state synchroniseren

Bestaande groene pulserende vingerafdruk is verbonden aan de WebSocket-status. Te onderzoeken of die handler al iets doet bij disconnect, of dat we daar nieuwe logica toevoegen om 'm uit/rood te zetten.

## Voorgestelde fasering

**Fase 1 — disconnect-detectie + rode rand (~30 min)**

- Tap in op bestaande WebSocket-handler
- Bij `onclose`/`onerror`: start 1500ms timer
- Bij timer-afloop zonder reconnect: voeg CSS-class `.disconnected` toe aan body
- CSS-regel: `.disconnected .mixer { border: ...rode rand... }`
- Bij `onopen`: verwijder class

**Fase 2 — controles vergrendelen (~30 min)**

- CSS-regel uitbreiden: `.disconnected input, .disconnected button, .disconnected .knob { pointer-events: none; opacity: 0.5; }`
- Test: tijdens disconnect, probeer fader te bewegen — zou niet moeten werken
- Test: na reconnect, fader werkt weer

**Fase 3 — vingerafdruk-state (~15 min)**

- Vingerafdruk gaat uit of rood bij disconnected
- Pulserende animatie pauzeert tijdens disconnected

**Fase 4 — testen in realistische scenario's (~30 min)**

- Bridge stoppen tijdens UI-gebruik: rode rand verschijnt na 1.5s
- Bridge herstarten: rode rand weg, controles werken weer, state synct
- TTB-popup open tijdens disconnect: blijft open, controles erin vergrendeld
- Korte hikkup (< 1.5s): geen visueel signaal

## Wat dit níet doet

- Geen auto-reconnect met retry-logica (v2)
- Geen gedifferentieerde disconnect-reden-display
- Geen audio-feedback bij verbroken verbinding (bewust)
- Geen detectie van JackTrip-uitval (apart probleem)

## Risico's en valkuilen

- **Custom-knob-elementen.** Knobs in TouchLab zijn SVG-based, geen native `<input>`. CSS `pointer-events: none` werkt op SVG-elementen, maar de drag-event-listeners op `window` (mousemove/touchmove) moeten ook respecteren dat we in disconnected-state zijn — anders blijft de drag werken zonder dat de gebruiker iets ziet. Dubbele check tijdens implementatie.
- **Timing van CSS-class verwijderen bij reconnect.** Als de WebSocket eerst `onopen` triggert maar de bridge nog niet klaar is om messages te accepteren, zou de UI controls weer activeren terwijl de eerste paar messages verloren gaan. Te bekijken of bridge een "ready"-message stuurt na verbinding voor we de UI activeren.
- **TTB-popup tijdens disconnect.** Open-blijven is het bewuste gedrag, maar test of de popup niet onbedoeld andere CSS-rules opvangt die 'm verstoppen.

## Volgende sessie startpunt

1. Lees deze note plus het algemene overdrachtsdocument.
2. Onderzoek architectuurvraag 1: waar zit de WebSocket-handler in `index.html`?
3. Bevestig CSS-class-aanpak (architectuurvraag 2).
4. Begin met fase 1 — minimale viable verbroken-verbinding-detectie + visueel signaal.
5. Test elke fase apart voor je doorgaat naar de volgende.
