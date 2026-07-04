# Minimal interactive zsh for Axon workspace PTY sessions.
export STARSHIP_DISABLED=1
# ANSI prompt (matches bash rc); avoids zsh %F{} width glitches in xterm.js.
export PROMPT=$'\033[36m%n@%m\033[0m:\033[32m%~\033[0m$ '
export HISTFILE="${HISTFILE:-$PWD/.axon_terminal_history}"
export SAVEHIST=5000
export HISTSIZE=5000
# Prevent zsh startup "%" line-clear from corrupting web terminal display.
setopt no_prompt_cr
unsetopt prompt_sp
PROMPT_EOL_MARK=''
setopt APPEND_HISTORY INC_APPEND_HISTORY SHARE_HISTORY HIST_IGNORE_DUPS
autoload -Uz up-line-or-history down-line-or-history
bindkey '^[[A' up-line-or-history
bindkey '^[[B' down-line-or-history
