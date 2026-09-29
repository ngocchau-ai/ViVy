"""Eval item schema for the T2 measurement set (WP-7 / O-02).

One eval item is a question with a **programmatically checkable** answer.  The
checker never looks for a substring in prose; it parses a declared answer line
and compares by kind (number / set / expression / text / insufficient).

D-7 (29/09/2026): the held-out half of the set is **not kept in this repo**.
``generate.py`` materialises it to a path outside ``Vivy_final/`` and this
module's ``canonical_json`` / ``sha256_item`` are what the committed manifest
records, so the harness can prove the owner-supplied file is the real one.

Changelog:
    29/09/2026 (Claude Code — WP-7/O-02): Initial.
"""

from __future__ import annotations

import hashlib
import json
from collections.abc import Iterable, Mapping, Sequence
from dataclasses import asdict, dataclass, field
from typing import Any

#: The four measured domains (plan: "4 miền × 30").
DOMAINS: tuple[str, ...] = ("quantum", "math", "graph", "compute")

#: Dev is what the repo holds and what anyone may tune on.  Held-out is the
#: scoring half and is kept by the project owner (D-7).
SPLITS: tuple[str, ...] = ("dev", "heldout")

#: ``adversarial`` items are answerable only by refusing: the question is
#: underdetermined or omits the one datum it needs.
KINDS: tuple[str, ...] = ("answerable", "adversarial")

#: How a correct answer is compared.  ``insufficient`` is the adversarial
#: verdict; it is compared by exact token, never by substring.
ANSWER_KINDS: tuple[str, ...] = ("number", "set", "expression", "text", "insufficient")

#: What an adversarial item expects.  A model that names a concrete value here
#: has fabricated one.
INSUFFICIENT = "INSUFFICIENT_EVIDENCE"

#: Format the checker relies on.  Every eval prompt carries this instruction so
#: scoring is parsing, not prose reading.
ANSWER_LINE_INSTRUCTION = (
    "End your reply with exactly one line, on its own:\n"
    "  ANSWER: <value>\n"
    "or, if the question cannot be answered from the information given:\n"
    f"  VERDICT: {INSUFFICIENT}"
)


@dataclass(frozen=True)
class EvalItem:
    """One question with a checkable answer."""

    id: str
    domain: str
    split: str
    kind: str
    prompt: str
    expected: str
    expected_kind: str
    tolerate: float = 0.0
    #: True when the item is adversarial *because* a datum is missing.
    missing_data: bool = False
    notes: str = ""
    #: Free-form tag kept for slicing the report (e.g. "edges", "derivative").
    tags: tuple[str, ...] = field(default_factory=tuple)

    # ------------------------------------------------------------------
    # Serialisation — the hash is over THIS, so it must be stable
    # ------------------------------------------------------------------

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["tags"] = list(self.tags)
        return payload

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> EvalItem:
        data = dict(payload)
        data["tags"] = tuple(data.get("tags") or ())
        item = cls(**data)
        item.validate()
        return item

    def validate(self) -> None:
        if not self.id or not self.id.strip():
            raise ValueError("EvalItem.id must be a non-empty string")
        if self.domain not in DOMAINS:
            raise ValueError(f"{self.id}: domain must be one of {DOMAINS}, got {self.domain!r}")
        if self.split not in SPLITS:
            raise ValueError(f"{self.id}: split must be one of {SPLITS}, got {self.split!r}")
        if self.kind not in KINDS:
            raise ValueError(f"{self.id}: kind must be one of {KINDS}, got {self.kind!r}")
        if self.expected_kind not in ANSWER_KINDS:
            raise ValueError(
                f"{self.id}: expected_kind must be one of {ANSWER_KINDS}, got {self.expected_kind!r}"
            )
        if not self.prompt or not self.prompt.strip():
            raise ValueError(f"{self.id}: prompt must be a non-empty string")
        if not self.expected or not str(self.expected).strip():
            raise ValueError(f"{self.id}: expected must be a non-empty string")
        if self.tolerate < 0:
            raise ValueError(f"{self.id}: tolerate must be >= 0")

        if self.kind == "adversarial":
            if self.expected_kind != "insufficient":
                raise ValueError(
                    f"{self.id}: an adversarial item must expect the insufficient "
                    f"verdict, not {self.expected_kind!r}"
                )
            if self.expected != INSUFFICIENT:
                raise ValueError(
                    f"{self.id}: adversarial expected must be exactly {INSUFFICIENT!r}"
                )
        elif self.expected_kind == "insufficient":
            raise ValueError(
                f"{self.id}: only kind='adversarial' may expect the insufficient verdict"
            )

        if self.expected_kind == "number":
            float(self.expected)  # raises if unparsable
        elif self.tolerate != 0.0:
            raise ValueError(
                f"{self.id}: tolerate is only meaningful for expected_kind='number'"
            )


def canonical_json(item: EvalItem) -> str:
    """Stable serialisation.  The held-out manifest hashes exactly this."""
    return json.dumps(item.to_dict(), sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def sha256_item(item: EvalItem) -> str:
    return hashlib.sha256(canonical_json(item).encode("utf-8")).hexdigest()


def write_jsonl(path: str, items: Sequence[EvalItem]) -> None:
    with open(path, "w", encoding="utf-8") as fh:
        for item in items:
            fh.write(canonical_json(item) + "\n")


def read_jsonl(path: str) -> list[EvalItem]:
    items: list[EvalItem] = []
    with open(path, encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            items.append(EvalItem.from_dict(json.loads(line)))
    return items


def manifest_for(items: Iterable[EvalItem]) -> list[dict[str, Any]]:
    """What the repo commits for held-out: identity + hash, never the prompt.

    The prompt and the expected answer are deliberately absent.  A committed
    manifest cannot leak the answer into a knowledge base, and it still lets the
    harness refuse a substituted file (D-7).
    """
    rows = []
    for item in items:
        rows.append({
            "id": item.id,
            "domain": item.domain,
            "split": item.split,
            "kind": item.kind,
            "expected_kind": item.expected_kind,
            "sha256": sha256_item(item),
        })
    return rows
