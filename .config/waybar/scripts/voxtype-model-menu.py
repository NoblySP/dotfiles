#!/usr/bin/env python3
"""Right-click menu for the waybar voxtype icon: switch transcription model."""

import os
import re
import subprocess

CFG = os.path.expanduser("~/.config/voxtype/config.toml")
MODEL_DIR = os.path.expanduser("~/.local/share/voxtype/models")

# (engine, model, installed path, menu label)
MODELS = [
    (
        "parakeet",
        "parakeet-unified-en-0.6b",
        "parakeet-unified-en-0.6b",
        "Parakeet Unified (streaming)",
    ),
    (
        "parakeet",
        "parakeet-tdt-0.6b-v3-int8",
        "parakeet-tdt-0.6b-v3-int8",
        "Parakeet TDT INT8 (batch)",
    ),
    ("cohere", "cohere-transcribe-q4f16", "cohere-transcribe-q4f16", "Cohere q4f16 (accurate)"),
    ("whisper", "tiny.en", "ggml-tiny.en.bin", "Whisper tiny.en (fastest)"),
    ("whisper", "base.en", "ggml-base.en.bin", "Whisper base.en"),
    ("whisper", "small.en", "ggml-small.en.bin", "Whisper small.en"),
    (
        "whisper",
        "large-v3-turbo",
        "ggml-large-v3-turbo.bin",
        "Whisper large-v3-turbo",
    ),
]


def read():
    with open(CFG) as f:
        return f.read()


def current():
    cfg = read()
    m = re.search(r'^engine = "([^"]+)"', cfg, re.M)
    engine = m.group(1) if m else "whisper"
    sec = model_section(cfg, engine)
    m = re.search(r'^model = "([^"]+)"', sec, re.M)
    return (engine, m.group(1) if m else None)


def model_section(cfg, name):
    match = re.search(rf'^\[{re.escape(name)}\]\s*$(.*?)(?=^\[|\Z)', cfg, re.M | re.S)
    return match.group(1) if match else ""


def installed(path):
    return os.path.exists(os.path.join(MODEL_DIR, path))


def apply(engine, model):
    cfg = read()
    cfg = re.sub(r'^engine = "[^"]*"', f'engine = "{engine}"', cfg, count=1, flags=re.M)
    out, section, found_section, replaced_model = [], None, False, False
    for line in cfg.splitlines(keepends=True):
        stripped = line.rstrip("\n")
        if stripped.startswith("[") and not stripped.startswith("#"):
            if section == engine and not replaced_model:
                out.append(f'model = "{model}"\n')
                replaced_model = True
            section = stripped.strip("[]").strip()
            found_section = found_section or section == engine
        if section == engine and stripped.startswith("model ="):
            out.append(f'model = "{model}"\n')
            replaced_model = True
            continue
        if engine == "parakeet" and section == "parakeet" and stripped.startswith("streaming ="):
            streaming = "true" if model == "parakeet-unified-en-0.6b" else "false"
            out.append(f"streaming = {streaming}\n")
            continue
        out.append(line)
    if found_section and section == engine and not replaced_model:
        out.append(f'model = "{model}"\n')
    elif not found_section:
        out.extend([f"\n[{engine}]\n", f'model = "{model}"\n'])
    cfg = "".join(out)
    with open(CFG, "w") as f:
        f.write(cfg)


def main():
    cur = current()
    labels = []
    available_models = [entry for entry in MODELS if installed(entry[2])]
    for engine, model, _, label in available_models:
        mark = "✓ " if (engine, model) == cur else ""
        labels.append(mark + label)

    sel = subprocess.run(
        [
            "fuzzel",
            "--config",
            os.path.expanduser("~/.config/fuzzel/top-bar-menu.ini"),
            "--dmenu",
            "--width",
            "40",
            "--anchor",
            "top-right",
            "--x-margin",
            "380",
            "--y-margin",
            "36",
        ],
        input="\n".join(labels),
        capture_output=True,
        text=True,
    )
    if sel.returncode != 0:
        return

    choice = sel.stdout.strip().lstrip("✓ ")
    for engine, model, _, label in available_models:
        if choice == label and (engine, model) != cur:
            apply(engine, model)
            subprocess.run(["systemctl", "--user", "restart", "voxtype.service"])
            return


if __name__ == "__main__":
    main()
