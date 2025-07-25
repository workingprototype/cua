"""
PII anonymization callback handler using Microsoft Presidio for text and image redaction.
"""

from typing import List, Dict, Any, Optional, Tuple
from .base import AsyncCallbackHandler
import base64
import io
import logging

try:
    from presidio_analyzer import AnalyzerEngine
    from presidio_anonymizer import AnonymizerEngine, DeanonymizeEngine
    from presidio_anonymizer.entities import RecognizerResult, OperatorConfig
    from presidio_image_redactor import ImageRedactorEngine
    from PIL import Image
    PRESIDIO_AVAILABLE = True
except ImportError:
    PRESIDIO_AVAILABLE = False

logger = logging.getLogger(__name__)

class PIIAnonymizationCallback(AsyncCallbackHandler):
    """
    Callback handler that anonymizes PII in text and images using Microsoft Presidio.
    
    This handler:
    1. Anonymizes PII in messages before sending to the agent loop
    2. Deanonymizes PII in tool calls and message outputs after the agent loop
    3. Redacts PII from images in computer_call_output messages
    """
    
    def __init__(
        self,
        anonymize_text: bool = True,
        anonymize_images: bool = True,
        entities_to_anonymize: Optional[List[str]] = None,
        anonymization_operator: str = "replace",
        image_redaction_color: Tuple[int, int, int] = (255, 192, 203)  # Pink
    ):
        """
        Initialize the PII anonymization callback.
        
        Args:
            anonymize_text: Whether to anonymize text content
            anonymize_images: Whether to redact images
            entities_to_anonymize: List of entity types to anonymize (None for all)
            anonymization_operator: Presidio operator to use ("replace", "mask", "redact", etc.)
            image_redaction_color: RGB color for image redaction
        """
        if not PRESIDIO_AVAILABLE:
            raise ImportError(
                "Presidio is not available. Install with: "
                "pip install presidio-analyzer presidio-anonymizer presidio-image-redactor"
            )
        
        self.anonymize_text = anonymize_text
        self.anonymize_images = anonymize_images
        self.entities_to_anonymize = entities_to_anonymize
        self.anonymization_operator = anonymization_operator
        self.image_redaction_color = image_redaction_color
        
        # Initialize Presidio engines
        self.analyzer = AnalyzerEngine()
        self.anonymizer = AnonymizerEngine()
        self.deanonymizer = DeanonymizeEngine()
        self.image_redactor = ImageRedactorEngine()
        
        # Store anonymization mappings for deanonymization
        self.anonymization_mappings: Dict[str, Any] = {}
    
    async def on_llm_start(self, messages: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Anonymize PII in messages before sending to agent loop.
        
        Args:
            messages: List of message dictionaries
            
        Returns:
            List of messages with PII anonymized
        """
        if not self.anonymize_text and not self.anonymize_images:
            return messages
        
        anonymized_messages = []
        for msg in messages:
            anonymized_msg = await self._anonymize_message(msg)
            anonymized_messages.append(anonymized_msg)
        
        return anonymized_messages
    
    async def on_llm_end(self, output: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Deanonymize PII in tool calls and message outputs after agent loop.
        
        Args:
            output: List of output dictionaries
            
        Returns:
            List of output with PII deanonymized for tool calls
        """
        if not self.anonymize_text:
            return output
        
        deanonymized_output = []
        for item in output:
            # Only deanonymize tool calls and computer_call messages
            if item.get("type") in ["computer_call", "computer_call_output"]:
                deanonymized_item = await self._deanonymize_item(item)
                deanonymized_output.append(deanonymized_item)
            else:
                deanonymized_output.append(item)
        
        return deanonymized_output
    
    async def _anonymize_message(self, message: Dict[str, Any]) -> Dict[str, Any]:
        """Anonymize PII in a single message."""
        msg_copy = message.copy()
        
        # Anonymize text content
        if self.anonymize_text:
            msg_copy = await self._anonymize_text_content(msg_copy)
        
        # Redact images in computer_call_output
        if self.anonymize_images and msg_copy.get("type") == "computer_call_output":
            msg_copy = await self._redact_image_content(msg_copy)
        
        return msg_copy
    
    async def _anonymize_text_content(self, message: Dict[str, Any]) -> Dict[str, Any]:
        """Anonymize text content in a message."""
        msg_copy = message.copy()
        
        # Handle content array
        content = msg_copy.get("content", [])
        if isinstance(content, str):
            anonymized_text, _ = await self._anonymize_text(content)
            msg_copy["content"] = anonymized_text
        elif isinstance(content, list):
            anonymized_content = []
            for item in content:
                if isinstance(item, dict) and item.get("type") == "text":
                    text = item.get("text", "")
                    anonymized_text, _ = await self._anonymize_text(text)
                    item_copy = item.copy()
                    item_copy["text"] = anonymized_text
                    anonymized_content.append(item_copy)
                else:
                    anonymized_content.append(item)
            msg_copy["content"] = anonymized_content
        
        return msg_copy
    
    async def _redact_image_content(self, message: Dict[str, Any]) -> Dict[str, Any]:
        """Redact PII from images in computer_call_output messages."""
        msg_copy = message.copy()
        output = msg_copy.get("output", {})
        
        if isinstance(output, dict) and "image_url" in output:
            try:
                # Extract base64 image data
                image_url = output["image_url"]
                if image_url.startswith("data:image/"):
                    # Parse data URL
                    header, data = image_url.split(",", 1)
                    image_data = base64.b64decode(data)
                    
                    # Load image with PIL
                    image = Image.open(io.BytesIO(image_data))
                    
                    # Redact PII from image
                    redacted_image = self.image_redactor.redact(image, self.image_redaction_color)
                    
                    # Convert back to base64
                    buffer = io.BytesIO()
                    redacted_image.save(buffer, format="PNG")
                    redacted_data = base64.b64encode(buffer.getvalue()).decode()
                    
                    # Update image URL
                    output_copy = output.copy()
                    output_copy["image_url"] = f"data:image/png;base64,{redacted_data}"
                    msg_copy["output"] = output_copy
                    
            except Exception as e:
                logger.warning(f"Failed to redact image: {e}")
        
        return msg_copy
    
    async def _deanonymize_item(self, item: Dict[str, Any]) -> Dict[str, Any]:
        """Deanonymize PII in tool calls and computer outputs."""
        item_copy = item.copy()
        
        # Handle computer_call arguments
        if item.get("type") == "computer_call":
            args = item_copy.get("args", {})
            if isinstance(args, dict):
                deanonymized_args = {}
                for key, value in args.items():
                    if isinstance(value, str):
                        deanonymized_value, _ = await self._deanonymize_text(value)
                        deanonymized_args[key] = deanonymized_value
                    else:
                        deanonymized_args[key] = value
                item_copy["args"] = deanonymized_args
        
        return item_copy
    
    async def _anonymize_text(self, text: str) -> Tuple[str, List[RecognizerResult]]:
        """Anonymize PII in text and return the anonymized text and results."""
        if not text.strip():
            return text, []
        
        try:
            # Analyze text for PII
            analyzer_results = self.analyzer.analyze(
                text=text,
                entities=self.entities_to_anonymize,
                language="en"
            )
            
            if not analyzer_results:
                return text, []
            
            # Anonymize the text
            anonymized_result = self.anonymizer.anonymize(
                text=text,
                analyzer_results=analyzer_results,
                operators={entity_type: OperatorConfig(self.anonymization_operator) 
                          for entity_type in set(result.entity_type for result in analyzer_results)}
            )
            
            # Store mapping for deanonymization
            mapping_key = str(hash(text))
            self.anonymization_mappings[mapping_key] = {
                "original": text,
                "anonymized": anonymized_result.text,
                "results": analyzer_results
            }
            
            return anonymized_result.text, analyzer_results
            
        except Exception as e:
            logger.warning(f"Failed to anonymize text: {e}")
            return text, []
    
    async def _deanonymize_text(self, text: str) -> Tuple[str, bool]:
        """Attempt to deanonymize text using stored mappings."""
        try:
            # Look for matching anonymized text in mappings
            for mapping_key, mapping in self.anonymization_mappings.items():
                if mapping["anonymized"] == text:
                    return mapping["original"], True
            
            # If no mapping found, return original text
            return text, False
            
        except Exception as e:
            logger.warning(f"Failed to deanonymize text: {e}")
            return text, False
