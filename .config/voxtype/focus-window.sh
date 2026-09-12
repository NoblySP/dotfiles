#!/usr/bin/env bash
# Keep Voxtype output tied to the window that was focused when recording began.
#
# Wayland sends virtual-keyboard input to the currently focused surface.  These
# three hook actions remember the original Niri window, focus it for Voxtype's
# output, and then return focus to the window used while transcription ran.

set -u

runtime_base=${XDG_RUNTIME_DIR:-/run/user/$(id -u)}
state_dir="$runtime_base/voxtype"
target_file="$state_dir/focus-target"
return_file="$state_dir/focus-return"

mkdir -p "$state_dir"

focused_window_id() {
    local response
    response=$(niri msg --json focused-window 2>/dev/null) || return 1
    jq -er '.id // .Ok.FocusedWindow.id // empty' <<<"$response" 2>/dev/null
}

read_window_id() {
    local file=$1 value
    [[ -r "$file" ]] || return 1
    IFS= read -r value < "$file" || return 1
    [[ "$value" =~ ^[0-9]+$ ]] || return 1
    printf '%s\n' "$value"
}

case "${1:-}" in
    save)
        # Clear a return target left by an interrupted/cancelled dictation.
        : > "$return_file"
        if window_id=$(focused_window_id); then
            printf '%s\n' "$window_id" > "$target_file"
        else
            : > "$target_file"
        fi
        ;;

    focus)
        target_id=$(read_window_id "$target_file") || exit 0
        current_id=$(focused_window_id) || exit 0

        if [[ "$current_id" != "$target_id" ]]; then
            printf '%s\n' "$current_id" > "$return_file"
            niri msg action focus-window --id "$target_id" >/dev/null 2>&1 || :
        else
            : > "$return_file"
        fi
        ;;

    restore)
        if return_id=$(read_window_id "$return_file"); then
            niri msg action focus-window --id "$return_id" >/dev/null 2>&1 || :
        fi
        : > "$return_file"
        : > "$target_file"
        ;;

    *)
        printf 'Usage: %s {save|focus|restore}\n' "$0" >&2
        exit 2
        ;;
esac
