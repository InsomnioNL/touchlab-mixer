#!/usr/bin/env python3
"""
TouchLab Mixer Config Parser
Leest het TERMINAL config formaat en genereert session_[naam].json
per endpoint dat mixer=1 heeft.

Gebruik:
  python3 parse-config.py Gaudeamus_Q8_test.txt

Genereert:
  session_uli.json
  session_pepe.json
  etc.

Daarna per endpoint:
  python3 generate-mixer.py session_uli.json
"""

import json, sys, os, re

def parse_config(path):
    with open(path) as f:
        text = f.read()

    def get(key):
        m = re.search(rf'^{key}\s*=\s*(.+)', text, re.MULTILINE)
        if not m: return None
        val = m.group(1).strip()
        val = re.sub(r'\s*#.*$', '', val).strip()
        return val

    def get_list(key):
        """Leest een waarde die mogelijk meerdere regels beslaat met backslash-continuatie."""
        m = re.search(rf'^{key}\s*=\s*\((.+?)\)', text, re.DOTALL | re.MULTILINE)
        if not m:
            return []
        raw = m.group(1)
        raw = re.sub(r'\\\s*\n', ' ', raw)
        items = [x.strip() for x in raw.split() if x.strip()]
        return items

    def get_numlist(key):
        """Leest een lijst van nummers."""
        m = re.search(rf'^{key}\s*=\s*\((.+?)\)', text, re.DOTALL | re.MULTILINE)
        if not m:
            return []
        raw = m.group(1)
        raw = re.sub(r'\\\s*\n', ' ', raw)
        items = [x.strip() for x in raw.split() if x.strip()]
        return [int(x) for x in items]

    # Basis parameters
    sample_rate = int(get('sample_rate') or 48000)
    fps         = int(get('fps') or 64)

    # Deelnemers
    participants = get_list('participants')
    endpoints    = get_list('endpoints')
    mixer_flags  = get_numlist('mixer')
    no_of_mics   = get_numlist('no_of_mics')
    lbw          = get_numlist('lbw_endpoint')

    N = len(participants)
    print(f"Sessie: {N} deelnemers")
    print(f"Sample rate: {sample_rate} Hz, fps: {fps}")
    print()

    # Bouw kanaallijst — alle deelnemers, ongeacht mixer flag
    # Elk kanaal is mono (TERMINAL vouwt meerdere mics samen)
    all_channels = []
    for i, name in enumerate(participants):
        all_channels.append({
            "index":    i + 1,
            "name":     name,
            "endpoint": endpoints[i] if i < len(endpoints) else f"ep{i}",
            "mics":     no_of_mics[i] if i < len(no_of_mics) else 1,
            "lbw":      bool(lbw[i]) if i < len(lbw) else False,
            "has_mixer": bool(mixer_flags[i]) if i < len(mixer_flags) else False,
            "type":     "mono",
        })

    # Genereer session.json per endpoint met mixer=1
    generated = []
    for ch in all_channels:
        if not ch["has_mixer"]:
            print(f"  {ch['name']:12} mixer=0, geen instantie")
            continue

        # Eigen kanaal vooraan, rest in config-volgorde
        own = ch
        others = [c for c in all_channels if c["index"] != own["index"]]
        ordered = [own] + others

        # Herbepaal indices voor PD (JACK input nummers)
        channels_out = []
        for jack_idx, c in enumerate(ordered, start=1):
            channels_out.append({
                "index": jack_idx,
                "name":  c["name"],
                "type":  c["type"],
            })

        session = {
            "session_name":      f"TouchLab — {ch['name']}",
            "endpoint":          ch["endpoint"],
            "osc_receive_port":  9000,
            "vu_send_host":      "127.0.0.1",
            "vu_send_port":      9001,
            "vu_interval_ms":    round(1000 / fps),
            "sample_rate":       sample_rate,
            "fps":               fps,
            "channels":          channels_out,
        }

        fname = f"session_{ch['name'].lower()}.json"
        with open(fname, "w") as f:
            json.dump(session, f, indent=2, ensure_ascii=False)

        print(f"  {ch['name']:12} mixer=1 → {fname}  ({len(channels_out)} kanalen)")
        generated.append((ch["name"], fname))

    print()
    print("Volgende stap — run per endpoint:")
    for name, fname in generated:
        print(f"  python3 generate-mixer.py {fname}")

    print()
    print("Of alles in één keer:")
    for name, fname in generated:
        print(f"  python3 generate-mixer.py {fname}  # {name}")

    return generated


if __name__ == "__main__":
    config = sys.argv[1] if len(sys.argv) > 1 else None
    if not config or not os.path.exists(config):
        print(f"Gebruik: python3 parse-config.py <config-bestand>")
        sys.exit(1)
    parse_config(config)
