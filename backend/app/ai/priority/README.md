# Priority Engine Module — CivicFlow AI

## Overview

The `priority/` module calculates a deterministic priority score and level for an incoming civic complaint. It acts as the fourth stage of the CivicFlow AI pipeline, consuming outputs from the Vision LLM and Duplicate Detection modules. It applies configuration-driven mathematical rules to derive priority without relying on direct LLM usage.

## Architecture

```
priority/
├── __init__.py              # Public API — exports calculate_priority()
├── config.py                # Environment-based configuration parameters
├── constants.py             # Static constants
├── exceptions.py            # Typed exception hierarchy
├── models.py                # Pydantic data models
├── scoring.py               # Deterministic scoring logic
├── priority_engine.py       # Orchestrator
└── README.md                # This file
```

## Scoring Formula

The priority score is calculated deterministically and capped at `[0.0, 100.0]`:

```
Raw Score = Base Urgency Score + Category Boost + Cluster Escalation Boost
```

1. **Base Urgency**: Sourced from the Vision LLM urgency flag (Critical=80, High=60, Medium=40, Low=20).
2. **Category Boost**: Priority escalation for high-impact categories (e.g. `Public Safety` gets +15).
3. **Cluster Escalation Boost**: Increase in score based on the community impact, computed as `(cluster_size - 1) * boost_per_complaint`, up to a configurable maximum limit.

The raw score is mapped to a Priority Level:
- `>= 80`: Critical
- `>= 60`: High
- `>= 40`: Medium
- `< 40`: Low

## Integration

The module provides the `calculate_priority` entry point for use in the main pipeline.

```python
from app.ai.priority import calculate_priority

priority_result = calculate_priority(
    complaint_data=llm_result,       # Dictionary from extract_complaint_information
    duplicate_data=duplicate_result  # Dictionary from find_duplicate_complaint
)
```
