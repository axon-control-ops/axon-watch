"""Prompt clause for long-running / external shell jobs (OTA, Expo, EAS)."""

LONG_RUNNING_SHELL_CLAUSE = (
    "Long-running / external jobs (OTA canary, Expo export/bundle, EAS, uploads, watches): "
    "start the job once and wait for that single shell tool to finish — do not busy-poll with "
    "repeated shell tools every few seconds (pstree / sleep loops / checking the same log). "
    "If you need status later, check sparsely (about once per 30–60s of wall time, or after a "
    "meaningful progress change). Prefer one bounded wait over many tiny polls. "
    "Heavy Expo/Metro/typecheck heaps burn host RAM and can OOM-kill the agent scope — "
    "do not launch a second heavy server when one is already running."
)
