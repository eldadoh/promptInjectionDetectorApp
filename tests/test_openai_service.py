import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))) 

import unittest
from unittest.mock import patch
import json

from app.services.openai_service import OpenAIService
from app.core.config import settings


class TestOpenAIService(unittest.TestCase):
    """Test cases for the OpenAIService class."""

    def setUp(self):
        """Set up test fixtures."""
        self.service = OpenAIService(api_key="test-api-key")
        
        # Sample OpenAI API response for a benign classification
        self.mock_benign_response = {
            'choices': [{
                'message': {
                    'content': '{"classification": "benign", "confidence": 0.95, "reasoning": "This is a simple question with no malicious intent."}'
                }
            }]
        }
        
        # Sample OpenAI API response for a malicious classification
        self.mock_malicious_response = {
            'choices': [{
                'message': {
                    'content': '{"classification": "malicious", "confidence": 0.98, "reasoning": "This contains a prompt injection attempt.", "severity": "high"}'
                }
            }]
        }
        
        # Sample OpenAI API response with invalid JSON
        self.mock_invalid_json_response = {
            'choices': [{
                'message': {
                    'content': 'This is not valid JSON'
                }
            }]
        }
    
    @patch('openai.ChatCompletion.create')
    def test_classify_text_benign(self, mock_create):
        """Test classification of benign text."""
        
        mock_create.return_value = self.mock_benign_response
        
        result = self.service.classify_text(
            prompt="Test prompt for benign text",
            model="gpt-4.1-nano"
        )
        
        self.assertEqual(result["classification"], "benign")
        self.assertEqual(result["confidence"], 0.95)
        self.assertIn("reasoning", result)
        self.assertEqual(result["severity"], "")
        self.assertIn("raw_response", result)
        
        mock_create.assert_called_with(
            model="gpt-4.1-nano",
            messages=[
                {"role": "system", "content": "You are a cybersecurity assistant that detects prompt injection attacks."},
                {"role": "user", "content": "Test prompt for benign text"}
            ],
            temperature=0.1
        )
    
    @patch('openai.ChatCompletion.create')
    def test_classify_text_malicious(self, mock_create):
        """Test classification of malicious text."""

        mock_create.return_value = self.mock_malicious_response
        
        result = self.service.classify_text(
            prompt="Test prompt for malicious text",
            model="gpt-4.1-nano"
        )
        
        self.assertEqual(result["classification"], "malicious")
        self.assertEqual(result["confidence"], 0.98)
        self.assertIn("reasoning", result)
        self.assertEqual(result["severity"], "high")
        self.assertIn("raw_response", result)
    
    @patch('openai.ChatCompletion.create')
    def test_classify_text_with_default_model(self, mock_create):
        """Test classification with default model."""

        mock_create.return_value = self.mock_benign_response
        
        result = self.service.classify_text(
            prompt="Test prompt with default model"
        )
        
        # Verify that the default model was used
        mock_create.assert_called_with(
            model=settings.DEFAULT_MODEL,
            messages=[
                {"role": "system", "content": "You are a cybersecurity assistant that detects prompt injection attacks."},
                {"role": "user", "content": "Test prompt with default model"}
            ],
            temperature=0.1
        )
    
    @patch('openai.ChatCompletion.create')
    def test_classify_text_with_invalid_json_response(self, mock_create):
        """Test handling of invalid JSON response."""
        
        # Configure mock to return invalid JSON
        mock_create.return_value = self.mock_invalid_json_response
        
        result = self.service.classify_text(
            prompt="Test prompt with invalid JSON response",
            model="gpt-4.1-nano"
        )
        
        # Verify fallback 
        self.assertEqual(result["classification"], "benign")
        self.assertEqual(result["confidence"], -1.0)
        self.assertEqual(result["reasoning"], "Error parsing response")
        self.assertEqual(result["severity"], "")
        self.assertEqual(result["raw_response"], "This is not valid JSON")
    
    @patch('openai.ChatCompletion.create')
    def test_api_error_handling(self, mock_create):
        """Test handling of API errors."""
        # Configure mock to raise an exception
        mock_create.side_effect = Exception("API Error")
        
        # Call classify_text method and expect exception to be propagated
        with self.assertRaises(Exception) as context:
            self.service.classify_text(
                prompt="Test prompt for API error",
                model="gpt-4.1-nano"
            )
        
        self.assertEqual(str(context.exception), "API Error")
    
    def test_process_response_malicious_with_severity(self):
        """Test processing response for malicious content with severity."""
        # Sample response with severity
        response_text = '{"classification": "malicious", "confidence": 0.98, "reasoning": "This is a test reasoning.", "severity": "high"}'
        
        result = self.service.process_response(
            response_text=response_text,
            prompt_version="v3",
            model_version="gpt-4.1-nano"
        )
        
        self.assertEqual(result["classification"], "malicious")
        self.assertEqual(result["confidence"], 0.98)
        self.assertEqual(result["reasoning"], "This is a test reasoning.")
        self.assertEqual(result["severity"], "high")
        self.assertEqual(result["model_version"], "gpt-4.1-nano")
        self.assertEqual(result["prompt_version"], "v3")
    
    def test_process_response_malicious_without_severity(self):
        """Test processing response for malicious content without severity (should calculate it)."""
        # Sample response without severity
        response_text = '{"classification": "malicious", "confidence": 0.85, "reasoning": "This is a test reasoning."}'
        
        result = self.service.process_response(
            response_text=response_text,
            prompt_version="v1",
            model_version="gpt-4.1-nano"
        )
        
        self.assertEqual(result["classification"], "malicious")
        self.assertEqual(result["confidence"], 0.85)
        self.assertEqual(result["severity"], "high")
        self.assertEqual(result["model_version"], "gpt-4.1-nano")
        self.assertEqual(result["prompt_version"], "v1")
    
    def test_process_response_malicious_medium_severity(self):
        """Test processing response with medium severity calculation."""
        # Sample response without severity and medium confidence
        response_text = '{"classification": "malicious", "confidence": 0.65, "reasoning": "This is a test reasoning."}'
        
        result = self.service.process_response(
            response_text=response_text,
            prompt_version="v1",
            model_version="gpt-4.1-nano"
        )
        
        self.assertEqual(result["classification"], "malicious")
        self.assertEqual(result["confidence"], 0.65)
        self.assertEqual(result["severity"], "medium") # A confidence of 0.65 should result in "medium" severity
    
    def test_process_response_malicious_low_severity(self):
        """Test processing response with low severity calculation."""
        # Sample response without severity and low confidence
        response_text = '{"classification": "malicious", "confidence": 0.35, "reasoning": "This is a test reasoning."}'
        
        result = self.service.process_response(
            response_text=response_text,
            prompt_version="v1",
            model_version="gpt-4.1-nano"
        )
        
        self.assertEqual(result["classification"], "malicious")
        self.assertEqual(result["confidence"], 0.35)
        self.assertEqual(result["severity"], "low") # A confidence of 0.35 should result in "low" severity
    
    def test_process_response_benign(self):
        """Test processing response for benign content."""
        # Sample benign response
        response_text = '{"classification": "benign", "confidence": 0.95, "reasoning": "This is a test reasoning."}'
        
        result = self.service.process_response(
            response_text=response_text,
            prompt_version="v2",
            model_version="gpt-4.1-nano"
        )
        
        self.assertEqual(result["classification"], "benign")
        self.assertEqual(result["confidence"], 0.95)
        self.assertEqual(result["reasoning"], "This is a test reasoning.")
        self.assertEqual(result["severity"], "")  # Should be empty for benign
        self.assertEqual(result["model_version"], "gpt-4.1-nano")
        self.assertEqual(result["prompt_version"], "v2")
    
    def test_process_response_error_handling(self):
        """Test error handling in process_response."""
        # Invalid JSON string
        response_text = "Not a valid JSON string"
        
        result = self.service.process_response(
            response_text=response_text,
            prompt_version="v1",
            model_version="gpt-4.1-nano"
        )
        
        self.assertEqual(result["classification"], "error")
        self.assertEqual(result["confidence"], 0)
        self.assertIn("Error processing response", result["reasoning"])
        self.assertEqual(result["severity"], "")
        self.assertEqual(result["model_version"], "gpt-4.1-nano")
        self.assertEqual(result["prompt_version"], "v1")


if __name__ == "__main__":
    unittest.main() 