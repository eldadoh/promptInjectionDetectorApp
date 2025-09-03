from typing import Dict, Any, Optional, Type
import logging
from abc import ABC, abstractmethod

from ..core.config import settings

logger = logging.getLogger(__name__)

class LLMProvider(ABC):
    """Abstract base class for LLM providers."""
    
    @abstractmethod
    def classify_text(self, prompt: str, model: str = None) -> Dict[str, Any]:
        """
        Classify text using the LLM provider's API.
        
        Args:
            prompt: The formatted prompt to send to the LLM
            model: The model to use for classification
            
        Returns:
            Dict with classification results
        """
        pass
    
    @abstractmethod
    def process_response(self, response_text: str, prompt_version: str, model_version: str) -> Dict[str, Any]:
        """
        Process the raw response from the LLM.
        
        Args:
            response_text: The raw response text
            prompt_version: The prompt version used
            model_version: The model version used
            
        Returns:
            Dict with processed results
        """
        pass


class LLMFactory:
    """Factory for creating LLM provider instances."""
    
    _providers: Dict[str, Type[LLMProvider]] = {}
    
    @classmethod
    def register_provider(cls, provider_name: str, provider_class: Type[LLMProvider]):
        """
        Register a provider with the factory.
        
        Args:
            provider_name: The name of the provider
            provider_class: The provider class
        """
        cls._providers[provider_name] = provider_class
    
    @classmethod
    def get_provider(cls, provider_name: Optional[str] = None, **kwargs) -> LLMProvider:
        """
        Get a provider instance.
        
        Args:
            provider_name: The name of the provider, or None to use the default
            **kwargs: Additional arguments to pass to the provider constructor
            
        Returns:
            An instance of the requested provider
            
        Raises:
            ValueError: If the requested provider is not registered
        """
        provider_name = provider_name or settings.DEFAULT_LLM_PROVIDER
        
        if provider_name not in cls._providers:
            available_providers = ", ".join(cls._providers.keys())
            raise ValueError(f"Provider '{provider_name}' not found. Available providers: {available_providers}")
        
        provider_class = cls._providers[provider_name]
        return provider_class(**kwargs) 