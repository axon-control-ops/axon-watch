"""Role/path keyword bags for teammate specialty scoring."""

from __future__ import annotations

import re

_ROLE_BAGS: list[tuple[str, int, list[re.Pattern[str]]]] = [
    (
        "frontend",
        1,
        [
            re.compile(r"\bui\b", re.I),
            re.compile(r"\bux\b", re.I),
            re.compile(r"\bscreen\b", re.I),
            re.compile(r"\bcomponent\b", re.I),
            re.compile(r"\bdashboard\b", re.I),
            re.compile(r"\blayout\b", re.I),
            re.compile(r"\bexpo\b", re.I),
            re.compile(r"\bandroid\b", re.I),
            re.compile(r"\bapp-?config\b", re.I),
            re.compile(r"\bconfirmation\b", re.I),
            re.compile(r"\benrol+ment\b", re.I),
            re.compile(r"\bpopup\b", re.I),
            re.compile(r"\bmodal\b", re.I),
            re.compile(r"\btoast\b", re.I),
            re.compile(r"\bcard\b", re.I),
            re.compile(r"\btsx\b", re.I),
            re.compile(r"\bcss\b", re.I),
            re.compile(r"\bvue\b", re.I),
            re.compile(r"\bparent[- ]facing\b", re.I),
            re.compile(r"\b(?:teacher|parent)s? dashboard\b", re.I),
            re.compile(r"\bcanary build\b", re.I),
            re.compile(r"\bmissing (?:on|in) (?:the )?(?:app|ui|screen|build)\b", re.I),
        ],
    ),
    (
        "frontend",
        2,
        [
            re.compile(r"\bconfirmation\b", re.I),
            re.compile(r"\benrol+ment\b", re.I),
            re.compile(r"\bpopup\b", re.I),
            re.compile(r"\bmodal\b", re.I),
        ],
    ),
    (
        "backend",
        1,
        [
            re.compile(r"\bapi\b", re.I),
            re.compile(r"\bendpoint\b", re.I),
            re.compile(r"\b/api/", re.I),
            re.compile(r"\bservice\b", re.I),
            re.compile(r"\bquality[- ]gate\b", re.I),
            re.compile(r"\bsupabase\b", re.I),
            re.compile(r"\brpc\b", re.I),
            re.compile(r"\bmigration\b", re.I),
            re.compile(r"\bschema\b", re.I),
            re.compile(r"\bpostgres\b", re.I),
            re.compile(r"\bserver\b", re.I),
            re.compile(r"\bdata(?:base)?\b", re.I),
            re.compile(r"\bdata cleanup\b", re.I),
            re.compile(r"\btenant\b", re.I),
            re.compile(r"\bpreschool\b", re.I),
            re.compile(r"\b(?:students?|learners?|children)\b", re.I),
            re.compile(r"\bidempotenc(?:y|e|ent)\b", re.I),
            re.compile(r"\bduplicate assignments?\b", re.I),
            re.compile(r"\bparent[- ]delivery data\b", re.I),
            re.compile(r"\bassignment records?\b", re.I),
        ],
    ),
    (
        "integrations",
        1,
        [
            re.compile(r"\bgithub actions\b", re.I),
            re.compile(r"\bworkflow\b", re.I),
            re.compile(r"\bsecrets?\b", re.I),
            re.compile(r"\brunner\b", re.I),
            re.compile(r"\bself[- ]hosted\b", re.I),
            re.compile(r"\bubuntu-latest\b", re.I),
            re.compile(r"\bsdk\b", re.I),
            re.compile(r"\bconnector\b", re.I),
            re.compile(r"\beas\b", re.I),
            re.compile(r"\bota\b", re.I),
            re.compile(r"\bexpo-cli\b", re.I),
        ],
    ),
    (
        "watcher",
        1,
        [
            re.compile(r"\bsentry\b", re.I),
            re.compile(r"\bsignal\b", re.I),
            re.compile(r"\bhealth\b", re.I),
            re.compile(r"\bred[- ]build\b", re.I),
            re.compile(r"\balert\b", re.I),
            re.compile(r"\bposthog\b", re.I),
        ],
    ),
    (
        "lead",
        1,
        [
            re.compile(r"\bpriorit(?:y|ies)\b", re.I),
            re.compile(r"\btriage\b", re.I),
            re.compile(r"\bproduct direction\b", re.I),
            re.compile(r"\bwho should own\b", re.I),
            re.compile(r"\bhand[- ]?off\b", re.I),
        ],
    ),
]

_PATH_ROLE_HINTS: list[tuple[str, re.Pattern[str], int]] = [
    (
        "frontend",
        re.compile(r"\b(?:app|components|screens|styles)/[\w./-]+\.(?:tsx?|jsx?|vue|css)\b", re.I),
        2,
    ),
    (
        "backend",
        re.compile(r"\b(?:services|api|server|supabase)/[\w./-]+\.(?:ts|py|sql)\b", re.I),
        2,
    ),
    (
        "integrations",
        re.compile(r"\b\.github/workflows/[\w./-]+\.ya?ml\b", re.I),
        2,
    ),
]
