"""
Deterministic scoring logic for the CivicFlow AI Priority Engine.
"""

from __future__ import annotations

from typing import Tuple

from . import config, constants
from .models import PriorityInput


def get_urgency_score(urgency: str | None) -> float:
    """Return the score contributed by complaint urgency."""
    return constants.URGENCY_SCORES.get(
        urgency,
        constants.DEFAULT_URGENCY_SCORE,
    )


def get_category_score(category: str | None) -> float:
    """Return the score contributed by complaint category."""
    if not category:
        return constants.DEFAULT_CATEGORY_SCORE

    return constants.CATEGORY_SCORES.get(
        category,
        constants.DEFAULT_CATEGORY_SCORE,
    )


def get_community_impact_score(cluster_size: int) -> float:
    """
    Return the score based on duplicate cluster size.
    """

    if cluster_size <= 1:
        return 0.0
    elif cluster_size <= 3:
        return 5.0
    elif cluster_size <= 5:
        return 10.0
    elif cluster_size <= 10:
        return 15.0
    else:
        return 20.0


def get_confidence_score(confidence: float) -> float:
    """
    Convert Vision LLM confidence into a score.
    """

    if confidence >= config.HIGH_CONFIDENCE_THRESHOLD:
        return 10.0
    elif confidence >= config.MEDIUM_CONFIDENCE_THRESHOLD:
        return 8.0
    elif confidence >= config.LOW_CONFIDENCE_THRESHOLD:
        return 6.0
    else:
        return 4.0


def get_sla_score(age_hours: int) -> float:
    """
    Estimate SLA risk score from complaint age.
    """

    if age_hours >= config.SLA_CRITICAL_HOURS:
        return 10.0
    elif age_hours >= config.SLA_RISK_HOURS:
        return 8.0
    elif age_hours >= config.SLA_WARNING_HOURS:
        return 5.0
    elif age_hours > 0:
        return 2.0

    return 0.0


def resolve_priority_level(score: float) -> str:
    """
    Convert a numeric score into a priority level.
    """

    if score >= config.CRITICAL_THRESHOLD:
        return constants.PRIORITY_CRITICAL

    if score >= config.HIGH_THRESHOLD:
        return constants.PRIORITY_HIGH

    if score >= config.MEDIUM_THRESHOLD:
        return constants.PRIORITY_MEDIUM

    return constants.PRIORITY_LOW


def calculate_score(
    data: PriorityInput,
) -> Tuple[float, str, dict[str, float], list[str]]:
    """
    Calculate the overall priority score.

    Returns
    -------
    Tuple containing

    final_score

    priority_level

    breakdown

    reasons
    """

    reasons: list[str] = []

    urgency_score = get_urgency_score(data.urgency)
    category_score = get_category_score(data.category)
    community_score = get_community_impact_score(data.cluster_size)
    confidence_score = get_confidence_score(data.confidence)
    sla_score = get_sla_score(data.complaint_age_hours)

    total_score = (
        urgency_score
        + category_score
        + community_score
        + confidence_score
        + sla_score
    )

    final_score = max(
        constants.MIN_SCORE,
        min(constants.MAX_SCORE, total_score),
    )

    priority_level = resolve_priority_level(final_score)

    breakdown = {
        "urgency": urgency_score,
        "category": category_score,
        "community_impact": community_score,
        "confidence": confidence_score,
        "sla_risk": sla_score,
    }

    if urgency_score:
        reasons.append(f"{data.urgency} urgency identified by Vision AI.")

    if category_score:
        reasons.append(
            f"{data.category} has elevated civic impact."
        )

    if community_score:
        reasons.append(
            f"{data.cluster_size} similar complaints indicate community impact."
        )

    if confidence_score >= 8:
        reasons.append(
            "High AI confidence in complaint analysis."
        )
    else:
        reasons.append(
            "Moderate AI confidence in complaint analysis."
        )

    if sla_score > 0:
        reasons.append(
            "Complaint approaching SLA deadline."
        )

    reasons.append(
        f"Final priority score is {final_score:.1f} ({priority_level})."
    )

    return (
        final_score,
        priority_level,
        breakdown,
        reasons,
    )