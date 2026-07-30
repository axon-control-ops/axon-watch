# Interactive bash for Axon workspace PTY sessions (local shell parity with zsh).
export STARSHIP_DISABLED=1
export EDITOR="${EDITOR:-nano}"
export PAGER="${PAGER:-less}"
export LESS="${LESS:--R}"
export HISTFILE="${HISTFILE:-$PWD/.axon_terminal_history}"
export HISTSIZE=10000
export HISTFILESIZE=10000
export HISTCONTROL=ignoreboth:erasedups
shopt -s histappend checkwinsize cmdhist 2>/dev/null || true

if command -v dircolors >/dev/null 2>&1; then
  eval "$(dircolors -b 2>/dev/null)" || true
fi
alias ls='ls --color=auto'
alias ll='ls -lah --color=auto'
alias la='ls -A --color=auto'
alias grep='grep --color=auto'

__axon_git_branch() {
  local branch dirty=''
  branch="$(git rev-parse --abbrev-ref HEAD 2>/dev/null)" || return 0
  if ! git diff --quiet --ignore-submodules -- 2>/dev/null \
    || ! git diff --cached --quiet --ignore-submodules -- 2>/dev/null; then
    dirty='*'
  fi
  printf ' git:(%s)%s' "$branch" "$dirty"
}

__axon_set_title() {
  printf '\033]0;%s@%s: %s\007' "$USER" "${HOSTNAME%%.*}" "${PWD/#$HOME/~}"
}
PROMPT_COMMAND='__axon_set_title'

export PS1='\[\033[36m\]\u@\h\[\033[0m\]:\[\033[32m\]\w\[\033[0m\]\[\033[33m\]$(__axon_git_branch)\[\033[0m\]\$ '

# Basic programmable completion when available.
if [[ -f /usr/share/bash-completion/bash_completion ]]; then
  # shellcheck disable=SC1091
  . /usr/share/bash-completion/bash_completion
elif [[ -f /etc/bash_completion ]]; then
  # shellcheck disable=SC1091
  . /etc/bash_completion
fi
