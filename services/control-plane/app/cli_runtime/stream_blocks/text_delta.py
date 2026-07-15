"""Assistant stream text delta deduplication."""

from __future__ import annotations

import re
from difflib import SequenceMatcher

from app.cli_runtime.stream_blocks.transcript_dedupe import collapse_duplicated_body


def _collapse_echo_text(text: str) -> str:
    """Drop a single-chunk assistant payload that repeats itself back-to-back."""
    return collapse_duplicated_body(text)


def _norm_stream_text(text: str) -> str:
    cleaned = re.sub(r"\s+", " ", text or "").strip().lstrip("'\"“”").lower()
    cleaned = re.sub(r"^i['']?ve\b", "ve", cleaned)
    cleaned = re.sub(r"^ve\b", "ve", cleaned)
    cleaned = re.sub(r"^i\s+", "", cleaned)
    return cleaned.strip()


def assistant_text_delta(accumulated: str, incoming: str) -> str:
    """Return only the suffix of *incoming* that is not already in *accumulated*.

    Cursor CLI with ``--stream-partial-output`` emits incremental assistant chunks
    (e.g. ``hello``, `` world``) and then a final aggregate event (``hello world``).
    Appending every event verbatim duplicates the full reply.
    """
    incoming = collapse_duplicated_body(incoming)
    if not incoming:
        return ""
    if incoming == accumulated:
        return ""
    if accumulated:
        norm_acc = _norm_stream_text(accumulated)
        norm_in = _norm_stream_text(incoming)
        if norm_acc and norm_acc == norm_in:
            return ""
        # Partial aggregate already present in the reply (often glued later).
        if len(incoming) >= 80 and len(accumulated) >= 80:
            semantic_acc = re.sub(r"\W+", "", accumulated).lower()
            semantic_in = re.sub(r"\W+", "", incoming).lower()
            if len(semantic_in) >= 60 and semantic_in in semantic_acc:
                return ""
            collapsed_append = collapse_duplicated_body(accumulated + incoming)
            if collapsed_append.strip() == accumulated.strip():
                return ""
        if len(accumulated) >= 200 and len(incoming) >= 200:
            semantic_acc = re.sub(r"\W+", "", accumulated).lower()
            semantic_in = re.sub(r"\W+", "", incoming).lower()
            similarity = SequenceMatcher(None, semantic_acc, semantic_in).ratio()
            hypothesis_counts_match = len(
                re.findall(r"\bH\d+\b", accumulated)
            ) == len(re.findall(r"\bH\d+\b", incoming))
            reproduce_counts_match = accumulated.count(
                ":::debug-reproduce"
            ) == incoming.count(":::debug-reproduce")
            if (
                similarity >= 0.86
                and hypothesis_counts_match
                and reproduce_counts_match
            ):
                # Cursor can emit token deltas followed by a formatted aggregate
                # of the same Debug reply. Appending that aggregate repeats the
                # complete hypothesis/reproduce section.
                return ""
        # Near-echo with a short prefix difference ("I " / leading apostrophe).
        if norm_in.endswith(norm_acc) and 0 < len(norm_in) - len(norm_acc) <= 4:
            return ""
        if norm_acc.endswith(norm_in) and 0 < len(norm_acc) - len(norm_in) <= 4:
            return ""
    if accumulated and incoming.startswith(accumulated):
        suffix = incoming[len(accumulated) :]
        if not suffix:
            return ""
        if suffix == accumulated or suffix.strip() == accumulated.strip():
            return ""
        collapsed_combined = collapse_duplicated_body(accumulated + suffix)
        if collapsed_combined.strip() == accumulated.strip():
            return ""
        return suffix
    if accumulated and accumulated.startswith(incoming):
        return ""
    return incoming
