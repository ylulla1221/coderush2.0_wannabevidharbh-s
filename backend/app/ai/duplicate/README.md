# Duplicate Detection Module — CivicFlow AI

## Overview

The `duplicate/` module detects whether an incoming civic complaint is a
duplicate of an existing complaint, classifies the match type, and assigns
every complaint to a **complaint cluster**. It is the third stage of the
CivicFlow AI pipeline:

```
Complaint Text (+ optional Image)
        ↓
YOLO Object Detection
        ↓
LLM Complaint Extraction   ← produces structured JSON
        ↓
Duplicate Detection         ← THIS MODULE
        ↓
Priority Engine
        ↓
Routing Engine
        ↓
Pipeline Response
```

---

## Architecture

```
duplicate/
├── __init__.py              # Public API — exports find_duplicate_complaint()
├── config.py                # Centralised env-based configuration
├── exceptions.py            # Typed exception hierarchy
├── models.py                # Pydantic data models
├── embedder.py              # Sentence embedding generation (HuggingFace)
├── vector_store.py          # Vector database abstraction (Qdrant)
├── duplicate_detector.py    # Orchestrator — the ONLY entry point
└── README.md                # This file
```

### Dependency Flow

```
__init__.py
    └── duplicate_detector.py        ← orchestrator
            ├── embedder.py          ← generates embeddings
            ├── vector_store.py      ← stores / searches vectors
            ├── models.py            ← data contracts
            ├── config.py            ← all configuration
            └── exceptions.py        ← error types
```

**No module outside `duplicate/` should import `embedder.py` or
`vector_store.py` directly.** This mirrors the LLM module's design
where only `extract_complaint_information()` is public.

---

## Public API

### `find_duplicate_complaint(complaint_data, complaint_id=None)`

The **only** function external modules should call.

**Parameters:**

| Parameter        | Type              | Description                                      |
|------------------|-------------------|--------------------------------------------------|
| `complaint_data` | `dict[str, Any]`  | Structured complaint JSON from the LLM module.   |
| `complaint_id`   | `str \| None`     | Optional unique ID. Auto-generated if omitted.   |

**Returns:**

```python
{
    "is_duplicate": True,
    "duplicate_type": "duplicate",        # "duplicate" | "possible_duplicate" | "new"
    "cluster_id": "cluster_a1b2c3d4",
    "matched_complaint_id": "cmp_103",
    "cluster_size": 32,
    "similarity_score": 0.94,
    "reason": [
        "High semantic similarity",
        "Same category",
        "Nearby location"
    ]
}
```

**Usage:**

```python
from app.ai.duplicate import find_duplicate_complaint

llm_result = {
    "category": "Road Damage",
    "department": "Road Department",
    "urgency": "High",
    "location": "Hanuman Mandir Chowk",
    "summary": "Large pothole causing accidents.",
    "confidence": 0.96,
}

duplicate_result = find_duplicate_complaint(
    complaint_data=llm_result,
    complaint_id="cmp_201",
)
```

---

## Workflow

```
Structured Complaint JSON (from LLM module)
        ↓
1. Extract the "summary" field
        ↓
2. Generate sentence embedding        (embedder.py)
        ↓
3. Search Qdrant for similar vectors  (vector_store.py)
        ↓
4. Adjust similarity scores           (duplicate_detector.py)
   • Boost for same location
   • Boost for same category
   • Penalty for different category
        ↓
5. Classify the best match            (duplicate_detector.py)
   • ≥ 0.90 → Duplicate
   • 0.75–0.90 → Possible Duplicate
   • < 0.75 → New Complaint
        ↓
6. Assign to cluster                  (duplicate_detector.py)
   • Duplicate → join existing cluster
   • New       → create new cluster
        ↓
7. Store complaint in vector DB       (vector_store.py)
        ↓
8. Return DuplicateResult
```

---

## How Duplicate Detection Works

1. **Embedding**: The complaint summary is converted to a 768-dimensional
   dense vector using `BAAI/bge-base-en-v1.5` (configurable).

2. **Vector Search**: Qdrant performs approximate nearest-neighbor search
   using cosine distance to find the top-K most similar stored complaints.

3. **Score Adjustment**: Raw cosine scores are refined using metadata:
   - **Same location** → score receives a `+0.03` boost.
   - **Same category** → score receives a `+0.02` boost.
   - **Different category** → score is multiplied by `0.90` (penalty).

4. **Classification**: The best adjusted score determines the verdict:
   - `≥ 0.90` → **Duplicate** (same issue reported again).
   - `0.75–0.90` → **Possible Duplicate** (likely related, needs review).
   - `< 0.75` → **New Complaint** (distinct issue).

5. **Explainability**: Every result includes a `reason` array with
   human-readable explanations.

---

## How Clustering Works

Every complaint belongs to exactly one cluster:

- **Duplicate / Possible Duplicate**: The complaint joins the cluster of
  its best match. The `cluster_size` field reflects the updated count.

- **New Complaint**: A fresh cluster is created with a unique ID
  (e.g., `cluster_a1b2c3d4`). The complaint becomes the first member.

### Example Cluster

```
Cluster cluster_a1b2c3d4
├── Category: Road Damage
├── Location: Hanuman Mandir Chowk
├── Size: 32 complaints
└── Members: cmp_001, cmp_015, cmp_042, ...
```

Clusters enable:
- **Aggregated reporting**: "32 people reported road damage at Hanuman Mandir Chowk."
- **Priority escalation**: Larger clusters signal higher community impact.
- **Officer assignment**: Route entire clusters, not individual complaints.

---

## Configuration

All values are read from environment variables (via `backend/.env`):

| Variable                       | Default                     | Description                          |
|--------------------------------|-----------------------------|--------------------------------------|
| `EMBEDDING_MODEL`              | `BAAI/bge-base-en-v1.5`    | HuggingFace model for embeddings     |
| `QDRANT_HOST`                  | `localhost`                 | Qdrant server hostname               |
| `QDRANT_PORT`                  | `6333`                     | Qdrant server port                   |
| `QDRANT_COLLECTION`            | `civicflow_complaints`      | Qdrant collection name               |
| `SIMILARITY_THRESHOLD`         | `0.90`                     | Score for "Duplicate"                |
| `POSSIBLE_DUPLICATE_THRESHOLD` | `0.75`                     | Score for "Possible Duplicate"       |
| `LOCATION_BOOST`               | `0.03`                     | Boost for same location              |
| `CATEGORY_BOOST`               | `0.02`                     | Boost for same category              |
| `CATEGORY_PENALTY`             | `0.90`                     | Multiplier for different category    |
| `SEARCH_LIMIT`                 | `10`                       | Max candidates per search            |

---

## Integration with Pipeline

### With `llm.py`

The duplicate module receives the **output** of `extract_complaint_information()`:

```python
from app.ai.llm import extract_complaint_information
from app.ai.duplicate import find_duplicate_complaint

# Stage 2: LLM extraction
llm_result = extract_complaint_information(
    complaint_text=text,
    yolo_detection=yolo_result,
    image_path=image,
)

# Stage 3: Duplicate detection
duplicate_result = find_duplicate_complaint(
    complaint_data=llm_result,
    complaint_id="cmp_201",
)
```

### With `pipeline.py`

```python
# In pipeline.py — the full pipeline orchestration:

llm_result = extract_complaint_information(...)
duplicate_result = find_duplicate_complaint(complaint_data=llm_result)
# priority_result = calculate_priority(...)
# routing_result = route_complaint(...)
```

---

## Exception Handling

```
DuplicateDetectionError           ← base exception
    ├── EmbeddingError            ← model load / inference failures
    └── VectorStoreError          ← Qdrant connectivity / operation failures
```

The public API **never raises exceptions to external callers**. All errors
are caught internally and a safe fallback result is returned (the complaint
is treated as new). This matches the LLM module's error philosophy.

---

## Prerequisites

```bash
pip install sentence-transformers qdrant-client pydantic python-dotenv
```

Ensure Qdrant is running:

```bash
docker run -p 6333:6333 -p 6334:6334 qdrant/qdrant
```

---

## Design Decisions

| Decision                            | Rationale                                              |
|-------------------------------------|--------------------------------------------------------|
| Singleton embedding model           | Avoids re-downloading the model on every request.      |
| Lazy loading                        | Startup cost is deferred to first actual use.           |
| Thread-safe initialisation          | Safe for ASGI servers running concurrent requests.     |
| Pydantic models                     | Automatic validation, serialisation, IDE support.      |
| Backend-agnostic vector store       | Swap Qdrant for FAISS/Pinecone by changing one file.   |
| Explainable reasons array           | Every decision is auditable and human-readable.        |
| Fallback on error                   | The pipeline never crashes — graceful degradation.     |
| SHA-256 ID hashing                  | String IDs are deterministically mapped to Qdrant ints.|
| Normalised embeddings               | Cosine similarity reduces to dot product (faster).     |
