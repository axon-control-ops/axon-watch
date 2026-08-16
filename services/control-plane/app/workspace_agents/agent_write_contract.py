"""How agents are expected to invoke tools, write files, and declare receipts.

Three failure modes this closes, all observed in real shifts:

1. Agents reach for `node -e` / `python -c` / `bash -c` to do file I/O. Those
   are categorical interpreter escapes in the shell hook and are denied no
   matter what the execution policy grants, so the write silently never lands.
2. Agents infer a receipt's file extension from neighbouring files rather than
   naming what they actually wrote. ``docs/ops/agent-reports/`` holds machine
   ``*.json`` watcher receipts next to human ``*.md`` shift reports, so a
   markdown report gets declared as ``.json`` and fails path verification.
3. Agents wrap an approved wrapper in a shell (``zsh -lc "<wrapper> ..."``).
   The shell is an interpreter escape, so the whole command is denied, and the
   agent reports the wrapper as missing rather than as wrongly invoked.
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
    "Invoking approved wrappers: call them directly, e.g. "
    "`axon-agent-terminal-job --workspace <id> -- <command>`. Never wrap one in "
    "`zsh -lc`, `bash -c`, or `sh -c`: the shell is an interpreter escape, so the "
    "whole command is denied and the wrapper looks missing when it is simply "
    "mis-invoked. On a headless shift, route shell work through "
    "`axon-agent-terminal-job --workspace <id> -- <command>`, where the inner "
    "command must itself be approved (for example `npx jest <path>`, "
    "`npm test -- <path>`, `npx tsc --noEmit`). A denial means wrong form or wrong "
    "role for your policy — never that the tool does not exist. Quote the exact "
    "denial text rather than concluding the tool is unavailable. "
)


__all__ = ["WRITE_CONTRACT_CLAUSE"]
