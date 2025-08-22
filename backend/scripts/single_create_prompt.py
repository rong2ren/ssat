#!/usr/bin/env python3
"""
Script to create writing prompts from individual images.
Usage: python single_create_prompt.py <image_path>
Example: python single_create_prompt.py admin_images/cool_dog.jpg
"""

import os
import sys
from pathlib import Path

# Add the core directory to the path
sys.path.append(str(Path(__file__).parent.parent / "core"))

from core.image_processor import describe_image_with_llm, copy_image_to_frontend, validate_image_file
from core.prompt_generator import generate_writing_prompt
from core.database_manager import save_prompt_to_database

def main():
    """Main function to process a single image."""
    if len(sys.argv) != 2:
        print("❌ Usage: python single_create_prompt.py <image_path>")
        print("Example: python single_create_prompt.py admin_images/cool_dog.jpg")
        return
    
    image_path = sys.argv[1]
    
    # Validate image file
    if not validate_image_file(image_path):
        return
    
    print(f"🚀 Processing image: {image_path}")
    
    try:
        # Step 1: Describe image with LLM
        print("🤖 Describing image with Gemini...")
        description = describe_image_with_llm(image_path)
        
        if not description:
            print("❌ Failed to describe image, aborting...")
            return
        
        print(f"📝 Description: {description}")
        
        # Step 2: Copy image to frontend
        print("📁 Copying image to frontend...")
        frontend_image_path = copy_image_to_frontend(image_path)
        
        if not frontend_image_path:
            print("❌ Failed to copy image, aborting...")
            return
        
        # Step 3: Generate writing prompt
        print("✍️  Generating writing prompt...")
        filename = os.path.basename(frontend_image_path)
        prompt_data = generate_writing_prompt(description, filename)
        
        print(f"📝 Generated prompt: {prompt_data['prompt']}")
        print(f"🖼️  Image path: {prompt_data['image_path']}")
        
        # Step 4: Save to database
        print("💾 Saving to database...")
        success = save_prompt_to_database(prompt_data)
        
        if success:
            print(f"\n🎉 SUCCESS!")
            print(f"✅ Image processed and prompt created")
            print(f"📝 Prompt ID: {prompt_data['id']}")
            print(f"🖼️  Image: {prompt_data['image_path']}")
            print(f"📄 Description: {description[:100]}...")
            print(f"\n💡 The prompt is now available in the writing prompt pool!")
        else:
            print("❌ Failed to save to database")
            
    except Exception as e:
        print(f"❌ Error processing image: {e}")

if __name__ == "__main__":
    main()
