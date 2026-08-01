"""VAXON Chief of Staff charter — standing identity for Ask / vaxon_runtime.

Loaded from config/agent-rules/vaxon-chief-of-staff.md (repo root).

Scope (important):
- Injected into Ask-mode system prompts and (compactly) into converse runtime context.
- Does NOT run on deterministic REPORT, template_status, bounded_command, or specialty
  handoff lanes — those bypass Ask runtime.
- Charter text is persona/policy guidance only; it does not implement mission lifecycle
  state machines, idle autonomy workers, or long-term memory stores.
"""

from __future__ import annotations

import logging
from pathlib import Path

logger = logging.getLogger(__name__)

CHIEF_OF_STAFF_MARKER = "VAXON Chief of Staff charter (authoritative):"
CHARTER_RELATIVE = Path("config") / "agent-rules" / "vaxon-chief-of-staff.md"

_FALLBACK_STANDING = (
    f"{CHIEF_OF_STAFF_MARKER}\n"
    "You are VAXON — Executive Intelligence / Chief of Staff of AXON-X. "
    "Not a chatbot, not a coding assistant, not a software engineer. "
    "Think in systems and missions. Ensure the right specialist does the right work "
    "at the right time. Never fabricate evidence. Never hide uncertainty. "
    "Delegate implementation. Irreversible actions require Operator approval."
)

_charter_cache: tuple[float, str] | None = None


def _repo_root() -> Path:
    # …/services/control-plane/app/kairo_chief_of_staff.py → parents[3] = repo root
    return Path(__file__).resolve().parents[3]


def charter_path() -> Path:
    return _repo_root() / CHARTER_RELATIVE


def clear_chief_of_staff_charter_cache() -> None:
    global _charter_cache
    _charter_cache = None


def load_vaxon_chief_of_staff_charter() -> str:
    """Load charter text; refresh when file mtime changes."""
    global _charter_cache
    path = charter_path()
    try:
        mtime = path.stat().st_mtime
    except OSError as exc:
        logger.warning("VAXON Chief of Staff charter unreadable at %s: %s", path, exc)
        return ""
    if _charter_cache is not None and _charter_cache[0] == mtime:
        return _charter_cache[1]
    try:
        text = path.read_text(encoding="utf-8").strip()
    except OSError as exc:
        logger.warning("VAXON Chief of Staff charter unreadable at %s: %s", path, exc)
        return ""
    _charter_cache = (mtime, text)
    return text


def _clip_charter(full: str) -> str:
    """Standing identity + principles + non-negotiables (token-lighter)."""
    clipped = full
    for marker in ("# Your Role", "# Executive Intent", "# Mission Lifecycle"):
        cut = full.find(marker)
        if cut > 0:
            clipped = full[:cut].rstrip()
            break
    non_neg = full.find("# Non-Negotiable Rules")
    if non_neg > 0:
        tail = full[non_neg:]
        end = tail.find("\n# First Directive")
        if end > 0:
            tail = tail[:end].rstrip()
        clipped = f"{clipped}\n\n{tail}"
    return clipped


def build_chief_of_staff_context_block(*, include_full_charter: bool = True) -> str:
    """Block for Ask system prompt (full) or runtime context (often compact)."""
    full = load_vaxon_chief_of_staff_charter()
    if not full:
        return _FALLBACK_STANDING
    body = full if include_full_charter else _clip_charter(full)
    return f"{CHIEF_OF_STAFF_MARKER}\n{body}"


def chief_of_staff_ask_identity_line() -> str:
    """Lead identity for build_ask_system_prompt (persona enabled)."""
    return (
        "You are VAXON — Executive Intelligence and Chief of Staff of the AXON-X Platform. "
        "You are not a chatbot, not a coding assistant, and not a software engineer. "
        "You ensure the right specialist performs the right work at the right time. "
        "Obey the VAXON Chief of Staff charter below. "
        "Evidence before assumption. Delegate implementation. Never fabricate status."
    )


__all__ = [
    "CHIEF_OF_STAFF_MARKER",
    "build_chief_of_staff_context_block",
    "charter_path",
    "chief_of_staff_ask_identity_line",
    "clear_chief_of_staff_charter_cache",
    "load_vaxon_chief_of_staff_charter",
]
