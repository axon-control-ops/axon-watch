#!/usr/bin/env bash
# Ensure legacy axon-local :7734 does not auto-start on login.
# Axon-X operator surface is :4173 (console-web + control-plane + watch).
set -euo pipefail

autostart_dir="${HOME}/.config/autostart"
mkdir -p "${autostart_dir}"

disabled_desktop="${autostart_dir}/axon-server-autostart.desktop"
cat >"${disabled_desktop}" <<'EOF'
[Desktop Entry]
Version=1.0
Name=Axon Server Autostart
Comment=Disabled — Axon-X :4173 is the operator surface (not legacy :7734)
Exec=/bin/true
Terminal=false
Type=Application
NoDisplay=true
X-GNOME-Autostart-enabled=false
EOF
chmod 600 "${disabled_desktop}"
echo "Wrote disabled autostart: ${disabled_desktop}"

# Mask common leftover unit names if present (ignore missing).
systemctl --user disable --now axon-server.service 2>/dev/null || true
systemctl --user mask axon-server.service 2>/dev/null || true

# Stop a live :7734 listener if one is up (does not uninstall axon-local).
pids="$(ss -ltnp 'sport = :7734' 2>/dev/null | rg -o 'pid=[0-9]+' | cut -d= -f2 | sort -u || true)"
for pid in ${pids}; do
  echo "Stopping legacy :7734 pid ${pid}"
  kill -TERM "${pid}" 2>/dev/null || true
done

echo "Legacy :7734 autostart disabled. Prefer: http://127.0.0.1:4173"
echo "Manual fallback still available via axon-local ./start.sh --no-open when needed."
