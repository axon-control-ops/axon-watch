"""Tunnel package exports."""

from app.tunnel.tunnel_control import (
    TunnelControlError,
    attempt_tunnel_autostart,
    tunnel_autostart_enabled,
    tunnel_start,
    tunnel_status,
    tunnel_stop,
)
from app.tunnel.tunnel_probe import (
    build_tunnel_diagnostics,
    probe_cloudflare_tunnel,
    probe_local_origin,
)
from app.tunnel.cloudflared_installer import (
    CloudflaredInstallError,
    install_cloudflared,
    installer_diagnostics,
)
from app.tunnel.tunnel_supervisor import (
    TunnelSupervisor,
    get_tunnel_supervisor,
    start_tunnel_supervisor,
    tunnel_supervisor_health,
)

__all__ = [
    "TunnelControlError",
    "attempt_tunnel_autostart",
    "CloudflaredInstallError",
    "TunnelSupervisor",
    "build_tunnel_diagnostics",
    "get_tunnel_supervisor",
    "install_cloudflared",
    "installer_diagnostics",
    "probe_local_origin",
    "start_tunnel_supervisor",
    "tunnel_supervisor_health",
    "probe_cloudflare_tunnel",
    "tunnel_autostart_enabled",
    "tunnel_start",
    "tunnel_status",
    "tunnel_stop",
]
