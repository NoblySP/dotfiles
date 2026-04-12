# dotfiles
 
## Restore on a new machine
 
```bash
# Clone just the git internals, no files yet
git clone --bare git@github.com:NoblySP/dotfiles.git $HOME/.dotfiles
 
# Set up the alias for this session
alias dots='git --git-dir=$HOME/.dotfiles/ --work-tree=$HOME'
 
# Write all tracked files out to ~
dots checkout
 
# Writes the setting into ~/.dotfiles/config on this machine, since this is not stored in a commit
dots config --local status.showUntrackedFiles no
```
 
Add the alias to `~/.config/fish/config.fish` to make it permanent.
 
## Day-to-day
 
```bash
dots status
dots add ~/.config/niri/config.kdl
dots commit -m "update niri config"
dots push
```
