"""
Data models for the CivicFlow AI Priority Engine.
"""

from __future__ import annotations

from pydantic import BaseModel, Field


class PriorityInput(BaseModel):
    """
    Input payload for the Priority Engine.

    This model combines structured outputs from the Vision LLM
    and Duplicate Detection modules.
    """

    urgency: str | None = Field(
        default=None,
        description="Urgency assigned by the Vision LLM (Critical, High, Medium, Low).",
    )

    category: str | None = Field(
        default=None,
        description="Category of the civic complaint.",
    )

    confidence: float = Field(
        default=1.0,
        ge=0.0,
        le=1.0,
        description="Confidence score returned by the Vision LLM.",
    )

    is_duplicate: bool = Field(
        default=False,
        description="Whether this complaint belongs to an existing duplicate cluster.",
    )

    cluster_size: int = Field(
        default=1,
        ge=1,
        description="Number of complaints in the duplicate cluster.",
    )

    similarity_score: float = Field(
        default=0.0,
        ge=0.0,
        le=1.0,
        description="Similarity score from the duplicate detection engine.",
    )

    complaint_age_hours: int = Field(
        default=0,
        ge=0,
        description="Age of the complaint in hours for SLA risk estimation.",
    )


class PriorityBreakdown(BaseModel):
    """
    Component-wise breakdown of the final priority score.
    """

    urgency: float = Field(
        ...,
        ge=0.0,
        description="Score contributed by complaint urgency.",
    )

    category: float = Field(
        ...,
        ge=0.0,
        description="Score contributed by category severity.",
    )

    community_impact: float = Field(
        ...,
        ge=0.0,
        description="Score contributed by duplicate cluster size.",
    )

    confidence: float = Field(
        ...,
        ge=0.0,
        description="Score contributed by Vision LLM confidence.",
    )

    sla_risk: float = Field(
        ...,
        ge=0.0,
        description="Score contributed by SLA breach risk.",
    )


class PriorityResult(BaseModel):
    """
    Final output produced by the Priority Engine.
    """

    priority_score: float = Field(
        ...,
        ge=0.0,
        le=100.0,
        description="Final calculated priority score.",
    )

    priority_level: str = Field(
        ...,
        description="Priority level (Low, Medium, High, Critical).",
    )

    breakdown: PriorityBreakdown = Field(
        ...,
        description="Detailed component-wise score breakdown.",
    )

    reasons: list[str] = Field(
        default_factory=list,
        description="Human-readable explanations describing how the score was calculated.",
    )