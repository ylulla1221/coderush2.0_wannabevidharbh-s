import uuid

from sentence_transformers import SentenceTransformer
from qdrant_client import QdrantClient
from qdrant_client.models import Distance, VectorParams, PointStruct
from dotenv import load_dotenv
import os

load_dotenv()

COLLECTION = os.getenv("QDRANT_COLLECTION")

client = QdrantClient(
    url=os.getenv("QDRANT_URL"),
    api_key=os.getenv("QDRANT_API_KEY")
)

model = SentenceTransformer("BAAI/bge-base-en-v1.5")

complaints = [
    {
        "id": str(uuid.uuid4()),
        "summary": "Large pothole outside VIT Pune Gate 3",
        "category": "Road Damage",
        "location": "VIT Pune"
    },
    {
        "id": str(uuid.uuid4()),
        "summary": "Huge road crack near VIT Main Gate",
        "category": "Road Damage",
        "location": "VIT Pune"
    },
    {
        "id": str(uuid.uuid4()),
        "summary": "Garbage overflowing near FC Road",
        "category": "Garbage",
        "location": "FC Road"
    },
]

points = []

for i, complaint in enumerate(complaints):
    vector = model.encode(complaint["summary"]).tolist()

    points.append(
        PointStruct(
            id=i + 1,
            vector=vector,
            payload=complaint
        )
    )

client.upsert(
    collection_name=COLLECTION,
    points=points
)

print(f"Inserted {len(points)} complaints.")

query = "Huge pothole near VIT Gate"

query_vector = model.encode(query).tolist()

results = client.query_points(
    collection_name=COLLECTION,
    query=query_vector,
    limit=3
).points

print("\nSearch Results\n")

for r in results:
    print("=" * 50)
    print("Score:", round(r.score, 4))
    print("Summary:", r.payload["summary"])
    print("Category:", r.payload["category"])
    print("Location:", r.payload["location"])