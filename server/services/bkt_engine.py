"""
server/services/bkt_engine.py — Bayesian Knowledge Tracing (BKT) Math Engine.
"""
from __future__ import annotations

import logging
import math
from datetime import datetime, timezone
from server.models.student import StudentMasteryDocument

logger = logging.getLogger("server.services.bkt")

# Default standard BKT model parameters
DEFAULT_P_L0 = 0.10  # Initial prior mastery
DEFAULT_P_TRANSIT = 0.15  # P(T) - Learning transition probability per practice
DEFAULT_P_GUESS = 0.25  # P(G) - Probability of guessing correctly without mastery
DEFAULT_P_SLIP = 0.10  # P(S) - Probability of slipping / making error despite mastery


class BKTEngine:
    """Standard Bayesian Knowledge Tracing computational engine."""

    def __init__(
        self,
        p_l0: float = DEFAULT_P_L0,
        p_transit: float = DEFAULT_P_TRANSIT,
        p_guess: float = DEFAULT_P_GUESS,
        p_slip: float = DEFAULT_P_SLIP,
    ):
        self.p_l0 = p_l0
        self.p_transit = p_transit
        self.p_guess = p_guess
        self.p_slip = p_slip

    def compute_update(
        self,
        prior: float,
        is_correct: bool,
    ) -> tuple[float, float]:
        """
        Calculates the Bayesian posterior given observation, and projects the next trial mastery.
        Returns: (posterior_observed, next_trial_mastery)
        """
        # Clamp prior to valid numerical range
        p_l = max(0.001, min(0.999, float(prior)))

        if is_correct:
            # P(L_t | Correct) = (P(L) * (1 - S)) / (P(L) * (1 - S) + (1 - P(L)) * G)
            numerator = p_l * (1.0 - self.p_slip)
            denominator = numerator + (1.0 - p_l) * self.p_guess
        else:
            # P(L_t | Incorrect) = (P(L) * S) / (P(L) * S + (1 - P(L)) * (1 - G))
            numerator = p_l * self.p_slip
            denominator = numerator + (1.0 - p_l) * (1.0 - self.p_guess)

        if denominator <= 0:
            p_obs = p_l
        else:
            p_obs = numerator / denominator

        # Project mastery for next trial incorporating learning transit:
        # P(L_{t+1}) = P(L_t | Obs) + (1 - P(L_t | Obs)) * P(T)
        p_next = p_obs + (1.0 - p_obs) * self.p_transit

        # Safe rounding
        p_obs = round(max(0.01, min(0.99, p_obs)), 4)
        p_next = round(max(0.01, min(0.99, p_next)), 4)

        return p_obs, p_next

    def compute_confidence(self, n_attempts: int, recent_answers: list[int]) -> float:
        """
        Learner Confidence Model (spec §3.10).
        - Conf_attempt(N) = 1 - exp(-0.35 * N)
        - Conf_consistency(R) = 1 - 4*p*(1-p), where p = mean of last 10 binary answers
        - Conf_final = (0.5*Conf_attempt + 0.5*Conf_consistency) * min(1.0, N/6)
        Returns a float in [0.0, 1.0].
        """
        conf_attempt = 1.0 - math.exp(-0.35 * n_attempts)

        if recent_answers:
            p = sum(recent_answers) / len(recent_answers)
        else:
            p = 0.0
        conf_consistency = 1.0 - 4.0 * p * (1.0 - p)

        scale = min(1.0, n_attempts / 6.0)
        conf_final = (0.5 * conf_attempt + 0.5 * conf_consistency) * scale
        return round(max(0.0, min(1.0, conf_final)), 4)

    def update_multi_concept_mastery(
        self,
        priors: dict[str, float],
        concept_weights: dict[str, float],
        is_correct: bool,
    ) -> dict[str, tuple[float, float]]:
        """
        Weighted multi-concept BKT update (spec §3.10 / GAP BE-6).
        concept_weights must sum to 1.0; primary concept weight >= 0.51.
        Returns {concept_name: (prior, updated)} for each concept.
        """
        results: dict[str, tuple[float, float]] = {}
        for concept, weight in concept_weights.items():
            p_prior = max(0.01, min(0.99, priors.get(concept, self.p_l0)))
            _, p_new = self.compute_update(p_prior, is_correct)
            # Weighted delta: preserve prior trajectory proportionally
            p_updated = p_prior + weight * (p_new - p_prior)
            p_updated = round(max(0.01, min(0.99, p_updated)), 4)
            results[concept] = (p_prior, p_updated)
        return results

    async def update_student_concept_mastery(
        self,
        student_id: str,
        course_id: str,
        concept_name: str,
        is_correct: bool,
    ) -> tuple[float, float]:
        """
        Fetch or create student mastery document, compute BKT update, and persist to MongoDB.
        Returns (prior_mastery, updated_mastery).
        """
        record = await StudentMasteryDocument.find_one(
            StudentMasteryDocument.student_id == student_id,
            StudentMasteryDocument.course_id == course_id,
            StudentMasteryDocument.concept_name == concept_name,
        )

        if not record:
            prior = self.p_l0
            attempts = 1
            corrects = 1 if is_correct else 0
            recent_answers = [1 if is_correct else 0]
            _, updated = self.compute_update(prior, is_correct)
            record = StudentMasteryDocument(
                student_id=student_id,
                course_id=course_id,
                concept_name=concept_name,
                mastery_probability=updated,
                attempts_count=attempts,
                correct_count=corrects,
                recent_answers=recent_answers,
                last_practiced_at=datetime.now(timezone.utc),
            )
            await record.insert()
        else:
            prior = record.mastery_probability
            _, updated = self.compute_update(prior, is_correct)
            record.mastery_probability = updated
            record.attempts_count += 1
            if is_correct:
                record.correct_count += 1
            # Maintain rolling window of last 10 answers
            recent_answers = list(record.recent_answers or [])
            recent_answers.append(1 if is_correct else 0)
            record.recent_answers = recent_answers[-10:]
            record.last_practiced_at = datetime.now(timezone.utc)
            await record.save()

        logger.info(
            "BKT update for student %s on concept '%s': prior=%.3f, updated=%.3f (correct=%s)",
            student_id,
            concept_name,
            prior,
            updated,
            is_correct,
        )
        return prior, updated


# Singleton instance
bkt_engine = BKTEngine()
