if status is-interactive
    # Commands to run in interactive sessions can go here
end
abbr --add gs git status
abbr --add kvim vim -u ~/.vimrc-kernel
abbr --add chef "xdg-open /opt/CyberChef_v10.22.1/CyberChef_v10.22.1.html"
abbr --add e exit
abbr --add q exit

alias dots='git --git-dir=$HOME/.dotfiles/ --work-tree=$HOME'

set -gx EDITOR vimx

# Yazi shell wrapper
function y
    set tmp (mktemp -t "yazi-cwd.XXXXXX")
    command yazi $argv --cwd-file="$tmp"
    if read -z cwd < "$tmp"; and [ "$cwd" != "$PWD" ]; and test -d "$cwd"
        builtin cd -- "$cwd"
    end
    rm -f -- "$tmp"
end

# Initialize zoxide
zoxide init fish --cmd cd | source

# Initialize fzf
fzf --fish | source
