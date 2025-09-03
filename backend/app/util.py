import re
import json
from typing import Any, Dict, Optional
from loguru import logger

def extract_json_from_text(text: str) -> Optional[Dict[str, Any]]:
    """
    Extract and parse JSON from text that might contain additional content.
    """
    # Try to find complete JSON objects by looking for balanced braces
    brace_count = 0
    start_pos = -1
    json_candidates = []
    
    for i, char in enumerate(text):
        if char == '{':
            if brace_count == 0:
                start_pos = i
            brace_count += 1
        elif char == '}':
            brace_count -= 1
            if brace_count == 0 and start_pos != -1:
                json_candidates.append(text[start_pos:i+1])
                start_pos = -1
    
    # Try each candidate
    for json_str in json_candidates:
        try:
            return json.loads(json_str)
        except json.JSONDecodeError:
            # Try cleaning up common formatting issues
            cleaned_json = re.sub(r'```json\s*|\s*```', '', json_str)
            try:
                return json.loads(cleaned_json)
            except json.JSONDecodeError:
                continue  # Try the next match
    
    # If no valid JSON found, try the original approach
    match = re.search(r'\{.*\}', text, re.DOTALL)
    if not match:
        return None

    json_str = match.group(0)

    try:
        return json.loads(json_str)
    except json.JSONDecodeError:
        json_str = re.sub(r'```json\s*|\s*```', '', json_str)
        try:
            return json.loads(json_str)
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse JSON: {str(e)}")
            return None


def validate_json_structure(data: Dict[str, Any], required_key: str) -> bool:
    """
    Validate that a JSON structure contains a required key with the correct type.
    
    Args:
        data: The JSON data to validate
        required_key: The key that must exist in the data
        
    Returns:
        bool: True if the structure is valid, False otherwise
    """
    if not isinstance(data, dict):
        return False
    
    if required_key not in data:
        return False
    
    value = data[required_key]
    
    # For list-type keys (questions, passages, etc.), ensure it's a list
    if required_key in ["questions", "passages", "prompts", "options"]:
        if not isinstance(value, list):
            return False
    
    # For string-type keys, ensure it's a string
    elif required_key in ["text", "explanation", "passage"]:
        if not isinstance(value, str):
            return False
    
    # For other keys, just ensure it's not None
    elif value is None:
        return False
    
    return True
