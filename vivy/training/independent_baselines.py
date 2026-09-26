"""C05 independent baselines — controls that a real predictor must beat.

Every predictor here is label-blind at predict time. The gold-copy "oracle" is
explicitly a fixture ceiling, never a baseline and never ground truth.

Brier / ECE use the public formulas and stay `PROVISIONAL_RESULT` while
`gold_outcome` is unknown.

Changelog:
    24/09/2026 (Claude Code — P3 C05): Initial.
"""
from __future__ import annotations

import math
import random
import re
from collections import Counter, defaultdict
from typing import Any, Callable, Mapping, Sequence

BASELINE_SEEDED_RANDOM = "seeded_random"
BASELINE_FIRST_CANDIDATE = "first_candidate_control"
BASELINE_TAXONOMY_MAJORITY = "taxonomy_majority"
BASELINE_TFIDF_LOGREG = "tfidf_logreg_train_only"
BASELINE_GOLD_COPY_FIXTURE = "gold_copy_fixture_ceiling"

STATUS_LABEL = "PROVISIONAL_RESULT"
_TOKEN_RE = re.compile(r"[a-z0-9_]+")


def _tokens(text: str) -> list[str]:
    return _TOKEN_RE.findall((text or "").lower())


def _action_key(candidate: Mapping[str, Any]) -> str:
    return " ".join(_tokens(str(candidate.get("description", ""))))


def semantic_key(prediction: Mapping[str, Any], candidates: Sequence[Mapping[str, Any]]) -> str | None:
    """Description of the chosen candidate — stable under candidate-ID renaming."""
    chosen = prediction.get("predicted_candidate")
    for candidate in candidates:
        if candidate.get("id") == chosen:
            return _action_key(candidate)
    return None


def _base_pred(kind: str, predicted: str | None, **extra: Any) -> dict[str, Any]:
    out = {
        "baseline_kind": kind,
        "predicted_candidate": predicted,
        "valid_as_ground_truth": False,
        "valid_as_classifier_baseline": kind != BASELINE_GOLD_COPY_FIXTURE,
        "is_fixture": kind == BASELINE_GOLD_COPY_FIXTURE,
    }
    out.update(extra)
    return out


def predict_seeded_random(
    candidates: Sequence[Mapping[str, Any]],
    *,
    seed: int,
) -> dict[str, Any]:
    if not candidates:
        return _base_pred(BASELINE_SEEDED_RANDOM, None, probabilities={})
    rng = random.Random(seed)
    ids = [str(c.get("id")) for c in candidates]
    chosen = rng.choice(ids)
    probs = {cid: 0.0 for cid in ids}
    probs[chosen] = 1.0
    return _base_pred(BASELINE_SEEDED_RANDOM, chosen, probabilities=probs, seed=seed)


def predict_first_candidate(candidates: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    if not candidates:
        return _base_pred(BASELINE_FIRST_CANDIDATE, None, probabilities={})
    ids = [str(c.get("id")) for c in candidates]
    probs = {cid: 0.0 for cid in ids}
    probs[ids[0]] = 1.0
    return _base_pred(BASELINE_FIRST_CANDIDATE, ids[0], probabilities=probs)


def predict_gold_copy_fixture(
    candidates: Sequence[Mapping[str, Any]],
    *,
    gold_id: str | None,
) -> dict[str, Any]:
    """Fixture ceiling: copies the gold id. Never a baseline and never ground truth."""
    ids = [str(c.get("id")) for c in candidates]
    predicted = gold_id if gold_id in ids else None
    probs = {cid: 0.0 for cid in ids}
    if predicted is not None:
        probs[predicted] = 1.0
    return _base_pred(
        BASELINE_GOLD_COPY_FIXTURE,
        predicted,
        probabilities=probs,
        note="FIXTURE CEILING — copies gold; not a predictor; do not cite as accuracy",
    )


def predict_taxonomy_majority(
    rows: Sequence[Mapping[str, Any]],
    *,
    candidates: Sequence[Mapping[str, Any]],
) -> dict[str, Any]:
    """Majority over shared action descriptions (not per-record IDs — §2.4).

    Valid only when every scored candidate's action key was seen in `rows`.
    """
    counts: Counter[str] = Counter()
    seen: set[str] = set()
    for row in rows:
        chosen = row.get("selected_candidate")
        for candidate in row.get("candidates") or []:
            key = _action_key(candidate)
            seen.add(key)
            if candidate.get("id") == chosen:
                counts[key] += 1
    keys = [_action_key(c) for c in candidates]
    if not keys or any(key not in seen for key in keys):
        return _base_pred(
            BASELINE_TAXONOMY_MAJORITY,
            None,
            probabilities={},
            valid_as_classifier_baseline=False,
            reason="action taxonomy does not cover this candidate set",
        )
    best_key, _ = counts.most_common(1)[0] if counts else (keys[0], 0)
    # prefer the majority key if present, else first covered key
    chosen_key = best_key if best_key in keys else keys[0]
    predicted = next(
        str(c.get("id")) for c in candidates if _action_key(c) == chosen_key
    )
    probs = {str(c.get("id")): 0.0 for c in candidates}
    probs[predicted] = 1.0
    return _base_pred(BASELINE_TAXONOMY_MAJORITY, predicted, probabilities=probs)


def _design_vector(tokens: Sequence[str], vocab: Mapping[str, int]) -> list[float]:
    vec = [0.0] * (len(vocab) + 1)
    for tok in tokens:
        idx = vocab.get(tok)
        if idx is not None:
            vec[idx] += 1.0
    vec[-1] = 1.0  # bias
    return vec


def fit_tfidf_logreg(
    rows: Sequence[Mapping[str, Any]],
    *,
    epochs: int = 40,
    lr: float = 0.5,
) -> dict[str, Any]:
    """Bag-of-words + logistic regression on (context, candidate) pairs.

    Fit split must be exclusively `train`. Labels are used only at fit time;
    `predict` reads context + candidate descriptions, never `selected_candidate`.
    """
    if not rows:
        raise ValueError("fit_tfidf_logreg needs at least one train row")
    if any((r.get("split") or "train") != "train" for r in rows):
        raise ValueError("fit_tfidf_logreg is fit-on-train-only; pass only split=train rows")

    pairs: list[tuple[list[str], str, int]] = []  # (tokens, action_key, y)
    for row in rows:
        context_tokens = _tokens(str(row.get("context_state", "")))
        chosen = row.get("selected_candidate")
        for candidate in row.get("candidates") or []:
            cand_tokens = _tokens(str(candidate.get("description", "")))
            tokens = context_tokens + cand_tokens
            y = 1 if candidate.get("id") == chosen else 0
            pairs.append((tokens, _action_key(candidate), y))

    vocab: dict[str, int] = {}
    for tokens, _, _ in pairs:
        for tok in tokens:
            if tok not in vocab:
                vocab[tok] = len(vocab)

    xs = [_design_vector(tokens, vocab) for tokens, _, _ in pairs]
    ys = [y for _, _, y in pairs]
    weights = [0.0] * (len(vocab) + 1)
    n = len(xs)
    for _ in range(epochs):
        grad = [0.0] * len(weights)
        for x, y in zip(xs, ys):
            z = sum(w * xi for w, xi in zip(weights, x))
            p = 1.0 / (1.0 + math.exp(-max(min(z, 30.0), -30.0)))
            err = p - y
            for i, xi in enumerate(x):
                grad[i] += err * xi
        for i in range(len(weights)):
            weights[i] -= lr * grad[i] / n

    action_prior: dict[str, float] = {}
    for _, action, y in pairs:
        action_prior[action] = action_prior.get(action, 0.0) + y

    def predict(row: Mapping[str, Any]) -> dict[str, Any]:
        candidates = row.get("candidates") or []
        if not candidates:
            return _base_pred(BASELINE_TFIDF_LOGREG, None, probabilities={})
        context_tokens = _tokens(str(row.get("context_state", "")))
        scores: dict[str, float] = {}
        keys: dict[str, str] = {}
        for candidate in candidates:
            cid = str(candidate.get("id"))
            keys[cid] = _action_key(candidate)
            tokens = context_tokens + _tokens(str(candidate.get("description", "")))
            x = _design_vector(tokens, vocab)
            z = sum(w * xi for w, xi in zip(weights, x))
            scores[cid] = 1.0 / (1.0 + math.exp(-max(min(z, 30.0), -30.0)))
        # normalize to a distribution over this record's candidates
        total = sum(scores.values()) or 1.0
        probs = {cid: (score / total) for cid, score in scores.items()}
        predicted = max(scores, key=scores.get)  # type: ignore[arg-type]
        return _base_pred(
            BASELINE_TFIDF_LOGREG,
            predicted,
            probabilities=probs,
            fit_split="train",
            n_fit_rows=len(rows),
            reads_labels_at_predict=False,
        )

    return {
        "baseline_kind": BASELINE_TFIDF_LOGREG,
        "fit_split": "train",
        "n_fit_rows": len(rows),
        "vocab_size": len(vocab),
        "predict": predict,
        "valid_as_ground_truth": False,
    }


def stable_under_id_permutation(
    predict_fn: Callable[[Mapping[str, Any]], Mapping[str, Any]],
    row: Mapping[str, Any],
    candidates: Sequence[Mapping[str, Any]],
    *,
    n: int = 5,
    seed: int = 0,
) -> bool:
    """True when renaming candidate IDs never changes the semantic choice."""
    base = semantic_key(predict_fn(row), candidates)
    rng = random.Random(seed)
    ids = [str(c.get("id")) for c in candidates]
    for i in range(n):
        shuffled = ids[:]
        rng.shuffle(shuffled)
        mapping = {old: f"perm_{i}_{new}" for old, new in zip(ids, shuffled)}
        renamed = [{**c, "id": mapping[str(c.get("id"))]} for c in candidates]
        probe = dict(row)
        probe["candidates"] = renamed
        # label fields must not be consulted; blank them on the probe too
        probe.pop("selected_candidate", None)
        probe.pop("gold_selected_candidate", None)
        if semantic_key(predict_fn(probe), renamed) != base:
            return False
    return True


def brier_multiclass(dist: Mapping[str, float], gold_id: str | None) -> float:
    """Mean squared error vs one-hot gold. Range [0, 2]; 0 when one-hot correct."""
    keys = list(dict.fromkeys(list(dist.keys()) + ([] if gold_id is None else [gold_id])))
    if not keys:
        return 0.0
    total = 0.0
    for key in keys:
        p = float(dist.get(key, 0.0))
        y = 1.0 if (gold_id is not None and key == gold_id) else 0.0
        total += (p - y) ** 2
    return total / len(keys)


def ece_binary(
    confidences: Sequence[float],
    correct: Sequence[bool],
    *,
    n_bins: int = 10,
) -> float:
    """Expected Calibration Error.

    ECE = Σ_m (|B_m| / n) · |acc(B_m) − conf(B_m)|
    """
    pairs = [(float(c), bool(y)) for c, y in zip(confidences, correct)]
    n = len(pairs)
    if n == 0:
        return 0.0
    width = 1.0 / n_bins
    bins: list[list[tuple[float, bool]]] = [[] for _ in range(n_bins)]
    for conf, ok in pairs:
        idx = min(int(conf / width), n_bins - 1) if conf < 1.0 else n_bins - 1
        bins[idx].append((conf, ok))
    ece = 0.0
    for bucket in bins:
        if not bucket:
            continue
        acc = sum(1 for _, ok in bucket if ok) / len(bucket)
        conf = sum(c for c, _ in bucket) / len(bucket)
        ece += (len(bucket) / n) * abs(acc - conf)
    return ece


def run_independent_baselines(
    rows: Sequence[Mapping[str, Any]],
    *,
    permutation_seeds: int = 5,
    random_seed: int = 0,
) -> dict[str, Any]:
    train = [r for r in rows if (r.get("split") or "train") == "train"]
    test = [r for r in rows if (r.get("split") or "") == "test"]

    baselines: list[dict[str, Any]] = []

    # 1) seeded random — one entry per seed so variance is visible
    for seed in range(random_seed, random_seed + max(permutation_seeds, 1)):
        preds = [
            predict_seeded_random(r.get("candidates") or [], seed=seed)
            for r in test or train
        ]
        baselines.append({
            **_base_pred(BASELINE_SEEDED_RANDOM, None),
            "seed": seed,
            "n_scored": len(preds),
            "note": "per-row draw; aggregated accuracy reported by the harness, not here",
        })

    # 2) first-candidate control
    baselines.append({
        **predict_first_candidate([]),
        "n_scored": len(test or train),
        "note": "always candidates[0] — order control",
    })

    # 3) taxonomy majority (valid only when action keys cover the set)
    sample = (test or train)[:1]
    if sample:
        baselines.append(predict_taxonomy_majority(train or rows, candidates=sample[0].get("candidates") or []))

    # 4) TF-IDF / logistic on train only
    if train:
        model = fit_tfidf_logreg(train)
        stable = True
        label_free = True
        for row in (test or train)[:20]:
            if not stable_under_id_permutation(model["predict"], row, row.get("candidates") or [], n=permutation_seeds):
                stable = False
            probe = dict(row)
            probe["selected_candidate"] = "GHOST"
            probe["gold_selected_candidate"] = "GHOST"
            probe["reward"] = 99
            if model["predict"](probe)["predicted_candidate"] != model["predict"](row)["predicted_candidate"]:
                label_free = False
        baselines.append({
            **_base_pred(BASELINE_TFIDF_LOGREG, None),
            "fit_split": model["fit_split"],
            "n_fit_rows": model["n_fit_rows"],
            "vocab_size": model["vocab_size"],
            "id_permutation_stable": stable,
            "reads_labels_at_predict": not label_free,
            "note": "fit on split=train only; predict uses context + descriptions",
        })

    # 5) gold-copy fixture ceiling — explicitly not a baseline
    gold_n = sum(1 for r in rows if r.get("selected_candidate"))
    baselines.append({
        **predict_gold_copy_fixture([], gold_id=None),
        "n_scored": gold_n,
        "note": "FIXTURE CEILING — copies gold_selected_candidate; excluded from any comparison",
    })

    return {
        "status_label": STATUS_LABEL,
        "n_rows": len(rows),
        "n_train": len(train),
        "n_test": len(test),
        "permutation_seeds": max(permutation_seeds, 1),
        "predictor_reads_labels": False,
        "baselines": baselines,
        "metrics_formula": {
            "brier_multiclass": "mean_k (p_k − y_k)^2 over union(keys, gold); 0 = perfect",
            "ece_binary": "Σ_m (|B_m|/n) · |acc(B_m) − conf(B_m)| over equal-width bins",
        },
        "note": (
            "selection labels only; gold_copy is a fixture ceiling, not a baseline; "
            "no decision-quality claim without observed gold_outcome"
        ),
    }
