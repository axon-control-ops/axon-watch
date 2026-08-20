"""Approved command-prefix allowlists shared by the role execution policies.

Split out of ``execution_policy.py`` per its ratchet target ("extract
allowlist/scope helpers next").

Every entry names a specific sub-command. The shell hook only grants a command
whose leading tokens match an entry exactly, so widening these tuples is the one
place that widens what an agent may run without an approval prompt.
"""

from __future__ import annotations

COMMON_READ_PREFIXES: tuple[tuple[str, ...], ...] = (
    ("git", "status"),
    ("git", "diff"),
    ("git", "log"),
    ("git", "grep"),
    ("rg",),
    # `rg` alone left plain `grep` denied, so every agent that reached for the
    # more common tool lost a turn to a policy error. It is read-only, and the
    # hook already rejects absolute paths and parent traversal in arguments, so
    # it cannot read outside the disposable checkout.
    ("grep",),
)

# gh read-only sub-commands used at ship gates: auth probe, CI run status, log
# tails. These never mutate repo or PR state; they're safe to pre-approve for
# Lead + Integrations. `gh` is also a raw network tool, so the shell hook only
# honours these because each entry is more than one token long.
GH_READ_PREFIXES: tuple[tuple[str, ...], ...] = (
    ("gh", "auth", "status"),
    ("gh", "run", "list"),
    ("gh", "run", "view"),
    ("gh", "run", "watch"),
    ("gh", "api", "repos"),
)

# Non-mutating validation the completion gate actually demands as evidence.
# Without these, an implementation shift is asked for test output while the
# sandbox denies every command that could produce it. `npm run <arbitrary>`
# stays gated so deploy/ship scripts cannot ride in on a generic approval.
VALIDATION_PREFIXES: tuple[tuple[str, ...], ...] = (
    ("npm", "ci"),
    ("npm", "test"),
    ("npm", "run", "test"),
    ("npm", "run", "lint"),
    ("npm", "run", "typecheck"),
    ("npx", "--no-install", "jest"),
    ("npx", "--no-install", "tsc"),
    ("npx", "--no-install", "tsx"),
    ("npx", "--no-install", "eslint"),
    ("npx", "--no-install", "vitest"),
)

COMMON_AUDITED_WRAPPERS: tuple[str, ...] = (
    "axon-agent-terminal-job",
    "workspace-live-verify",
)

# Lead-only: fan a goal out into role-scoped tasks and dispatch teammates.
# A Lead without this can only describe a handoff in a document — nobody is
# actually dispatched, which reads as "the fleet did nothing".
LEAD_DISPATCH_WRAPPERS: tuple[str, ...] = ("axon-assign",)


__all__ = [
    "COMMON_AUDITED_WRAPPERS",
    "LEAD_DISPATCH_WRAPPERS",
    "COMMON_READ_PREFIXES",
    "GH_READ_PREFIXES",
    "VALIDATION_PREFIXES",
]
