#!/usr/bin/env bash

ps -eo comm=,rss= \
| awk '
{
  mem[$1] += $2
}
END {
  for (p in mem)
    printf "%-20s %8.1f MiB\n", p, mem[p] / 1024
}' \
| sort -k2 -nr \
| head -n 8 \
| fuzzel --config ~/.config/fuzzel/top-bar-menu.ini --dmenu --width 45 --anchor top-right --prompt "Top RAM: " >/dev/null
