function open
    for i in $argv
        command xdg-open $i >/dev/null 2>&1 & disown
    end
end
