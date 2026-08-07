"""
Comprehensive test suite for the CivicFlow AI Priority Engine.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

# ---------------------------------------------------------------------
# Add project root to Python path
# ---------------------------------------------------------------------

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.append(str(PROJECT_ROOT))

from app.ai.priority.priority_engine import calculate_priority


def print_result(title: str, result: dict) -> None:
    """Pretty-print a priority result."""

    print("\n" + "=" * 90)
    print(title)
    print("=" * 90)

    print(json.dumps(result, indent=4))


TEST_CASES = [
    {
        "title": "1. Critical Open Manhole",
        "complaint": {
            "urgency": "Critical",
            "category": "Open Manhole",
            "confidence": 0.98,
            "complaint_age_hours": 60,
        },
        "duplicate": {
            "is_duplicate": True,
            "cluster_size": 12,
            "similarity_score": 0.97,
        },
    },
    {
        "title": "2. Road Damage",
        "complaint": {
            "urgency": "High",
            "category": "Road Damage",
            "confidence": 0.95,
            "complaint_age_hours": 20,
        },
        "duplicate": {
            "is_duplicate": True,
            "cluster_size": 5,
            "similarity_score": 0.93,
        },
    },
    {
        "title": "3. Garbage Collection",
        "complaint": {
            "urgency": "Low",
            "category": "Garbage",
            "confidence": 0.82,
            "complaint_age_hours": 4,
        },
        "duplicate": {
            "is_duplicate": False,
            "cluster_size": 1,
            "similarity_score": 0.0,
        },
    },
    {
        "title": "4. Flooding Complaint",
        "complaint": {
            "urgency": "Critical",
            "category": "Flooding",
            "confidence": 0.99,
            "complaint_age_hours": 72,
        },
        "duplicate": {
            "is_duplicate": True,
            "cluster_size": 18,
            "similarity_score": 0.98,
        },
    },
    {
        "title": "5. Street Light Failure",
        "complaint": {
            "urgency": "Medium",
            "category": "Street Light",
            "confidence": 0.89,
            "complaint_age_hours": 10,
        },
        "duplicate": {
            "is_duplicate": True,
            "cluster_size": 3,
            "similarity_score": 0.91,
        },
    },
]


def main() -> None:
    print("\n")
    print("=" * 90)
    print("CIVICFLOW PRIORITY ENGINE TEST SUITE")
    print("=" * 90)

    for case in TEST_CASES:

        result = calculate_priority(
            complaint_data=case["complaint"],
            duplicate_data=case["duplicate"],
        )

        print_result(case["title"], result)

    print("\n")
    print("=" * 90)
    print("All Priority Engine tests completed successfully.")
    print("=" * 90)


if __name__ == "__main__":
    main()