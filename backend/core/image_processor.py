#!/usr/bin/env python3
"""
Core image processing module for writing prompt generation.
Handles image description with LLM and file operations.
"""

import os
import glob
import shutil
import base64
import uuid
from typing import List
import google.generativeai as genai
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Configure Gemini
genai.configure(api_key=os.getenv('GEMINI_API_KEY'))
model = genai.GenerativeModel('gemini-1.5-flash')

def find_images_in_folder(folder_path: str) -> List[str]:
    """Find all image files in the specified folder."""
    image_extensions = ['*.jpg', '*.jpeg', '*.png', '*.gif', '*.bmp']
    image_files = []
    
    for ext in image_extensions:
        pattern = os.path.join(folder_path, ext)
        image_files.extend(glob.glob(pattern))
    
    return sorted(image_files)

def describe_image_with_llm(image_path: str) -> str:
    """Use Gemini to describe an image."""
    try:
        # Read image file
        with open(image_path, 'rb') as img_file:
            image_data = img_file.read()
        
        # Encode image for Gemini
        image_bytes = base64.b64encode(image_data).decode('utf-8')
        
        # Create image part for Gemini
        image_part = {
            "mime_type": "image/jpeg",
            "data": image_bytes
        }
        
        # Generate description
        prompt = "Describe this image in 2-3 sentences. Be clear and engaging, but keep it short and simple. Focus on what's happening in the image."
        response = model.generate_content([prompt, image_part])
        
        # Clean up the response - remove any "Here's a description" prefixes
        description = response.text.strip()
        if description.lower().startswith("here's a description"):
            # Find the first period and take everything after it
            first_period = description.find('.')
            if first_period != -1:
                description = description[first_period + 1:].strip()
        
        return description
        
    except Exception as e:
        print(f"❌ Error describing image {image_path}: {e}")
        return ""

def copy_image_to_frontend(image_path: str) -> str:
    """Copy image to frontend directory and return the relative path."""
    try:
        # Create frontend directory if it doesn't exist
        frontend_images_dir = "../frontend/public/images/writing_prompts"
        os.makedirs(frontend_images_dir, exist_ok=True)
        
        # Get filename and create unique name
        original_filename = os.path.basename(image_path)
        name, ext = os.path.splitext(original_filename)
        unique_filename = f"admin_{name}_{str(uuid.uuid4())[:8]}{ext}"
        frontend_path = os.path.join(frontend_images_dir, unique_filename)
        
        # Copy image
        shutil.copy2(image_path, frontend_path)
        print(f"✅ Copied image to frontend: {unique_filename}")
        
        return f"writing_prompts/{unique_filename}"
        
    except Exception as e:
        print(f"❌ Error copying image {image_path}: {e}")
        return ""

def validate_image_file(image_path: str) -> bool:
    """Validate that the image file exists and is readable."""
    if not os.path.exists(image_path):
        print(f"❌ Image file not found: {image_path}")
        return False
    
    # Check if it's a file (not directory)
    if not os.path.isfile(image_path):
        print(f"❌ Path is not a file: {image_path}")
        return False
    
    # Check file extension
    valid_extensions = ['.jpg', '.jpeg', '.png', '.gif', '.bmp']
    file_ext = os.path.splitext(image_path)[1].lower()
    if file_ext not in valid_extensions:
        print(f"❌ Invalid file type: {file_ext}. Supported: {valid_extensions}")
        return False
    
    return True
