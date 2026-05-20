#!/usr/bin/env bash
selected=$(cliphist list | fuzzel --dmenu)
[ -z "$selected" ] && exit 0
printf '%s' "$selected" | cliphist decode | wl-copy
sleep 0.1
wtype -M ctrl -k v -m ctrl
