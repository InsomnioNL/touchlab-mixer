#!/bin/bash
# regen.sh — Regenerate all TouchLab mixer patches from session.json.
#
# Runs the three generators in order, then applies the post-generation
# patch-scripts (master-vol + rec-path injection) so the FUDI keten
# blijft compleet:
#
#   1. generate-mixer.py   → ch1..N.pd, fx-bus.pd, master-section.pd,
#                            vu-sender.pd, touchlab-mixer[-ttb].pd
#   2. generate-router.py  → sampler-router.pd
#   3. generate-slots.py   → sampler-slot-2..N.pd  (from slot-1 template),
#                            sampler-host.pd
#   4. patches             → patch-host-master-vol.py
#                            patch-host-rec-path.py
#                            patch-sampler-host-rec-path.py
#
# Patch-scripts zijn idempotent (markers) — herhaaldelijk draaien is
# veilig. Volgorde van patches is wel belangrijk: master-vol vóór
# rec-path (rec-path-patch zoekt 'sampler-master-vol' in route-regel).
#
# Idempotent — run after any session.json change, or just to refresh.
# Requires python3 on PATH.

set -euo pipefail

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

for script in generate-mixer.py generate-router.py generate-slots.py \
              patch-host-master-vol.py patch-host-rec-path.py \
              patch-sampler-host-rec-path.py; do
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

echo "[1/4] Mixer  (channels + master + fx + vu + toplevels)"
echo "────────────────────────────────────────────────────────────────"
python3 generate-mixer.py session.json
echo ""

echo "[2/4] Sampler router"
echo "────────────────────────────────────────────────────────────────"
python3 generate-router.py
echo ""

echo "[3/4] Sampler slots  (slots 2..N from slot-1 template, plus host)"
echo "────────────────────────────────────────────────────────────────"
python3 generate-slots.py
echo ""

echo "[4/4] Post-regen patches  (master-vol + rec-path injection)"
echo "────────────────────────────────────────────────────────────────"
python3 patch-host-master-vol.py
python3 patch-host-rec-path.py
python3 patch-sampler-host-rec-path.py
echo ""

echo "════════════════════════════════════════════════════════════════"
echo " ✓ Regeneration complete"
echo "════════════════════════════════════════════════════════════════"
