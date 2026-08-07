from sentence_transformers import SentenceTransformer

model = SentenceTransformer("BAAI/bge-base-en-v1.5")

text = "Large pothole near Hanuman Mandir Chowk"

embedding = model.encode(text)

print(f"Embedding dimension: {len(embedding)}")