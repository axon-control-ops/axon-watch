#!/usr/bin/env python3
"""Sample host health into the Cursor debug NDJSON log (session 9e41d8)."""

from __future__ import annotations

import json
import os
import subprocess
import time
from pathlib import Path

LOG_PATH = Path("/home/edp/axon-nvme/repos/axon-watch/.cursor/debug-9e41d8.log")
SESSION_ID = "9e41d8"
INTERVAL_S = 5.0


def _sh(cmd: str) -> str:
    try:
        out = subprocess.check_output(cmd, shell=True, text=True, stderr=subprocess.DEVNULL)
        return out.strip()
    except Exception:
        return ""


def _pressure(kind: str) -> dict[str, float]:
    path = Path(f"/proc/pressure/{kind}")
    if not path.exists():
        return {}
    data: dict[str, float] = {}
    for line in path.read_text().splitlines():
        # some avg10=0.00 avg60=0.00 avg300=0.00 total=2
        parts = line.split()
        if not parts:
            continue
        prefix = parts[0]
        for token in parts[1:]:
            if "=" not in token:
                continue
            k, v = token.split("=", 1)
            try:
                data[f"{prefix}_{k}"] = float(v)
            except ValueError:
                pass
    return data


def _nouveau_errors_since(boot_marker: str) -> int:
    # Count DATA_ERROR lines since boot; cheap enough at 5s when journal is local.
    out = _sh(
        "journalctl -b 0 -k --no-pager --output=cat 2>/dev/null | "
        "rg -c 'nouveau.*DATA_ERROR' || true"
    )
    try:
        return int(out or "0")
    except ValueError:
        return -1


def sample(run_id: str, seq: int) -> dict:
    mem = {}
    for line in Path("/proc/meminfo").read_text().splitlines():
        if line.startswith(("MemTotal:", "MemAvailable:", "SwapTotal:", "SwapFree:")):
            key, val = line.split(":", 1)
            mem[key] = int(val.strip().split()[0])

    disk = _sh("df -P / | awk 'NR==2 {print $3,$4,$5}'").split()
    disk_used_k, disk_avail_k, disk_pct = (disk + ["0", "0", "0%"])[:3]

    gpu_err = _nouveau_errors_since("boot0")
    chrome_gpu = _sh("pgrep -af 'chrome --type=gpu-process' | head -1")
    top_rss = _sh(
        "ps -eo rss,comm --sort=-rss | awk 'NR>1 && NR<=6 {printf \"%s:%s \", $2, $1}'"
    )
    load1 = os.getloadavg()[0]
    # NVMe composite temps when readable without root (hwmon); else blank.
    nvme_temps = _sh(
        "for t in /sys/class/hwmon/hwmon*/temp*_input; do "
        "d=$(dirname \"$t\"); n=$(cat \"$d/name\" 2>/dev/null || true); "
        "[[ \"$n\" == nvme* ]] || continue; "
        "printf '%s:%s ' \"$n\" \"$(($(cat \"$t\")/1000))\"; done"
    )

    return {
        "sessionId": SESSION_ID,
        "runId": run_id,
        "id": f"freeze_sample_{int(time.time())}_{seq}",
        "timestamp": int(time.time() * 1000),
        "location": "scripts/ops/freeze-sentinel.py",
        "message": "host health sample",
        "hypothesisId": "B,F,G",
        "data": {
            "seq": seq,
            "load1": load1,
            "mem_available_kb": mem.get("MemAvailable"),
            "mem_total_kb": mem.get("MemTotal"),
            "swap_free_kb": mem.get("SwapFree"),
            "swap_total_kb": mem.get("SwapTotal"),
            "disk_used_k": int(disk_used_k) if str(disk_used_k).isdigit() else disk_used_k,
            "disk_avail_k": int(disk_avail_k) if str(disk_avail_k).isdigit() else disk_avail_k,
            "disk_pct": disk_pct,
            "nouveau_data_errors_boot": gpu_err,
            "chrome_gpu_process": bool(chrome_gpu),
            "top_rss": top_rss,
            "nvme_temps_c": nvme_temps,
            "pressure_memory": _pressure("memory"),
            "pressure_io": _pressure("io"),
            "pressure_cpu": _pressure("cpu"),
            "driver": _sh("lsmod | awk '/^nouveau|^nvidia /{print $1}' | tr '\\n' ','"),
        },
    }


def main() -> None:
    run_id = os.environ.get("FREEZE_RUN_ID", "pre-fix")
    LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
    seq = 0
    # #region agent log
    with LOG_PATH.open("a", encoding="utf-8") as fh:
        boot = {
            "sessionId": SESSION_ID,
            "runId": run_id,
            "id": f"freeze_boot_{int(time.time())}",
            "timestamp": int(time.time() * 1000),
            "location": "scripts/ops/freeze-sentinel.py:main",
            "message": "freeze sentinel started",
            "hypothesisId": "A,B,C,D,E",
            "data": {
                "pid": os.getpid(),
                "interval_s": INTERVAL_S,
                "cmdline": _sh("cat /proc/cmdline"),
            },
        }
        fh.write(json.dumps(boot) + "\n")
        fh.flush()
        while True:
            seq += 1
            row = sample(run_id, seq)
            fh.write(json.dumps(row) + "\n")
            fh.flush()
            time.sleep(INTERVAL_S)
    # #endregion


if __name__ == "__main__":
    main()
