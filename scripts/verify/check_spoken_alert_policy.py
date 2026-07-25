"""Validate spoken alert eligibility fields on operator briefing payloads."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from scripts.verify.common import CheckResult, emit, load_json

REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_SPEC_PATH = REPO_ROOT / "config" / "spoken-alert-contract.json"
DEFAULT_FIXTURE_PATH = (
    REPO_ROOT / "packages/shared-types/fixtures/operator-briefing.example.json"
)


def validate_spoken_alert(
    payload: dict[str, Any],
    *,
    spec: dict[str, Any] | None = None,
) -> CheckResult:
    spec = spec or load_json(DEFAULT_SPEC_PATH)
    presence = payload.get("operator_presence")
    if not isinstance(presence, dict):
        return CheckResult(
            name="spoken_high_value_alerts",
            status="fail",
            message="operator_presence block missing or not an object",
        )

    spoken = presence.get("spoken_alert")
    if not isinstance(spoken, dict):
        return CheckResult(
            name="spoken_high_value_alerts",
            status="fail",
            message="spoken_alert block missing or not an object",
        )

    required_fields = spec["spoken_alert_required_fields"]
    missing = [field for field in required_fields if field not in spoken]
    if missing:
        return CheckResult(
            name="spoken_high_value_alerts",
            status="fail",
            message="spoken_alert contract incomplete",
            details=[f"missing={missing}"],
        )

    eligible = bool(spoken.get("eligible"))
    message = str(spoken.get("message", "")).strip()
    reason = str(spoken.get("reason", "")).strip()

    if eligible and spec.get("require_message_when_eligible") and not message:
        return CheckResult(
            name="spoken_high_value_alerts",
            status="fail",
            message="eligible spoken_alert requires non-empty message",
        )

    if (
        not eligible
        and spec.get("require_empty_message_when_ineligible")
        and message
    ):
        return CheckResult(
            name="spoken_high_value_alerts",
            status="fail",
            message="ineligible spoken_alert must not carry a message",
        )

    blocked_reasons = set(spec.get("blocked_reasons", []))
    if not eligible and reason and reason not in blocked_reasons:
        return CheckResult(
            name="spoken_high_value_alerts",
            status="fail",
            message=f"ineligible spoken_alert has unexpected reason: {reason}",
            details=[f"blocked={sorted(blocked_reasons)}"],
        )

    if eligible and not reason:
        return CheckResult(
            name="spoken_high_value_alerts",
            status="fail",
            message="eligible spoken_alert requires a reason",
        )

    settings = presence.get("settings")
    if isinstance(settings, dict):
        for toggle in (
            "spoken_alerts_enabled",
            "privacy_mode",
            "operator_persona_enabled",
            "mobile_compact_preferred",
        ):
            if toggle in settings and not isinstance(settings[toggle], bool):
                return CheckResult(
                    name="spoken_high_value_alerts",
                    status="fail",
                    message=f"operator_presence.settings.{toggle} must be boolean",
                )

    return CheckResult(
        name="spoken_high_value_alerts",
        status="pass",
        message="spoken_alert contract satisfied",
        details=[f"spec={DEFAULT_SPEC_PATH.relative_to(REPO_ROOT)}"],
    )


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--payload", help="operator briefing JSON payload path")
    parser.add_argument("--spec", help="spoken alert contract path")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv or sys.argv[1:])
    payload_path = Path(args.payload) if args.payload else DEFAULT_FIXTURE_PATH
    spec_path = Path(args.spec) if args.spec else DEFAULT_SPEC_PATH
    payload = load_json(payload_path)
    spec = load_json(spec_path)
    return emit(validate_spoken_alert(payload, spec=spec))


if __name__ == "__main__":
    raise SystemExit(main())
