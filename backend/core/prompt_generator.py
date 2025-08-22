#!/usr/bin/env python3
"""
Core prompt generation module for writing prompts.
Handles prompt creation and data structure.
"""

import uuid
from typing import Dict, Any

def generate_writing_prompt(description: str, image_filename: str) -> Dict[str, Any]:
    """Generate a writing prompt based on the image description."""
    prompt_id = f"ADMIN-IMG-{str(uuid.uuid4())[:8].upper()}"
    
    # Create a writing prompt based on the image
    writing_prompt = f"Look at this picture and write a story about what might happen next. What adventures could this scene have?"
    
    return {
        "id": prompt_id,
        "prompt": writing_prompt,
        "visual_description": description,
        "image_path": f"writing_prompts/{image_filename}",
        "tags": [
            "admin-created",
            "visual-inspiration",
            "descriptive-language", 
            "image-based"
        ],
        "source_file": "admin_upload"
    }

def create_prompt_data(prompt_dict: Dict[str, Any]) -> Dict[str, Any]:
    """Create the data structure for database insertion."""
    return {
        'id': prompt_dict['id'],
        'source_file': prompt_dict['source_file'],
        'prompt': prompt_dict['prompt'],
        'tags': prompt_dict['tags'],
        'visual_description': prompt_dict['visual_description'],
        'image_path': prompt_dict['image_path']
    }

def validate_prompt_data(prompt_dict: Dict[str, Any]) -> bool:
    """Validate that prompt data has all required fields."""
    required_fields = ['id', 'prompt', 'visual_description', 'image_path', 'tags', 'source_file']
    
    for field in required_fields:
        if field not in prompt_dict:
            print(f"❌ Missing required field: {field}")
            return False
        
        if not prompt_dict[field]:
            print(f"❌ Empty required field: {field}")
            return False
    
    return True
