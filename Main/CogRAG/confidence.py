import math


def _clamp01(value):
    return max(0.0, min(1.0, float(value)))


def compute_attempt_confidence(questions_attempted, saturation_rate=0.35):
    """
    Attempt-based confidence.

    Uses an exponential saturation curve:
        confidence = 1 - exp(-saturation_rate * questions_attempted)

    This grows quickly early on and saturates toward 1.0 as evidence accumulates.
    """
    attempts = max(0, int(questions_attempted or 0))
    rate = max(1e-9, float(saturation_rate))
    value = 1.0 - math.exp(-rate * attempts)
    return _clamp01(value)


def compute_consistency_confidence(recent_answers):
    """
    Consistency-based confidence from recent binary outcomes.

    Given recent_answers in {0,1}, compute:
      p = mean(recent_answers)
      variability = 4 * p * (1-p)   # in [0,1], max at p=0.5
      consistency_conf = 1 - variability

    Behavior:
      [1,1,1,1,1] -> high confidence
      [0,0,0,0,0] -> high confidence (consistently weak)
      [1,0,1,0,1] -> low confidence
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
    questions_attempted,
    recent_answers,
    attempt_weight=0.5,
    consistency_weight=0.5,
    saturation_rate=0.35,
    min_attempts_for_reliability=5
):
    """
    Combined learner-confidence score in [0, 1].

    Weighted normalized combination of:
      - attempt confidence
      - consistency confidence

    Reliability gate:
      Before `min_attempts_for_reliability`, confidence is scaled down by:
        questions_attempted / min_attempts_for_reliability
      This enforces that confidence is not treated as reliable from only
      a handful of answers.
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
        saturation_rate=saturation_rate
    )
    consistency_conf = compute_consistency_confidence(recent_answers=recent_answers)

    combined = (aw * attempt_conf) + (cw * consistency_conf)

    attempts = max(0, int(questions_attempted or 0))
    min_attempts = max(1, int(min_attempts_for_reliability or 1))

    if attempts < min_attempts:
        evidence_factor = attempts / min_attempts
        combined = combined * evidence_factor

    return _clamp01(combined)
