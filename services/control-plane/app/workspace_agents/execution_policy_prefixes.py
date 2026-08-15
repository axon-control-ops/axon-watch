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
    ("rg",),
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
    ("npm", "test"),
    ("npm", "run", "test"),
    ("npm", "run", "lint"),
    ("npm", "run", "typecheck"),
    ("npx", "jest"),
    ("npx", "tsc"),
    ("npx", "tsx"),
    ("npx", "eslint"),
    ("npx", "vitest"),
)

COMMON_AUDITED_WRAPPERS: tuple[str, ...] = ("axon-agent-terminal-job",)


__all__ = [
    "COMMON_AUDITED_WRAPPERS",
    "COMMON_READ_PREFIXES",
    "GH_READ_PREFIXES",
    "VALIDATION_PREFIXES",
]
