"""
Integration test for the complete CivicFlow AI Pipeline.

Pipeline:

Complaint
    ↓
Vision LLM
    ↓
Duplicate Detection
    ↓
Priority Engine
    ↓
Routing Engine

This test uses the REAL AI pipeline.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

# ---------------------------------------------------------------------
# Add project root
# ---------------------------------------------------------------------

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from app.ai.pipeline import process_complaint


def print_section(title: str) -> None:
    print("\n" + "=" * 90)
    print(title)
    print("=" * 90)


def main() -> None:

    complaint = """
    There is a huge pothole near VIT Pune main gate.

    Multiple two-wheelers have slipped because of it.

    It becomes worse during rain and is dangerous for commuters.

    Please repair it as soon as possible.
    """

    print_section("RUNNING CIVICFLOW AI PIPELINE")

    result = process_complaint(
        complaint_text=complaint,
        image_path=None,          # Add an image path if you have one
        location="VIT Pune",
    )

    print_section("FULL PIPELINE OUTPUT")

    print(json.dumps(result, indent=4))

    print_section("PIPELINE SUMMARY")

    summary = result.get("summary", {})

    print(f"Category              : {summary.get('category')}")
    print(f"Urgency              : {summary.get('urgency')}")
    print(f"Duplicate            : {summary.get('is_duplicate')}")
    print(f"Priority             : {summary.get('priority')}")
    print(f"Priority Score       : {summary.get('priority_score')}")
    print(f"Department           : {summary.get('department')}")
    print(f"Team                 : {summary.get('team')}")
    print(f"Zone                 : {summary.get('zone')}")
    print(f"SLA                  : {summary.get('sla_hours')} hrs")
    print(f"Escalation Required  : {summary.get('requires_escalation')}")

    print_section("PIPELINE VALIDATION")

    assert result["status"] == "success"

    assert "complaint" in result

    assert "analysis" in result

    assert "duplicate" in result["analysis"]

    assert "priority" in result["analysis"]

    assert "routing" in result["analysis"]

    assert "summary" in result

    print("✓ Pipeline executed successfully.")
    print("✓ Vision LLM completed.")
    print("✓ Duplicate Detection completed.")
    print("✓ Priority Engine completed.")
    print("✓ Routing Engine completed.")
    print("✓ Final JSON structure validated.")


if __name__ == "__main__":
    main()