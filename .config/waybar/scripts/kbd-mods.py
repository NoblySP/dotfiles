#!/usr/bin/env python3
"""Waybar module: crkbd modifier and layer indicator.

Modifiers (Shift, Ctrl, Alt, Super) are detected via evdev active_keys().

Layer changes are detected via a firmware push: layer_state_set_user() in the
Vial QMK firmware calls raw_hid_send() with command byte 0xA0 and the new
layer number every time the layer state changes.  The via_layer_monitor thread
does a blocking read on the Vial raw HID device (/dev/hidraw*) and updates a
shared variable instantly — no polling, no tapping-term wait.
"""

import json
import os
import re
import sys
import threading
import time
from pathlib import Path

import evdev
from evdev import ecodes

# ── device ────────────────────────────────────────────────────────────────────
DEVICE_NAME  = "foostan Corne v4"
CORNE_HID_ID = "00004653:00000004"
POLL_HZ      = 50

# ── firmware push protocol ────────────────────────────────────────────────────
LAYER_STATUS_CMD = 0xA0   # must match #define in keymap.c
MSG_LEN          = 32

# ── modifier labels ───────────────────────────────────────────────────────────
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

# evdev keys used to infer layer when VIA push is unavailable (fallback)
L2_KEYS = frozenset({
    ecodes.KEY_LEFT, ecodes.KEY_RIGHT,
    ecodes.KEY_UP,   ecodes.KEY_DOWN,
    ecodes.KEY_HOME, ecodes.KEY_END,
})
L3_KEYS = frozenset({
    ecodes.KEY_1, ecodes.KEY_2, ecodes.KEY_3,
    ecodes.KEY_4, ecodes.KEY_5, ecodes.KEY_6,
    ecodes.KEY_7, ecodes.KEY_8, ecodes.KEY_9,
    ecodes.KEY_0,
})
SHIFT_KEYS = frozenset({ecodes.KEY_LEFTSHIFT, ecodes.KEY_RIGHTSHIFT})

# ── Catppuccin Mocha colours ──────────────────────────────────────────────────
COLORS = {
    "Sft":  "#89dceb",
    "Ctl":  "#f38ba8",
    "Alt":  "#a6e3a1",
    "Sup":  "#cba6f7",
    "L2":   "#f9e2af",
    "L3":   "#fab387",
    "L4":   "#94e2d5",
    "idle": "#45475a",
}

# ── shared layer state (written by monitor thread, read by main loop) ─────────
_via_layer = 0
_via_lock  = threading.Lock()


# ── helpers ───────────────────────────────────────────────────────────────────
def span(text: str, color: str, bold: bool = True) -> str:
    inner = f"<b>{text}</b>" if bold else text
    return f'<span foreground="{color}">{inner}</span>'


# ── Vial raw HID discovery ────────────────────────────────────────────────────
def find_via_hidraw() -> str | None:
    """Return the /dev/hidrawN path for the Corne's Vial raw HID interface."""
    try:
        for name in sorted(os.listdir("/sys/class/hidraw")):
            uevent_path = f"/sys/class/hidraw/{name}/device/uevent"
            try:
                uevent = Path(uevent_path).read_text()
                # input1 = VIA/Vial raw HID interface (not input0 = keyboard)
                if CORNE_HID_ID in uevent and re.search(r"/input1\b", uevent):
                    return f"/dev/{name}"
            except OSError:
                pass
    except OSError:
        pass
    return None


# ── layer push monitor thread ─────────────────────────────────────────────────
def via_layer_monitor() -> None:
    """Daemon thread: block-read the Vial HID device for layer-push events."""
    global _via_layer

    def open_device():
        path = find_via_hidraw()
        if not path:
            return None
        try:
            return open(path, "rb", buffering=0)
        except OSError:
            return None

    dev = open_device()

    while True:
        if dev is None:
            time.sleep(2)
            dev = open_device()
            continue

        try:
            data = dev.read(MSG_LEN)
        except OSError:
            try:
                dev.close()
            except OSError:
                pass
            dev = None
            continue

        if len(data) >= 2 and data[0] == LAYER_STATUS_CMD:
            with _via_lock:
                _via_layer = data[1]


# ── output builder ─────────────────────────────────────────────────────────────
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

    # Layer: firmware push is authoritative; evdev keys are the fallback
    with _via_lock:
        via = _via_layer

    has_nav     = bool(active & L2_KEYS)
    has_numbers = bool(active & L3_KEYS)
    has_shift   = bool(active & SHIFT_KEYS)

    on_l2 = via == 2 or has_nav
    on_l3 = via == 3 or (has_numbers and not has_shift)
    on_l4 = via == 4

    if on_l2:
        parts.append(span("L2", COLORS["L2"]))
        tooltip_parts.append("Layer 2 (Nav/Sym)")
        classes.append("layer2")
    elif on_l3:
        parts.append(span("L3", COLORS["L3"]))
        tooltip_parts.append("Layer 3 (Num)")
        classes.append("layer3")
    elif on_l4:
        parts.append(span("L4", COLORS["L4"]))
        tooltip_parts.append("Layer 4 (Mouse)")
        classes.append("layer4")

    if not parts:
        text = span("⌨", COLORS["idle"], bold=False)
        css  = "kbd-idle"
        tip  = "crkbd: idle"
    else:
        text = " ".join(parts)
        css  = " ".join(classes)
        tip  = "crkbd: " + " · ".join(tooltip_parts)

    return {"text": text, "class": css, "tooltip": tip}


# ── evdev device discovery ─────────────────────────────────────────────────────
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


# ── main loop ──────────────────────────────────────────────────────────────────
def main() -> None:
    devices = find_crkbd()

    if not devices:
        out = {
            "text":    span("⌨", COLORS["idle"], bold=False),
            "class":   "kbd-disconnected",
            "tooltip": "crkbd: not connected",
        }
        print(json.dumps(out), flush=True)
        while True:
            time.sleep(5)
            devices = find_crkbd()
            if devices:
                break
        main()
        return

    # Start Vial layer-push listener in background
    t = threading.Thread(target=via_layer_monitor, daemon=True)
    t.start()

    interval  = 1.0 / POLL_HZ
    last_json = ""

    while True:
        active: set[int] = set()
        alive:  list[evdev.InputDevice] = []
        for dev in devices:
            try:
                active.update(dev.active_keys())
                alive.append(dev)
            except OSError:
                pass

        if not alive:
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
