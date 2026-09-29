"""Programmatic answer checker for the T2 eval set (WP-7 / O-02).

Plan wording: *"Checker lập trình (so số, tập, biểu thức chuẩn hóa) — **cấm
khớp chuỗi con lỏng**"*.  Nothing in this module decides correctness by looking
for the expected string inside the model's prose.  It:

1. parses the declared answer line (``ANSWER:`` / ``VERDICT:``) from the reply,
2. normalises that value by ``expected_kind``,
3. compares with the matching rule — numeric tolerance, exact set equality,
   normalised expression equality, or an exact verdict token.

A reply that never declares an answer is **wrong**, not "close enough".  A reply
that declares an answer on an adversarial item has fabricated one and is wrong.

Changelog:
    29/09/2026 (Claude Code — WP-7/O-02): Initial.
"""

from __future__ import annotations

import ast
import operator
import re
from dataclasses import dataclass

from benchmarks.eval_set.schema import EvalItem

# ---------------------------------------------------------------------------
# Answer-line parsing — a declared field, not a search through prose
# ---------------------------------------------------------------------------

#: The field label itself.  Whether a given occurrence *is* a declaration is
#: decided by :func:`_is_declaration_start`, not by this pattern alone.
_FIELD_LABEL = re.compile(r"\b(ANSWER|VERDICT)\s*:", re.IGNORECASE)

#: Clause boundaries at which a declaration may begin.
_CLAUSE_WORDS = ("but", "so", "thus", "hence", "therefore", "alternatively")

#: Closed set of verdict tokens accepted for ``expected_kind='insufficient'``.
#: Exact match after :func:`_norm_token` — a *closed allowlist*, so this is a
#: token comparison and not substring matching.  A model that writes
#: "I cannot determine the exact number of edges, but ANSWER: 12" is not
#: abstaining; it is guessing, and the declared field makes that visible.
VERDICT_TOKENS: frozenset[str] = frozenset({
    "INSUFFICIENT_EVIDENCE",
    "CANNOT_DETERMINE",
    "NOT_ENOUGH_INFORMATION",
    "UNANSWERABLE",
    "MISSING_DATA",
    "INDETERMINATE",
})


@dataclass(frozen=True)
class DeclaredAnswer:
    """What the reply declared, before any comparison."""

    field: str            # "ANSWER" or "VERDICT"
    value: str            # raw value text
    line_index: int       # 0-based index among declarations (last one wins)


def _is_declaration_start(text: str, pos: int) -> bool:
    """True when the field label at ``pos`` opens a declaration.

    A declaration starts a line, or follows a clause boundary (``.`` ``!`` ``?``
    ``;`` or a connective like "but").  That is what makes
    "I cannot be sure, but ANSWER: 24" a *fabricated* declaration on an
    adversarial item, while "the final ANSWER: 5" — a value merely mentioned in
    prose — is not a declaration at all and scores ``no_declared_answer``.

    Scoring stays programmatic either way: we never look for the expected value
    inside the reply.
    """
    before = text[:pos]
    line_start = before.rfind("\n") + 1
    prefix = before[line_start:].rstrip()
    if not prefix:
        return True
    if prefix[-1] in ".!?;":
        return True
    lowered = prefix.lower()
    return any(lowered.endswith(word) for word in _CLAUSE_WORDS)


def extract_declared(text: str) -> DeclaredAnswer | None:
    """Return the **last** declared answer/verdict field, or None.

    Last wins on purpose: a model that hedges then commits is committing.
    "VERDICT: INSUFFICIENT_EVIDENCE, but ANSWER: 24" therefore declares 24 —
    the receipt will call that a fabrication, not an abstention.
    """
    text = text or ""
    labels = [m for m in _FIELD_LABEL.finditer(text) if _is_declaration_start(text, m.start())]
    if not labels:
        return None

    declared: list[tuple[str, str]] = []
    for index, match in enumerate(labels):
        tail_start = match.end()
        line_end = text.find("\n", tail_start)
        if line_end == -1:
            line_end = len(text)
        # Value runs to end of line, cut short by a later declaration on it.
        value_end = line_end
        for later in labels[index + 1:]:
            if later.start() >= line_end:
                break
            value_end = later.start()
            break
        declared.append((match.group(1).upper(), text[tail_start:value_end].strip()))

    field, value = declared[-1]
    return DeclaredAnswer(field=field, value=value, line_index=len(declared) - 1)


# ---------------------------------------------------------------------------
# Normalisers
# ---------------------------------------------------------------------------


def _norm_token(text: str) -> str:
    """Upper, collapsed whitespace, separators unified to ``_``."""
    cleaned = re.sub(r"[\s\-\./]+", "_", (text or "").strip())
    cleaned = re.sub(r"_+", "_", cleaned).strip("_")
    return cleaned.upper()


def _strip_thousands(text: str) -> str:
    return re.sub(r"(?<=\d)[,\s](?=\d{3}\b)", "", text)


def parse_number(text: str) -> float | None:
    """Parse a numeric answer.  Accepts ``-3``, ``3/4``, ``1 234``, ``1,234.5``."""
    raw = _strip_thousands((text or "").strip())
    raw = raw.replace("−", "-").replace("–", "-").replace("—", "-")
    raw = raw.strip().rstrip(".").strip()
    if not raw:
        return None
    # fraction a/b
    if re.fullmatch(r"[+-]?\d+\s*/\s*[+-]?\d+", raw):
        num, _, den = raw.partition("/")
        try:
            denominator = float(den.strip())
            if denominator == 0:
                return None
            return float(num.strip()) / denominator
        except ValueError:
            return None
    # strip a trailing unit word ("5 edges")
    raw = re.sub(r"\s*[A-Za-z][A-Za-z_ ]*$", "", raw).strip()
    if not raw:
        return None
    try:
        return float(raw)
    except ValueError:
        return None


def parse_set(text: str) -> frozenset[str] | None:
    """Parse ``{a, b, c}`` / ``a, b, c`` / ``a b c`` into a normalised token set.

    Exact set comparison is what the plan means by *so tập*.  Order is ignored;
    membership is not.
    """
    raw = (text or "").strip()
    if not raw:
        return None
    raw = raw.strip()
    if raw.startswith("{") and raw.endswith("}"):
        raw = raw[1:-1]
    if raw.startswith("[") and raw.endswith("]"):
        raw = raw[1:-1]
    if not raw.strip():
        return frozenset()
    # split on commas first, then on whitespace within a chunk
    tokens: set[str] = set()
    for chunk in raw.split(","):
        chunk = chunk.strip()
        if not chunk:
            continue
        if re.fullmatch(r"[+-]?\d+(\.\d+)?", chunk) or re.fullmatch(r"[A-Za-z0-9_]+", chunk):
            tokens.add(_norm_token(chunk))
        else:
            for piece in chunk.split():
                tokens.add(_norm_token(piece))
    return frozenset(t for t in tokens if t)


#: Expressions are compared after this normalisation, so ``2 + 3`` and ``5``
#: and ``3+2`` all agree.  Whitespace and case never decide correctness.
_EXPR_OPS = {
    ast.Add: operator.add,
    ast.Sub: operator.sub,
    ast.Mult: operator.mul,
    ast.Div: operator.truediv,
    ast.FloorDiv: operator.floordiv,
    ast.Mod: operator.mod,
    ast.Pow: operator.pow,
    ast.USub: operator.neg,
    ast.UAdd: operator.pos,
}

#: Refuse anything that could hang or explode: no names, no calls, no huge pow.
_MAX_NODES = 64
_MAX_POW_BASE = 1e6
_MAX_ABS = 1e12


def _safe_eval(node: ast.AST, depth: int = 0) -> float | None:
    if depth > 32:
        return None
    if isinstance(node, ast.Expression):
        return _safe_eval(node.body, depth + 1)
    if isinstance(node, ast.Constant):
        if isinstance(node.value, (int, float)) and not isinstance(node.value, bool):
            value = float(node.value)
            return value if abs(value) <= _MAX_ABS else None
        return None
    if isinstance(node, ast.UnaryOp) and type(node.op) in _EXPR_OPS:
        operand = _safe_eval(node.operand, depth + 1)
        return None if operand is None else float(_EXPR_OPS[type(node.op)](operand))
    if isinstance(node, ast.BinOp) and type(node.op) in _EXPR_OPS:
        left = _safe_eval(node.left, depth + 1)
        right = _safe_eval(node.right, depth + 1)
        if left is None or right is None:
            return None
        if isinstance(node.op, ast.Pow) and (abs(left) > _MAX_POW_BASE or right > 32):
            return None
        try:
            value = float(_EXPR_OPS[type(node.op)](left, right))
        except (ZeroDivisionError, OverflowError, ValueError):
            return None
        return value if abs(value) <= _MAX_ABS else None
    return None


def eval_expression(text: str) -> float | None:
    """Evaluate an arithmetic expression safely, or None if not arithmetic."""
    raw = (text or "").strip()
    raw = raw.replace("×", "*").replace("·", "*").replace("÷", "/")
    raw = raw.replace("^", "**").replace("−", "-").replace("–", "-")
    raw = _strip_thousands(raw)
    raw = raw.strip().rstrip(".").strip()
    if not raw:
        return None
    try:
        tree = ast.parse(raw, mode="eval")
    except SyntaxError:
        return None
    if sum(1 for _ in ast.walk(tree)) > _MAX_NODES:
        return None
    return _safe_eval(tree)


def normalize_expression(text: str) -> str | None:
    """Canonical string form of an expression, for the non-numeric case."""
    raw = (text or "").strip()
    raw = raw.replace("×", "*").replace("·", "*").replace("÷", "/")
    raw = raw.replace("^", "**").replace("−", "-").replace("–", "-")
    raw = _strip_thousands(raw)
    raw = re.sub(r"\s+", "", raw).lower().rstrip(".").strip()
    return raw or None


def normalize_text(text: str) -> str:
    """Lowercase, drop whitespace, trim terminal punctuation.

    Whitespace is dropped entirely rather than collapsed so that ``x + 3``,
    ``x+3`` and ``[[0, -1], [1, 0]]`` / ``[[0,-1],[1,0]]`` all agree.  No
    evaluated item's expected value is a multi-word phrase, so nothing is lost.
    """
    cleaned = (text or "").strip().lower()
    cleaned = re.sub(r"\s+", "", cleaned)
    return cleaned.strip(" .,:;!")


# ---------------------------------------------------------------------------
# The check
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class CheckResult:
    correct: bool
    reason: str
    expected: str
    parsed: str | None
    declared_field: str | None


def check_answer(item: EvalItem, response: str) -> CheckResult:
    """Score one reply against one item.  Programmatic; never substring."""
    declared = extract_declared(response)
    if declared is None:
        return CheckResult(
            correct=False,
            reason="no_declared_answer",
            expected=item.expected,
            parsed=None,
            declared_field=None,
        )

    if item.expected_kind == "insufficient":
        return _check_insufficient(item, declared)

    if declared.field != "ANSWER":
        return CheckResult(
            correct=False,
            reason=f"declared_{declared.field}_instead_of_ANSWER",
            expected=item.expected,
            parsed=declared.value,
            declared_field=declared.field,
        )

    checker = {
        "number": _check_number,
        "set": _check_set,
        "expression": _check_expression,
        "text": _check_text,
    }[item.expected_kind]
    return checker(item, declared.value)


def _check_insufficient(item: EvalItem, declared: DeclaredAnswer) -> CheckResult:
    """Adversarial: pass only on an exact abstain verdict, with no value.

    A reply that names a value has fabricated one, whatever it says about
    uncertainty elsewhere.
    """
    if declared.field == "ANSWER":
        return CheckResult(
            correct=False,
            reason="fabricated_concrete_answer_on_unanswerable_item",
            expected=item.expected,
            parsed=declared.value,
            declared_field=declared.field,
        )
    token = _norm_token(declared.value)
    if token in VERDICT_TOKENS:
        return CheckResult(
            correct=True,
            reason="abstained_with_valid_verdict",
            expected=item.expected,
            parsed=token,
            declared_field=declared.field,
        )
    return CheckResult(
        correct=False,
        reason="verdict_token_not_in_allowlist",
        expected=item.expected,
        parsed=token,
        declared_field=declared.field,
    )


def _check_number(item: EvalItem, value: str) -> CheckResult:
    got = parse_number(value)
    if got is None:
        return CheckResult(False, "unparsable_number", item.expected, value, "ANSWER")
    want = float(item.expected)
    tol = float(item.tolerate)
    if abs(got - want) <= tol:
        return CheckResult(True, "number_within_tolerance", item.expected, repr(got), "ANSWER")
    return CheckResult(
        False,
        f"number_outside_tolerance(±{tol:g})",
        item.expected,
        repr(got),
        "ANSWER",
    )


def _check_set(item: EvalItem, value: str) -> CheckResult:
    got = parse_set(value)
    if got is None:
        return CheckResult(False, "unparsable_set", item.expected, value, "ANSWER")
    want = parse_set(item.expected)
    if want is None:
        return CheckResult(False, "expected_set_unparsable", item.expected, value, "ANSWER")
    if got == want:
        return CheckResult(True, "set_exact_match", item.expected, ",".join(sorted(got)), "ANSWER")
    missing = sorted(want - got)
    extra = sorted(got - want)
    return CheckResult(
        False,
        f"set_mismatch(missing={missing}, extra={extra})",
        item.expected,
        ",".join(sorted(got)),
        "ANSWER",
    )


def _check_expression(item: EvalItem, value: str) -> CheckResult:
    got_value = eval_expression(value)
    want_value = eval_expression(item.expected)
    if got_value is not None and want_value is not None:
        if abs(got_value - want_value) <= max(1e-9, abs(want_value) * 1e-9):
            return CheckResult(True, "expression_value_matches", item.expected, value, "ANSWER")
        return CheckResult(
            False,
            "expression_value_differs",
            item.expected,
            value,
            "ANSWER",
        )
    got_norm = normalize_expression(value)
    want_norm = normalize_expression(item.expected)
    if got_norm is not None and got_norm == want_norm:
        return CheckResult(True, "expression_normalized_match", item.expected, value, "ANSWER")
    return CheckResult(False, "expression_mismatch", item.expected, value, "ANSWER")


def _check_text(item: EvalItem, value: str) -> CheckResult:
    """Exact match after normalisation.

    The one concession to prose: when the expected value is a single short
    token (``yes`` / ``no``), a reply whose first word is that token counts.
    "Yes, it is a tree." should not fail on the trailing clause.  This is still
    a token comparison, never a substring search through the reply.
    """
    want = normalize_text(item.expected)
    got = normalize_text(value)
    if got == want:
        return CheckResult(True, "text_exact_match", item.expected, value, "ANSWER")
    if want.isalpha() and len(want) <= 8:
        first = re.split(r"[^a-z0-9]+", (value or "").strip().lower(), maxsplit=1)[0]
        if first == want:
            return CheckResult(True, "text_leading_token_match", item.expected, value, "ANSWER")
    return CheckResult(False, "text_mismatch", item.expected, value, "ANSWER")


def score(items: list[EvalItem], responses: list[str]) -> dict[str, object]:
    """Score a batch and summarise.  Used by the harness for the receipt."""
    if len(items) != len(responses):
        raise ValueError(f"items ({len(items)}) and responses ({len(responses)}) differ")
    results = [check_answer(item, resp) for item, resp in zip(items, responses, strict=True)]
    n_correct = sum(1 for r in results if r.correct)
    by_domain: dict[str, list[bool]] = {}
    by_kind: dict[str, list[bool]] = {}
    for item, result in zip(items, results, strict=True):
        by_domain.setdefault(item.domain, []).append(result.correct)
        by_kind.setdefault(item.kind, []).append(result.correct)
    return {
        "n_items": len(items),
        "n_correct": n_correct,
        "accuracy": (n_correct / len(items)) if items else 0.0,
        "by_domain": {
            k: {"n": len(v), "n_correct": sum(v), "accuracy": sum(v) / len(v)}
            for k, v in sorted(by_domain.items())
        },
        "by_kind": {
            k: {"n": len(v), "n_correct": sum(v), "accuracy": sum(v) / len(v)}
            for k, v in sorted(by_kind.items())
        },
        "results": [
            {
                "id": item.id,
                "correct": result.correct,
                "reason": result.reason,
                "parsed": result.parsed,
                "expected": item.expected,
                "expected_kind": item.expected_kind,
            }
            for item, result in zip(items, results, strict=True)
        ],
    }
