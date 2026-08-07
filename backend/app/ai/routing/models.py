"""
Pydantic v2 data models for the CivicFlow AI Routing Engine.

All data exchanged between the Routing Engine and its callers is
defined here. Using Pydantic ensures:

- Automatic field-level validation at construction time.
- Serialisation to dict / JSON via `.model_dump()`.
- Self-documenting schemas through type hints and Field descriptions.
- IDE auto-completion and static analysis support.

Models
------
RoutingInput   — validated combination of upstream pipeline outputs.
RoutingResult  — the structured routing decision returned to the pipeline.
"""

from __future__ import annotations

from pydantic import BaseModel, Field


# =============================================================================
# INPUT MODEL
# =============================================================================


class RoutingInput(BaseModel):
    """Validated input payload consumed by the Routing Engine.

    This model combines the outputs of three upstream pipeline stages:

    1. **Vision LLM** — ``category``, ``location``.
    2. **Duplicate Detection** — ``cluster_size``, ``is_duplicate``.
    3. **Priority Engine** — ``priority_level``, ``priority_score``.

    Attributes:
        category: Civic issue category extracted by the Vision LLM.
            Expected values are keys from ``constants.CATEGORY_TO_DEPARTMENT``.
            ``None`` triggers fallback routing to the default department.
        location: Free-text location string extracted by the Vision LLM.
            Optional; used only for logging and future zone enrichment.
        priority_level: Priority level determined by the Priority Engine
            (``"Low"``, ``"Medium"``, ``"High"``, or ``"Critical"``).
        priority_score: Numeric priority score in ``[0.0, 100.0]``
            produced by the Priority Engine.
        cluster_size: Number of complaints in the duplicate cluster.
            ``1`` means the complaint is unique.
        is_duplicate: Whether this complaint was classified as a duplicate
            by the Duplicate Detection module.
    """

    category: str | None = Field(
        default=None,
        description=(
            "Civic issue category from the Vision LLM "
            "(e.g. 'Road Damage', 'Flooding')."
        ),
    )

    location: str | None = Field(
        default=None,
        description="Free-text location string from the Vision LLM.",
    )

    priority_level: str = Field(
        default="Medium",
        description=(
            "Priority level from the Priority Engine "
            "(Low | Medium | High | Critical)."
        ),
    )

    priority_score: float = Field(
        default=40.0,
        ge=0.0,
        le=100.0,
        description="Numeric priority score in [0.0, 100.0].",
    )

    cluster_size: int = Field(
        default=1,
        ge=1,
        description="Number of complaints in the duplicate cluster.",
    )

    is_duplicate: bool = Field(
        default=False,
        description="Whether this complaint is a duplicate.",
    )


# =============================================================================
# OUTPUT MODEL
# =============================================================================


class RoutingResult(BaseModel):
    """Structured routing decision produced by the Routing Engine.

    Attributes:
        department: Name of the government department assigned to this
            complaint (e.g. ``"Road Department"``).
        team: Name of the specialist field team within the department
            (e.g. ``"Road Maintenance Team"``).
        zone: Administrative geographic zone where the complaint should
            be handled (e.g. ``"Zone A"``).
        sla_hours: Maximum number of hours the assigned team has to
            resolve this complaint.
        requires_escalation: ``True`` if the complaint must bypass the
            standard queue and be escalated to a supervisor.
        routing_reason: Ordered list of human-readable sentences
            explaining every routing decision.  Each sentence describes
            one deterministic step so that auditors can trace the
            decision without access to logs.
    """

    department: str = Field(
        ...,
        description="Assigned government department.",
    )

    team: str = Field(
        ...,
        description="Specialist field team within the department.",
    )

    zone: str = Field(
        ...,
        description="Administrative geographic zone.",
    )

    sla_hours: int = Field(
        ...,
        ge=1,
        description="SLA commitment in hours.",
    )

    requires_escalation: bool = Field(
        ...,
        description="Whether the complaint must be escalated.",
    )

    routing_reason: list[str] = Field(
        default_factory=list,
        description=(
            "Ordered human-readable explanations for every routing decision."
        ),
    )
