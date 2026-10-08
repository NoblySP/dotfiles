#!/bin/sh
# Restart waybar shortly after the system wakes from suspend, so the bar
# doesn't race niri's output re-initialization (and to recover from any
# battery-module crash that happened during sleep).
gdbus monitor --system --dest org.freedesktop.login1 \
  --object-path /org/freedesktop/login1 |
while IFS= read -r line; do
  case "$line" in
    *"PrepareForSleep (false"*)
      sleep 3
      systemctl --user restart waybar
      ;;
  esac
done
