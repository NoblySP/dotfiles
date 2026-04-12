#!/usr/bin/env bash
#
# Shows open windows in fuzzel dmenu. Format: "App Name | Window Title"
# Selecting a window focuses it without warping cursor.
# Keybind: Mod+Shift+Space

TMPFILE=$(mktemp /tmp/niri-picker.XXXXXX)
trap 'rm -f "$TMPFILE"' EXIT

niri msg -j windows 2>/dev/null | python3 -c "
import json, sys

def clean_name(app_id):
    '''org.mozilla.firefox -> Firefox, foot -> Foot'''
    if not app_id:
        return '?'
    name = app_id.split('.')[-1]       # last segment of reverse-DNS
    return name[0].upper() + name[1:]  # capitalize first letter

windows = json.load(sys.stdin)
for w in windows:
    app_id = w.get('app_id') or ''
    title  = (w.get('title') or '(no title)').replace('\x01', '')
    name   = clean_name(app_id).replace('\x01', '')
    wid    = w['id']
    # Display: 'App Name | Window Title'
    # \x01 (SOH) is the invisible separator before the window ID — fuzzel never sees it
    display = f'{name} | {title}'
    print(f'{display}\x01{wid}')
" > "$TMPFILE"

[[ ! -s "$TMPFILE" ]] && exit 0

SELECTION=$(cut -d$'\x01' -f1 "$TMPFILE" | fuzzel --dmenu --prompt=' window: ')
[[ -z "$SELECTION" ]] && exit 0

WINDOW_ID=$(grep -F "${SELECTION}"$'\x01' "$TMPFILE" | head -1 | cut -d$'\x01' -f2)
[[ -z "$WINDOW_ID" ]] && exit 0

niri msg action focus-window --id "$WINDOW_ID"
