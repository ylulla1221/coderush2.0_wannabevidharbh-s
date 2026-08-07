from fastapi import FastAPI
from pydantic import BaseModel
from typing import Optional

from app.ai.pipeline import process_complaint

app = FastAPI(
    title="CivicFlow AI API",
    version="1.0.0"
)


class ComplaintRequest(BaseModel):
    complaint_text: str
    image_path: Optional[str] = None
    location: Optional[str] = None


@app.get("/")
def health():
    return {
        "status": "running",
        "service": "CivicFlow AI"
    }


@app.post("/pipeline")
def run_pipeline(request: ComplaintRequest):
    result = process_complaint(
        complaint_text=request.complaint_text,
        image_path=request.image_path,
        location=request.location,
    )

    return result 