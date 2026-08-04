"""Machine CEO host pulse — Linux /proc inventory (no psutil dependency)."""

from __future__ import annotations

import os
import re
from pathlib import Path
from typing import Any

from app.host_context.models import utc_now_iso

# Never auto-target these name fragments (case-insensitive).
_PROTECTED_NAME_RE = re.compile(
    r"("
    r"axon|control-plane|uvicorn|cursor|code$|code-|"
    r"systemd|Xorg|wayland|pipewire|pulseaudio|dbus|"
    r"ssh|login|gdm|sddm|gnome-shell|kwin|plasmashell|"
    r"dockerd|containerd|kube|postgres|mysql|redis|"
    r"python3?$"  # bare interpreter — too ambiguous to auto-kill
    r")",
    re.I,
)

# Safe auto-kill candidates when VAXON AUTO is on (high RSS + match).
_JUNK_ALLOWLIST_RE = re.compile(
    r"("
    r"chrome_crashpad|crashpad_handler|"
    r"Code Helper \(Plugin\)|Code Helper \(Renderer\)|"
    r"firefox-bin.*RDD|Web Content$"
    r")",
    re.I,
)

_AUTO_KILL_RSS_MB = 900
_TOP_N = 12


def _read_text(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return ""


def _meminfo() -> dict[str, float | None]:
    raw = _read_text(Path("/proc/meminfo"))
    total_kb = available_kb = None
    for line in raw.splitlines():
        if line.startswith("MemTotal:"):
            total_kb = float(line.split()[1])
        elif line.startswith("MemAvailable:"):
            available_kb = float(line.split()[1])
    if not total_kb:
        return {"memory_percent": None, "memory_total_mb": None, "memory_available_mb": None}
    used_kb = total_kb - (available_kb or 0.0)
    return {
        "memory_percent": round(100.0 * used_kb / total_kb, 1),
        "memory_total_mb": round(total_kb / 1024.0, 1),
        "memory_available_mb": round((available_kb or 0.0) / 1024.0, 1),
    }


def _loadavg() -> dict[str, float | None]:
    raw = _read_text(Path("/proc/loadavg")).strip().split()
    if len(raw) < 3:
        return {"load_1": None, "load_5": None, "load_15": None}
    try:
        return {
            "load_1": float(raw[0]),
            "load_5": float(raw[1]),
            "load_15": float(raw[2]),
        }
    except ValueError:
        return {"load_1": None, "load_5": None, "load_15": None}


def _proc_rss_mb(pid: int) -> float | None:
    status = _read_text(Path(f"/proc/{pid}/status"))
    for line in status.splitlines():
        if line.startswith("VmRSS:"):
            try:
                return round(float(line.split()[1]) / 1024.0, 1)
            except (IndexError, ValueError):
                return None
    return None


def _proc_name(pid: int) -> str:
    comm = _read_text(Path(f"/proc/{pid}/comm")).strip()
    if comm:
        return comm
    cmdline = _read_text(Path(f"/proc/{pid}/cmdline")).replace("\x00", " ").strip()
    if not cmdline:
        return ""
    return Path(cmdline.split()[0]).name


def _proc_cmdline(pid: int) -> str:
    return _read_text(Path(f"/proc/{pid}/cmdline")).replace("\x00", " ").strip()[:240]


def _is_protected(name: str, cmdline: str, pid: int) -> bool:
    if pid in {1, os.getpid(), os.getppid()}:
        return True
    hay = f"{name} {cmdline}"
    return bool(_PROTECTED_NAME_RE.search(hay))


def _is_junk_candidate(name: str, cmdline: str) -> bool:
    hay = f"{name} {cmdline}"
    return bool(_JUNK_ALLOWLIST_RE.search(hay))


def list_top_processes(*, limit: int = _TOP_N) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    proc_root = Path("/proc")
    if not proc_root.is_dir():
        return rows
    for entry in proc_root.iterdir():
        if not entry.name.isdigit():
            continue
        pid = int(entry.name)
        rss = _proc_rss_mb(pid)
        if rss is None or rss < 40:
            continue
        name = _proc_name(pid)
        cmdline = _proc_cmdline(pid)
        protected = _is_protected(name, cmdline, pid)
        junk = (not protected) and _is_junk_candidate(name, cmdline)
        auto_killable = junk and rss >= _AUTO_KILL_RSS_MB
        rows.append(
            {
                "pid": pid,
                "name": name or f"pid-{pid}",
                "cmdline": cmdline,
                "rss_mb": rss,
                "protected": protected,
                "junk_candidate": junk,
                "auto_killable": auto_killable,
            }
        )
    rows.sort(key=lambda item: float(item.get("rss_mb") or 0), reverse=True)
    return rows[: max(1, int(limit))]


def build_machine_pulse(*, process_limit: int = _TOP_N) -> dict[str, Any]:
    """Return host memory/load + top RSS processes for VAXON Machine CEO."""
    if not Path("/proc").is_dir():
        return {
            "ok": False,
            "reason": "proc_unavailable",
            "generated_at": utc_now_iso(),
            "platform": os.name,
            "health": {},
            "processes": [],
            "recommendations": [],
            "spoken": "Machine pulse unavailable on this host.",
        }

    health = {**_meminfo(), **_loadavg()}
    processes = list_top_processes(limit=process_limit)
    recommendations = [
        {
            "pid": item["pid"],
            "name": item["name"],
            "rss_mb": item["rss_mb"],
            "action": "kill" if item["auto_killable"] else "review",
            "reason": (
                f"Allowlisted junk over {_AUTO_KILL_RSS_MB} MB RSS"
                if item["auto_killable"]
                else "High memory — review before kill"
            ),
        }
        for item in processes
        if item.get("auto_killable") or (not item.get("protected") and float(item.get("rss_mb") or 0) >= 1500)
    ][:5]

    mem_pct = health.get("memory_percent")
    top = processes[0] if processes else None
    if mem_pct is not None and top:
        spoken = (
            f"Machine pulse: memory {mem_pct:.0f} percent. "
            f"Top consumer {top['name']} at {top['rss_mb']:.0f} megabytes."
        )
        if recommendations and recommendations[0].get("action") == "kill":
            spoken += (
                f" I can reclaim memory by stopping {recommendations[0]['name']} "
                f"pid {recommendations[0]['pid']}."
            )
        else:
            spoken += " No safe auto-kill targets right now."
    else:
        spoken = "Machine pulse collected."

    return {
        "ok": True,
        "reason": "ok",
        "generated_at": utc_now_iso(),
        "platform": "linux",
        "hostname": _read_text(Path("/proc/sys/kernel/hostname")).strip(),
        "health": health,
        "processes": processes,
        "recommendations": recommendations,
        "spoken": spoken,
        "self_pid": os.getpid(),
    }
