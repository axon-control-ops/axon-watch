#!/usr/bin/env bash
# Host freeze remediation: leave nouveau, install proprietary NVIDIA, free system caches.
# Requires root. Prefer: pkexec "$0"   or: sudo "$0"
set -euo pipefail

if [[ ${EUID:-$(id -u)} -ne 0 ]]; then
  echo "Re-running with pkexec for root privileges..."
  exec pkexec env \
    DISPLAY="${DISPLAY:-}" \
    WAYLAND_DISPLAY="${WAYLAND_DISPLAY:-}" \
    XAUTHORITY="${XAUTHORITY:-}" \
    DEBIAN_FRONTEND=noninteractive \
    "$0" "$@"
fi

export DEBIAN_FRONTEND=noninteractive
log() { printf '[fix-host-freeze] %s\n' "$*"; }

log "1/5 vacuum journal + apt package cache only (no autoremove)"
journalctl --vacuum-size=400M || true
apt-get clean || true

log "2/5 mask cups snap crash-loop"
systemctl stop snap.cups.cups-browsed.service snap.cups.cupsd.service 2>/dev/null || true
systemctl mask snap.cups.cups-browsed.service snap.cups.cupsd.service 2>/dev/null || true

log "3/5 blacklist nouveau before driver install"
cat >/etc/modprobe.d/blacklist-nouveau.conf <<'EOF'
# Written by axon-watch scripts/ops/fix-host-freeze.sh
# Nouveau DATA_ERROR floods from Chrome/WebGL were freezing this host.
blacklist nouveau
options nouveau modeset=0
EOF

log "4/5 repair interrupted dpkg, then install NVIDIA driver (no mass upgrades)"
# Previous freeze interrupted apt mid-configure.
dpkg --configure -a || true
apt-get -f install -y || true
apt-get update
# Install only the driver stack — do not apt upgrade the world mid-freeze recovery.
apt-get install -y --no-install-recommends nvidia-driver nvidia-driver-libs || \
  apt-get install -y --no-install-recommends nvidia-driver

log "5/5 refresh initramfs"
if command -v update-initramfs >/dev/null; then
  update-initramfs -u
fi

log "DONE. Reboot required."
log "After reboot: nvidia-smi && lsmod | grep -E 'nvidia|nouveau'"
df -h /
ls -l /etc/modprobe.d/blacklist-nouveau.conf
dpkg -l 'nvidia-driver*' 2>/dev/null | awk '/^ii/{print}'
