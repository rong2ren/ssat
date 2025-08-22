#!/usr/bin/env python3
"""
Script to process multiple images and create writing prompts.
This script:
1. Finds images in specified folder
2. Uses Gemini LLM to describe each image
3. Copies images to frontend/public/images/writing_prompts/
4. Generates writing prompts and saves directly to database
5. Shows progress and results

Usage: python batch_create_prompts.py --folder <folder_path>
Example: python batch_create_prompts.py --folder admin_images/
"""

import os
import sys
import argparse
from pathlib import Path

# Add the core directory to the path
sys.path.append(str(Path(__file__).parent.parent / "core"))

from core.image_processor import find_images_in_folder, describe_image_with_llm, copy_image_to_frontend
from core.prompt_generator import generate_writing_prompt
from core.database_manager import batch_save_prompts_to_database

def main():
    """Main function to process multiple images."""
    parser = argparse.ArgumentParser(description='Process multiple images and create writing prompts')
    parser.add_argument('--folder', required=True, help='Folder containing images to process')
    args = parser.parse_args()
    
    folder_path = args.folder
    
    # Check if folder exists
    if not os.path.exists(folder_path):
        print(f"❌ Error: Folder not found: {folder_path}")
        return
    
    print(f"🚀 Starting batch processing of images in: {folder_path}")
    
    # Find all images
    image_files = find_images_in_folder(folder_path)
    print(f"📁 Found {len(image_files)} images in {folder_path}")
    
    if not image_files:
        print("❌ No images found!")
        return
    
    # Process each image
    writing_prompts = []
    successful_count = 0
    error_count = 0
    
    for i, image_path in enumerate(image_files, 1):
        print(f"\n🔄 Processing image {i}/{len(image_files)}: {os.path.basename(image_path)}")
        
        try:
            # Step 1: Describe image with LLM
            print("  🤖 Describing image with Gemini...")
            description = describe_image_with_llm(image_path)
            
            if not description:
                print(f"  ❌ Failed to describe image, skipping...")
                error_count += 1
                continue
            
            # Step 2: Copy image to frontend
            print("  📁 Copying image to frontend...")
            frontend_image_path = copy_image_to_frontend(image_path)
            
            if not frontend_image_path:
                print(f"  ❌ Failed to copy image, skipping...")
                error_count += 1
                continue
            
            # Step 3: Generate writing prompt
            print("  ✍️  Generating writing prompt...")
            filename = os.path.basename(image_path)
            prompt_data = generate_writing_prompt(description, filename)
            writing_prompts.append(prompt_data)
            
            successful_count += 1
            print(f"  ✅ Successfully processed: {filename}")
            
        except Exception as e:
            print(f"  ❌ Error processing {image_path}: {e}")
            error_count += 1
            continue
    
    # Save all prompts to database
    if writing_prompts:
        print(f"\n💾 Saving {len(writing_prompts)} prompts to database...")
        results = batch_save_prompts_to_database(writing_prompts)
        
        print(f"\n🎉 BATCH PROCESSING COMPLETE!")
        print(f"✅ Successfully processed: {successful_count} images")
        print(f"❌ Errors: {error_count} images")
        print(f"💾 Database results: {results['successful']} saved, {results['failed']} failed")
        print(f"📄 Total prompts created: {len(writing_prompts)}")
        
        if results['successful'] > 0:
            print(f"\n💡 {results['successful']} prompts are now available in the writing prompt pool!")
    else:
        print(f"\n❌ No prompts were created successfully")

if __name__ == "__main__":
    main()
