#!/usr/bin/env bash

choice="$(printf "Lock\nSuspend\nLog out\nReboot\nShutdown" | fuzzel --config ~/.config/fuzzel/top-bar-menu.ini --dmenu --width 15 --anchor top-right --prompt 'Power: ')"

case "$choice" in
  "Lock") swaylock -f -c 1f1f1f ;;
  "Suspend") systemctl suspend ;;
  "Log out") niri msg action quit ;;
  "Reboot") systemctl reboot ;;
  "Shutdown") systemctl poweroff ;;
esac
