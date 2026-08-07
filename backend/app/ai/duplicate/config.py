"""
Configuration for CivicFlow AI Duplicate Detection module.

All configurable values are sourced from environment variables with
sensible production defaults. No other file in this module should
read os.environ directly — everything flows through this module.

Environment Variables:
    EMBEDDING_MODEL             HuggingFace model for sentence embeddings.
    QDRANT_HOST                 Qdrant server hostname.
    QDRANT_PORT                 Qdrant server gRPC port.
    QDRANT_COLLECTION           Name of the Qdrant collection.
    SIMILARITY_THRESHOLD        Score at or above which a complaint is
                                classified as a definite duplicate.
    POSSIBLE_DUPLICATE_THRESHOLD Score at or above which a complaint is
                                 classified as a possible duplicate.
    LOCATION_BOOST              Additive similarity boost for same location.
    CATEGORY_BOOST              Additive similarity boost for same category.
    CATEGORY_PENALTY            Multiplicative confidence penalty for
                                different category.
    SEARCH_LIMIT                Maximum number of similar vectors to
                                retrieve from the vector store per query.
"""

from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv

# =============================================================================
# LOAD ENVIRONMENT
# =============================================================================

load_dotenv(Path(__file__).resolve().parents[3] / ".env")

# =============================================================================
# EMBEDDING CONFIGURATION
# =============================================================================

EMBEDDING_MODEL: str = os.getenv(
    "EMBEDDING_MODEL",
    "BAAI/bge-base-en-v1.5",
)

# =============================================================================
# QDRANT CONFIGURATION
# =============================================================================

QDRANT_URL: str | None = os.getenv("QDRANT_URL")
QDRANT_API_KEY: str | None = os.getenv("QDRANT_API_KEY")
QDRANT_HOST: str = os.getenv("QDRANT_HOST", "localhost")
QDRANT_PORT: int = int(os.getenv("QDRANT_PORT", "6333"))
QDRANT_COLLECTION: str = os.getenv("QDRANT_COLLECTION", "civicflow_complaints")
# =============================================================================
# SIMILARITY THRESHOLDS
# =============================================================================

SIMILARITY_THRESHOLD: float = float(
    os.getenv("SIMILARITY_THRESHOLD", "0.90"),
)

POSSIBLE_DUPLICATE_THRESHOLD: float = float(
    os.getenv("POSSIBLE_DUPLICATE_THRESHOLD", "0.75"),
)

# =============================================================================
# SIMILARITY ADJUSTMENTS
# =============================================================================

LOCATION_BOOST: float = float(
    os.getenv("LOCATION_BOOST", "0.03"),
)

CATEGORY_BOOST: float = float(
    os.getenv("CATEGORY_BOOST", "0.02"),
)

CATEGORY_PENALTY: float = float(
    os.getenv("CATEGORY_PENALTY", "0.90"),
)

# =============================================================================
# SEARCH CONFIGURATION
# =============================================================================

SEARCH_LIMIT: int = int(
    os.getenv("SEARCH_LIMIT", "10"),
)
