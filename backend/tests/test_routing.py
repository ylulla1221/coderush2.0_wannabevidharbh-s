"""
Unit tests for the CivicFlow AI Routing Engine.

Covers:
- Department / team / zone lookup (known and unknown categories)
- SLA: base SLA, priority override (stricter), no-override (base is stricter)
- SLA hard clamp (min / max)
- Escalation: each of the four triggers independently
- No escalation (all triggers absent)
- Input validation fallback (bad priority_score type)
- Full integration path via calculate_route()
"""

from __future__ import annotations

import pytest

from app.ai.routing import calculate_route
from app.ai.routing.routing_engine import (
    _resolve_department,
    _resolve_escalation,
    _resolve_sla,
    _resolve_team,
    _resolve_zone,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _route(
    category: str | None = "Road Damage",
    location: str | None = None,
    priority_level: str = "Medium",
    priority_score: float = 50.0,
    cluster_size: int = 1,
    is_duplicate: bool = False,
) -> dict:
    """Convenience wrapper that constructs pipeline dicts and calls calculate_route."""
    return calculate_route(
        complaint_data={"category": category, "location": location},
        duplicate_data={"is_duplicate": is_duplicate, "cluster_size": cluster_size},
        priority_data={"priority_level": priority_level, "priority_score": priority_score},
    )


# ===========================================================================
# Department resolution
# ===========================================================================


class TestResolveDepartment:
    def test_known_category_road_damage(self) -> None:
        reasons: list[str] = []
        dept = _resolve_department("Road Damage", reasons)
        assert dept == "Road Department"
        assert any("Road Department" in r for r in reasons)

    def test_known_category_flooding(self) -> None:
        reasons: list[str] = []
        dept = _resolve_department("Flooding", reasons)
        assert dept == "Water Supply Department"

    def test_known_category_electrical_hazard(self) -> None:
        reasons: list[str] = []
        dept = _resolve_department("Electrical Hazard", reasons)
        assert dept == "Electricity Department"

    def test_unknown_category_falls_back_to_default(self) -> None:
        reasons: list[str] = []
        dept = _resolve_department("Flying Cars", reasons)
        assert dept == "General Administration"
        assert any("defaulting" in r for r in reasons)

    def test_none_category_falls_back_to_default(self) -> None:
        reasons: list[str] = []
        dept = _resolve_department(None, reasons)
        assert dept == "General Administration"


# ===========================================================================
# Team resolution
# ===========================================================================


class TestResolveTeam:
    def test_known_category_open_manhole(self) -> None:
        reasons: list[str] = []
        team = _resolve_team("Open Manhole", reasons)
        assert team == "Road Safety Team"

    def test_known_category_garbage(self) -> None:
        reasons: list[str] = []
        team = _resolve_team("Garbage", reasons)
        assert team == "Waste Collection Team"

    def test_unknown_category_falls_back(self) -> None:
        reasons: list[str] = []
        team = _resolve_team("Telekinesis", reasons)
        assert team == "General Field Team"

    def test_none_category_falls_back(self) -> None:
        reasons: list[str] = []
        team = _resolve_team(None, reasons)
        assert team == "General Field Team"


# ===========================================================================
# Zone resolution
# ===========================================================================


class TestResolveZone:
    def test_known_category_returns_correct_zone(self) -> None:
        reasons: list[str] = []
        zone = _resolve_zone("Road Damage", reasons)
        assert zone == "Zone A"

    def test_known_category_flooding_zone_c(self) -> None:
        reasons: list[str] = []
        zone = _resolve_zone("Flooding", reasons)
        assert zone == "Zone C"

    def test_unknown_category_falls_back_to_default_zone(self) -> None:
        reasons: list[str] = []
        zone = _resolve_zone("Invisible Wall", reasons)
        assert zone == "Zone G"


# ===========================================================================
# SLA resolution
# ===========================================================================


class TestResolveSla:
    def test_critical_override_is_stricter_than_base(self) -> None:
        """Open Manhole base=6h, Critical override=4h → should apply 4h."""
        reasons: list[str] = []
        sla = _resolve_sla("Open Manhole", "Critical", reasons)
        assert sla == 4
        assert any("overrides SLA to 4" in r for r in reasons)

    def test_base_stricter_than_high_override(self) -> None:
        """Open Manhole base=6h, High override=12h → base wins → 6h."""
        reasons: list[str] = []
        sla = _resolve_sla("Open Manhole", "High", reasons)
        assert sla == 6
        assert any("base SLA retained" in r for r in reasons)

    def test_high_override_stricter_than_garbage_base(self) -> None:
        """Garbage base=48h, High override=12h → override wins → 12h."""
        reasons: list[str] = []
        sla = _resolve_sla("Garbage", "High", reasons)
        assert sla == 12
        assert any("overrides SLA to 12" in r for r in reasons)

    def test_unknown_category_uses_default_sla(self) -> None:
        reasons: list[str] = []
        sla = _resolve_sla("Unicorn Sighting", "Low", reasons)
        # Default base = 72, Low override = 72 → either wins, result = 72
        assert sla == 72

    def test_sla_not_below_min(self) -> None:
        """Even Critical override (4h) must be >= MIN_SLA_HOURS (2h)."""
        reasons: list[str] = []
        sla = _resolve_sla("Flooding", "Critical", reasons)
        assert sla >= 2

    def test_sla_not_above_max(self) -> None:
        reasons: list[str] = []
        sla = _resolve_sla("Noise Pollution", "Low", reasons)
        assert sla <= 168


# ===========================================================================
# Escalation resolution
# ===========================================================================


class TestResolveEscalation:
    def _escalate(self, **kwargs) -> tuple[bool, list[str]]:
        defaults = dict(
            priority_level="Medium",
            priority_score=50.0,
            category="Garbage",
            cluster_size=1,
        )
        defaults.update(kwargs)
        reasons: list[str] = []
        result = _resolve_escalation(**defaults, reasons=reasons)
        return result, reasons

    def test_critical_level_triggers_escalation(self) -> None:
        escalate, reasons = self._escalate(priority_level="Critical")
        assert escalate is True
        assert any("'Critical' priority level" in r for r in reasons)

    def test_high_level_triggers_escalation(self) -> None:
        escalate, reasons = self._escalate(priority_level="High")
        assert escalate is True

    def test_score_above_threshold_triggers_escalation(self) -> None:
        escalate, reasons = self._escalate(priority_level="Low", priority_score=75.0)
        assert escalate is True
        assert any("75.0" in r for r in reasons)

    def test_always_escalate_category_triggers(self) -> None:
        escalate, reasons = self._escalate(
            priority_level="Low", priority_score=30.0,
            category="Electrical Hazard",
        )
        assert escalate is True
        assert any("public-safety hazard" in r for r in reasons)

    def test_cluster_size_threshold_triggers(self) -> None:
        escalate, reasons = self._escalate(
            priority_level="Low", priority_score=30.0,
            category="Garbage", cluster_size=10,
        )
        assert escalate is True
        assert any("community impact threshold" in r for r in reasons)

    def test_no_trigger_means_no_escalation(self) -> None:
        escalate, reasons = self._escalate(
            priority_level="Low", priority_score=30.0,
            category="Garbage", cluster_size=1,
        )
        assert escalate is False
        assert any("standard queue" in r for r in reasons)

    def test_medium_level_does_not_escalate_alone(self) -> None:
        escalate, _ = self._escalate(priority_level="Medium", priority_score=50.0)
        assert escalate is False


# ===========================================================================
# calculate_route() — integration tests
# ===========================================================================


class TestCalculateRoute:
    def test_known_category_returns_full_routing_result(self) -> None:
        result = _route(category="Road Damage", priority_level="Medium", priority_score=50.0)
        assert result["department"] == "Road Department"
        assert result["team"] == "Road Maintenance Team"
        assert result["zone"] == "Zone A"
        assert isinstance(result["sla_hours"], int)
        assert isinstance(result["requires_escalation"], bool)
        assert len(result["routing_reason"]) > 0

    def test_unknown_category_uses_defaults(self) -> None:
        result = _route(category="Invisible Bridge", priority_level="Low", priority_score=20.0)
        assert result["department"] == "General Administration"
        assert result["team"] == "General Field Team"
        assert result["zone"] == "Zone G"

    def test_none_category_uses_defaults(self) -> None:
        result = _route(category=None)
        assert result["department"] == "General Administration"

    def test_critical_priority_applies_4h_sla_when_stricter(self) -> None:
        # Garbage base SLA = 48h; Critical override = 4h → 4h
        result = _route(category="Garbage", priority_level="Critical", priority_score=92.0)
        assert result["sla_hours"] == 4
        assert result["requires_escalation"] is True

    def test_high_cluster_triggers_escalation(self) -> None:
        result = _route(
            category="Garbage",
            priority_level="Low",
            priority_score=20.0,
            cluster_size=15,
        )
        assert result["requires_escalation"] is True

    def test_routing_reason_is_non_empty_list_of_strings(self) -> None:
        result = _route()
        assert isinstance(result["routing_reason"], list)
        assert all(isinstance(r, str) for r in result["routing_reason"])
        assert len(result["routing_reason"]) >= 5

    def test_invalid_priority_score_returns_fallback(self) -> None:
        """priority_score > 100 fails Pydantic validation → graceful fallback."""
        result = calculate_route(
            complaint_data={"category": "Garbage"},
            duplicate_data={"is_duplicate": False, "cluster_size": 1},
            priority_data={"priority_level": "High", "priority_score": 999.0},
        )
        # Fallback result should still be a valid RoutingResult shape
        assert "department" in result
        assert "routing_reason" in result
        # Fallback message recorded
        assert any("fallback" in r.lower() for r in result["routing_reason"])

    def test_flooding_always_escalates(self) -> None:
        result = _route(category="Flooding", priority_level="Low", priority_score=30.0)
        assert result["requires_escalation"] is True

    def test_all_required_keys_present(self) -> None:
        result = _route()
        required = {"department", "team", "zone", "sla_hours",
                    "requires_escalation", "routing_reason"}
        assert required.issubset(result.keys())
