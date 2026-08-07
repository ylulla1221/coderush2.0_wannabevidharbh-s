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

    # -------------------------------------------------------------------------
    # Phase 1 — Routing Knowledge Base fields
    # -------------------------------------------------------------------------

    department_code: str | None = Field(
        default=None,
        description="Short alphanumeric code for the assigned department.",
    )

    description: str | None = Field(
        default=None,
        description="What the assigned department does.",
    )

    default_explanation: str | None = Field(
        default=None,
        description="Citizen-facing explanation for why this complaint was routed here.",
    )

    routing_status: str = Field(
        default="success",
        description=(
            '"success" when a known category matched; '
            '"manual_review" when the category was unrecognised.'
        ),
    )

    # -------------------------------------------------------------------------
    # Phase 2 — Jurisdiction & Geography Engine fields
    # -------------------------------------------------------------------------

    ward: str | None = Field(
        default=None,
        description="Municipal ward resolved from the complaint location.",
    )

    zone_jurisdiction: str | None = Field(
        default=None,
        description="Administrative zone resolved from the complaint location (jurisdiction).",
    )

    municipal_body: str | None = Field(
        default=None,
        description="Municipal corporation responsible for the complaint location (e.g. PMC, PCMC).",
    )

    jurisdiction_found: bool = Field(
        default=False,
        description="True when the location was successfully resolved to a jurisdiction.",
    )

    # -------------------------------------------------------------------------
    # Phase 3 — Intelligent Routing Decision Engine fields
    # -------------------------------------------------------------------------

    routing_confidence: float = Field(
        default=0.0,
        ge=0.0,
        le=1.0,
        description="Composite confidence score for the routing decision (0.0–1.0).",
    )

    routing_confidence_percentage: float = Field(
        default=0.0,
        ge=0.0,
        le=100.0,
        description="Routing confidence expressed as a percentage (0.0–100.0).",
    )

    routing_confidence_level: str = Field(
        default="Low",
        description=(
            "Human-readable confidence band: "
            "\"Very High\" | \"High\" | \"Medium\" | \"Low\"."
        ),
    )

    human_review_required: bool = Field(
        default=False,
        description=(
            "True when the routing decision should be reviewed by a human "
            "(low confidence, unknown category, or unknown jurisdiction)."
        ),
    )

    decision_status: str = Field(
        default="human_review",
        description=(
            "\"automatic\" when routed with sufficient confidence; "
            "\"human_review\" when a reviewer should inspect the decision."
        ),
    )

    alternative_department: str | None = Field(
        default=None,
        description="Optional secondary department that may also handle this complaint.",
    )

    decision_explanation: list[str] = Field(
        default_factory=list,
        description=(
            "Ordered, citizen-facing explanation of how the routing decision "
            "was reached. Generated deterministically — no LLM involved."
        ),
    )

    # -------------------------------------------------------------------------
    # Phase 4 — Operational Planning Engine fields
    # -------------------------------------------------------------------------

    expected_response_hours: int | None = Field(
        default=None,
        description=(
            "Expected complaint resolution time in hours based on the "
            "department's operational plan (MVP: equals sla_hours from plan)."
        ),
    )

    current_workload: int | None = Field(
        default=None,
        description="Number of active complaints currently in the department's queue.",
    )

    queue_capacity: int | None = Field(
        default=None,
        description="Maximum queue capacity for the assigned department.",
    )

    workload_percentage: float | None = Field(
        default=None,
        ge=0.0,
        le=100.0,
        description="Department queue utilisation as a percentage (0–100).",
    )

    sla_risk: str = Field(
        default="Unknown",
        description=(
            "SLA risk derived from current workload: "
            "\"Low\" | \"Medium\" | \"High\" | \"Unknown\"."
        ),
    )

    escalation_chain: list[str] = Field(
        default_factory=list,
        description=(
            "Ordered list of escalation roles for this department, "
            "as defined in planning_rules.json."
        ),
    )

    # -------------------------------------------------------------------------
    # Phase 5 — Governance & Accountability Layer fields
    # -------------------------------------------------------------------------

    governance_status: str = Field(
        default="requires_review",
        description=(
            "\"governed\" when the decision was made automatically with "
            "sufficient confidence; \"requires_review\" when human review "
            "is needed."
        ),
    )

    accountability_summary: str = Field(
        default="",
        description=(
            "Deterministic, citizen-facing single-sentence summary of how "
            "the routing decision was reached and whether review is needed."
        ),
    )

    human_override_allowed: bool = Field(
        default=True,
        description="Always True — any routing decision may be overridden by an authorised reviewer.",
    )

    human_override_reason: str | None = Field(
        default=None,
        description="Free-text reason supplied when a human overrides this decision. Null until set.",
    )

    human_override_timestamp: str | None = Field(
        default=None,
        description="ISO-8601 timestamp of the most recent human override. Null until set.",
    )

    human_override_by: str | None = Field(
        default=None,
        description="Identifier of the reviewer who performed the last override. Null until set.",
    )

    provenance: dict = Field(
        default_factory=dict,
        description=(
            "Structured record of the pipeline stages that produced this "
            "routing decision and the engine version."
        ),
    )

    audit: dict = Field(
        default_factory=dict,
        description=(
            "Audit snapshot: timestamp of the routing decision, engine "
            "version, decision_status, and routing_confidence."
        ),
    )

    fairness_review: dict = Field(
        default_factory=dict,
        description=(
            "Lightweight fairness context recorded at routing time. "
            "Not an AI model — purely observational metadata."
        ),
    )
