# Minimal interactive bash for Axon workspace PTY sessions.
export STARSHIP_DISABLED=1
export PS1='\[\033[36m\]\u@\h\[\033[0m\]:\[\033[32m\]\W\[\033[0m\]\$ '
export HISTFILE="${HISTFILE:-$PWD/.axon_terminal_history}"
export HISTSIZE=5000
export HISTFILESIZE=5000
export HISTCONTROL=ignoreboth:erasedups
shopt -s histappend
