"""Deterministic candidate-order perturbations for stability evaluation."""
from __future__ import annotations

import random
from typing import Any, Mapping


def permute_candidates(record: Mapping[str, Any], seed: int) -> dict[str, Any]:
    result = dict(record)
    candidates = list(record.get("candidates", []))
    random.Random(seed).shuffle(candidates)
    result["candidates"] = candidates
    return result


def order_flip_rate(record: Mapping[str, Any], predictions: list[str | None], seeds: int = 5) -> float:
    """Compare supplied predictions across perturbations; no model is invoked."""
    if not predictions or len(predictions) != seeds:
        raise ValueError("predictions length must equal seeds")
    first = predictions[0]
    return sum(prediction != first for prediction in predictions[1:]) / max(1, seeds - 1)
