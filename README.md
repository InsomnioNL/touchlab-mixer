# TouchLab Mixer — Pure Data vervanging voor JackMixer

Headless PD mixer met WebSocket bediening vanuit de frontend app.

## Bestanden

| Bestand | Rol |
|---|---|
| `session.json` | Sessie config: kanalen, namen, poorten |
| `generate-mixer.py` | Genereert `touchlab-mixer.pd` + `vu-sender.pd` |
| `channel-strip.pd` | Abstractie: één kanaalstrip (volume, pan, mute/solo gate, fx, VU) |
| `fx-bus.pd` | Reverb return bus (`rev2~`) |
| `master-section.pd` | Master volume + aparte hoofdtelefoon mix |
| `vu-sender.pd` | *(gegenereerd)* VU metering → UDP naar bridge |
| `touchlab-mixer.pd` | *(gegenereerd)* Hoofdpatch, headless |
| `bridge.js` | Node.js: WebSocket ↔ PD FUDI, mute+solo logica |
| `panner.pd` | Constante-kracht panner (origineel, ongewijzigd) |
| `rev2_.pd` | Goedkope reverb (origineel, ongewijzigd) |

## Installatie

### Pure Data (Linux / Raspberry Pi)
```bash
sudo apt install puredata
```

### Node.js bridge
```bash
npm install ws
node bridge.js session.json
```

### JACK
```bash
jackd -d alsa -d hw:0 -r 48000 -p 256 &
```

## Workflow

### 1. Sessie aanpassen
Bewerk `session.json` met de juiste kanalen en namen:
```json
{
  "channels": [
    { "index": 1, "name": "Bas",    "type": "mono" },
    { "index": 2, "name": "Piano",  "type": "mono" }
  ]
}
```
`index` = JACK input kanaal nummer.

### 2. Patch genereren
```bash
python3 generate-mixer.py session.json
```

### 3. Starten
```bash
# JACK
jackd -d alsa -d hw:0 -r 48000 -p 256 &

# PD (headless)
pd -nogui -jack -r 48000 touchlab-mixer.pd &

# Bridge
node bridge.js session.json
```

### 4. Frontend verbinden
De frontend verbindt via WebSocket op `ws://localhost:8080`.

## OSC / berichten schema

### Frontend → Bridge (WebSocket JSON)
```json
{ "type": "volume",    "channel": 1, "value": 0.75 }
{ "type": "pan",       "channel": 1, "value": 0.5  }
{ "type": "mute",      "channel": 1, "value": true  }
{ "type": "solo",      "channel": 1, "value": true  }
{ "type": "fx",        "channel": 1, "value": 0.2  }
{ "type": "masterVol",               "value": 0.8  }
{ "type": "hpVol",                   "value": 0.9  }
{ "type": "fxReturn",                "value": 0.3  }
```

### Bridge → PD (TCP FUDI, poort 9000)
```
; ch1-vol  0.75;
; ch1-pan  0.5;
; ch1-gate 1;       ← 0 of 1, berekend uit mute + solo
; ch1-fx   0.2;
; masterVol 0.8;
; hpVol    0.9;
; fxReturn 0.3;
```

### PD → Bridge (UDP, poort 9001)
```
vu 1 -23.5;
vu 2 -18.0;
vu master -20.1;
```

### Bridge → Frontend (WebSocket JSON)
```json
{ "type": "vu", "channels": [{"index":1,"vu":-23.5},...], "masterVu": -20.1 }
{ "type": "volume", "channel": 1, "value": 0.75 }
```

## Mute + Solo logica

Solo logica wordt volledig in de bridge afgehandeld:
- Meerdere kanalen kunnen tegelijk gesolo'd zijn
- Solo override mute niet (gemutede + gesolo'de kanaal = stil)
- PD ontvangt alleen een `gate` (0 of 1) per kanaal

## JACK routing

PD outputs:
- `dac~ 1 2` → monitor mix (JACK outputs 1+2)
- `dac~ 3 4` → hoofdtelefoon mix (JACK outputs 3+4)

PD inputs:
- `adc~ N` → JACK input N (één per kanaal, via channel-strip abstractie)

## Fase 2 (toekomst)
- MIDI trigger systeem (vervangt Teensyduino)
- Directe opname per kanaal
- WAV file upload
- MIDI learn
