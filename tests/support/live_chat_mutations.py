"""Guards that keep live acceptance tests from polluting operator chat threads.

Live POST /api/chat/messages with ``git status`` appends real operator/agent
messages to workspace threads the IDE shows. Agents running verify scripts
against a live control-plane repeatedly created paired ``Git status`` runs the
operator never asked for.

Opt in explicitly:

  AXON_ALLOW_LIVE_CHAT_MUTATIONS=1 python3 -m unittest tests.test_parity_d4_multi_project
"""

from __future__ import annotations

import os


def live_chat_mutations_allowed() -> bool:
    return os.environ.get("AXON_ALLOW_LIVE_CHAT_MUTATIONS", "").strip() in {
        "1",
        "true",
        "yes",
        "on",
    }


LIVE_CHAT_MUTATION_SKIP_REASON = (
    "set AXON_ALLOW_LIVE_CHAT_MUTATIONS=1 to POST chat into the live control-plane "
    "(avoids polluting operator threads with git status probes)"
)
