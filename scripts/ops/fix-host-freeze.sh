#!/usr/bin/env bash
# Host freeze remediation for edudashpro (nouveau GPU hang + disk pressure).
# Requires root. Prefer: pkexec "$0"   or: sudo "$0"
set -euo pipefail

if [[ ${EUID:-$(id -u)} -ne 0 ]]; then
  echo "Re-running with pkexec for root privileges..."
  exec pkexec env DISPLAY="${DISPLAY:-}" WAYLAND_DISPLAY="${WAYLAND_DISPLAY:-}" XAUTHORITY="${XAUTHORITY:-}" "$0" "$@"
fi

log() { printf '[fix-host-freeze] %s\n' "$*"; }

log "1/5 vacuum journal + apt caches"
journalctl --vacuum-size=400M || true
apt-get clean || true
if command -v apt >/dev/null; then
  apt-get -y autoremove --purge || true
fi

log "2/5 stop cups snap crash-loop (optional; harmless if unused)"
systemctl stop snap.cups.cups-browsed.service snap.cups.cupsd.service 2>/dev/null || true
systemctl mask snap.cups.cups-browsed.service snap.cups.cupsd.service 2>/dev/null || true

log "3/5 blacklist nouveau"
cat >/etc/modprobe.d/blacklist-nouveau.conf <<'EOF'
# Written by axon-watch scripts/ops/fix-host-freeze.sh
# Nouveau DATA_ERROR floods from Chrome/WebGL were freezing this host.
blacklist nouveau
options nouveau modeset=0
EOF

log "4/5 install proprietary NVIDIA driver"
export DEBIAN_FRONTEND=noninteractive
apt-get update
# Kali/Debian metapackage pulls matching kernel module
apt-get install -y nvidia-driver nvidia-driver-libs || apt-get install -y nvidia-driver

log "5/5 refresh initramfs so nouveau stays out after reboot"
if command -v update-initramfs >/dev/null; then
  update-initramfs -u
fi

log "DONE. Reboot required for the NVIDIA module to load."
log "After reboot verify: nvidia-smi && lsmod | grep -E 'nvidia|nouveau'"
df -h /
