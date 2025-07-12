#!/usr/bin/env python3
"""Enhanced PDF extraction with intelligent OCR for image description."""

import pdfplumber
import os
import re
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple
from loguru import logger

# OCR imports
try:
    from pdf2image import convert_from_path
    import pytesseract
    OCR_AVAILABLE = True
except ImportError as e:
    print(f"OCR dependencies not available: {e}")
    OCR_AVAILABLE = False

# Loguru is configured automatically

def clean_text(text: str) -> str:
    """Clean extracted text for better processing."""
    if not text:
        return ""
    
    # Remove excessive whitespace
    text = re.sub(r'\s+', ' ', text)
    
    # Remove page headers/footers (common patterns)
    text = re.sub(r'Page \d+ of \d+', '', text)
    text = re.sub(r'\d+', '', text)  # Remove standalone page numbers
    
    # Clean up common OCR artifacts
    text = re.sub(r'[^\w\s\.\,\;\:\!\?\(\)\[\]\-\+\=\*\/\@\#\$\%\&]', '', text)
    
    # Remove multiple consecutive periods
    text = re.sub(r'\.{2,}', '.', text)
    
    # Normalize line breaks
    text = text.replace('\n\n', '\n').replace('\n\n\n', '\n')
    
    return text.strip()

def analyze_image_with_ocr(image) -> str:
    """Analyze image content using multiple OCR approaches."""
    try:
        # Try different OCR configurations for better results
        configs = [
            '--psm 6',  # Uniform block of text
            '--psm 3',  # Fully automatic page segmentation
            '--psm 11', # Sparse text with OSD
            '--psm 13'  # Raw line with no specific orientation
        ]
        
        all_text = []
        for config in configs:
            try:
                text = pytesseract.image_to_string(image, config=config)
                if text.strip():
                    all_text.append(text.strip())
            except:
                continue
        
        # Combine all OCR results
        combined_text = ' '.join(all_text)
        
        # Analyze the extracted text for content clues
        description = []
        
        # Look for common objects/actions in SSAT prompts
        objects = ['ball', 'book', 'tree', 'house', 'car', 'dog', 'cat', 'bird', 'flower', 'chair', 'table', 'door', 'window']
        actions = ['play', 'read', 'run', 'walk', 'sit', 'stand', 'eat', 'drink', 'sleep', 'jump', 'climb']
        people = ['child', 'boy', 'girl', 'man', 'woman', 'family', 'teacher', 'student']
        places = ['park', 'school', 'home', 'garden', 'street', 'room', 'kitchen', 'bedroom']
        
        text_lower = combined_text.lower()
        
        # Find detected objects
        found_objects = [obj for obj in objects if obj in text_lower]
        if found_objects:
            description.append(f"contains: {', '.join(found_objects[:3])}")
        
        # Find detected actions
        found_actions = [action for action in actions if action in text_lower]
        if found_actions:
            description.append(f"shows: {', '.join(found_actions[:2])}")
        
        # Find detected people
        found_people = [person for person in people if person in text_lower]
        if found_people:
            description.append(f"features: {', '.join(found_people[:2])}")
        
        # Find detected places
        found_places = [place for place in places if place in text_lower]
        if found_places:
            description.append(f"set in: {', '.join(found_places[:2])}")
        
        # Analyze text patterns
        if len(combined_text) > 100:
            description.append("detailed scene")
        elif len(combined_text) > 50:
            description.append("moderate detail")
        else:
            description.append("simple scene")
        
        # Check for numbers (might indicate age, time, etc.)
        numbers = re.findall(r'\d+', combined_text)
        if numbers:
            description.append(f"includes numbers: {', '.join(numbers[:3])}")
        
        if description:
            return f"Image appears to be a {', '.join(description)}. "
        else:
            return "Image content could not be clearly identified. "
        
    except Exception as e:
        logger.warning(f"Image analysis failed: {e}")
        return "Image content could not be analyzed. "

def extract_text_with_pdfplumber(pdf_path: str) -> Tuple[Optional[str], int]:
    """Extract text using pdfplumber and return text + pages with text count."""
    try:
        with pdfplumber.open(pdf_path) as pdf:
            texts = []
            pages_with_text = 0
            
            for page in pdf.pages:
                text = page.extract_text()
                if text and len(text.strip()) > 50:  # Only count pages with substantial text
                    texts.append(text)
                    pages_with_text += 1
            
            return "\n\n".join(texts) if texts else None, pages_with_text
    except Exception as e:
        logger.warning(f"pdfplumber extraction failed: {e}")
        return None, 0

def extract_text_with_ocr(pdf_path: str) -> Optional[str]:
    """Extract text using OCR (for scanned PDFs)."""
    if not OCR_AVAILABLE:
        logger.error("OCR dependencies not available")
        return None
    
    try:
        # Convert PDF to images
        logger.info(f"Converting PDF to images: {os.path.basename(pdf_path)}")
        images = convert_from_path(pdf_path, dpi=300)  # Higher DPI for better OCR
        
        texts = []
        for i, image in enumerate(images):
            logger.info(f"Processing page {i+1}/{len(images)} with OCR")
            
            # Extract text using Tesseract
            text = pytesseract.image_to_string(image, config='--psm 6')
            if text.strip():
                texts.append(text)
        
        return "\n\n".join(texts) if texts else None
        
    except Exception as e:
        logger.error(f"OCR extraction failed: {e}")
        return None

def extract_writing_prompts_with_images(pdf_path: str) -> str:
    """Extract writing prompts and analyze images using OCR."""
    if not OCR_AVAILABLE:
        logger.error("OCR dependencies not available for image analysis")
        return ""
    
    try:
        # Convert PDF to images
        logger.info(f"Converting writing prompts PDF to images: {os.path.basename(pdf_path)}")
        images = convert_from_path(pdf_path, dpi=300)
        
        prompts = []
        prompt_number = 1
        
        for i, image in enumerate(images):
            logger.info(f"Analyzing page {i+1}/{len(images)} for writing prompts")
            
            # Extract text from the page
            text = pytesseract.image_to_string(image, config='--psm 6')
            
            # Look for writing prompt patterns
            if "Practice Prompt" in text or "Look at the picture" in text:
                # Analyze the image content using OCR
                image_description = analyze_image_with_ocr(image)
                
                # Create enhanced prompt
                enhanced_prompt = f"Writing Prompt #{prompt_number}:\n"
                enhanced_prompt += f"Image Description: {image_description}\n"
                enhanced_prompt += f"Instructions: Look at the picture and make up a story about what happened. "
                enhanced_prompt += f"Make sure your story has a beginning, a middle, and an end.\n"
                enhanced_prompt += f"Original Text: {text[:200]}...\n"
                enhanced_prompt += "-" * 80 + "\n"
                
                prompts.append(enhanced_prompt)
                prompt_number += 1
        
        return "\n".join(prompts) if prompts else ""
        
    except Exception as e:
        logger.error(f"Writing prompts extraction failed: {e}")
        return ""

def extract_pdf_text(pdf_path: str) -> Dict[str, Any]:
    """Extract text from PDF using enhanced methods."""
    filename = os.path.basename(pdf_path)
    file_size_mb = round(os.path.getsize(pdf_path) / (1024 * 1024), 2)
    
    # Special handling for writing prompts
    if "writing" in filename.lower() or "prompt" in filename.lower():
        logger.info(f"Detected writing prompts file: {filename}")
        text_content = extract_writing_prompts_with_images(pdf_path)
        extraction_method = "writing_prompts_with_images"
    else:
        # Try text extraction first
        text_content, pages_with_text = extract_text_with_pdfplumber(pdf_path)
        extraction_method = "text"
        
        # Smart OCR detection: if very little text found relative to PDF size
        if text_content and len(text_content) < 1000 and file_size_mb > 1.0:
            logger.info(f"Little text found in large PDF, trying OCR: {filename}")
            ocr_content = extract_text_with_ocr(pdf_path)
            if ocr_content and len(ocr_content) > len(text_content) * 2:
                text_content = ocr_content
                extraction_method = "ocr"
        
        # If no text found, try OCR
        elif not text_content and OCR_AVAILABLE:
            logger.info(f"No text found with pdfplumber, trying OCR for: {filename}")
            text_content = extract_text_with_ocr(pdf_path)
            extraction_method = "ocr"
    
    # Clean the extracted text
    if text_content:
        cleaned_text = clean_text(text_content)
        total_characters = len(cleaned_text)
    else:
        cleaned_text = ""
        total_characters = 0
        extraction_method = "failed"
    
    return {
        "filename": filename,
        "file_size_mb": file_size_mb,
        "extraction_method": extraction_method,
        "total_characters": total_characters,
        "full_text": cleaned_text
    }

def save_text_to_file(text_data: Dict[str, Any], output_dir: str = "extracted_texts"):
    """Save extracted text to files."""
    # Create output directory
    os.makedirs(output_dir, exist_ok=True)
    
    filename = text_data["filename"].replace(".pdf", "")
    
    # Save full text only
    full_text_file = os.path.join(output_dir, f"{filename}.txt")
    with open(full_text_file, 'w', encoding='utf-8') as f:
        f.write(text_data["full_text"])
    
    return full_text_file

def main():
    """Extract text from all PDFs in examples folder using enhanced methods."""
    if not OCR_AVAILABLE:
        print("ERROR: OCR dependencies not available!")
        print("Install with: pip install pdf2image pytesseract")
        print("Also install Tesseract OCR:")
        print("  macOS: brew install tesseract")
        print("  Ubuntu: sudo apt-get install tesseract-ocr")
        print("  Windows: Download from https://github.com/UB-Mannheim/tesseract/wiki")
        return
    
    examples_dir = Path("examples")
    pdf_files = list(examples_dir.glob("*.pdf"))
    
    print(f"Found {len(pdf_files)} PDF files to extract text from...\n")
    
    all_extractions = []
    
    for pdf_file in pdf_files:
        print(f"Extracting text from: {pdf_file.name}")
        
        text_data = extract_pdf_text(str(pdf_file))
        all_extractions.append(text_data)
        
        # Save individual file
        txt_file = save_text_to_file(text_data)
        
        print(f"  Method: {text_data['extraction_method']}")
        print(f"  Characters: {text_data['total_characters']:,}")
        print(f"  Size: {text_data['file_size_mb']}MB")
        print(f"  Saved to: {txt_file}")
        print()
    
    # Print summary
    print("=== EXTRACTION SUMMARY ===")
    successful = [e for e in all_extractions if e["total_characters"] > 0]
    failed = [e for e in all_extractions if e["total_characters"] == 0]
    
    print(f"Successfully extracted: {len(successful)} files")
    print(f"Failed: {len(failed)} files")
    
    if successful:
        total_chars = sum(e["total_characters"] for e in successful)
        text_method = len([e for e in successful if e["extraction_method"] == "text"])
        ocr_method = len([e for e in successful if e["extraction_method"] == "ocr"])
        writing_method = len([e for e in successful if e["extraction_method"] == "writing_prompts_with_images"])
        
        print(f"Total characters extracted: {total_chars:,}")
        print(f"Text-based extractions: {text_method}")
        print(f"OCR-based extractions: {ocr_method}")
        print(f"Writing prompts with images: {writing_method}")
    
    if failed:
        print(f"\nFailed files:")
        for f in failed:
            print(f"  - {f['filename']}")
    
    print(f"\nAll extractions saved to: extracted_texts/")

if __name__ == "__main__":
    main() 