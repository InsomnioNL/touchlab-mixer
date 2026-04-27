"""Verwijder dode 'with_ttb'-tak uit write_main.

Na de cleanup-merge wordt write_main alleen nog aangeroepen voor de
basic touchlab-mixer.pd. write_main_ttb heeft de TTB-tak overgenomen.
Parameters with_ttb en sampler_cfg blijven bestaan voor backward
compat (als no-op) zodat eventuele oude aanroepers niet crashen.

Idempotent via marker REMOVE-DEADCODE-V1.
"""
import sys

PATH = "generate-mixer.py"
MARKER = "REMOVE-DEADCODE-V1"

with open(PATH) as f:
    content = f.read()

if MARKER in content:
    print(f"done — {PATH} al gepatcht ({MARKER})")
    sys.exit(0)

# 1. Docstring updaten
OLD_DOC = '''def write_main(channels, osc_in_port, with_ttb=False, sampler_cfg=None):
    """Schrijf touchlab-mixer.pd of touchlab-mixer-ttb.pd.

    Als with_ttb=True: voegt sampler-router, sampler-slots, en een tweede
    FUDI-input (UDP 9002) toe voor sampler-commando's.
    """'''

NEW_DOC = '''def write_main(channels, osc_in_port, with_ttb=False, sampler_cfg=None):
    """Schrijf touchlab-mixer.pd (basic, zonder TTB).

    REMOVE-DEADCODE-V1: parameters with_ttb en sampler_cfg blijven bestaan
    voor backward compat maar zijn no-ops. TTB-versie wordt door
    write_main_ttb afgehandeld (cleanup-merge, commit 287f368).
    """'''

if OLD_DOC not in content:
    print("ERROR: docstring-anker niet gevonden", file=sys.stderr)
    sys.exit(1)

content = content.replace(OLD_DOC, NEW_DOC, 1)

# 2. suffix-regel simpeler maken
OLD_SUFFIX = '    suffix = "-ttb" if with_ttb else ""\n'
NEW_SUFFIX = ''  # weg, fname-string wordt direct touchlab-mixer.pd

if OLD_SUFFIX not in content:
    print("ERROR: suffix-anker niet gevonden", file=sys.stderr)
    sys.exit(1)

content = content.replace(OLD_SUFFIX, NEW_SUFFIX, 1)

# 3. De hele if-with_ttb blok wegsnijden, plus de comment-banner ervoor.
# We zoeken vanaf het comment-begin tot vlak vóór 'fname = ...'.
DEAD_BLOCK_START = '    # ------------------------------------------------------------------\n    # TTB: sampler-router, sampler slots, sampler FUDI input, status out\n    # ------------------------------------------------------------------\n    if with_ttb and sampler_cfg:'
DEAD_BLOCK_END = '            add(f"#X obj {sx} {sy} sampler-slot-{i + 1};")\n\n    fname = f"touchlab-mixer{suffix}.pd"'

if DEAD_BLOCK_START not in content:
    print("ERROR: dead-block start-anker niet gevonden", file=sys.stderr)
    sys.exit(1)
if DEAD_BLOCK_END not in content:
    print("ERROR: dead-block end-anker niet gevonden", file=sys.stderr)
    sys.exit(1)

# Vind de bereik en vervang door alleen de fname-regel
start_idx = content.index(DEAD_BLOCK_START)
end_idx = content.index(DEAD_BLOCK_END) + len(DEAD_BLOCK_END)
replacement = '    fname = "touchlab-mixer.pd"'
content = content[:start_idx] + replacement + content[end_idx:]

# 4. Print-tail simpler
OLD_PRINT = '    print(f"  ✓  {fname}  ({N} kanalen, TCP poort {osc_in_port}"\n          f"{\', +TTB sampler\' if with_ttb else \'\'})")'
NEW_PRINT = '    print(f"  ✓  {fname}  ({N} kanalen, TCP poort {osc_in_port})")'

if OLD_PRINT not in content:
    print("ERROR: print-anker niet gevonden", file=sys.stderr)
    sys.exit(1)

content = content.replace(OLD_PRINT, NEW_PRINT, 1)

with open(PATH, "w") as f:
    f.write(content)

print(f"✓ Patched {PATH} ({MARKER})")
print("  Dode if-with_ttb-tak verwijderd")
print("  Docstring + suffix + print bijgewerkt")
