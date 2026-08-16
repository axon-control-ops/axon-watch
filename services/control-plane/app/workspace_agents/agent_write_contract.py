"""How agents are expected to write files and declare what they wrote.

Two failure modes this closes, both observed in real shifts:

1. Agents reach for `node -e` / `python -c` / `bash -c` to do file I/O. Those
   are categorical interpreter escapes in the shell hook and are denied no
   matter what the execution policy grants, so the write silently never lands.
2. Agents infer a receipt's file extension from neighbouring files rather than
   naming what they actually wrote. ``docs/ops/agent-reports/`` holds machine
   ``*.json`` watcher receipts next to human ``*.md`` shift reports, so a
   markdown report gets declared as ``.json`` and fails path verification.
"""

from __future__ import annotations

WRITE_CONTRACT_CLAUSE = (
    " File writes: use your Write/Edit tools, never a shell interpreter. "
    "`node -e`, `python -c`, `bash -c`, and `sh -c` are denied by the sandbox "
    "as interpreter escapes regardless of what your policy otherwise allows — "
    "a write attempted that way never lands, even though the turn may look "
    "like it succeeded. If a write is refused, report the refusal; do not "
    "reach for an interpreter to work around it. "
    "Receipts: when you declare an edit receipt path, name the exact file you "
    "wrote — same directory and same extension. Do not copy the extension from "
    "neighbouring files: `docs/ops/agent-reports/` holds machine `*.json` "
    "watcher receipts alongside human `*.md` shift reports, so a markdown "
    "report declared as `.json` fails verification and your completion claim "
    "is marked unverified. "
)


__all__ = ["WRITE_CONTRACT_CLAUSE"]
