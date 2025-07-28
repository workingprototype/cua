"""
Image retention callback handler that limits the number of recent images in message history.
"""

from typing import List, Dict, Any, Optional
from .base import AsyncCallbackHandler


class ImageRetentionCallback(AsyncCallbackHandler):
    """
    Callback handler that applies image retention policy to limit the number
    of recent images in message history to prevent context window overflow.
    """
    
    def __init__(self, only_n_most_recent_images: Optional[int] = None):
        """
        Initialize the image retention callback.
        
        Args:
            only_n_most_recent_images: If set, only keep the N most recent images in message history
        """
        self.only_n_most_recent_images = only_n_most_recent_images
    
    async def on_llm_start(self, messages: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Apply image retention policy to messages before sending to agent loop.
        
        Args:
            messages: List of message dictionaries
            
        Returns:
            List of messages with image retention policy applied
        """
        if self.only_n_most_recent_images is None:
            return messages
        
        return self._apply_image_retention(messages)
    
    def _apply_image_retention(self, messages: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Apply image retention policy to keep only the N most recent images.
        
        Removes computer_call_output items with image_url and their corresponding computer_call items,
        keeping only the most recent N image pairs based on only_n_most_recent_images setting.
        
        Args:
            messages: List of message dictionaries
            
        Returns:
            Filtered list of messages with image retention applied
        """
        if self.only_n_most_recent_images is None:
            return messages
        
        # First pass: Assign call_id to reasoning items based on the next computer_call
        messages_with_call_ids = []
        for i, msg in enumerate(messages):
            msg_copy = msg.copy() if isinstance(msg, dict) else msg
            
            # If this is a reasoning item without a call_id, find the next computer_call
            if (msg_copy.get("type") == "reasoning" and 
                not msg_copy.get("call_id")):
                # Look ahead for the next computer_call
                for j in range(i + 1, len(messages)):
                    next_msg = messages[j]
                    if (next_msg.get("type") == "computer_call" and 
                        next_msg.get("call_id")):
                        msg_copy["call_id"] = next_msg.get("call_id")
                        break
            
            messages_with_call_ids.append(msg_copy)
        
        # Find all computer_call_output items with images and their call_ids
        image_call_ids = []
        for msg in reversed(messages_with_call_ids):  # Process in reverse to get most recent first
            if (msg.get("type") == "computer_call_output" and 
                isinstance(msg.get("output"), dict) and 
                "image_url" in msg.get("output", {})):
                call_id = msg.get("call_id")
                if call_id and call_id not in image_call_ids:
                    image_call_ids.append(call_id)
                    if len(image_call_ids) >= self.only_n_most_recent_images:
                        break
        
        # Keep the most recent N image call_ids (reverse to get chronological order)
        keep_call_ids = set(image_call_ids[:self.only_n_most_recent_images])
        
        # Filter messages: remove computer_call, computer_call_output, and reasoning for old images
        filtered_messages = []
        for msg in messages_with_call_ids:
            msg_type = msg.get("type")
            call_id = msg.get("call_id")
            
            # Remove old computer_call items
            if msg_type == "computer_call" and call_id not in keep_call_ids:
                # Check if this call_id corresponds to an image call
                has_image_output = any(
                    m.get("type") == "computer_call_output" and 
                    m.get("call_id") == call_id and
                    isinstance(m.get("output"), dict) and
                    "image_url" in m.get("output", {})
                    for m in messages_with_call_ids
                )
                if has_image_output:
                    continue  # Skip this computer_call
            
            # Remove old computer_call_output items with images
            if (msg_type == "computer_call_output" and 
                call_id not in keep_call_ids and
                isinstance(msg.get("output"), dict) and 
                "image_url" in msg.get("output", {})):
                continue  # Skip this computer_call_output
            
            # Remove old reasoning items that are paired with removed computer calls
            if (msg_type == "reasoning" and 
                call_id and call_id not in keep_call_ids):
                # Check if this call_id corresponds to an image call that's being removed
                has_image_output = any(
                    m.get("type") == "computer_call_output" and 
                    m.get("call_id") == call_id and
                    isinstance(m.get("output"), dict) and
                    "image_url" in m.get("output", {})
                    for m in messages_with_call_ids
                )
                if has_image_output:
                    continue  # Skip this reasoning item
            
            filtered_messages.append(msg)
        
        # Clean up: Remove call_id from reasoning items before returning
        final_messages = []
        for msg in filtered_messages:
            if msg.get("type") == "reasoning" and "call_id" in msg:
                # Create a copy without call_id for reasoning items
                cleaned_msg = {k: v for k, v in msg.items() if k != "call_id"}
                final_messages.append(cleaned_msg)
            else:
                final_messages.append(msg)
        
        return final_messages