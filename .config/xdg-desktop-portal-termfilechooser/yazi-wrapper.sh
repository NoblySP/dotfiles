#!/usr/bin/env sh
set -e
multiple="$1"
directory="$2"
save="$3"
path="$4"
out="$5"

# Set up arguments for Yazi's internal chooser flag
if [ "$save" = "1" ]; then
    set -- --chooser-file="$out" "$path"
elif [ "$directory" = "1" ]; then
    set -- --chooser-file="$out" "$path"
else
    set -- --chooser-file="$out" "$path"
fi

# Execute Foot using its app-id argument to isolate the window
foot --app-id=file_chooser yazi "$@"
