import json
import os
import sys
from pathlib import Path

# Add the app directory to the path so we can import from it
sys.path.append(str(Path(__file__).parent.parent / "app"))

from services.database import get_database_connection
from services.embedding_service import EmbeddingService
import asyncio

async def upload_image_prompts_to_database():
    """Upload the generated image-based writing prompts to the database."""
    
    # Load the generated prompts
    with open("writing_prompts_tobe_saved.json", "r") as f:
        data = json.load(f)
    
    prompts = data.get("writing_prompts", [])
    
    if not prompts:
        print("❌ No prompts found in image_based_prompts.json")
        return
    
    print(f"📝 Found {len(prompts)} image-based writing prompts to upload")
    
    # Initialize services
    supabase = get_database_connection()
    embedding_service = EmbeddingService()
    
    # Upload each prompt
    uploaded_count = 0
    failed_count = 0
    
    for prompt in prompts:
        try:
            # Generate embedding for the prompt text
            prompt_text = prompt["prompt"]
            embedding = embedding_service.generate_embedding(prompt_text)
            
            # Prepare data for database with the new image_path column
            prompt_data = {
                'id': prompt['id'],
                'source_file': prompt['source_file'],
                'prompt': prompt_text,
                'tags': prompt['tags'],
                'visual_description': prompt['visual_description'],
                'image_path': prompt['image_path'],  # Already in correct format from JSON
                'embedding': embedding
            }
            
            # Insert into writing_prompts table
            response = supabase.table("writing_prompts").upsert(prompt_data).execute()
            
            if response.data:
                uploaded_count += 1
                print(f"✅ Uploaded: {prompt['id']} - {prompt_text[:50]}...")
            else:
                failed_count += 1
                print(f"❌ Failed to upload: {prompt['id']}")
                
        except Exception as e:
            failed_count += 1
            print(f"❌ Error uploading {prompt.get('id', 'unknown')}: {e}")
    
    print(f"\n📊 UPLOAD SUMMARY:")
    print(f"✅ Successfully uploaded: {uploaded_count}")
    print(f"❌ Failed: {failed_count}")
    print(f"📝 Total processed: {len(prompts)}")
    
    if uploaded_count > 0:
        print(f"\n🎉 Successfully uploaded {uploaded_count} image-based writing prompts to your SSAT database!")
        print(f"These prompts are now available for generating SSAT writing tests.")

def copy_images_to_public_folder():
    """Copy extracted images to a public folder for web access."""
    
    # Create public images directory if it doesn't exist
    public_dir = Path("public/images/writing_prompts")
    public_dir.mkdir(parents=True, exist_ok=True)
    
    # Copy images from extracted_images to public folder
    extracted_dir = Path("extracted_images")
    
    if not extracted_dir.exists():
        print("❌ extracted_images directory not found")
        return
    
    copied_count = 0
    for image_file in extracted_dir.glob("*.jpeg"):
        try:
            # Copy to public folder
            dest_path = public_dir / image_file.name
            import shutil
            shutil.copy2(image_file, dest_path)
            copied_count += 1
            print(f"📁 Copied: {image_file.name}")
        except Exception as e:
            print(f"❌ Failed to copy {image_file.name}: {e}")
    
    print(f"\n📁 Copied {copied_count} images to {public_dir}")
    print(f"Images are now accessible at: /images/writing_prompts/")

if __name__ == "__main__":
    print("🚀 Starting upload of image-based writing prompts...")
    
    # First, copy images to public folder
    print("\n📁 Step 1: Copying images to public folder...")
    copy_images_to_public_folder()
    
    # Then upload prompts to database
    print("\n📝 Step 2: Uploading prompts to database...")
    asyncio.run(upload_image_prompts_to_database())
    
    print(f"\n🎯 NEXT STEPS:")
    print("1. The image-based prompts are now in your database with image_path column")
    print("2. Images are copied to public/images/writing_prompts/")
    print("3. Update your frontend to display actual images using the image_path field")
    print("4. Test generating SSAT writing tests with these new image-based prompts")
