#!/usr/bin/env python3
"""Regenerate missing GNOME thumbnails for ~/Pictures/Screenshots."""
from __future__ import annotations

import hashlib
import json
import subprocess
import time
from pathlib import Path

import gi

gi.require_version("Gio", "2.0")
from gi.repository import Gio  # noqa: E402

LOG = Path("/home/edp/axon-nvme/repos/axon-watch/.cursor/debug-9e41d8.log")
FOLDER = Path("/home/edp/Pictures/Screenshots")
LARGE = Path.home() / ".cache/thumbnails/large"
NORMAL = Path.home() / ".cache/thumbnails/normal"
SESSION = "9e41d8"


def log(hypothesis_id: str, message: str, data: dict, run_id: str = "thumb-regen") -> None:
    # #region agent log
    payload = {
        "sessionId": SESSION,
        "runId": run_id,
        "hypothesisId": hypothesis_id,
        "location": "regen-screenshot-thumbs.py",
        "message": message,
        "data": data,
        "timestamp": int(time.time() * 1000),
    }
    LOG.parent.mkdir(parents=True, exist_ok=True)
    with LOG.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(payload, separators=(",", ":")) + "\n")
    # #endregion


def nvme_temps_c() -> list[int]:
    temps: list[int] = []
    hwmon = Path("/sys/class/nvme/nvme0")
    for p in sorted(hwmon.glob("hwmon*/temp*_input")):
        try:
            temps.append(int(p.read_text().strip()) // 1000)
        except OSError:
            pass
    return temps


def main() -> None:
    LARGE.mkdir(parents=True, exist_ok=True)
    NORMAL.mkdir(parents=True, exist_ok=True)
    temps0 = nvme_temps_c()
    log("H2", "thumb_regen_start", {"folder": str(FOLDER), "nvme_temps_c": temps0})

    missing: list[tuple[Path, str, Path]] = []
    zero = have = 0
    for path in sorted(FOLDER.glob("*.png"), key=lambda p: p.stat().st_mtime, reverse=True):
        if path.stat().st_size == 0:
            zero += 1
            continue
        uri = Gio.File.new_for_path(str(path.resolve())).get_uri()
        digest = hashlib.md5(uri.encode()).hexdigest() + ".png"
        out = LARGE / digest
        if out.exists() and out.stat().st_size > 200:
            have += 1
            continue
        missing.append((path, uri, out))

    log(
        "H2",
        "thumb_inventory",
        {"have": have, "missing_nonzero": len(missing), "zero_byte": zero},
    )

    made = failed = 0
    for i, (path, uri, out) in enumerate(missing, 1):
        temps = nvme_temps_c()
        if temps and max(temps) >= 90:
            log("H5", "thumb_regen_paused_hot", {"i": i, "nvme_temps_c": temps, "made": made})
            time.sleep(15)
            continue
        try:
            r = subprocess.run(
                ["glycin-thumbnailer", "--input", uri, "--output", str(out), "--size", "256"],
                capture_output=True,
                text=True,
                timeout=20,
            )
            ok = r.returncode == 0 and out.exists() and out.stat().st_size > 200
            if ok:
                nout = NORMAL / out.name
                subprocess.run(
                    ["glycin-thumbnailer", "--input", uri, "--output", str(nout), "--size", "128"],
                    capture_output=True,
                    text=True,
                    timeout=20,
                )
                made += 1
            else:
                failed += 1
                if failed <= 8:
                    log(
                        "H2",
                        "thumb_fail",
                        {
                            "name": path.name,
                            "rc": r.returncode,
                            "stderr": (r.stderr or "")[:240],
                        },
                    )
        except Exception as exc:  # noqa: BLE001
            failed += 1
            if failed <= 8:
                log("H2", "thumb_exc", {"name": path.name, "err": str(exc)[:240]})

        if i % 50 == 0 or i == len(missing):
            log(
                "H2",
                "thumb_progress",
                {
                    "i": i,
                    "total": len(missing),
                    "made": made,
                    "failed": failed,
                    "nvme_temps_c": nvme_temps_c(),
                },
            )
        # light pacing to avoid IO spikes on warm NVMe
        if i % 25 == 0:
            time.sleep(0.4)

    log(
        "H2",
        "thumb_regen_done",
        {
            "made": made,
            "failed": failed,
            "remaining_estimate": max(0, len(missing) - made),
            "nvme_temps_c": nvme_temps_c(),
            "icon_theme_note": "Adwaita set; Flat-Remix inherit fixed locally",
        },
        run_id="thumb-regen",
    )


if __name__ == "__main__":
    main()
