"""Effect classification and exact-approval fingerprints."""

from __future__ import annotations

import hashlib
import json
from typing import Any

from app.safe_improvement.models import EffectKind

EXACT_APPROVAL_EFFECTS: frozenset[EffectKind] = frozenset(
    {"policy", "secret", "production", "merge"}
)


def classify_effect(effect_kind: str) -> EffectKind:
    kind = str(effect_kind or "").strip().lower()
    if kind not in EXACT_APPROVAL_EFFECTS:
        raise ValueError(
            f"unsupported effect kind `{effect_kind}`; "
            f"allowed: {sorted(EXACT_APPROVAL_EFFECTS)}"
        )
    return kind  # type: ignore[return-value]


def effect_fingerprint(
    *,
    proposal_id: str,
    effect_kind: EffectKind,
    target_ref: str,
    payload: dict[str, Any],
) -> str:
    """Canonical fingerprint bound to the exact approved effect."""
    canonical = {
        "proposal_id": proposal_id.strip(),
        "effect_kind": effect_kind,
        "target_ref": target_ref.strip(),
        "payload": payload,
    }
    encoded = json.dumps(canonical, sort_keys=True, separators=(",", ":"))
    digest = hashlib.sha256(encoded.encode("utf-8")).hexdigest()
    return f"eff_{digest[:24]}"


def fingerprints_match(expected: str | None, presented: str | None) -> bool:
    left = str(expected or "").strip()
    right = str(presented or "").strip()
    return bool(left) and left == right
