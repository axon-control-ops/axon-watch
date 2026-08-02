#!/usr/bin/env bash
# Finish interrupted nvidia-driver configure (iU) + initramfs. Root required.
set -uo pipefail

if [[ ${EUID:-$(id -u)} -ne 0 ]]; then
  exec pkexec env \
    DISPLAY="${DISPLAY:-}" \
    WAYLAND_DISPLAY="${WAYLAND_DISPLAY:-}" \
    XAUTHORITY="${XAUTHORITY:-}" \
    DEBIAN_FRONTEND=noninteractive \
    "$0" "$@"
fi

export DEBIAN_FRONTEND=noninteractive
# Keep DKMS light — this host freezes under GPU+IO load.
export MAKEFLAGS='-j1'
export DKMS_PARALLEL=1

log() { printf '[finish-nvidia] %s\n' "$*"; }

log "start $(date -Is)"
log "kernel $(uname -r)"
test -f /etc/modprobe.d/blacklist-nouveau.conf || {
  cat >/etc/modprobe.d/blacklist-nouveau.conf <<'EOF'
blacklist nouveau
options nouveau modeset=0
EOF
}
cat /etc/modprobe.d/blacklist-nouveau.conf

log "dpkg --configure -a"
if ! dpkg --configure -a; then
  log "dpkg --configure failed; trying apt-get -f install"
  apt-get -f install -y || true
  dpkg --configure -a || true
fi

log "ensure packages present"
apt-get install -y --no-install-recommends \
  nvidia-driver nvidia-driver-libs nvidia-kernel-dkms nvidia-driver-bin || true

log "initramfs"
update-initramfs -u || true

log "results"
dpkg -l 'nvidia-driver' 'nvidia-kernel-dkms' 'nvidia-driver-bin' 'libnvidia-ml1' | awk '/^ii|^iU|^hi/{print}' || true
dkms status || true
command -v nvidia-smi || ls -l /usr/bin/nvidia-smi || true
modinfo nvidia 2>/dev/null | head -5 || log "nvidia module not built yet"
log "DONE $(date -Is) — reboot required"
