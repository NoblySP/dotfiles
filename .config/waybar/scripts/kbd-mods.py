#!/usr/bin/env python3
"""Waybar module: crkbd modifier and layer indicator.

Uses EVIOCGKEY polling (active_keys) to read the crkbd's current key state
directly from the kernel, bypassing any evdev grab by keyd.

Modifiers (Shift, Ctrl, Alt, Super) are detected immediately.
Layers are inferred from which keys are actively pressed:
  - L2 (nav/symbols): navigation keys appear only on Layer 2
  - L3 (numbers):     number keys only appear on Layer 3 on the crkbd
                      (the crkbd has no physical number row)
  - L4 (mouse):       mouse scroll/button events on Layer 4
"""

import json
import sys
import time

import evdev
from evdev import ecodes

DEVICE_NAME = "foostan Corne v4"
POLL_HZ = 50  # polls per second

# Modifier keycodes → display label
MOD_LABELS: dict[int, str] = {
    ecodes.KEY_LEFTSHIFT:  "Sft",
    ecodes.KEY_RIGHTSHIFT: "Sft",
    ecodes.KEY_LEFTCTRL:   "Ctl",
    ecodes.KEY_RIGHTCTRL:  "Ctl",
    ecodes.KEY_LEFTALT:    "Alt",
    ecodes.KEY_RIGHTALT:   "Alt",
    ecodes.KEY_LEFTMETA:   "Sup",
    ecodes.KEY_RIGHTMETA:  "Sup",
}

# Layer 2 (nav/symbols) indicator keys — never present in crkbd base layers
L2_KEYS = frozenset({
    ecodes.KEY_LEFT, ecodes.KEY_RIGHT,
    ecodes.KEY_UP, ecodes.KEY_DOWN,
    ecodes.KEY_HOME, ecodes.KEY_END,
})

# Layer 3 (numbers) indicator keys — crkbd has no top number row, so digits
# only appear when Layer 3 is active
L3_KEYS = frozenset({
    ecodes.KEY_1, ecodes.KEY_2, ecodes.KEY_3,
    ecodes.KEY_4, ecodes.KEY_5, ecodes.KEY_6,
    ecodes.KEY_7, ecodes.KEY_8, ecodes.KEY_9,
    ecodes.KEY_0,
})

# Layer 4 (mouse) indicator — these are the scroll keycodes QMK sends
L4_KEYS = frozenset({
    ecodes.KEY_SCROLLLOCK,  # placeholder; QMK mouse layer sends BTN events
})

# Pango markup colors (Catppuccin Mocha palette)
COLORS = {
    "Sft":  "#89dceb",   # sky
    "Ctl":  "#f38ba8",   # red
    "Alt":  "#a6e3a1",   # green
    "Sup":  "#cba6f7",   # mauve
    "L2":   "#f9e2af",   # yellow
    "L3":   "#fab387",   # peach
    "L4":   "#94e2d5",   # teal
    "idle": "#45475a",   # surface2 (dim)
}

SHIFT_KEYS = frozenset({ecodes.KEY_LEFTSHIFT, ecodes.KEY_RIGHTSHIFT})


def span(text: str, color: str, bold: bool = True) -> str:
    inner = f"<b>{text}</b>" if bold else text
    return f'<span foreground="{color}">{inner}</span>'


def build_output(active: frozenset[int]) -> dict:
    parts: list[str] = []
    tooltip_parts: list[str] = []
    classes: list[str] = []

    # Modifiers — deduplicated, ordered
    seen: set[str] = set()
    for kc in (
        ecodes.KEY_LEFTSHIFT, ecodes.KEY_RIGHTSHIFT,
        ecodes.KEY_LEFTCTRL,  ecodes.KEY_RIGHTCTRL,
        ecodes.KEY_LEFTALT,   ecodes.KEY_RIGHTALT,
        ecodes.KEY_LEFTMETA,  ecodes.KEY_RIGHTMETA,
    ):
        if kc in active:
            label = MOD_LABELS[kc]
            if label not in seen:
                seen.add(label)
                parts.append(span(label, COLORS[label]))
                tooltip_parts.append(label)
                classes.append(f"mod-{label.lower()}")

    # Layer inference
    has_nav     = bool(active & L2_KEYS)
    has_numbers = bool(active & L3_KEYS)
    has_shift   = bool(active & SHIFT_KEYS)

    if has_nav:
        parts.append(span("L2", COLORS["L2"]))
        tooltip_parts.append("Layer 2 (Nav/Sym)")
        classes.append("layer2")
    elif has_numbers and not has_shift:
        # numbers + no shift = Layer 3; numbers + shift = Layer 2 LSFT(KC_n) symbols
        parts.append(span("L3", COLORS["L3"]))
        tooltip_parts.append("Layer 3 (Num)")
        classes.append("layer3")

    if not parts:
        text = span("⌨", COLORS["idle"], bold=False)
        css  = "kbd-idle"
        tip  = "crkbd: idle"
    else:
        text = " ".join(parts)
        css  = " ".join(classes)
        tip  = "crkbd: " + " · ".join(tooltip_parts)

    return {"text": text, "class": css, "tooltip": tip}


def find_crkbd() -> list[evdev.InputDevice]:
    devices: list[evdev.InputDevice] = []
    for path in evdev.list_devices():
        try:
            d = evdev.InputDevice(path)
            if DEVICE_NAME in d.name:
                devices.append(d)
        except OSError:
            pass
    return devices


def main() -> None:
    devices = find_crkbd()

    if not devices:
        out = {
            "text":    span("⌨", COLORS["idle"], bold=False),
            "class":   "kbd-disconnected",
            "tooltip": "crkbd: not connected",
        }
        print(json.dumps(out), flush=True)
        # Keep running so waybar doesn't spam restarts; re-check every 5s
        while True:
            time.sleep(5)
            devices = find_crkbd()
            if devices:
                break
        main()
        return

    interval = 1.0 / POLL_HZ
    last_json = ""

    while True:
        active: set[int] = set()
        alive: list[evdev.InputDevice] = []
        for dev in devices:
            try:
                active.update(dev.active_keys())
                alive.append(dev)
            except OSError:
                pass  # device disappeared; drop it

        if not alive:
            # All devices gone — restart detection
            main()
            return

        devices = alive
        out_str = json.dumps(build_output(frozenset(active)))
        if out_str != last_json:
            print(out_str, flush=True)
            last_json = out_str

        time.sleep(interval)


if __name__ == "__main__":
    main()
