from qdrant_client import QdrantClient
from qdrant_client.models import Distance, VectorParams
import os
from dotenv import load_dotenv

load_dotenv()

client = QdrantClient(
    url=os.getenv("QDRANT_URL"),
    api_key=os.getenv("QDRANT_API_KEY"),
)

collection_name = os.getenv("QDRANT_COLLECTION", "civicflow_complaints")

collections = [c.name for c in client.get_collections().collections]

if collection_name not in collections:
    client.create_collection(
        collection_name=collection_name,
        vectors_config=VectorParams(
            size=768,      # matches BAAI/bge-base-en-v1.5
            distance=Distance.COSINE,
        ),
    )
    print(f"Created collection: {collection_name}")
else:
    print(f"Collection already exists: {collection_name}")