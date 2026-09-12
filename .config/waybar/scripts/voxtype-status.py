#!/usr/bin/env python3
"""Waybar status wrapper: rewrites voxtype's tooltip to show the active model."""

import json
import subprocess

proc = subprocess.Popen(
    ["voxtype", "status", "--follow", "--format", "json", "--extended"],
    stdout=subprocess.PIPE,
    text=True,
    bufsize=1,
)

for line in proc.stdout:
    line = line.strip()
    if not line:
        continue
    try:
        d = json.loads(line)
    except json.JSONDecodeError:
        continue

    cls = d.get("class", "idle")
    model = d.get("model") or "unknown"

    if "parakeet-unified" in model:
        engine_label = f"Parakeet streaming ({model})"
    elif "parakeet" in model:
        engine_label = f"Parakeet batch ({model})"
    elif "cohere" in model:
        engine_label = f"Cohere ({model})"
    else:
        engine_label = f"Whisper ({model})"

    if cls == "idle":
        d["tooltip"] = f"Model: {engine_label}"
    elif cls in ("recording", "streaming"):
        d["tooltip"] = f"Recording — {engine_label}"
    elif cls == "transcribing":
        d["tooltip"] = f"Transcribing — {engine_label}"

    print(json.dumps(d), flush=True)
