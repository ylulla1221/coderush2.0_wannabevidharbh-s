import sys
from pathlib import Path
from pprint import pprint

# ---------------------------------------------------------------------
# Add backend/ to Python path
# ---------------------------------------------------------------------

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from app.ai.duplicate import find_duplicate_complaint


# ---------------------------------------------------------------------
# Test Dataset
# ---------------------------------------------------------------------

complaints = [
    {
        "category": "Road Damage",
        "department": "Road Department",
        "urgency": "High",
        "location": "VIT Pune Gate 3",
        "summary": "Large pothole outside VIT Pune Gate 3 causing accidents.",
        "confidence": 0.98,
    },
    {
        "category": "Road Damage",
        "department": "Road Department",
        "urgency": "High",
        "location": "VIT Pune",
        "summary": "Huge pothole near VIT Main Gate.",
        "confidence": 0.97,
    },
    {
        "category": "Road Damage",
        "department": "Road Department",
        "urgency": "Medium",
        "location": "VIT Pune Gate 3",
        "summary": "Road completely damaged outside Gate 3.",
        "confidence": 0.95,
    },
    {
        "category": "Garbage",
        "department": "Sanitation",
        "urgency": "Medium",
        "location": "FC Road",
        "summary": "Garbage overflowing near FC Road.",
        "confidence": 0.96,
    },
    {
        "category": "Garbage",
        "department": "Sanitation",
        "urgency": "Medium",
        "location": "FC Road",
        "summary": "Waste has not been collected on FC Road.",
        "confidence": 0.95,
    },
    {
        "category": "Street Light",
        "department": "Electricity",
        "urgency": "Low",
        "location": "Pune Station",
        "summary": "Streetlight not working near Pune Station.",
        "confidence": 0.94,
    },
    {
        "category": "Water Leakage",
        "department": "Water Department",
        "urgency": "High",
        "location": "Shivajinagar",
        "summary": "Water pipeline burst near Shivajinagar bus stand.",
        "confidence": 0.98,
    },
    {
        "category": "Water Leakage",
        "department": "Water Department",
        "urgency": "High",
        "location": "Shivajinagar",
        "summary": "Continuous water leakage near the Shivajinagar bus stop.",
        "confidence": 0.97,
    },
]


# ---------------------------------------------------------------------
# Run Test
# ---------------------------------------------------------------------

print("\n")
print("=" * 100)
print("CIVICFLOW AI - DUPLICATE DETECTION PIPELINE TEST")
print("=" * 100)

cluster_summary = {}

for i, complaint in enumerate(complaints, start=1):

    print("\n")
    print("=" * 100)
    print(f"Complaint #{i}")
    print("=" * 100)

    print("Summary:")
    print(complaint["summary"])

    result = find_duplicate_complaint(
        complaint_data=complaint,
        complaint_id=f"cmp_test_{i:03d}",
    )

    pprint(result)

    cluster_id = result["cluster_id"]

    cluster_summary.setdefault(cluster_id, 0)
    cluster_summary[cluster_id] += 1


print("\n")
print("=" * 100)
print("CLUSTER SUMMARY")
print("=" * 100)

for cluster, size in cluster_summary.items():
    print(f"{cluster:<35} -> {size} complaint(s)")

print("\n")
print("=" * 100)
print("TEST COMPLETED")
print("=" * 100)