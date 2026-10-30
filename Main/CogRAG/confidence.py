"""
confidence.py — Calculates learner response confidence using exponential attempt saturation
and recent binary answer consistency variability.
"""
from __future__ import annotations

import math
from typing import Any, List


def _clamp01(value: float) -> float:
    return max(0.0, min(1.0, float(value)))


def compute_attempt_confidence(questions_attempted: int | float, saturation_rate: float = 0.35) -> float:
    """
    Attempt-based confidence using an exponential saturation curve:
        confidence = 1 - exp(-saturation_rate * questions_attempted)
    """
    attempts = max(0, int(questions_attempted or 0))
    rate = max(1e-9, float(saturation_rate))
    value = 1.0 - math.exp(-rate * attempts)
    return _clamp01(value)


def compute_consistency_confidence(recent_answers: List[Any]) -> float:
    """
    Consistency-based confidence from recent binary outcomes:
        p = mean(recent_answers)
        variability = 4 * p * (1 - p)   # in [0, 1], max variability at p=0.5
        consistency_conf = 1 - variability
    """
    if not isinstance(recent_answers, list) or len(recent_answers) == 0:
        return 0.0

    cleaned = []
    for item in recent_answers:
        if item in (0, 1):
            cleaned.append(int(item))
        elif isinstance(item, bool):
            cleaned.append(int(item))
        elif isinstance(item, (int, float)):
            cleaned.append(1 if item >= 0.5 else 0)

    if not cleaned:
        return 0.0

    p = sum(cleaned) / len(cleaned)
    variability = 4.0 * p * (1.0 - p)
    value = 1.0 - variability
    return _clamp01(value)


def compute_confidence(
    questions_attempted: int | float,
    recent_answers: List[Any],
    attempt_weight: float = 0.5,
    consistency_weight: float = 0.5,
    saturation_rate: float = 0.35,
    min_attempts_for_reliability: int = 5,
) -> float:
    """
    Combined learner-confidence score in [0, 1].
    Weighted combination of attempt confidence and consistency confidence,
    scaled by an evidence reliability factor if attempts < min_attempts_for_reliability.
    """
    aw = max(0.0, float(attempt_weight))
    cw = max(0.0, float(consistency_weight))
    total = aw + cw

    if total == 0:
        aw, cw = 0.5, 0.5
    else:
        aw, cw = aw / total, cw / total

    attempt_conf = compute_attempt_confidence(
        questions_attempted=questions_attempted,
        saturation_rate=saturation_rate,
    )
    consistency_conf = compute_consistency_confidence(recent_answers=recent_answers)

    combined = (aw * attempt_conf) + (cw * consistency_conf)

    attempts = max(0, int(questions_attempted or 0))
    min_attempts = max(1, int(min_attempts_for_reliability or 1))

    if attempts < min_attempts:
        evidence_factor = attempts / min_attempts
        combined = combined * evidence_factor

    return round(_clamp01(combined), 4)


__all__ = [
    "compute_attempt_confidence",
    "compute_consistency_confidence",
    "compute_confidence",
]
