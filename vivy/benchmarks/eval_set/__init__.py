"""T2 eval set (WP-7 / O-02).

Exports the item schema and the helpers the harness and the tests need.  The
generator lives in :mod:`benchmarks.eval_set.generate`; the answer checker lives
one level up in :mod:`benchmarks.checker` because it is shared with the harness.

Changelog:
    29/09/2026 (Claude Code — WP-7/O-02): Initial.
"""

from benchmarks.eval_set.schema import (
    ANSWER_KINDS,
    ANSWER_LINE_INSTRUCTION,
    DOMAINS,
    INSUFFICIENT,
    KINDS,
    SPLITS,
    EvalItem,
    canonical_json,
    manifest_for,
    read_jsonl,
    sha256_item,
    write_jsonl,
)

__all__ = [
    "ANSWER_KINDS",
    "ANSWER_LINE_INSTRUCTION",
    "DOMAINS",
    "INSUFFICIENT",
    "KINDS",
    "SPLITS",
    "EvalItem",
    "canonical_json",
    "manifest_for",
    "read_jsonl",
    "sha256_item",
    "write_jsonl",
]
