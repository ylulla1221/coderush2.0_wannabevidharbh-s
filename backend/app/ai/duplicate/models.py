"""
Data models for CivicFlow AI Duplicate Detection module.

All structured data exchanged within the duplicate detection pipeline
is defined here using Pydantic models. This provides:
    - Automatic validation at construction time.
    - Serialisation to dict / JSON with .model_dump().
    - Self-documenting schemas via type hints and field descriptions.
    - IDE autocompletion and static analysis support.

Models:
    ComplaintVector  — A complaint record stored in the vector database.
    DuplicateMatch   — A single candidate match returned by similarity search.
    DuplicateResult  — The final structured result of duplicate detection.
"""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class ComplaintVector(BaseModel):
    """Represents a complaint stored in the vector database.

    This model maps 1-to-1 with a Qdrant point. The embedding vector
    itself is handled separately by the vector store layer; this model
    carries only the metadata payload.

    Attributes:
        complaint_id: Unique identifier for the complaint.
        cluster_id:   Identifier of the cluster this complaint belongs to.
        category:     Civic issue category extracted by the LLM module.
        location:     Location extracted by the LLM module.
        summary:      Concise English summary extracted by the LLM module.
        department:   Government department responsible.
        urgency:      Urgency level assigned by the LLM module.
    """

    complaint_id: str = Field(
        ...,
        description="Unique identifier for the complaint.",
    )

    cluster_id: str = Field(
        ...,
        description="Identifier of the cluster this complaint belongs to.",
    )

    category: str | None = Field(
        default=None,
        description="Civic issue category.",
    )

    location: str | None = Field(
        default=None,
        description="Location reference from the complaint.",
    )

    summary: str | None = Field(
        default=None,
        description="Concise English summary of the complaint.",
    )

    department: str | None = Field(
        default=None,
        description="Responsible government department.",
    )

    urgency: str | None = Field(
        default=None,
        description="Urgency level: Critical, High, Medium, or Low.",
    )

    def to_payload(self) -> dict[str, Any]:
        """Convert to a flat dictionary suitable for Qdrant point payload.

        Returns:
            Dictionary with string keys and JSON-serialisable values.
        """
        return self.model_dump()


class DuplicateMatch(BaseModel):
    """A single candidate match from similarity search.

    Attributes:
        complaint_id:    ID of the matched complaint.
        cluster_id:      Cluster the matched complaint belongs to.
        raw_score:       Raw cosine similarity score before adjustments.
        adjusted_score:  Score after location / category boosts and penalties.
        category:        Category of the matched complaint.
        location:        Location of the matched complaint.
        reasons:         Human-readable explanations for the similarity.
    """

    complaint_id: str = Field(
        ...,
        description="ID of the matched complaint.",
    )

    cluster_id: str = Field(
        ...,
        description="Cluster ID of the matched complaint.",
    )

    raw_score: float = Field(
        ...,
        ge=0.0,
        le=1.0,
        description="Raw cosine similarity score.",
    )

    adjusted_score: float = Field(
        ...,
        ge=0.0,
        le=1.0,
        description="Similarity score after contextual adjustments.",
    )

    category: str | None = Field(
        default=None,
        description="Category of the matched complaint.",
    )

    location: str | None = Field(
        default=None,
        description="Location of the matched complaint.",
    )

    reasons: list[str] = Field(
        default_factory=list,
        description="Human-readable explanations for the similarity.",
    )


class DuplicateResult(BaseModel):
    """Final structured result of the duplicate detection pipeline.

    This is the return type of the public API `find_duplicate_complaint()`.

    Attributes:
        is_duplicate:         Whether the complaint is a duplicate.
        duplicate_type:       Classification: "duplicate", "possible_duplicate",
                              or "new".
        cluster_id:           Cluster the complaint was assigned to.
        matched_complaint_id: ID of the closest matching complaint, or None.
        cluster_size:         Number of complaints in the assigned cluster.
        similarity_score:     Highest adjusted similarity score, or 0.0.
        reason:               List of human-readable reasons explaining the
                              classification decision.
    """

    is_duplicate: bool = Field(
        ...,
        description="Whether the complaint is a duplicate.",
    )

    duplicate_type: str = Field(
        ...,
        description='Classification: "duplicate", "possible_duplicate", or "new".',
    )

    cluster_id: str = Field(
        ...,
        description="Cluster the complaint was assigned to.",
    )

    matched_complaint_id: str | None = Field(
        default=None,
        description="ID of the closest matching complaint.",
    )

    cluster_size: int = Field(
        default=1,
        ge=1,
        description="Number of complaints in the assigned cluster.",
    )

    similarity_score: float = Field(
        default=0.0,
        ge=0.0,
        le=1.0,
        description="Highest adjusted similarity score.",
    )

    confidence: float | None = Field(
        default=None,
        ge=0.0,
        le=1.0,
        description="Explainable confidence score.",
    )

    confidence_percentage: float | None = Field(
        default=None,
        ge=0.0,
        le=100.0,
        description="Confidence percentage (0-100).",
    )

    confidence_level: str | None = Field(
        default=None,
        description='Confidence level: "Very High", "High", "Medium", or "Low".',
    )

    review_required: bool | None = Field(
        default=None,
        description="Whether human review is required.",
    )

    reason: list[str] = Field(
        default_factory=list,
        description="Human-readable reasons for the classification.",
    )
