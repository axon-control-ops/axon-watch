"""Abandoned worker checkouts must be swept before they exhaust /tmp.

Regression guard for a real outage: preserve_isolation kept checkouts on disk
for operator recovery, nothing ever swept them, and 77 accumulated (7.9G) on a
9.8G tmpfs until it hit 100% and every *new* isolation started failing with
"failed to create disposable isolation root ... refusing to write the bound
project root" -- a platform-wide stall caused by disk pressure alone.
"""

from __future__ import annotations

import json
import subprocess
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import patch

from app.workspace_agents.isolation_reaper import (
    find_abandoned_isolation_roots,
    reap_abandoned_worker_isolations,
)


def _iso(dt: datetime) -> str:
    return dt.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


class IsolationReaperTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.tmp_root = Path(self.temp.name)
        patcher = patch("tempfile.gettempdir", return_value=str(self.tmp_root))
        patcher.start()
        self.addCleanup(patcher.stop)

    def _make_isolation(
        self,
        run_id: str,
        *,
        age: timedelta,
        bound_root: Path | None = None,
    ) -> Path:
        base_dir = self.tmp_root / f"axon-si-{run_id[:12]}-probe"
        checkout = base_dir / "checkout"
        sidecar = checkout / ".axon-si"
        sidecar.mkdir(parents=True)
        created_at = datetime.now(timezone.utc) - age
        bound = str(bound_root) if bound_root is not None else str(self.tmp_root / "bound")
        (sidecar / "baseline.json").write_text(
            json.dumps(
                {
                    "proposal_id": run_id,
                    "created_at": _iso(created_at),
                    "bound_project_root": bound,
                    "isolation_kind": "worktree",
                    "worker_branch": f"worker/{run_id}",
                }
            ),
            encoding="utf-8",
        )
        return checkout

    def test_terminal_run_past_the_age_floor_is_a_candidate(self) -> None:
        self._make_isolation("run_a", age=timedelta(hours=2))
        with patch(
            "app.persistence.run_store.get_run", return_value={"phase": "failed"}
        ):
            found = find_abandoned_isolation_roots(min_age_seconds=600)
        self.assertEqual(len(found), 1)
        self.assertEqual(found[0]["run_id"], "run_a")

    def test_unknown_run_id_is_treated_as_safe_to_reap(self) -> None:
        # Pruned run history is expected: an orphaned checkout with no ledger
        # row is exactly the shape that accumulated and filled /tmp.
        self._make_isolation("run_b", age=timedelta(hours=2))
        with patch("app.persistence.run_store.get_run", return_value=None):
            found = find_abandoned_isolation_roots(min_age_seconds=600)
        self.assertEqual(len(found), 1)
        self.assertFalse(found[0]["run_known"])

    def test_non_terminal_run_is_never_a_candidate_regardless_of_age(self) -> None:
        # A checkout mid-dispatch must never be swept just because it is old.
        self._make_isolation("run_c", age=timedelta(days=1))
        with patch(
            "app.persistence.run_store.get_run", return_value={"phase": "executing"}
        ):
            found = find_abandoned_isolation_roots(min_age_seconds=600)
        self.assertEqual(found, [])

    def test_fresh_checkout_is_protected_even_if_the_run_looks_terminal(self) -> None:
        # A run row can lag its checkout by a beat; the age floor is the real
        # guard against racing an in-flight dispatch.
        self._make_isolation("run_d", age=timedelta(seconds=5))
        with patch(
            "app.persistence.run_store.get_run", return_value={"phase": "completed"}
        ):
            found = find_abandoned_isolation_roots(min_age_seconds=600)
        self.assertEqual(found, [])

    def test_reap_actually_removes_the_checkout_from_disk(self) -> None:
        bound = self.tmp_root / "bound-repo"
        bound.mkdir()
        for args in (
            ["git", "init", "-q"],
            ["git", "config", "user.email", "t@e.c"],
            ["git", "config", "user.name", "T"],
        ):
            subprocess.run(args, cwd=bound, check=True)
        (bound / "seed.txt").write_text("x", encoding="utf-8")
        subprocess.run(["git", "add", "seed.txt"], cwd=bound, check=True)
        subprocess.run(["git", "commit", "-qm", "s"], cwd=bound, check=True)
        subprocess.run(
            ["git", "worktree", "add", "-b", "worker/run_e", str(bound.parent / "wt-e"), "HEAD"],
            cwd=bound,
            check=True,
        )
        base_dir = self.tmp_root / "axon-si-run_e-probe"
        base_dir.mkdir()
        checkout_target = base_dir / "checkout"
        (bound.parent / "wt-e").rename(checkout_target)
        subprocess.run(
            ["git", "worktree", "repair", str(checkout_target)], cwd=bound, check=True
        )
        sidecar = checkout_target / ".axon-si"
        sidecar.mkdir()
        (sidecar / "baseline.json").write_text(
            json.dumps(
                {
                    "proposal_id": "run_e",
                    "created_at": _iso(datetime.now(timezone.utc) - timedelta(hours=1)),
                    "bound_project_root": str(bound),
                    "isolation_kind": "worktree",
                    "worker_branch": "worker/run_e",
                }
            ),
            encoding="utf-8",
        )

        with patch("app.persistence.run_store.get_run", return_value={"phase": "failed"}):
            cleaned = reap_abandoned_worker_isolations(min_age_seconds=600)

        self.assertEqual(len(cleaned), 1)
        self.assertFalse(checkout_target.exists())


if __name__ == "__main__":
    unittest.main()
