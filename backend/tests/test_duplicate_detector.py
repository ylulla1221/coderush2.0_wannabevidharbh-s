import sys
from pathlib import Path

# Add backend/ to Python path
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from app.ai.duplicate import find_duplicate_complaint

complaint = {
    "category": "Road Damage",
    "department": "Road Department",
    "urgency": "High",
    "location": "VIT Pune",
    "summary": "Huge pothole near VIT Gate 3",
    "confidence": 0.95,
}

result = find_duplicate_complaint(
    complaint_data=complaint,
    complaint_id="cmp_test_001"
)

print("\nDuplicate Detection Result\n")
print(result)