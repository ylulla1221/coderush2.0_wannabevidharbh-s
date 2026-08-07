# Routing Engine — CivicFlow AI

## Purpose

The **Routing Engine** is the fifth stage of the CivicFlow AI pipeline.
It receives the combined output of the Vision LLM, Duplicate Detection,
and Priority Engine and produces a deterministic routing decision that
tells the system *where* a complaint should go and *how fast* it must
be resolved.

**Routing is fully deterministic.**  No AI, no ML, no embeddings, no
external APIs, and no randomness are used anywhere in this module.

---

## Position in the Pipeline

```
Complaint Text (+ optional image)
        ↓
Vision LLM Extraction          ← produces category, location, urgency, …
        ↓
Duplicate Detection             ← produces is_duplicate, cluster_size, …
        ↓
Priority Engine                 ← produces priority_score, priority_level
        ↓
Routing Engine                  ← THIS MODULE
        ↓
MongoDB (via the main pipeline)
```

---

## Module Structure

```
routing/
├── __init__.py         Public API  — exports calculate_route()
├── config.py           Env-based runtime configuration (SLA overrides, thresholds)
├── constants.py        Business lookup tables (department / team / zone / SLA maps)
├── exceptions.py       Typed exception hierarchy
├── models.py           Pydantic v2 input & output models
├── routing_engine.py   Orchestrator — the ONLY entry point
└── README.md           This file
```

---

## Inputs

`calculate_route()` accepts three dictionaries produced by upstream stages:

```python
calculate_route(
    complaint_data = {        # from Vision LLM
        "category":  "Road Damage",
        "location":  "MG Road, Pune",
        # … other fields ignored by routing
    },
    duplicate_data = {        # from Duplicate Detection
        "is_duplicate": True,
        "cluster_size": 14,
    },
    priority_data = {         # from Priority Engine
        "priority_level": "High",
        "priority_score": 74.5,
    },
)
```

### RoutingInput fields

| Field            | Type         | Source               | Default   |
|------------------|--------------|----------------------|-----------|
| `category`       | `str \| None` | Vision LLM           | `None`    |
| `location`       | `str \| None` | Vision LLM           | `None`    |
| `priority_level` | `str`        | Priority Engine      | `"Medium"`|
| `priority_score` | `float`      | Priority Engine      | `40.0`    |
| `cluster_size`   | `int ≥ 1`    | Duplicate Detection  | `1`       |
| `is_duplicate`   | `bool`       | Duplicate Detection  | `False`   |

---

## Output

```json
{
    "department":          "Road Department",
    "team":                "Road Maintenance Team",
    "zone":                "Zone A",
    "sla_hours":           12,
    "requires_escalation": true,
    "routing_reason": [
        "Category 'Road Damage' maps to 'Road Department'.",
        "Complaint assigned to 'Road Maintenance Team'.",
        "Complaint routed to geographic 'Zone A'.",
        "Base SLA for 'Road Damage' is 12 hours.",
        "Base SLA (12 h) is already stricter than 'High' priority SLA (12 h); base SLA retained.",
        "'High' priority level triggers escalation.",
        "Cluster size 14 meets or exceeds the community impact threshold (10 complaints); escalation required."
    ]
}
```

### RoutingResult fields

| Field                 | Type        | Description                                      |
|-----------------------|-------------|--------------------------------------------------|
| `department`          | `str`       | Assigned government department                   |
| `team`                | `str`       | Specialist field team within the department      |
| `zone`                | `str`       | Administrative geographic zone                   |
| `sla_hours`           | `int`       | Maximum hours to resolve                         |
| `requires_escalation` | `bool`      | Whether the complaint bypasses the standard queue|
| `routing_reason`      | `list[str]` | Step-by-step audit trail of every decision       |

---

## Routing Flow

```
1. DEPARTMENT
   ├── Lookup category in CATEGORY_TO_DEPARTMENT
   └── Fallback → DEFAULT_DEPARTMENT (env-configurable)

2. TEAM
   ├── Lookup category in CATEGORY_TO_TEAM
   └── Fallback → DEFAULT_TEAM (env-configurable)

3. ZONE
   ├── Lookup category in CATEGORY_TO_ZONE
   └── Fallback → DEFAULT_ZONE (env-configurable)

4. SLA
   ├── Base SLA  = CATEGORY_TO_BASE_SLA[category]
   ├── Priority override = CRITICAL/HIGH/MEDIUM/LOW_PRIORITY_SLA
   ├── Apply override only if it is STRICTER (fewer hours) than base
   └── Clamp to [MIN_SLA_HOURS, MAX_SLA_HOURS]

5. ESCALATION  (OR logic — any trigger fires escalation)
   ├── priority_level in {Critical, High}
   ├── priority_score ≥ ESCALATION_SCORE_THRESHOLD (default 70.0)
   ├── category in ALWAYS_ESCALATE_CATEGORIES (life-safety hazards)
   └── cluster_size ≥ ESCALATION_CLUSTER_THRESHOLD (default 10)
```

---

## Department Mapping

| Category              | Department                  |
|-----------------------|-----------------------------|
| Road Damage           | Road Department             |
| Open Manhole          | Road Department             |
| Water Leakage         | Water Supply Department     |
| No Water Supply       | Water Supply Department     |
| Drainage Blocked      | Water Supply Department     |
| Flooding              | Water Supply Department     |
| Garbage               | Sanitation Department       |
| Dead Animal           | Sanitation Department       |
| Street Light          | Electricity Department      |
| Electrical Hazard     | Electricity Department      |
| Tree Fallen           | Parks Department            |
| Tree Hazard           | Parks Department            |
| Traffic Signal        | Traffic Department          |
| Illegal Parking       | Traffic Department          |
| Public Safety         | Public Safety Department    |
| Fire Hazard           | Public Safety Department    |
| Illegal Construction  | Town Planning Department    |
| Noise Pollution       | Environmental Department    |
| *(unknown)*           | General Administration      |

---

## SLA Mapping

### Base SLA by category

| Category              | Base SLA (hours) |
|-----------------------|-----------------|
| Open Manhole          | 6               |
| Electrical Hazard     | 6               |
| Flooding              | 6               |
| Tree Fallen           | 6               |
| Fire Hazard           | 6               |
| Road Damage           | 12              |
| Water Leakage         | 12              |
| No Water Supply       | 12              |
| Public Safety         | 12              |
| Drainage Blocked      | 24              |
| Traffic Signal        | 24              |
| Street Light          | 24              |
| Garbage               | 48              |
| Footpath Damage       | 48              |
| Illegal Construction  | 72              |
| Noise Pollution       | 72              |

### Priority SLA overrides (applied only if stricter)

| Priority Level | SLA Override (hours) |
|----------------|---------------------|
| Critical       | 4                   |
| High           | 12                  |
| Medium         | 24                  |
| Low            | 72                  |

---

## Escalation Rules

Escalation is triggered by **any** of the following:

1. `priority_level` is `"Critical"` or `"High"`.
2. `priority_score ≥ 70.0` (configurable via `ROUTING_ESCALATION_SCORE_THRESHOLD`).
3. `category` is in the always-escalate set:  
   `Electrical Hazard`, `Open Manhole`, `Flooding`, `Fire Hazard`, `Public Safety`.
4. `cluster_size ≥ 10` (configurable via `constants.ESCALATION_CLUSTER_THRESHOLD`).

---

## Configuration Reference

All values below can be overridden via `backend/.env`:

| Variable                              | Default | Description                            |
|---------------------------------------|---------|----------------------------------------|
| `ROUTING_DEFAULT_DEPARTMENT`          | `"General Administration"` | Fallback department |
| `ROUTING_DEFAULT_TEAM`                | `"General Field Team"`     | Fallback team       |
| `ROUTING_DEFAULT_ZONE`                | `"Zone G"`                 | Fallback zone       |
| `ROUTING_DEFAULT_SLA_HOURS`           | `72`    | Fallback SLA (hours)                   |
| `ROUTING_CRITICAL_PRIORITY_SLA`       | `4`     | SLA override for Critical priority     |
| `ROUTING_HIGH_PRIORITY_SLA`           | `12`    | SLA override for High priority         |
| `ROUTING_MEDIUM_PRIORITY_SLA`         | `24`    | SLA override for Medium priority       |
| `ROUTING_LOW_PRIORITY_SLA`            | `72`    | SLA override for Low priority          |
| `ROUTING_MIN_SLA_HOURS`               | `2`     | Hard floor on SLA                      |
| `ROUTING_MAX_SLA_HOURS`               | `168`   | Hard ceiling on SLA (7 days)           |
| `ROUTING_ESCALATION_SCORE_THRESHOLD`  | `70.0`  | Score that forces escalation           |

---

## Integration

```python
from app.ai.routing import calculate_route

routing_result = calculate_route(
    complaint_data=llm_result,
    duplicate_data=duplicate_result,
    priority_data=priority_result,
)
```

In `pipeline.py`:

```python
# Stage 4: Routing
logger.info("Stage 4: Department Routing")
routing_result = calculate_route(
    complaint_data=llm_result,
    duplicate_data=duplicate_result,
    priority_data=priority_result,
)
```

---

## Exception Handling

```
RoutingEngineError          (base — catch this for blanket handling)
    ├── RoutingValidationError     — bad input from upstream stage
    └── RoutingConfigurationError  — operator misconfigured env vars
```

The engine **never propagates exceptions** into the pipeline. If
Pydantic validation fails, a safe fallback `RoutingResult` is returned
and the error is logged at `ERROR` level.

---

## Future Improvements

- **Location-to-zone resolution**: Enrich `_resolve_zone()` with a
  postcode / area-name → zone lookup table so zone assignment is driven
  by the complaint's actual location rather than its category.
- **Officer assignment**: Extend `RoutingResult` with an `assigned_officer`
  field once the officer directory is available.
- **Cluster-aware department merging**: When a duplicate cluster spans
  multiple categories, implement multi-department co-routing.
- **SLA breach notification hooks**: Emit structured events when a
  complaint is within N hours of its SLA so downstream consumers can
  act without polling.
- **Hot-reload of lookup tables**: Allow `constants.py` mappings to be
  reloaded from a MongoDB config collection without restarting the service.
