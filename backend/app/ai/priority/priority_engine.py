"""
Orchestrator for the CivicFlow AI Priority Engine.
"""

from __future__ import annotations

import logging
from typing import Any

from . import scoring
from .models import (
    PriorityBreakdown,
    PriorityInput,
    PriorityResult,
)

logger = logging.getLogger("civicflow.ai.priority")


def calculate_priority(
    complaint_data: dict[str, Any],
    duplicate_data: dict[str, Any],
) -> dict[str, Any]:
    """
    Calculate the priority of a civic complaint.

    This is the primary entry point for the Priority Engine.
    It consumes outputs from the Vision LLM and Duplicate Detection
    modules, validates them, computes the deterministic priority score,
    and returns a structured PriorityResult.

    Args:
        complaint_data:
            Structured complaint extracted by the Vision LLM.

        duplicate_data:
            Output produced by the Duplicate Detection module.

    Returns:
        Dictionary representation of PriorityResult.
    """

    logger.info("=" * 80)
    logger.info("Starting Priority Engine")

    # ------------------------------------------------------------------
    # Merge inputs from previous pipeline stages
    # ------------------------------------------------------------------

    combined_input = {
        "urgency": complaint_data.get("urgency"),
        "category": complaint_data.get("category"),
        "confidence": complaint_data.get("confidence", 1.0),
        "is_duplicate": duplicate_data.get("is_duplicate", False),
        "cluster_size": duplicate_data.get("cluster_size", 1),
        "similarity_score": duplicate_data.get("similarity_score", 0.0),
        "complaint_age_hours": complaint_data.get(
            "complaint_age_hours",
            0,
        ),
    }

    logger.debug("Merged input: %s", combined_input)

    # ------------------------------------------------------------------
    # Validate input
    # ------------------------------------------------------------------

    try:
        validated_input = PriorityInput.model_validate(combined_input)

    except Exception as exc:
        logger.exception("Priority Engine validation failed.")

        fallback = PriorityResult(
            priority_score=40.0,
            priority_level="Medium",
            breakdown=PriorityBreakdown(
                urgency=15.0,
                category=10.0,
                community_impact=0.0,
                confidence=10.0,
                sla_risk=5.0,
            ),
            reasons=[
                "Input validation failed.",
                f"Fallback priority assigned ({exc}).",
            ],
        )

        return fallback.model_dump()

    logger.info(
        "Processing complaint | "
        "Urgency=%s | "
        "Category=%s | "
        "Cluster=%d",
        validated_input.urgency,
        validated_input.category,
        validated_input.cluster_size,
    )

    # ------------------------------------------------------------------
    # Calculate score
    # ------------------------------------------------------------------

    (
        final_score,
        priority_level,
        breakdown,
        reasons,
    ) = scoring.calculate_score(validated_input)

    # ------------------------------------------------------------------
    # Build response
    # ------------------------------------------------------------------

    result = PriorityResult(
        priority_score=final_score,
        priority_level=priority_level,
        breakdown=PriorityBreakdown(**breakdown),
        reasons=reasons,
    )

    logger.info(
        "Priority calculation completed | "
        "Score=%.1f | "
        "Level=%s",
        final_score,
        priority_level,
    )

    logger.info("=" * 80)

    return result.model_dump()