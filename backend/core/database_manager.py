#!/usr/bin/env python3
"""
Core database manager module for writing prompts.
Handles database operations for prompt storage.
"""

import sys
from pathlib import Path
from typing import Dict, Any, List

# Add the app directory to the path so we can import from it
sys.path.append(str(Path(__file__).parent.parent / "app"))

from app.services.database import get_database_connection
from app.services.embedding_service import EmbeddingService

def save_prompt_to_database(prompt_data: Dict[str, Any]) -> bool:
    """Save a single prompt to the database."""
    try:
        # Initialize services
        supabase = get_database_connection()
        embedding_service = EmbeddingService()
        
        # Generate embedding for the prompt text
        prompt_text = prompt_data["prompt"]
        embedding = embedding_service.generate_embedding(prompt_text)
        
        # Prepare data for database
        db_data = {
            'id': prompt_data['id'],
            'source_file': prompt_data['source_file'],
            'prompt': prompt_text,
            'tags': prompt_data['tags'],
            'visual_description': prompt_data['visual_description'],
            'image_path': prompt_data['image_path'],
            'embedding': embedding
        }
        
        # Insert into writing_prompts table
        response = supabase.table("writing_prompts").upsert(db_data).execute()
        
        if response.data:
            print(f"✅ Successfully saved to database: {prompt_data['id']}")
            return True
        else:
            print(f"❌ Failed to save to database")
            return False
            
    except Exception as e:
        print(f"❌ Error saving to database: {e}")
        return False

def batch_save_prompts_to_database(prompts_data: List[Dict[str, Any]]) -> Dict[str, int]:
    """Save multiple prompts to the database and return statistics."""
    try:
        # Initialize services
        supabase = get_database_connection()
        embedding_service = EmbeddingService()
        
        successful_count = 0
        failed_count = 0
        
        for prompt_data in prompts_data:
            try:
                # Generate embedding for the prompt text
                prompt_text = prompt_data["prompt"]
                embedding = embedding_service.generate_embedding(prompt_text)
                
                # Prepare data for database
                db_data = {
                    'id': prompt_data['id'],
                    'source_file': prompt_data['source_file'],
                    'prompt': prompt_text,
                    'tags': prompt_data['tags'],
                    'visual_description': prompt_data['visual_description'],
                    'image_path': prompt_data['image_path'],
                    'embedding': embedding
                }
                
                # Insert into writing_prompts table
                response = supabase.table("writing_prompts").upsert(db_data).execute()
                
                if response.data:
                    successful_count += 1
                    print(f"✅ Saved: {prompt_data['id']}")
                else:
                    failed_count += 1
                    print(f"❌ Failed: {prompt_data['id']}")
                    
            except Exception as e:
                failed_count += 1
                print(f"❌ Error saving {prompt_data.get('id', 'unknown')}: {e}")
        
        return {
            'successful': successful_count,
            'failed': failed_count,
            'total': len(prompts_data)
        }
        
    except Exception as e:
        print(f"❌ Error in batch save: {e}")
        return {'successful': 0, 'failed': len(prompts_data), 'total': len(prompts_data)}

def check_existing_prompt(prompt_id: str) -> bool:
    """Check if a prompt already exists in the database."""
    try:
        supabase = get_database_connection()
        response = supabase.table("writing_prompts").select("id").eq("id", prompt_id).execute()
        return len(response.data) > 0
    except Exception as e:
        print(f"❌ Error checking existing prompt: {e}")
        return False
