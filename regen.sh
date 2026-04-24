#!/bin/bash
# regen.sh — Regenerate all TouchLab mixer patches from session.json.
#
# Runs the three generators in order:
#   1. generate-mixer.py   → ch1..N.pd, fx-bus.pd, master-section.pd,
#                             vu-sender.pd, touchlab-mixer[-ttb].pd
#   2. generate-router.py  → sampler-router.pd
#   3. generate-slots.py   → sampler-slot-2..N.pd  (from slot-1 template),
#                             sampler-host.pd
#
# Idempotent — run after any session.json change, or just to refresh.
# Requires python3 on PATH.

set -euo pipefail

# Run from this script's own directory so all relative paths resolve here,
# regardless of where the user invokes it from.
cd "$(dirname "$0")"

# Pre-flight checks
if [ ! -f session.json ]; then
    echo "ERROR: session.json not found in $(pwd)" >&2
    exit 1
fi

if [ ! -f sampler-slot-1.pd ]; then
    echo "ERROR: sampler-slot-1.pd (template) not found in $(pwd)" >&2
    exit 1
fi

for script in generate-mixer.py generate-router.py generate-slots.py; do
    if [ ! -f "$script" ]; then
        echo "ERROR: $script not found in $(pwd)" >&2
        exit 1
    fi
done

echo "════════════════════════════════════════════════════════════════"
echo " TouchLab — regenerating all patches from session.json"
echo " Directory: $(pwd)"
echo "════════════════════════════════════════════════════════════════"
echo ""

echo "[1/3] Mixer  (channels + master + fx + vu + toplevels)"
echo "────────────────────────────────────────────────────────────────"
python3 generate-mixer.py session.json
echo ""

echo "[2/3] Sampler router"
echo "────────────────────────────────────────────────────────────────"
python3 generate-router.py
echo ""

echo "[3/3] Sampler slots  (slots 2..N from slot-1 template, plus host)"
echo "────────────────────────────────────────────────────────────────"
python3 generate-slots.py
echo ""

echo "════════════════════════════════════════════════════════════════"
echo " ✓ Regeneration complete"
echo "════════════════════════════════════════════════════════════════"
