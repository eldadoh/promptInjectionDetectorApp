from pydantic import BaseModel
from typing import Optional

class ClassificationRequest(BaseModel):
    """Request schema for classification."""
    text: str
    model_version: Optional[str] = None
    prompt_version: Optional[str] = None
    provider: Optional[str] = None

class ClassificationResponse(BaseModel):
    """Response schema for classification."""
    text: str
    classification: str
    confidence: float
    reasoning: Optional[str] = "No reasoning provided"
    severity: Optional[str] = ""
    model_version: str
    prompt_version: str
    request_id: str
    timestamp: str