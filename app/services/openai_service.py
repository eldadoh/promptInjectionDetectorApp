import openai
import json
from typing import Dict, Any, Optional
from ..core.config import settings
import logging

from .llm_factory import LLMProvider, LLMFactory

logger = logging.getLogger(__name__)

class OpenAIService(LLMProvider):
    """Service for interacting with OpenAI API."""
    
    def __init__(self, api_key: Optional[str] = None):
        
        openai.api_key = api_key or settings.OPENAI_API_KEY
    
    def classify_text(self, prompt: str, model: str = None) -> Dict[str, Any]:
        """
        Classify text using OpenAI's API.
        
        Args:
            prompt: The formatted prompt to send to OpenAI
            model: The model to use for classification
            
        Returns:
            Dict with classification results
        """
        try:
            model = model or settings.DEFAULT_MODEL
            
            # Old-style API call
            response = openai.ChatCompletion.create(
                model=model,
                messages=[
                    {"role": "system", "content": "You are a cybersecurity assistant that detects prompt injection attacks."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.1
            )
            
            # Extract the response content - adjust for old API response format
            content = response['choices'][0]['message']['content']
            
            # Parse the JSON response
            try:
                result = json.loads(content)
                classification = result.get("classification", "benign")
                confidence = result.get("confidence", 0.0)
                
                # Add default severity for malicious results if not present
                severity = result.get("severity", "")
                
                return {
                    "classification": classification,
                    "confidence": confidence,
                    "reasoning": result.get("reasoning", "No reasoning provided"),
                    "severity": severity,
                    "raw_response": content
                }
            except json.JSONDecodeError:
                logger.error(f"Failed to parse OpenAI response as JSON: {content}")
                return {
                    "classification": "benign",
                    "confidence": -1.0,
                    "reasoning": "Error parsing response",
                    "severity": "",
                    "raw_response": content
                }
                
        except Exception as e:
            logger.error(f"Error calling OpenAI API: {str(e)}")
            raise

    def process_response(self, response_text: str, prompt_version: str, model_version: str) -> Dict[str, Any]:
        try:
            # Parse the JSON response
            result = json.loads(response_text)
            
            # For older prompt versions, calculate severity if malicious
            if "severity" not in result and result.get("classification") == "malicious":
                confidence = result.get("confidence", 0)
                
                # Determine severity based on confidence level
                if confidence >= 0.8:
                    result["severity"] = "high"
                elif confidence >= 0.5:
                    result["severity"] = "medium"
                else:
                    result["severity"] = "low"
            
            # Ensure response has consistent fields
            return {
                "classification": result.get("classification"),
                "confidence": result.get("confidence"),
                "reasoning": result.get("reasoning"),
                "severity": result.get("severity", ""),  # Default to empty string if missing
                "model_version": model_version,
                "prompt_version": prompt_version
            }
        except Exception as e:
            logger.error(f"Error processing LLM response: {e}")
            # Return a default error response
            return {
                "classification": "error",
                "confidence": 0,
                "reasoning": f"Error processing response: {str(e)}",
                "severity": "",
                "model_version": model_version,
                "prompt_version": prompt_version
            }

# Register the OpenAI provider with the factory
LLMFactory.register_provider("openai", OpenAIService)
