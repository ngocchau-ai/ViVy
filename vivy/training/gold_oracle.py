"""Deterministic gold-label proposer over goal text + candidate semantics.

Independence contract: this module NEVER receives, reads, or is influenced by
the legacy `selected_candidate`. Its only inputs are `context_state` and
`candidates`. Callers that need to compare against the legacy label must do so
after `propose()` returns.

The oracle is a proposer, not ground truth. A human remains the labeler of
record (see evidence/GOLD_TRIAGE_RUNBOOK.md).
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any, Mapping, Sequence

RULE_VERSION = "gold_rules_v1"

# Rule ids and the tier each one claims when it is the only rule that fired.
# When several rules agree on one candidate the proposal keeps the weakest tier
# among them, so a strong rule cannot launder a weak one.
RULE_TIERS = {
    "R1_SAFETY_ABSTAIN": "A_strong",
    "R2_GOAL_VERB_UNIQUE": "A_strong",
    "R3_GOAL_PROHIBITION": "A_strong",
    "R4_NONDESTRUCTIVE_PREFER": "A_weak",
    "R5_EXEC_WHEN_PRECONDITION_OBSERVED": "A_template",
}
_TIER_STRENGTH = {"A_strong": 3, "A_weak": 2, "A_template": 1, "C": 0}

RATIONALE_BY_RULE = {
    "R1_SAFETY_ABSTAIN": "SAFETY_ABSTAIN",
    "R2_GOAL_VERB_UNIQUE": "GOAL_VERB_UNIQUE_MATCH",
    "R3_GOAL_PROHIBITION": "GOAL_PROHIBITION_AVOID",
    "R4_NONDESTRUCTIVE_PREFER": "MINIMAL_DESTRUCTION",
    "R5_EXEC_WHEN_PRECONDITION_OBSERVED": "EXEC_PRECONDITION_OBSERVED",
}

ACTION_TAG = re.compile(r"\(action:\s*([a-z0-9_]+)\)", re.I)

DESTRUCTIVE_ACTIONS = frozenset({"delete", "kill"})
DESTRUCTIVE_WORDS = frozenset({"wipe", "force", "abort", "delete", "kill", "erase"})
RECOVERY_ACTIONS = frozenset({"retry", "read", "screenshot"})
RECOVERY_WORDS = frozenset({"retry", "backoff", "read", "reobserve", "wait", "capture", "inspect"})

HALT_WORDS = frozenset({"halt", "abstain", "pause", "stop"})
HALT_HUMAN_WORDS = frozenset({"halt", "abstain", "human", "confirmation", "request", "authorization", "unmet"})
FORCE_CONFIRM_WORDS = frozenset({"force", "confirm", "authorization", "unauthorized", "instant", "market", "order", "buy", "trade"})

UNSAFE_GOAL_MARKERS = (
    "unsafe", "unknown executable", "untrusted", "security dialog",
    "critical security", "without authorization", "unauthorized",
)
PROHIBITION_PATTERNS = (
    re.compile(r"\bwithout\s+(?:placing\s+|stealing\s+|doing\s+)?([a-z][a-z0-9_\- ]{2,40})", re.I),
    re.compile(r"\bdo\s+not\s+([a-z][a-z0-9_\- ]{2,40})", re.I),
    re.compile(r"\bnever\s+([a-z][a-z0-9_\- ]{2,40})", re.I),
    re.compile(r"\bavoid\s+([a-z][a-z0-9_\- ]{2,40})", re.I),
)

TEMPLATE_GOAL = re.compile(r"^Execute automated bounded workspace task #(\d+)$", re.I)
TEMPLATE_OBSERVATION = re.compile(
    r"Workspace desktop window #(\d+) rendered with active GUI elements", re.I
)
TEMPLATE_EXEC = re.compile(r"_exec$", re.I)
TEMPLATE_HALT = re.compile(r"_halt$", re.I)

STOPWORDS = frozenset(
    "a an and as at be by for from has have if in into is it its of on or "
    "the to via was were will with without during then than this that "
    "current while when where what which who how".split()
)

# Verb-alias groups only. Nouns must match by exact or 5-char prefix; putting
# nouns in these groups makes e.g. "login" match "click" and breaks uniqueness.
SYNONYM_GROUPS = (
    frozenset({"run", "execute", "verify", "verification", "verified", "test", "suite", "check"}),
    frozenset({"switch", "focus", "activate", "terminal", "powershell", "console", "shell"}),
    frozenset({"save", "saving", "write", "persist"}),
    frozenset({"click", "press"}),
    frozenset({"timeout", "retry", "backoff", "recover", "resume", "wait", "handle"}),
    frozenset({"wipe", "abort", "delete", "erase"}),
    frozenset({"inspect", "read", "view", "capture", "observe"}),
    frozenset({"trade", "buy", "purchase", "market"}),
    frozenset({"reobserve", "screenshot", "observe"}),
    frozenset({"export", "print"}),
    frozenset({"close", "discard", "drop"}),
    frozenset({"kill", "terminate"}),
)


@dataclass(frozen=True)
class OracleProposal:
    proposed_selected_candidate: str | None
    rule_ids: tuple[str, ...]
    rationale_code: str
    tier: str
    rule_version: str
    conflict: bool


def propose(context_state: str, candidates: Sequence[Mapping[str, Any]]) -> OracleProposal:
    """Deterministic policy over goal text + candidate semantics ONLY.

    Never receives, reads, or is influenced by selected_candidate (enforced by
    signature + tests). Returns proposed_selected_candidate=None when rules do
    not uniquely determine a candidate, or when rules conflict.
    """
    goal, observation = _split_context(context_state)
    violators = _prohibition_violators(goal, candidates)
    # Hard constraint first: a candidate that violates an explicit prohibition
    # is never proposed by the softer verb-overlap / preference rules.
    soft_pool = [c for c in candidates if str(c.get("id")) not in violators]

    fires: list[tuple[str, str]] = []  # (rule_id, candidate_id)
    fires.extend(_match_safety_abstain(goal, soft_pool))
    fires.extend(_match_goal_prohibition(goal, candidates))
    fires.extend(_match_goal_verb_unique(goal, soft_pool))
    fires.extend(_match_nondestructive_prefer(goal, soft_pool))
    fires.extend(_match_exec_template(goal, observation, soft_pool))

    if not fires:
        return OracleProposal(None, (), "AMBIGUOUS", "C", RULE_VERSION, False)

    rule_ids = tuple(sorted({rule for rule, _ in fires}))
    picked = {cid for _, cid in fires}
    if len(picked) > 1:
        return OracleProposal(None, rule_ids, "RULE_CONFLICT", "C", RULE_VERSION, True)

    chosen = picked.pop()
    ids = {str(c.get("id")) for c in candidates}
    if chosen not in ids:
        return OracleProposal(None, rule_ids, "AMBIGUOUS", "C", RULE_VERSION, False)

    tier = min((RULE_TIERS[r] for r in rule_ids), key=lambda t: _TIER_STRENGTH[t])
    rationale = RATIONALE_BY_RULE[rule_ids[0]] if len(rule_ids) == 1 else "MULTI_RULE_AGREE"
    return OracleProposal(chosen, rule_ids, rationale, tier, RULE_VERSION, False)


def _split_context(context_state: str) -> tuple[str, str]:
    goal, observation = "", ""
    for line in str(context_state).splitlines():
        stripped = line.strip()
        if stripped.lower().startswith("task goal:"):
            goal = stripped.split(":", 1)[1].strip()
        elif stripped.lower().startswith("observation context:"):
            observation = stripped.split(":", 1)[1].strip()
    return goal, observation


def _action_of(candidate: Mapping[str, Any]) -> str:
    match = ACTION_TAG.search(str(candidate.get("description", "")))
    return match.group(1).lower() if match else ""


def _tokens(text: str) -> list[str]:
    return [w for w in re.findall(r"[a-z0-9]+", str(text).lower()) if len(w) >= 3 and w not in STOPWORDS]


def _tokens_match(a: str, b: str) -> bool:
    if a == b:
        return True
    n = min(5, len(a), len(b))
    if n >= 5 or (len(a) < 5 and len(b) < 5 and n >= 3):
        if a[:n] == b[:n]:
            return True
    for group in SYNONYM_GROUPS:
        if a in group and b in group:
            return True
    return False


def _overlap_score(goal_tokens: Sequence[str], description: str) -> int:
    cand_tokens = _tokens(description)
    score = 0
    for g in goal_tokens:
        if any(_tokens_match(g, c) for c in cand_tokens):
            score += 1
    return score


def _match_safety_abstain(goal: str, candidates: Sequence[Mapping[str, Any]]) -> list[tuple[str, str]]:
    if not candidates:
        return []
    goal_l = goal.lower()
    if not any(marker in goal_l for marker in UNSAFE_GOAL_MARKERS):
        return []
    halt_ids, force_ids = [], []
    for candidate in candidates:
        desc = str(candidate.get("description", "")).lower()
        action = _action_of(candidate)
        cid = str(candidate.get("id"))
        words = set(_tokens(desc))
        if action == "halt" or (words & HALT_HUMAN_WORDS and words & HALT_WORDS) or "abstain" in words or "halt" in words:
            halt_ids.append(cid)
        if action in {"click", "trade_buy"} and (words & {"force", "unauthorized", "instant", "market", "buy", "trade"}):
            force_ids.append(cid)
        elif words & {"force", "confirm"} and words & {"authorization", "unauthorized"}:
            force_ids.append(cid)
    if halt_ids and force_ids and len(halt_ids) == 1:
        return [("R1_SAFETY_ABSTAIN", halt_ids[0])]
    return []


def _prohibited_tokens(goal: str) -> set[str]:
    goal_l = goal.lower()
    prohibited: set[str] = set()
    for pattern in PROHIBITION_PATTERNS:
        for match in pattern.finditer(goal_l):
            prohibited |= set(_tokens(match.group(1)))
    # "avoid X" is only a prohibition when X names a harmful action, not a step.
    if prohibited and not any(p in goal_l for p in ("without", "do not", "never")):
        risky = {"trade", "buy", "purchase", "delete", "wipe", "kill", "force", "confirm", "execute", "order"}
        if not (prohibited & risky):
            prohibited = set()
    return prohibited


def _prohibition_violators(goal: str, candidates: Sequence[Mapping[str, Any]]) -> set[str]:
    prohibited = _prohibited_tokens(goal)
    if not prohibited:
        return set()
    violators: set[str] = set()
    risky_actions = {"trade_buy", "delete", "kill"}
    risky_words = {"trade", "buy", "purchase", "market", "order", "delete", "wipe", "kill", "force", "confirm"}
    for candidate in candidates:
        desc = str(candidate.get("description", "")).lower()
        action = _action_of(candidate)
        words = set(_tokens(desc)) | {action}
        if action in risky_actions or (words & prohibited and words & risky_words):
            violators.add(str(candidate.get("id")))
    return violators


def _match_goal_prohibition(goal: str, candidates: Sequence[Mapping[str, Any]]) -> list[tuple[str, str]]:
    prohibited = _prohibited_tokens(goal)
    if not prohibited:
        return []
    violators = _prohibition_violators(goal, candidates)
    clean = [str(c.get("id")) for c in candidates if str(c.get("id")) not in violators]
    if violators and len(clean) == 1:
        return [("R3_GOAL_PROHIBITION", clean[0])]
    return []


def _match_goal_verb_unique(goal: str, candidates: Sequence[Mapping[str, Any]]) -> list[tuple[str, str]]:
    if not candidates:
        return []
    goal_tokens = _tokens(goal)
    if not goal_tokens:
        return []
    scored = [
        (str(c.get("id")), _overlap_score(goal_tokens, str(c.get("description", ""))))
        for c in candidates
    ]
    best = max(scored, key=lambda item: item[1])[1]
    if best < 2:
        return []
    winners = [cid for cid, score in scored if score == best]
    if len(winners) != 1:
        return []
    others = [score for cid, score in scored if cid != winners[0]]
    if others and max(others) >= best:
        return []
    return [("R2_GOAL_VERB_UNIQUE", winners[0])]


def _match_nondestructive_prefer(goal: str, candidates: Sequence[Mapping[str, Any]]) -> list[tuple[str, str]]:
    if not candidates:
        return []
    goal_l = goal.lower()
    destructive_ids, recovery_ids = [], []
    for candidate in candidates:
        desc = str(candidate.get("description", "")).lower()
        action = _action_of(candidate)
        cid = str(candidate.get("id"))
        words = set(_tokens(desc))
        is_destructive = action in DESTRUCTIVE_ACTIONS or bool(words & DESTRUCTIVE_WORDS) or action == "delete"
        is_recovery = action in RECOVERY_ACTIONS or bool(words & RECOVERY_WORDS)
        if is_destructive and not is_recovery:
            destructive_ids.append(cid)
        if is_recovery and not is_destructive:
            recovery_ids.append(cid)
    if not destructive_ids or not recovery_ids:
        return []
    # Goal must not itself demand the destructive action (literal verb only —
    # synonym matching would treat "download" as demanding "wipe").
    goal_words = set(_tokens(goal))
    if goal_words & DESTRUCTIVE_WORDS:
        return []
    if len(recovery_ids) == 1:
        return [("R4_NONDESTRUCTIVE_PREFER", recovery_ids[0])]
    return []


def _match_exec_template(goal: str, observation: str, candidates: Sequence[Mapping[str, Any]]) -> list[tuple[str, str]]:
    if not candidates:
        return []
    goal_match = TEMPLATE_GOAL.match(goal.strip())
    obs_match = TEMPLATE_OBSERVATION.search(observation)
    if not goal_match or not obs_match:
        return []
    if goal_match.group(1) != obs_match.group(1):
        return []
    if len(candidates) != 2:
        return []
    exec_ids = [str(c.get("id")) for c in candidates if TEMPLATE_EXEC.search(str(c.get("id")))]
    halt_ids = [str(c.get("id")) for c in candidates if TEMPLATE_HALT.search(str(c.get("id")))]
    if len(exec_ids) == 1 and len(halt_ids) == 1:
        return [("R5_EXEC_WHEN_PRECONDITION_OBSERVED", exec_ids[0])]
    return []
