#!/usr/bin/env bash
# Symlink repo bin/ one-word commands into ~/.local/bin
# (axonhealth, axonrestart, axonrevive, axonfixconnectors).
set -euo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
bin_dst="${HOME}/.local/bin"
mkdir -p "${bin_dst}"

for name in axonhealth axonrestart axonrevive axonfixconnectors; do
  src="${repo_root}/bin/${name}"
  dst="${bin_dst}/${name}"
  if [[ ! -x "${src}" ]]; then
    echo "ERROR: missing executable ${src}" >&2
    exit 1
  fi
  ln -sf "${src}" "${dst}"
  echo "Linked ${dst} -> ${src}"
done

echo "One-word stack commands are on PATH: axonhealth, axonrestart, axonrevive, axonfixconnectors"
