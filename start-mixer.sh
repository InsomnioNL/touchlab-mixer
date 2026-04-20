#!/bin/bash
# ─────────────────────────────────────────────────────────────────────────────
# TouchLab Mixer — Start script
# Gebruik: ./start-mixer.sh <config-bestand> <endpoint-naam>
#
# Voorbeeld:
#   ./start-mixer.sh Gaudeamus_Q8_test.txt Uli
#
# Wat dit doet:
#   1. Parse de TERMINAL config → session_[naam].json
#   2. Genereer PD patches voor dit endpoint
#   3. Start JACK (als nog niet actief)
#   4. Start PD headless
#   5. Start de WebSocket bridge
# ─────────────────────────────────────────────────────────────────────────────

set -e

CONFIG="$1"
ENDPOINT="$2"
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"

# ── Argument check ────────────────────────────────────────────────────────────
if [ -z "$CONFIG" ] || [ -z "$ENDPOINT" ]; then
  echo "Gebruik: $0 <config-bestand> <endpoint-naam>"
  echo "Voorbeeld: $0 Gaudeamus_Q8_test.txt Uli"
  exit 1
fi

if [ ! -f "$CONFIG" ]; then
  echo "Fout: config bestand '$CONFIG' niet gevonden."
  exit 1
fi

ENDPOINT_LOWER=$(echo "$ENDPOINT" | tr '[:upper:]' '[:lower:]')
SESSION="session_${ENDPOINT_LOWER}.json"

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "  TouchLab Mixer — $ENDPOINT"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

# ── Stap 1: Parse config ──────────────────────────────────────────────────────
echo "▶  Config parsen..."
python3 "$SCRIPT_DIR/parse-config.py" "$CONFIG"

if [ ! -f "$SESSION" ]; then
  echo "Fout: $SESSION niet aangemaakt. Controleer of '$ENDPOINT' in de config staat met mixer=1."
  exit 1
fi

# ── Stap 2: Genereer PD patches ───────────────────────────────────────────────
echo ""
echo "▶  PD patches genereren voor $ENDPOINT..."
python3 "$SCRIPT_DIR/generate-mixer.py" "$SESSION"

# ── Stap 3: Sample rate uit session JSON ─────────────────────────────────────
SAMPLE_RATE=$(python3 -c "import json; d=json.load(open('$SESSION')); print(d.get('sample_rate', 48000))")
FPS=$(python3 -c "import json; d=json.load(open('$SESSION')); print(d.get('fps', 64))")

echo ""
echo "▶  Audio: ${SAMPLE_RATE}Hz, ${FPS}fps"

# ── Stap 4: Stop eventuele oude instanties ────────────────────────────────────
echo ""
echo "▶  Oude instanties stoppen..."
pkill -f "touchlab-mixer.pd" 2>/dev/null && echo "   PD gestopt" || true
pkill -f "bridge.js" 2>/dev/null && echo "   Bridge gestopt" || true
sleep 0.5

# ── Stap 5: JACK starten (alleen Linux) ──────────────────────────────────────
if [[ "$OSTYPE" == "linux-gnu"* ]]; then
  if ! pgrep -x jackd > /dev/null && ! pgrep -x jackdbus > /dev/null; then
    echo ""
    echo "▶  JACK starten..."
    jackd -d alsa -r "$SAMPLE_RATE" -p "$FPS" &
    JACK_PID=$!
    sleep 2
    echo "   JACK gestart (PID $JACK_PID)"
  else
    echo "▶  JACK draait al"
  fi
elif [[ "$OSTYPE" == "darwin"* ]]; then
  if ! pgrep -x jackd > /dev/null; then
    echo ""
    echo "▶  JACK starten (macOS)..."
    jackd -d coreaudio -r "$SAMPLE_RATE" -p "$FPS" &
    JACK_PID=$!
    sleep 2
    echo "   JACK gestart (PID $JACK_PID)"
  else
    echo "▶  JACK draait al"
  fi
fi

# ── Stap 6: PD headless starten ───────────────────────────────────────────────
echo ""
echo "▶  Pure Data starten (headless)..."

# Zoek pd executable
if command -v pd &> /dev/null; then
  PD_CMD="pd"
elif [ -f "/Applications/Pd-0.55-2.app/Contents/Resources/bin/pd" ]; then
  PD_CMD="/Applications/Pd-0.55-2.app/Contents/Resources/bin/pd"
elif [ -f "/usr/bin/pd" ]; then
  PD_CMD="/usr/bin/pd"
else
  echo "Fout: Pure Data niet gevonden. Installeer PD of pas PD_CMD aan in dit script."
  exit 1
fi

"$PD_CMD" -nogui -jack -r "$SAMPLE_RATE" -path "$SCRIPT_DIR" "$SCRIPT_DIR/touchlab-mixer.pd" &
PD_PID=$!
echo "   PD gestart (PID $PD_PID)"
sleep 1

# ── Stap 7: Bridge starten ────────────────────────────────────────────────────
echo ""
echo "▶  WebSocket bridge starten..."
node "$SCRIPT_DIR/bridge.js" "$SESSION" &
BRIDGE_PID=$!
echo "   Bridge gestart (PID $BRIDGE_PID)"

# ── Samenvatting ──────────────────────────────────────────────────────────────
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "  Mixer actief voor: $ENDPOINT"
echo "  Mixer UI:  https://insomnionl.github.io/touchlab-mixer"
echo "  WebSocket: ws://localhost:8080"
echo "  PID PD:    $PD_PID"
echo "  PID Bridge: $BRIDGE_PID"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "  Stop alles met: Ctrl+C"
echo ""

# ── Wacht en stop netjes bij Ctrl+C ──────────────────────────────────────────
trap "echo ''; echo 'Stoppen...'; kill $PD_PID $BRIDGE_PID 2>/dev/null; exit 0" INT TERM

wait
