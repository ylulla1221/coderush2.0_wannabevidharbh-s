"""
CivicFlow AI Routing Engine — orchestrator.

Public API
----------
This module exposes exactly ONE callable to the rest of the system::

    from app.ai.routing import calculate_route

    result: dict = calculate_route(
        complaint_data=llm_result,
        duplicate_data=duplicate_result,
        priority_data=priority_result,
    )

Architecture
------------
The function follows a strict, linear decision pipeline:

    ┌──────────────────────────────────────┐
    │  1. Merge & validate inputs          │
    │     (Pydantic v2 model_validate)     │
    ├──────────────────────────────────────┤
    │  2. Determine department             │
    │     (CATEGORY_TO_DEPARTMENT lookup)  │
    ├──────────────────────────────────────┤
    │  3. Determine team                   │
    │     (CATEGORY_TO_TEAM lookup)        │
    ├──────────────────────────────────────┤
    │  4. Determine zone                   │
    │     (CATEGORY_TO_ZONE lookup)        │
    ├──────────────────────────────────────┤
    │  5. Determine SLA                    │
    │     (base SLA + priority override)   │
    ├──────────────────────────────────────┤
    │  6. Determine escalation             │
    │     (level, score, category, cluster)│
    ├──────────────────────────────────────┤
    │  7. Assemble routing_reason list     │
    ├──────────────────────────────────────┤
    │  8. Return RoutingResult.model_dump()│
    └──────────────────────────────────────┘

Design Principles
-----------------
- **Deterministic**: identical inputs always produce identical outputs.
- **No AI / no randomness**: every decision traces to a dict lookup or
  an integer / float comparison.
- **Defensive**: every dict access has a typed fallback; Pydantic
  validation is wrapped so the engine degrades gracefully instead of
  raising unhandled exceptions into the pipeline.
- **Auditable**: the ``routing_reason`` field in the result records each
  individual decision step so auditors can reproduce the decision.
"""

from __future__ import annotations

import logging
from typing import Any

from . import config, constants
from .exceptions import RoutingValidationError
from .models import RoutingInput, RoutingResult

logger = logging.getLogger("civicflow.ai.routing")

# =============================================================================
# PRIVATE HELPERS
#
# Each helper resolves ONE routing dimension and appends a sentence to the
# shared ``reasons`` list. They are intentionally small, single-purpose
# functions to remain individually testable.
# =============================================================================


def _resolve_department(category: str | None, reasons: list[str]) -> str:
    """Map complaint category to its responsible government department.

    Performs a case-sensitive dict lookup against
    ``constants.CATEGORY_TO_DEPARTMENT``. Falls back to
    ``config.DEFAULT_DEPARTMENT`` when the category is absent or unknown.

    Args:
        category: Civic issue category string from the Vision LLM.
        reasons: Mutable list that receives an explanatory sentence.

    Returns:
        Name of the assigned department.
    """
    if category and category in constants.CATEGORY_TO_DEPARTMENT:
        department = constants.CATEGORY_TO_DEPARTMENT[category]
        reasons.append(
            f"Category '{category}' maps to '{department}'."
        )
    else:
        department = config.DEFAULT_DEPARTMENT
        reasons.append(
            f"Category '{category}' is unrecognised; "
            f"defaulting to '{department}'."
        )

    return department


def _resolve_team(category: str | None, reasons: list[str]) -> str:
    """Map complaint category to the specialist field team.

    Performs a case-sensitive dict lookup against
    ``constants.CATEGORY_TO_TEAM``. Falls back to
    ``config.DEFAULT_TEAM`` when the category is absent or unknown.

    Args:
        category: Civic issue category string from the Vision LLM.
        reasons: Mutable list that receives an explanatory sentence.

    Returns:
        Name of the assigned specialist team.
    """
    if category and category in constants.CATEGORY_TO_TEAM:
        team = constants.CATEGORY_TO_TEAM[category]
        reasons.append(
            f"Complaint assigned to '{team}'."
        )
    else:
        team = config.DEFAULT_TEAM
        reasons.append(
            f"No specialist team found for '{category}'; "
            f"defaulting to '{team}'."
        )

    return team


def _resolve_zone(category: str | None, reasons: list[str]) -> str:
    """Map complaint category to an administrative geographic zone.

    Performs a case-sensitive dict lookup against
    ``constants.CATEGORY_TO_ZONE``. Falls back to
    ``config.DEFAULT_ZONE`` when the category is absent or unknown.

    Args:
        category: Civic issue category string from the Vision LLM.
        reasons: Mutable list that receives an explanatory sentence.

    Returns:
        Zone identifier string (e.g. ``"Zone A"``).
    """
    if category and category in constants.CATEGORY_TO_ZONE:
        zone = constants.CATEGORY_TO_ZONE[category]
        reasons.append(
            f"Complaint routed to geographic '{zone}'."
        )
    else:
        zone = config.DEFAULT_ZONE
        reasons.append(
            f"No zone mapping found for '{category}'; "
            f"defaulting to '{zone}'."
        )

    return zone


def _resolve_sla(
    category: str | None,
    priority_level: str,
    reasons: list[str],
) -> int:
    """Calculate the final SLA commitment in hours.

    The algorithm uses two steps:

    1. **Base SLA**: looked up from ``constants.CATEGORY_TO_BASE_SLA``
       (or ``config.DEFAULT_SLA_HOURS`` if the category is absent).
    2. **Priority override**: maps the priority level to a stricter SLA
       from ``config`` (CRITICAL_PRIORITY_SLA, HIGH_PRIORITY_SLA, etc.).
       The override is applied only when it is *stricter* (fewer hours)
       than the base SLA, so a High-priority Garbage complaint gets the
       High override (12 h) rather than the base (48 h).

    The result is clamped between ``config.MIN_SLA_HOURS`` and
    ``config.MAX_SLA_HOURS``.

    Args:
        category: Civic issue category string from the Vision LLM.
        priority_level: Priority level string from the Priority Engine.
        reasons: Mutable list that receives explanatory sentences.

    Returns:
        Final SLA commitment in hours.
    """
    # Step 1 — base SLA from category
    if category and category in constants.CATEGORY_TO_BASE_SLA:
        base_sla = constants.CATEGORY_TO_BASE_SLA[category]
        reasons.append(
            f"Base SLA for '{category}' is {base_sla} hours."
        )
    else:
        base_sla = config.DEFAULT_SLA_HOURS
        reasons.append(
            f"No base SLA mapping for '{category}'; "
            f"using default {base_sla} hours."
        )

    # Step 2 — priority-level override
    _priority_sla_map: dict[str, int] = {
        "Critical": config.CRITICAL_PRIORITY_SLA,
        "High":     config.HIGH_PRIORITY_SLA,
        "Medium":   config.MEDIUM_PRIORITY_SLA,
        "Low":      config.LOW_PRIORITY_SLA,
    }
    priority_sla = _priority_sla_map.get(priority_level, config.DEFAULT_SLA_HOURS)

    if priority_sla < base_sla:
        reasons.append(
            f"'{priority_level}' priority overrides SLA to {priority_sla} hours "
            f"(stricter than base {base_sla} hours)."
        )
        effective_sla = priority_sla
    else:
        reasons.append(
            f"Base SLA ({base_sla} h) is already stricter than "
            f"'{priority_level}' priority SLA ({priority_sla} h); "
            "base SLA retained."
        )
        effective_sla = base_sla

    # Step 3 — hard clamp
    final_sla = max(config.MIN_SLA_HOURS, min(config.MAX_SLA_HOURS, effective_sla))

    if final_sla != effective_sla:
        reasons.append(
            f"SLA clamped to hard limit: {final_sla} hours."
        )

    return final_sla


def _resolve_escalation(
    priority_level: str,
    priority_score: float,
    category: str | None,
    cluster_size: int,
    reasons: list[str],
) -> bool:
    """Determine whether the complaint must be escalated.

    Escalation is triggered by **any** of the following (OR logic):

    1. ``priority_level`` is in ``constants.ESCALATION_PRIORITY_LEVELS``
       (``"Critical"`` or ``"High"``).
    2. ``priority_score >= config.ESCALATION_SCORE_THRESHOLD`` — numeric
       safety net for borderline High/Critical complaints.
    3. ``category`` is in ``constants.ALWAYS_ESCALATE_CATEGORIES``
       (life-threatening categories always escalate).
    4. ``cluster_size >= constants.ESCALATION_CLUSTER_THRESHOLD`` — high
       community impact signals systemic failure.

    Args:
        priority_level: Priority level string from the Priority Engine.
        priority_score: Numeric score from the Priority Engine.
        category: Civic issue category from the Vision LLM.
        cluster_size: Duplicate cluster size from Duplicate Detection.
        reasons: Mutable list that receives explanatory sentences.

    Returns:
        ``True`` if the complaint must be escalated; ``False`` otherwise.
    """
    escalate = False

    # Trigger 1 — priority level
    if priority_level in constants.ESCALATION_PRIORITY_LEVELS:
        escalate = True
        reasons.append(
            f"'{priority_level}' priority level triggers escalation."
        )

    # Trigger 2 — numeric score safety net
    if priority_score >= config.ESCALATION_SCORE_THRESHOLD:
        if not escalate:
            escalate = True
            reasons.append(
                f"Priority score {priority_score:.1f} exceeds escalation "
                f"threshold ({config.ESCALATION_SCORE_THRESHOLD:.1f})."
            )

    # Trigger 3 — always-escalate categories
    if category and category in constants.ALWAYS_ESCALATE_CATEGORIES:
        if not escalate:
            escalate = True
        reasons.append(
            f"Category '{category}' is classified as a public-safety "
            "hazard and always requires escalation."
        )

    # Trigger 4 — community impact / cluster size
    if cluster_size >= constants.ESCALATION_CLUSTER_THRESHOLD:
        if not escalate:
            escalate = True
        reasons.append(
            f"Cluster size {cluster_size} meets or exceeds the community "
            f"impact threshold ({constants.ESCALATION_CLUSTER_THRESHOLD} "
            "complaints); escalation required."
        )

    if not escalate:
        reasons.append(
            "No escalation criteria met; complaint enters standard queue."
        )

    return escalate


# =============================================================================
# FALLBACK RESULT
#
# Used when Pydantic validation fails so the pipeline can continue
# instead of crashing. The fallback is logged at ERROR level.
# =============================================================================

def _build_fallback_result(exc: Exception) -> dict[str, Any]:
    """Build a safe fallback RoutingResult after a validation failure.

    Args:
        exc: The exception that caused the fallback.

    Returns:
        Dictionary representation of a default RoutingResult.
    """
    return RoutingResult(
        department=config.DEFAULT_DEPARTMENT,
        team=config.DEFAULT_TEAM,
        zone=config.DEFAULT_ZONE,
        sla_hours=config.DEFAULT_SLA_HOURS,
        requires_escalation=False,
        routing_reason=[
            "Input validation failed; fallback routing applied.",
            f"Cause: {exc}",
        ],
    ).model_dump()


# =============================================================================
# PUBLIC API
# =============================================================================


def calculate_route(
    complaint_data: dict[str, Any],
    duplicate_data: dict[str, Any],
    priority_data: dict[str, Any],
) -> dict[str, Any]:
    """Route a civic complaint to the correct department, team, and zone.

    This is the **only** public function exposed by the routing module.
    All other functions in this file are private helpers.

    The function is fully deterministic: the same inputs always produce
    the same output with zero randomness, no AI, and no external I/O.

    Pipeline:

        complaint_data + duplicate_data + priority_data
                ↓
            RoutingInput (Pydantic validation)
                ↓
            _resolve_department()
                ↓
            _resolve_team()
                ↓
            _resolve_zone()
                ↓
            _resolve_sla()
                ↓
            _resolve_escalation()
                ↓
            RoutingResult.model_dump()

    Args:
        complaint_data: Structured complaint dict from the Vision LLM.
            Expected keys: ``category``, ``location``.
        duplicate_data: Result dict from the Duplicate Detection module.
            Expected keys: ``is_duplicate``, ``cluster_size``.
        priority_data: Result dict from the Priority Engine.
            Expected keys: ``priority_level``, ``priority_score``.

    Returns:
        A JSON-serialisable dictionary matching the ``RoutingResult``
        schema::

            {
                "department":         str,
                "team":               str,
                "zone":               str,
                "sla_hours":          int,
                "requires_escalation": bool,
                "routing_reason":     list[str],
            }

    Raises:
        RoutingValidationError: Logged internally; the function degrades
            to a safe fallback result rather than propagating the exception
            up to the pipeline.
    """
    logger.info("=" * 80)
    logger.info("Starting Routing Engine")

    # ------------------------------------------------------------------
    # Step 1 — merge and validate inputs
    # ------------------------------------------------------------------

    combined: dict[str, Any] = {
        "category":      complaint_data.get("category"),
        "location":      complaint_data.get("location"),
        "priority_level": priority_data.get("priority_level", "Medium"),
        "priority_score": priority_data.get("priority_score", 40.0),
        "cluster_size":  duplicate_data.get("cluster_size", 1),
        "is_duplicate":  duplicate_data.get("is_duplicate", False),
    }

    logger.debug("Merged routing input: %s", combined)

    try:
        validated = RoutingInput.model_validate(combined)
    except Exception as exc:
        err = RoutingValidationError(str(exc))
        logger.error(
            "Routing Engine validation failed: %s", err.message
        )
        return _build_fallback_result(err)

    logger.info(
        "Routing | Category=%s | Priority=%s (%.1f) | Cluster=%d",
        validated.category,
        validated.priority_level,
        validated.priority_score,
        validated.cluster_size,
    )

    # ------------------------------------------------------------------
    # Shared reasons accumulator — passed by reference to each helper
    # ------------------------------------------------------------------

    reasons: list[str] = []

    # ------------------------------------------------------------------
    # Step 2 — department
    # ------------------------------------------------------------------

    department = _resolve_department(validated.category, reasons)

    # ------------------------------------------------------------------
    # Step 3 — team
    # ------------------------------------------------------------------

    team = _resolve_team(validated.category, reasons)

    # ------------------------------------------------------------------
    # Step 4 — zone
    # ------------------------------------------------------------------

    zone = _resolve_zone(validated.category, reasons)

    # ------------------------------------------------------------------
    # Step 5 — SLA
    # ------------------------------------------------------------------

    sla_hours = _resolve_sla(validated.category, validated.priority_level, reasons)

    # ------------------------------------------------------------------
    # Step 6 — escalation
    # ------------------------------------------------------------------

    requires_escalation = _resolve_escalation(
        priority_level=validated.priority_level,
        priority_score=validated.priority_score,
        category=validated.category,
        cluster_size=validated.cluster_size,
        reasons=reasons,
    )

    # ------------------------------------------------------------------
    # Step 7 — assemble result
    # ------------------------------------------------------------------

    result = RoutingResult(
        department=department,
        team=team,
        zone=zone,
        sla_hours=sla_hours,
        requires_escalation=requires_escalation,
        routing_reason=reasons,
    )

    logger.info(
        "Routing completed | Department=%s | Team=%s | "
        "Zone=%s | SLA=%dh | Escalation=%s",
        result.department,
        result.team,
        result.zone,
        result.sla_hours,
        result.requires_escalation,
    )
    logger.info("=" * 80)

    return result.model_dump()
