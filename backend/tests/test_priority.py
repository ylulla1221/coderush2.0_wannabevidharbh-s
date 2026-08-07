"""
Unit tests for the CivicFlow AI Priority Engine.
"""

from app.ai.priority.constants import (
    PRIORITY_CRITICAL,
    PRIORITY_HIGH,
    PRIORITY_LOW,
    PRIORITY_MEDIUM,
)
from app.ai.priority.models import PriorityInput
from app.ai.priority.priority_engine import calculate_priority
from app.ai.priority.scoring import calculate_score


def test_calculate_score_critical():
    """Test priority calculation for a critical issue."""
    data = PriorityInput(
        urgency="Critical",
        category="Public Safety",
        confidence=0.9,
        is_duplicate=True,
        cluster_size=4,
    )

    score, level, breakdown, reasons = calculate_score(data)

    assert level == PRIORITY_CRITICAL
    assert score >= 80.0
    assert breakdown["base_urgency_score"] == 80.0
    # Category Boost for Public Safety is 15.0
    assert breakdown["category_boost"] == 15.0
    # Cluster size 4 -> 3 * 3.0 = 9.0
    assert breakdown["cluster_escalation_boost"] == 9.0
    assert score == 100.0  # Capped at 100.0


def test_calculate_score_low():
    """Test priority calculation for a low priority issue."""
    data = PriorityInput(
        urgency="Low",
        category="Unknown",
        confidence=0.8,
        is_duplicate=False,
        cluster_size=1,
    )

    score, level, breakdown, reasons = calculate_score(data)

    assert level == PRIORITY_LOW
    assert breakdown["base_urgency_score"] == 20.0
    assert breakdown["category_boost"] == 0.0
    assert breakdown["cluster_escalation_boost"] == 0.0
    assert score == 20.0


def test_priority_engine_integration():
    """Test the priority engine orchestrator with mock dictionaries."""
    complaint_data = {
        "urgency": "High",
        "category": "Road Damage",
        "confidence": 0.95,
    }

    duplicate_data = {
        "is_duplicate": True,
        "cluster_size": 3,
    }

    result = calculate_priority(complaint_data, duplicate_data)

    assert "priority_score" in result
    assert "priority_level" in result
    assert "breakdown" in result

    assert result["priority_level"] in [PRIORITY_HIGH, PRIORITY_CRITICAL]
    # base(60) + category(5) + cluster(6) = 71
    assert result["priority_score"] == 71.0


def test_priority_engine_invalid_input():
    """Test fallback when input validation fails."""
    # confidence > 1.0 will trigger Pydantic validation error
    complaint_data = {
        "urgency": "High",
        "confidence": 5.0,
    }

    result = calculate_priority(complaint_data, {})

    assert result["priority_level"] == "Medium"
    assert result["priority_score"] == 40.0
