"""Machine CEO host pulse — Linux /proc inventory (no psutil dependency)."""

from __future__ import annotations

import os
import re
from pathlib import Path
from typing import Any

from app.host_context.models import utc_now_iso

# Hard ceiling — Full AUTO Machine CEO must reclaim below this.
MEMORY_CEILING_PERCENT = 80.0
# Keep reclaiming until headroom recovers (hysteresis vs Cursor tsserver respawn).
MEMORY_RECLAIM_FLOOR_PERCENT = 75.0

# Process-local latch: once over the ceiling, stay in reclaim until under the floor.
_pressure_latch = False

# Never auto-target these name fragments (case-insensitive), except orphan SI carve-out.
_PROTECTED_NAME_RE = re.compile(
    r"("
    r"axon|control-plane|uvicorn|"
    r"systemd|Xorg|wayland|pipewire|pulseaudio|dbus|"
    r"ssh|login|gdm|sddm|gnome-shell|kwin|plasmashell|"
    r"dockerd|containerd|kube|postgres|mysql|redis|"
    r"python3?$"  # bare interpreter — too ambiguous to auto-kill
    r")",
    re.I,
)

# Cursor / VS Code IDE stay protected unless orphaned SI checkout workers.
_IDE_PROTECTED_RE = re.compile(r"(cursor|code$|code-)", re.I)

# Safe auto-kill candidates (always, high RSS).
_JUNK_ALLOWLIST_RE = re.compile(
    r"("
    r"chrome_crashpad|crashpad_handler|"
    r"Code Helper \(Plugin\)|Code Helper \(Renderer\)|"
    r"firefox-bin.*RDD|Web Content$"
    r")",
    re.I,
)

# Under memory pressure (>= ceiling), also reclaim these wasteful consumers.
_PRESSURE_RECLAIM_RE = re.compile(
    r"("
    r"tsserver|"
    r"jest-worker|processChild\.js|"
    r"chrome_crashpad|crashpad_handler|"
    r"Code Helper \(Plugin\)|Code Helper \(Renderer\)|"
    r"firefox-bin.*RDD|Web Content$"
    r")",
    re.I,
)

_AUTO_KILL_RSS_MB = 900
_PRESSURE_JUNK_RSS_MB = 300
_PRESSURE_TSSERVER_RSS_MB = 200  # Cursor respawns; reclaim early under pressure
_PRESSURE_WORKER_RSS_MB = 80
_PRESSURE_ORPHAN_SI_RSS_MB = 120
_PRESSURE_NPM_RSS_MB = 350
_TOP_N = 12


def _read_text(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return ""


def _meminfo() -> dict[str, float | None]:
    raw = _read_text(Path("/proc/meminfo"))
    total_kb = available_kb = None
    swap_total_kb = swap_free_kb = None
    for line in raw.splitlines():
        if line.startswith("MemTotal:"):
            total_kb = float(line.split()[1])
        elif line.startswith("MemAvailable:"):
            available_kb = float(line.split()[1])
        elif line.startswith("SwapTotal:"):
            swap_total_kb = float(line.split()[1])
        elif line.startswith("SwapFree:"):
            swap_free_kb = float(line.split()[1])
    if not total_kb:
        return {
            "memory_percent": None,
            "memory_total_mb": None,
            "memory_available_mb": None,
            "swap_percent": None,
        }
    used_kb = total_kb - (available_kb or 0.0)
    swap_percent = None
    if swap_total_kb and swap_total_kb > 0:
        swap_used = swap_total_kb - (swap_free_kb or 0.0)
        swap_percent = round(100.0 * swap_used / swap_total_kb, 1)
    return {
        "memory_percent": round(100.0 * used_kb / total_kb, 1),
        "memory_total_mb": round(total_kb / 1024.0, 1),
        "memory_available_mb": round((available_kb or 0.0) / 1024.0, 1),
        "swap_percent": swap_percent,
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


def _is_orphan_si_worker(cmdline: str) -> bool:
    return "/tmp/axon-si-run" in str(cmdline or "")


def _is_ci_runner_worker(cmdline: str) -> bool:
    """DashPro self-hosted Actions work processes — often 5GB+ when stacked."""
    text = str(cmdline or "")
    return "actions-runner-dashpro" in text and (
        "/_work/" in text or "/.npm/" in text or "Runner.Worker" in text
    )


def _is_protected(name: str, cmdline: str, pid: int) -> bool:
    if pid in {1, os.getpid(), os.getppid()}:
        return True
    # Orphaned SI checkout agents are reclaimable (check before "axon" protect).
    if _is_orphan_si_worker(cmdline):
        return False
    # CI work children are reclaimable; keep the listener via service stop, not here.
    if _is_ci_runner_worker(cmdline):
        return False
    hay = f"{name} {cmdline}"
    if _PROTECTED_NAME_RE.search(hay):
        return True
    return bool(_IDE_PROTECTED_RE.search(hay))


def _is_junk_candidate(name: str, cmdline: str) -> bool:
    hay = f"{name} {cmdline}"
    return bool(_JUNK_ALLOWLIST_RE.search(hay))


def _under_memory_pressure(
    mem_pct: float | None,
    *,
    swap_pct: float | None = None,
) -> bool:
    """True at/over 80% RAM or 70% swap; stays latched until under 75% RAM."""
    global _pressure_latch
    # Swap thrash freezes the desktop before MemAvailable looks critical.
    swap_hot = swap_pct is not None and float(swap_pct) >= 55.0
    if mem_pct is None and not swap_hot:
        return bool(_pressure_latch)
    pct = float(mem_pct) if mem_pct is not None else 0.0
    if pct >= MEMORY_CEILING_PERCENT or swap_hot:
        _pressure_latch = True
    elif pct < MEMORY_RECLAIM_FLOOR_PERCENT and not swap_hot:
        _pressure_latch = False
    return bool(_pressure_latch)


def _is_auto_killable(
    *,
    name: str,
    cmdline: str,
    rss: float,
    protected: bool,
    junk: bool,
    mem_pct: float | None,
    swap_pct: float | None = None,
) -> bool:
    """Decide if Full-AUTO Machine CEO may SIGTERM this process."""
    pressure = _under_memory_pressure(mem_pct, swap_pct=swap_pct)
    hay = f"{name} {cmdline}"

    if protected:
        return False

    if junk and rss >= (_PRESSURE_JUNK_RSS_MB if pressure else _AUTO_KILL_RSS_MB):
        return True

    if not pressure:
        return False

    # Pressure reclaim — stop wasteful consumers so RAM stays under the ceiling.
    if _is_ci_runner_worker(cmdline) and rss >= _PRESSURE_WORKER_RSS_MB:
        return True
    if _is_orphan_si_worker(cmdline) and rss >= _PRESSURE_ORPHAN_SI_RSS_MB:
        return True
    if re.search(r"tsserver", hay, re.I) and rss >= _PRESSURE_TSSERVER_RSS_MB:
        return True
    if re.search(r"jest-worker|processChild\.js", hay, re.I) and rss >= _PRESSURE_WORKER_RSS_MB:
        return True
    if re.search(r"\bnpm(?:\s+install|\s+ci|\s+run\b)", hay, re.I) and rss >= _PRESSURE_NPM_RSS_MB:
        return True
    if _PRESSURE_RECLAIM_RE.search(hay) and rss >= _PRESSURE_JUNK_RSS_MB:
        return True
    return False


def list_top_processes(
    *,
    limit: int = _TOP_N,
    mem_pct: float | None = None,
    swap_pct: float | None = None,
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    proc_root = Path("/proc")
    if not proc_root.is_dir():
        return rows
    min_rss = 40.0
    if _under_memory_pressure(mem_pct, swap_pct=swap_pct):
        # Surface smaller CI workers that still add up under pressure.
        min_rss = 60.0
    for entry in proc_root.iterdir():
        if not entry.name.isdigit():
            continue
        pid = int(entry.name)
        rss = _proc_rss_mb(pid)
        if rss is None or rss < min_rss:
            continue
        name = _proc_name(pid)
        cmdline = _proc_cmdline(pid)
        protected = _is_protected(name, cmdline, pid)
        junk = (not protected) and _is_junk_candidate(name, cmdline)
        auto_killable = _is_auto_killable(
            name=name,
            cmdline=cmdline,
            rss=float(rss),
            protected=protected,
            junk=junk,
            mem_pct=mem_pct,
            swap_pct=swap_pct,
        )
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
            "memory_ceiling_percent": MEMORY_CEILING_PERCENT,
            "memory_pressure": False,
        }

    health = {**_meminfo(), **_loadavg()}
    mem_pct = health.get("memory_percent")
    swap_pct = health.get("swap_percent")
    pressure = _under_memory_pressure(
        mem_pct if isinstance(mem_pct, (int, float)) else None,
        swap_pct=float(swap_pct) if isinstance(swap_pct, (int, float)) else None,
    )
    # Under pressure, scan deeper so jest-workers / orphan SI agents surface.
    scan_limit = max(int(process_limit), 40 if pressure else int(process_limit))
    processes = list_top_processes(
        limit=scan_limit,
        mem_pct=float(mem_pct) if isinstance(mem_pct, (int, float)) else None,
        swap_pct=float(swap_pct) if isinstance(swap_pct, (int, float)) else None,
    )
    recommendations = [
        {
            "pid": item["pid"],
            "name": item["name"],
            "rss_mb": item["rss_mb"],
            "action": "kill" if item["auto_killable"] else "review",
            "reason": (
                (
                    f"Memory {mem_pct:.0f}% ≥ {MEMORY_CEILING_PERCENT:.0f}% ceiling — reclaim"
                    if pressure and item["auto_killable"]
                    else f"Allowlisted junk over {_AUTO_KILL_RSS_MB} MB RSS"
                )
                if item["auto_killable"]
                else "High memory — review before kill"
            ),
        }
        for item in processes
        if item.get("auto_killable")
        or (not item.get("protected") and float(item.get("rss_mb") or 0) >= 1500)
    ][:8]

    top = processes[0] if processes else None
    if mem_pct is not None and top:
        swap_bit = (
            f", swap {swap_pct:.0f} percent"
            if isinstance(swap_pct, (int, float))
            else ""
        )
        spoken = (
            f"Machine pulse: memory {mem_pct:.0f} percent{swap_bit}"
            f"{' — over ' + str(int(MEMORY_CEILING_PERCENT)) + '% ceiling' if pressure else ''}. "
            f"Top consumer {top['name']} at {top['rss_mb']:.0f} megabytes."
        )
        killable = [row for row in recommendations if row.get("action") == "kill"]
        if killable:
            spoken += (
                f" Reclaiming memory by stopping {killable[0]['name']} "
                f"pid {killable[0]['pid']}"
                + (f" and {len(killable) - 1} more." if len(killable) > 1 else ".")
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
        # Keep the full scan (deeper under pressure) so CEO kills can resolve PIDs.
        "processes": processes,
        "recommendations": recommendations,
        "spoken": spoken,
        "self_pid": os.getpid(),
        "memory_ceiling_percent": MEMORY_CEILING_PERCENT,
        "memory_pressure": pressure,
    }
