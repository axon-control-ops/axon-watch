#!/usr/bin/env bash
set -euo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
source "${repo_root}/scripts/dev/lib/common.sh"
cd "${repo_root}"

python_bin="$(resolve_python)"
venv_root="${repo_root}/.venv"
stamp_dir="${repo_root}/scripts/.cache/python-bootstrap"
stamp_path="${stamp_dir}/requirements.sha256"
legacy_stamp_dir="${repo_root}/output/python-bootstrap"
legacy_stamp_path="${legacy_stamp_dir}/requirements.sha256"
requirements_path="${repo_root}/requirements.txt"

if [[ ! -x "${venv_root}/bin/python3" ]]; then
  echo "Creating Axon-Watch Python venv at ${venv_root}"
  python3 -m venv "${venv_root}"
  python_bin="${venv_root}/bin/python3"
fi

mkdir -p "${stamp_dir}"

# Keep the bootstrap hash out of output/ so worker delivery does not classify
# the runtime stamp as private-company material.
if [[ -f "${legacy_stamp_path}" ]] && [[ ! -f "${stamp_path}" ]]; then
  mkdir -p "${stamp_dir}"
  mv "${legacy_stamp_path}" "${stamp_path}"
fi
if [[ -d "${legacy_stamp_dir}" ]]; then
  rmdir "${legacy_stamp_dir}" 2>/dev/null || true
fi

"${python_bin}" "${repo_root}/scripts/verify/check_python_bootstrap_stamp.py"

read -r requirements_hash _ < <(sha256sum "${requirements_path}")
watch_service_dist="$(find "${venv_root}/lib" -path '*/site-packages/__editable__.axon_watch_service-0.1.0.pth' -print -quit 2>/dev/null || true)"
control_plane_dist="$(find "${venv_root}/lib" -path '*/site-packages/__editable__.axon_watch_control_plane-0.1.0.pth' -print -quit 2>/dev/null || true)"
installed_editables_ready=0
if [[ -f "${watch_service_dist}" ]] && [[ -f "${control_plane_dist}" ]]; then
  installed_editables_ready=1
fi

if [[ "${installed_editables_ready}" -eq 1 ]] && [[ ! -f "${stamp_path}" ]]; then
  printf '%s\n' "${requirements_hash}" > "${stamp_path}"
fi

if [[ -f "${stamp_path}" ]] && [[ "$(cat "${stamp_path}")" == "${requirements_hash}" ]] && [[ "${installed_editables_ready}" -eq 1 ]]; then
  exit 0
fi

"${python_bin}" -m pip install -q -U pip wheel
"${python_bin}" -m pip install -q -r "${requirements_path}"
printf '%s\n' "${requirements_hash}" > "${stamp_path}"
