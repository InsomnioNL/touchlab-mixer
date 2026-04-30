# Feature scope — Remote mix-assist via Tailscale

**Datum:** 30 april 2026 (avond, herzien)
**Status:** scope-document, nog niet gestart
**Doel:** documenteren van de architectuur-keuzes en ontwerp-vragen voor een feature waarmee Uli en Christiaan op afstand kunnen ingrijpen in andermans TouchLab Mixer-instantie tijdens of voor een sessie. Eind-doel: integratie in het InsomnioNL-frontend met een dedicated tonmeester-pagina.

## Aanleiding

TouchLab Mixer + TTB is per ontwerp een persoonlijke monitor-mixer: één muzikant draait Pd + bridge op zijn audio-eindpunt, en zijn UI verbindt naar `localhost:8080` op diezelfde machine. Niemand anders heeft toegang. Dat is goed — het is een persoonlijk instrument.

Maar er is een legitieme behoefte voor een tonmeester-rol: minder technische muzikanten in de groep hebben hulp nodig bij hun mix-instellingen, hetzij voor een sessie (initiële setup, balansering) of tijdens (correcties op het moment). Uli en Christiaan willen die hulp kunnen geven zonder fysiek aanwezig te zijn.

Op termijn wordt dit ingebed in het bredere InsomnioNL-frontend, waar Uli en Christiaan een dedicated tonmeester-pagina krijgen vanwaar ze kunnen schakelen tussen mixers van verschillende muzikanten in een sessie.

## De architectuur bestaat al

Belangrijk inzicht: TouchLab heeft al het architectuurpatroon dat voor remote mix-assist nodig is. De bestaande opzet is een browser-UI die via WebSocket een lokale API (bridge.js) bedient, die op zijn beurt het audio-systeem (Pd) aanstuurt. Precies hetzelfde model dat in de bredere InsomnioNL-context is aangedragen voor remote-bediening van eindpunten — dedicated UI in browser, lokale API op eindpunt, mixer-commands. We bouwen voor remote mix-assist dus geen nieuwe architectuur. We maken alleen de bestaande bridge bereikbaar over een Tailscale-tunnel in plaats van alleen op `localhost`.

Dat heeft voordelen ten opzichte van screen-sharing-alternatieven (RustDesk, TeamViewer, etc.):

- Geen extra applicatie-belasting op het audio-eindpunt
- Lage latency — directe API-calls in plaats van pixel-streaming
- Werkt op elk apparaat met een browser, inclusief tablet en telefoon
- De muzikant blijft baas — geen volledig scherm overgenomen, alleen mixer-controls

## Tailscale als transport

Het audio-eindpunt staat thuis bij de muzikant, achter NAT en eventueel een firewall. Om vanaf buiten naar de bridge te kunnen verbinden zonder port-forwarding is een mesh-VPN het standaard antwoord. Tailscale doet dit met WireGuard onderwater, peer-to-peer encrypted verbindingen die door NAT heen werken, met centrale authenticatie via een gehoste coordinator.

InsomnioNL gebruikt al Tailscale, dus voor TouchLab sluiten we daar op aan. (Headscale — de open-source self-hosted variant — blijft een mogelijke overstap voor later, mocht InsomnioNL ooit kiezen voor self-hosting van de coordinator om data-soevereiniteit-redenen of grootschalige groei. Voor nu niet relevant; Tailscale-clients werken sowieso met beide, dus de overstap is een operationele aangelegenheid, geen TouchLab-code-wijziging.)

## Operationeel model: alle audio-eindpunten zijn InsomnioNL-eigendom

Alle audio-eindpunten (Mac Minis, mini-PCs) worden door InsomnioNL geconfigureerd voordat ze naar de muzikant gaan. Tailscale staat al geïnstalleerd en is geregistreerd in jullie tailnet als tagged resource (`tag:musicus`). De muzikant ontvangt een werkend kastje en hoeft zelf nooit een Tailscale-account aan te maken of een app te installeren.

Concreet voor device-types:

- **Audio-eindpunten van muzikanten:** in jullie tailnet als tagged resources. Tellen niet als seats. Beheerd door jullie.
- **Tonmeester-devices (Uli + Christiaan):** user-seats in jullie tailnet. Twee seats van de zes gratis seats gebruikt.
- **UI-devices van muzikanten zelf** (hun eigen telefoon/tablet om hun eigen mixer te bedienen): niet in Tailscale. Verbinden gewoon over LAN naar het audio-eindpunt thuis.
- **UI-devices van tonmeesters voor remote work** (jullie laptops/tablets): in Tailscale als user-devices van jullie eigen account. Onbeperkt aantal user-devices op het gratis plan.

Seat-rekensom voor het gratis Tailscale Personal plan: Uli + Christiaan = 2 seats. Vier seats over voor toekomstige groei aan tonmeester-kant. Audio-eindpunten zijn tagged resources, geen seats, dus de groei in muzikant-aantal kost niks.

## Aanpassingen aan TouchLab

### Bridge: configureerbaar listen-address

Nu luistert de bridge alleen op `localhost:8080`. Voor remote-toegang moet hij ook op het Tailscale-interface kunnen luisteren.

Optie A — `0.0.0.0` opt-in via session.json. Default blijft `localhost`. Wie remote-assist wil, zet de flag.

Optie B — bind specifiek aan het Tailscale-interface (`100.x.x.x`). Veiliger maar vereist dat de bridge het Tailscale-IP weet, wat dynamisch is.

Voorkeur tbd: A is simpeler. Tailscale-ACL's vangen het risico op dat een willekeurige LAN-peer zomaar kan verbinden.

### UI: configureerbare WebSocket-URL

Nu hardcoded `ws://localhost:8080`. Voor remote-gebruik moet je een andere URL kunnen opgeven.

Eenvoudigste route: query-parameter, bv. `https://insomnionl.github.io/touchlab-mixer?ws=ws://uli-macmini:8080`. Default blijft `localhost`. UI leest `?ws=` uit `window.location` bij opstart.

### Sample-fetch route — open vraag

UI haalt waveform-data uit `http://localhost:8080/samples/<filename>`. Bij remote-gebruik moet die URL ook verwijzen naar de remote bridge, niet localhost. Mogelijke oplossingen:

- Hardcoded gefixed door dezelfde host als WS te gebruiken (afgeleid van `?ws=`)
- Aparte `?http=` parameter
- Bridge serveert ook de UI zelf en de URL is altijd relatief

Te beslissen.

## Toegangsbeheer via Tailscale-ACL's

Tagging: `tag:tonmeester` voor Uli + Christiaan, `tag:musicus` voor alle audio-eindpunten. ACL-regels in de admin-console: alleen sources met `tag:tonmeester` mogen poort 8080 op destinations met `tag:musicus` bereiken. Geen regel voor muzikant-onderling — die zijn als tagged resources sowieso niet aan een gebruiker gekoppeld en kunnen elkaar niet vanuit het account bereiken. Default-deny zorgt voor de rest.

Eerste setup samen doen, daarna periodiek verifiëren met een test (kan een willekeurige niet-tonmeester de bridge bereiken? Hopelijk niet).

## Frontend-integratie (eind-doel)

InsomnioNL-frontend krijgt een dedicated tonmeester-pagina. Vereist:

1. **Sessie-registratie:** een mechanisme waarmee de frontend weet welke muzikanten in een sessie zitten en op welke Tailscale-hostnamen hun bridges luisteren.
2. **Schakel-UI voor tonmeester:** een dropdown of tabs waarmee Uli/Christiaan switcht tussen mixers. Achter elke tab zit feitelijk een aparte UI-instantie verbonden naar een andere bridge.
3. **Authenticatie aansluiten:** frontend authenticeert al z'n eigen gebruikers. Tailscale-toegang loopt parallel daaraan. Niet alle frontend-gebruikers zijn Tailscale-gebruikers; alleen de tonmeesters.
4. **Ontwerpvraag:** kan de tonmeester-UI tegelijk meerdere mixers tonen (multi-pane) of altijd één tegelijk?

## Open ontwerpvragen

1. **Authenticatie binnen TouchLab zelf?** Nu is er geen auth — wie de WS bereikt mag alles. Met Tailscale-ACL's is dat acceptabel binnen de tunnel, maar je kunt overwegen om ook in TouchLab zelf een eenvoudige token-check toe te voegen. Lijkt me niet urgent voor v1.
2. **Wat als de muzikant aan dezelfde fader draait als de tonmeester?** Last-write-wins is de huidige defacto-behavior. Voor v1 acceptabel; muzikanten merken het meteen en kunnen praten.
3. **Visuele indicator voor de muzikant dat er een tonmeester verbonden is?** Voor v1 zou een eenvoudig icoontje rechtsboven al volstaan ("Christiaan kijkt mee").
4. **Sessie-opnames remote starten?** Komt automatisch mee zodra de hele UI op afstand werkt.
5. **Latency van UI-controles via Tailscale?** Naar verwachting verwaarloosbaar (orde van milliseconden voor een fader-event). Audio gaat sowieso niet door deze WS — die loopt via JackTrip. Te verifiëren bij eerste prototype.

## Voorgestelde fasering

**Fase 1 — bridge-listen + UI-WS-URL configureerbaar (1-2u)**

- session.json `bridge.listen` toevoegen
- bridge.js leest die config, valt terug op `localhost`
- index.html leest `?ws=` query-parameter, valt terug op `ws://localhost:8080`
- Test: Uli draait bridge op zijn machine, Christiaan opent op zijn laptop de UI met `?ws=`-parameter naar Uli's Tailscale-hostname

**Fase 2 — sample-route afleiden van WS-host (30 min)**

UI gebruikt dezelfde host als WS voor de `/samples/`-fetch in plaats van hardcoded `localhost`.

**Fase 3 — Tailscale-ACL configureren**

Geen code-werk, wel administratie. Tonmeester-vs-musicus-tagging in de Tailscale admin-console. Verifiëren met test.

**Fase 4 — Frontend-integratie (apart traject)**

Tonmeester-pagina in InsomnioNL-frontend, sessie-registratie en hostname-discovery, multi-mixer-UI.

## Wat dit níet doet (bewust)

- Geen authenticatie in TouchLab zelf (delegatie aan Tailscale-ACL's)
- Geen audio-routing aanpassingen — JackTrip blijft het transport voor audio
- Geen muzikant-tot-muzikant peer-mixing (tonmeester-only)
- Geen real-time scherm-deling — alleen control-state synchronisatie
- Geen RustDesk/TeamViewer-integratie (browser-naar-API is voldoende)

## Risico's en valkuilen

- Bridge die op alle interfaces luistert is een vergroot aanvalsoppervlak. Ondervangen door Tailscale-ACL's, maar het audio-eindpunt moet wel Tailscale draaien én correct geconfigureerd zijn.
- Configuratie-fouten in ACL's kunnen tonmeesters blokkeren of muzikanten elkaars mixers laten zien. Eerste setup samen doen, daarna periodiek verifiëren.
- Tailscale-uitval valt buiten onze controle. Geen plan-B in fase 1; voor productiegebruik later wellicht een SSH-tunnel-fallback.
- UI-state-divergentie: als WS-verbinding kort wegvalt en herstelt, kan UI-state desyncen met bridge-state. Bestaand probleem ook lokaal, maar kwetsbaarder over latere link.

## Volgende sessie startpunt

1. Lees deze note plus de overdrachtsdocumenten.
2. Bevestig fase 1 als startfase: bridge-listen-flag + UI-WS-URL-parameter.
3. Bevestig de open vraag over de sample-route-aanpak (fase 2).
4. Pre-flight, dan patch-script schrijven dat session.json-schema, bridge.js, en index.html in één commit aanpast.
5. Test in v2 met een tweede machine in hetzelfde Tailscale-tailnet.
