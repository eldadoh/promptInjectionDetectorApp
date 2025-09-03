from uuid import uuid4
from datetime import datetime
from typing import Dict, Any, Optional
import logging

from ..core.config import settings
from ..prompts.prompt_templates import get_prompt_template
from .llm_factory import LLMFactory, LLMProvider

logger = logging.getLogger(__name__)

class ClassifierService:
    """Service for classifying text."""
    
    def __init__(self, llm_provider: Optional[LLMProvider] = None, provider_name: Optional[str] = None):
        """
        Initialize the classifier service.
        
        Args:
            llm_provider: An optional LLM provider instance. If not provided, one will be created
                using the factory and provider_name.
            provider_name: The name of the provider to use. Ignored if llm_provider is provided.
        """
        self.llm_provider = llm_provider or LLMFactory.get_provider(provider_name)
    
    def classify_text(
        self, 
        text: str, 
        model_version: Optional[str] = None,
        prompt_version: Optional[str] = None,
        conn = None
    ) -> Dict[str, Any]:
        """
        Classify text as malicious or benign.
        
        Args:
            text: The text to classify
            model_version: The model version to use
            prompt_version: The prompt version to use
            conn: Database connection for logging
            
        Returns:
            Dict with classification results
        """
        
        model_version = model_version or settings.DEFAULT_MODEL
        prompt_version = prompt_version or settings.DEFAULT_PROMPT_VERSION
        
        request_id = str(uuid4())
        
        # Format prompt using the specified prompt template
        prompt_template = get_prompt_template(prompt_version)
        formatted_prompt = prompt_template.format(text)
        
        model_name = model_version  
        
        # Call LLM provider for classification
        result = self.llm_provider.classify_text(
            prompt=formatted_prompt,
            model=model_name
        )
        
        now = datetime.now()
        
        logger.info(f"Service response: {result}")
        logger.info(f"Service Classification response: {result['classification']}, Confidence: {result['confidence']}")
        
        # Prepare response
        response = {
            "text": text,
            "classification": result["classification"],
            "confidence": result["confidence"],
            "reasoning": result.get("reasoning", ""),
            "severity": result.get("severity", ""),
            "model_version": model_version,
            "prompt_version": prompt_version,
            "request_id": request_id,
            "timestamp": now,
        }
        
        # Log to database if connection is provided
        if conn:
            try:
                cursor = conn.cursor()
                cursor.execute(
                    """
                    INSERT INTO prompt_logs 
                    (request_id, input_text, classification, confidence, 
                    model_version, prompt_version, raw_response, created_at) 
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                    """,
                    (
                        request_id,
                        text,
                        result["classification"],
                        result["confidence"],
                        model_name,
                        prompt_version,
                        result.get("raw_response", ""),
                        now
                    )
                )
                conn.commit()
                cursor.close()
            except Exception as e:
                logger.error(f"Database logging error: {e}")
                conn.rollback()
        
        return response
