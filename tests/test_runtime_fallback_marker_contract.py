"""Contract: every fallback_reply() shape stays recognizable to the console.

A runtime fallback ("the CLI could not run") is delivered to the operator as
an ordinary assistant message, so by default it renders identically to a real
answer — an operator has to read it closely to notice nothing actually ran.
The console styles these distinctly via
apps/console-web/src/lib/thread-message-view.ts
::agentContentLooksLikeRuntimeFallback, which matches on the exact opening
shape this module produces.

Those two detectors live in different languages and cannot import each other,
so this test pins them together: it asserts every branch of fallback_reply()
is matched by the Python-side predicate, AND that the literal prefix/verbs the
console hardcodes are the ones actually emitted. Reword the operator copy
without updating the console and this fails.
"""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

CONTROL_PLANE_ROOT = Path(__file__).resolve().parents[1] / "services" / "control-plane"
sys.path.insert(0, str(CONTROL_PLANE_ROOT))

from app.cli_runtime.runtime_failure import (  # noqa: E402
    RUNTIME_FALLBACK_PREFIX,
    RUNTIME_FALLBACK_VERBS,
    fallback_reply,
    looks_like_runtime_fallback,
)

# Kept byte-identical to the console constants in
# apps/console-web/src/lib/thread-message-view.ts.
_CONSOLE_PREFIX = "Lane B ("
_CONSOLE_VERBS = ("failed on ", "could not start", "cannot start because")


def _reply(**overrides) -> str:
    kwargs = {
        "composer_mode": "agent",
        "user_prompt": "do the thing",
        "context_block": "ctx",
        "reason": "something went wrong",
    }
    kwargs.update(overrides)
    return fallback_reply(**kwargs)


class RuntimeFallbackMarkerContractTests(unittest.TestCase):
    def test_console_constants_match_the_python_constants(self) -> None:
        self.assertEqual(_CONSOLE_PREFIX, RUNTIME_FALLBACK_PREFIX)
        self.assertEqual(set(_CONSOLE_VERBS), set(RUNTIME_FALLBACK_VERBS))

    def test_every_fallback_branch_is_detected(self) -> None:
        branches = {
            "run_error generic": _reply(
                failure_phase="run_error", runtime_label="Cursor CLI (local)"
            ),
            "run_error usage limit": _reply(
                failure_phase="run_error",
                runtime_label="Cursor CLI (local)",
                reason="ActionRequiredError: You've hit your usage limit",
            ),
            "run_error unpaid invoice": _reply(
                failure_phase="run_error",
                runtime_label="Cursor CLI (local)",
                reason="ActionRequiredError: You have an unpaid invoice",
            ),
            "not_ready generic": _reply(reason="Cursor auth probe timed out"),
            "not_ready usage limit": _reply(
                reason="ActionRequiredError: You've hit your usage limit"
            ),
            "not_ready unpaid invoice": _reply(
                reason="ActionRequiredError: You have an unpaid invoice"
            ),
            "no runtime label": _reply(failure_phase="run_error", runtime_label=""),
        }
        for name, text in branches.items():
            with self.subTest(branch=name):
                self.assertTrue(
                    looks_like_runtime_fallback(text),
                    f"console would render this as a normal answer: {text!r}",
                )
                # Prove the console's own literal matching would also fire.
                self.assertTrue(text.startswith(_CONSOLE_PREFIX), text)
                self.assertTrue(any(v in text for v in _CONSOLE_VERBS), text)

    def test_every_composer_mode_is_detected(self) -> None:
        for mode in ("ask", "plan", "agent", "debug"):
            with self.subTest(mode=mode):
                self.assertTrue(
                    looks_like_runtime_fallback(
                        _reply(composer_mode=mode, failure_phase="run_error")
                    )
                )

    def test_real_agent_answers_are_not_flagged(self) -> None:
        for text in (
            "Done — I updated README.md and the tests pass.",
            "I could not start the server because port 8787 was busy.",  # not our prefix
            "Lane B is a concept in this repo; here is how it works.",  # prefix-ish, no verb
            "",
            "   ",
            "## Summary\n\nThe fix landed cleanly.",
        ):
            with self.subTest(text=text[:40]):
                self.assertFalse(looks_like_runtime_fallback(text))

    def test_detection_survives_whitespace_normalization(self) -> None:
        text = _reply(failure_phase="run_error", runtime_label="Cursor CLI (local)")
        self.assertTrue(looks_like_runtime_fallback(f"  {text}  "))
        self.assertTrue(looks_like_runtime_fallback(text.replace(" ", "  ", 1)))


if __name__ == "__main__":
    unittest.main()
