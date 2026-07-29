# Interactive zsh for Axon workspace PTY sessions (local shell, not agent mirror).
export STARSHIP_DISABLED=1
export EDITOR="${EDITOR:-nano}"
export PAGER="${PAGER:-less}"
export LESS="${LESS:--R}"
export HISTFILE="${HISTFILE:-$PWD/.axon_terminal_history}"
export SAVEHIST=10000
export HISTSIZE=10000

# xterm.js-friendly: avoid startup "%" marks and CR prompt glitches.
setopt no_prompt_cr
unsetopt prompt_sp
PROMPT_EOL_MARK=''

setopt APPEND_HISTORY INC_APPEND_HISTORY SHARE_HISTORY HIST_IGNORE_DUPS
setopt HIST_IGNORE_SPACE HIST_REDUCE_BLANKS HIST_VERIFY
setopt INTERACTIVE_COMMENTS AUTO_CD AUTO_PUSHD PUSHD_IGNORE_DUPS
setopt NO_BEEP EXTENDED_GLOB

# Completion dump lives with workspace history (ZDOTDIR is read-only package path).
export ZSH_COMPDUMP="${HISTFILE%/*}/.axon_zcompdump"
autoload -Uz compinit
if ! compinit -d "$ZSH_COMPDUMP" -C 2>/dev/null; then
  compinit -d "$ZSH_COMPDUMP" -i
fi
zstyle ':completion:*' menu select
zstyle ':completion:*' matcher-list 'm:{a-z}={A-Z}'
zstyle ':completion:*' list-colors "${(s.:.)LS_COLORS}"

# Emacs-style editing + word navigation that works in xterm.js.
bindkey -e
autoload -Uz up-line-or-beginning-search down-line-or-beginning-search
zle -N up-line-or-beginning-search
zle -N down-line-or-beginning-search
bindkey '^[[A' up-line-or-beginning-search
bindkey '^[[B' down-line-or-beginning-search
bindkey '^[[H' beginning-of-line
bindkey '^[[F' end-of-line
bindkey '^[[1;5C' forward-word
bindkey '^[[1;5D' backward-word
bindkey '^[[3~' delete-char
# Ctrl+R incremental history (true shell feel).
autoload -Uz history-incremental-search-backward
bindkey '^R' history-incremental-search-backward

# Colors for ls/grep when available.
if command -v dircolors >/dev/null 2>&1; then
  eval "$(dircolors -b 2>/dev/null)" || true
fi
alias ls='ls --color=auto'
alias ll='ls -lah --color=auto'
alias la='ls -A --color=auto'
alias grep='grep --color=auto'
alias eg='grep --color=auto'

# Git branch (+ dirty marker) in the prompt.
autoload -Uz vcs_info
precmd() {
  vcs_info
  print -Pn "\e]0;%n@%m: %~\a"
}
zstyle ':vcs_info:*' enable git
zstyle ':vcs_info:*' check-for-changes true
zstyle ':vcs_info:git:*' formats ' %F{yellow}git:(%b)%f%F{red}%u%c%f'
zstyle ':vcs_info:git:*' actionformats ' %F{yellow}git:(%b|%a)%f%F{red}%u%c%f'
zstyle ':vcs_info:*' unstagedstr '*'
zstyle ':vcs_info:*' stagedstr '+'
setopt prompt_subst
export PROMPT=$'%F{cyan}%n@%m%f:%F{green}%~%f${vcs_info_msg_0_} %# '
export RPROMPT=''
