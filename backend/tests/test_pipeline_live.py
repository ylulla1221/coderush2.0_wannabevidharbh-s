"""
Live end-to-end test for the CivicFlow AI Pipeline.

Runs the COMPLETE pipeline using the real AI modules and
stores the final output as JSON.

Pipeline

Complaint
    ↓
Vision LLM
    ↓
Duplicate Detection
    ↓
Priority Engine
    ↓
Routing Engine

Output

tests/output/pipeline_output.json
"""

from __future__ import annotations

import json
import sys
import time
from pathlib import Path

# ----------------------------------------------------------------------
# Add backend root
# ----------------------------------------------------------------------

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from app.ai.pipeline import process_complaint


# ----------------------------------------------------------------------
# ANSI Colors
# ----------------------------------------------------------------------

RESET = "\033[0m"

RED = "\033[91m"
GREEN = "\033[92m"
YELLOW = "\033[93m"
BLUE = "\033[94m"
MAGENTA = "\033[95m"
CYAN = "\033[96m"

BOLD = "\033[1m"


def banner(title: str) -> None:
    print()
    print(CYAN + "=" * 90)
    print(title.center(90))
    print("=" * 90 + RESET)


def success(msg: str) -> None:
    print(GREEN + "✓ " + msg + RESET)


def info(msg: str) -> None:
    print(BLUE + "• " + msg + RESET)


def warning(msg: str) -> None:
    print(YELLOW + "⚠ " + msg + RESET)


def error(msg: str) -> None:
    print(RED + "✗ " + msg + RESET)


# ----------------------------------------------------------------------
# Test Complaint
# ----------------------------------------------------------------------

TEST_COMPLAINT = """
There is a huge pothole near VIT Pune Main Gate.

The pothole has become dangerous after heavy rainfall.

Many two-wheelers have slipped.

Please repair it immediately before someone gets seriously injured.
"""


def main():

    banner("CIVICFLOW AI PIPELINE")

    start = time.perf_counter()

    result = process_complaint(
        complaint_text=TEST_COMPLAINT,
        image_path=None,
        location="VIT Pune",
    )

    total_time = time.perf_counter() - start

    if result["status"] != "success":
        error("Pipeline failed.")
        print(json.dumps(result, indent=4))
        return

    success("Vision LLM completed")

    success("Duplicate Detection completed")

    success("Priority Engine completed")

    success("Routing Engine completed")

    banner("PIPELINE SUMMARY")

    summary = result["summary"]

    print(f"{BOLD}Category             :{RESET} {summary.get('category')}")
    print(f"{BOLD}Urgency              :{RESET} {summary.get('urgency')}")
    print(f"{BOLD}Duplicate            :{RESET} {summary.get('is_duplicate')}")
    print(f"{BOLD}Priority             :{RESET} {summary.get('priority')}")
    print(f"{BOLD}Priority Score       :{RESET} {summary.get('priority_score')}")
    print(f"{BOLD}Department           :{RESET} {summary.get('department')}")
    print(f"{BOLD}Team                 :{RESET} {summary.get('team')}")
    print(f"{BOLD}Zone                 :{RESET} {summary.get('zone')}")
    print(f"{BOLD}SLA                  :{RESET} {summary.get('sla_hours')} hours")
    print(f"{BOLD}Escalation           :{RESET} {summary.get('requires_escalation')}")

    banner("AI DECISIONS")

    print(MAGENTA + "Duplicate Detection" + RESET)

    print(json.dumps(result["analysis"]["duplicate"], indent=4))

    print()

    print(MAGENTA + "Priority Engine" + RESET)

    print(json.dumps(result["analysis"]["priority"], indent=4))

    print()

    print(MAGENTA + "Routing Engine" + RESET)

    print(json.dumps(result["analysis"]["routing"], indent=4))

    # ------------------------------------------------------------------
    # Save JSON
    # ------------------------------------------------------------------

    output_dir = PROJECT_ROOT / "tests" / "output"

    output_dir.mkdir(parents=True, exist_ok=True)

    output_file = output_dir / "pipeline_output.json"

    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(result, f, indent=4)

    banner("PIPELINE COMPLETE")

    success("Pipeline executed successfully")

    success(f"Execution Time : {total_time:.2f} seconds")

    info(f"JSON saved to : {output_file}")

    print()


if __name__ == "__main__":
    main()