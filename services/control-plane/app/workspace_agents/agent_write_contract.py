"""How agents are expected to invoke tools, write files, and declare receipts.

Three failure modes this closes, all observed in real shifts:

1. Agents reach for `node -e` / `python -c` / `bash -c` to do routine file I/O.
   Full role access can run those tools, but reviewable Write/Edit patches are
   safer and produce clearer receipts.
2. Agents infer a receipt's file extension from neighbouring files rather than
   naming what they actually wrote. ``docs/ops/agent-reports/`` holds machine
   ``*.json`` watcher receipts next to human ``*.md`` shift reports, so a
   markdown report gets declared as ``.json`` and fails path verification.
3. Agents wrap an approved wrapper in an unnecessary shell
   (``zsh -lc "<wrapper> ..."``), obscuring the command and its receipt.
"""

from __future__ import annotations

WRITE_CONTRACT_CLAUSE = (
    " File writes: prefer Write/Edit tools for reviewable patches. Full Access "
    "also permits project runtimes and scripts in the sandbox; use shell-based "
    "file generation only when the task genuinely requires it, then inspect the "
    "result before claiming success. If a write is refused, report the exact refusal. "
    "Receipts: when you declare an edit receipt path, name the exact file you "
    "wrote — same directory and same extension. Do not copy the extension from "
    "neighbouring files: `docs/ops/agent-reports/` holds machine `*.json` "
    "watcher receipts alongside human `*.md` shift reports, so a markdown "
    "report declared as `.json` fails verification and your completion claim "
    "is marked unverified. "
    "Invoking approved wrappers: call them directly, e.g. "
    "`axon-agent-terminal-job --workspace <id> -- <command>`. Direct invocation "
    "is preferred because it preserves an unambiguous audit receipt. On a headless "
    "shift, route shell work through that wrapper. Full role access permits the "
    "normal project toolchain inside the role-owned filesystem surface, while "
    "privilege escalation, destructive Git, cross-workspace mutation, publication, "
    "deployment, and secret access retain separate gates. A denial does not prove "
    "that the tool is absent. Quote the exact "
    "denial text rather than concluding the tool is unavailable. "
    "Publication: company documents, customer records, RFQ/requisition packs, "
    "internal profiles, generated exports, evidence bundles, and office files "
    "(`.pdf`, `.docx`, `.xlsx`, `.zip`, etc.) stay local/private. Never stage, "
    "commit, push, attach to a PR, or place those materials in a public web root. "
    "Commit only reviewed source, tests, public assets, and deployment configuration. "
    "The delivery gate enforces this and will block the whole delivery if one "
    "private-company path is present. "
    "Commit messages: make them explain the change and surface, in the form "
    "`fix(scope): outcome`, `feat(scope): capability`, `docs: purpose`, or "
    "`chore(scope): maintenance`. Never use `update files`, `changes`, or a "
    "run id as the entire message. "
)


__all__ = ["WRITE_CONTRACT_CLAUSE"]
