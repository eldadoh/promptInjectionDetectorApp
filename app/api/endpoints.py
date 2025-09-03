from fastapi import APIRouter, Depends, HTTPException
import uuid
from datetime import datetime

from ..schemas.request_response import ClassificationRequest, ClassificationResponse
from ..services.classifier import ClassifierService
from ..services.llm_factory import LLMFactory
from ..db.database import get_db
from ..core.config import settings

router = APIRouter()

@router.post("/classify", response_model=ClassificationResponse)
async def classify_text(
    request: ClassificationRequest,
    conn = Depends(get_db),
):
    """
    Classify text as either malicious (prompt injection) or benign.
    """
    try:
        # Check if provider is specified and not "openai"
        if request.provider is not None and request.provider != "openai":
            raise ValueError(f"Provider '{request.provider}' is not supported. Only 'openai' is available.")
            
        # Initialize classifier service with the OpenAI provider
        classifier_service = ClassifierService(provider_name="openai")
        
        # Classify text
        result = classifier_service.classify_text(
            text=request.text,
            model_version=request.model_version or settings.DEFAULT_MODEL,
            prompt_version=request.prompt_version or settings.DEFAULT_PROMPT_VERSION,
            conn=conn
        )
        
        # Make sure to include all fields in the response, with safe fallbacks for missing fields
        response = {
            "text": request.text,
            "classification": result.get("classification", "unknown"),
            "confidence": result.get("confidence", 0.0),
            "reasoning": result.get("reasoning", "No reasoning provided"),
            "severity": result.get("severity", ""),
            "model_version": request.model_version or settings.DEFAULT_MODEL,
            "prompt_version": request.prompt_version or settings.DEFAULT_PROMPT_VERSION,
            "request_id": str(uuid.uuid4()),
            "timestamp": datetime.now().isoformat()
        }
        
        return response
        
    except ValueError as e:
        # Handle provider errors with a specific error code
        if "Provider" in str(e) and "not supported" in str(e):
            raise HTTPException(status_code=400, detail=str(e))
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        # Add more debug information
        import traceback
        error_detail = f"{str(e)}\n{traceback.format_exc()}"
        raise HTTPException(status_code=500, detail=error_detail)
