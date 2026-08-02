#!/usr/bin/env bash
# Mitigate IO freezes: shrink journal writes, clean corrupt journals, lighten disk load.
# Root required. Prefer: sudo -A "$0"  or  pkexec "$0"
set -euo pipefail

if [[ ${EUID:-$(id -u)} -ne 0 ]]; then
  ASK="${SUDO_ASKPASS:-}"
  if [[ -n "$ASK" && -x "$ASK" ]]; then
    exec sudo -A -E "$0" "$@"
  fi
  exec pkexec env DISPLAY="${DISPLAY:-}" WAYLAND_DISPLAY="${WAYLAND_DISPLAY:-}" \
    XAUTHORITY="${XAUTHORITY:-}" DEBIAN_FRONTEND=noninteractive "$0" "$@"
fi

log() { printf '[fix-host-io] %s\n' "$*"; }

log "1/5 journald caps (persistent journal was failing with EIO under IO storm)"
mkdir -p /etc/systemd/journald.conf.d
cat >/etc/systemd/journald.conf.d/99-axon-io.conf <<'EOF'
[Journal]
# Keep enough for debugging freezes, but stop multi-GB journal write storms.
SystemMaxUse=200M
SystemKeepFree=2G
RuntimeMaxUse=80M
MaxFileSec=1day
Compress=yes
EOF
# Remove torn journals from hard shutdowns (safe; active files recreated)
find /var/log/journal -type f -name '*~' -delete 2>/dev/null || true
journalctl --vacuum-size=150M || true
systemctl restart systemd-journald || true

log "2/5 drop pagecache pressure helpers — raise dirty writeback aggressiveness slightly"
# Flush dirty pages sooner so a 26G Cursor DB sync cannot stall the whole machine.
sysctl -w vm.dirty_ratio=10
sysctl -w vm.dirty_background_ratio=3
sysctl -w vm.dirty_expire_centisecs=1500
sysctl -w vm.dirty_writeback_centisecs=500
# Persist
mkdir -p /etc/sysctl.d
cat >/etc/sysctl.d/99-axon-io.conf <<'EOF'
vm.dirty_ratio = 10
vm.dirty_background_ratio = 3
vm.dirty_expire_centisecs = 1500
vm.dirty_writeback_centisecs = 500
EOF

log "3/5 NVMe thermal check (Critical Comp. Temperature Time was elevated)"
if command -v smartctl >/dev/null; then
  smartctl -a /dev/nvme0 | rg -i 'Temperature|Critical|Warning|Percentage Used|Unsafe|Available Spare|SMART overall' || true
fi

log "4/5 mask heavy optional services if present"
# cups already masked earlier; keep journal quiet
systemctl stop snap.cups.cupsd.service snap.cups.cups-browsed.service 2>/dev/null || true

log "5/5 done"
df -h /
journalctl --disk-usage || true
log "NEXT: compact Cursor state.vscdb (26G) with Cursor fully quit, then reboot once for clean FS."
