# Writing Prompt Scripts

This folder contains scripts for creating and managing writing prompts with images.

## Scripts

### `single_create_prompt.py`
Process a single image and create a writing prompt directly in the database.

**Usage:**
```bash
cd scripts
uv run python single_create_prompt.py <image_path>
```

**Example:**
```bash
uv run python single_create_prompt.py ../extracted_images/girafee.jpg
```

### `batch_create_prompts.py`
Process multiple images in a folder and create writing prompts directly in the database.

**Usage:**
```bash
cd scripts
uv run python batch_create_prompts.py --folder <folder_path>
```

**Example:**
```bash
uv run python batch_create_prompts.py --folder ../extracted_images/
```

### `upload_image_prompts.py`
Upload existing JSON files containing writing prompts to the database.

**Usage:**
```bash
cd scripts
uv run python upload_image_prompts.py
```

## Data Files

- `writing_prompts_tobe_saved.json` - Generated prompts ready for upload
- `image_based_prompts.json` - Reference data from previous runs
- `image_descriptions.json` - LLM-generated image descriptions

## Requirements

- Python 3.8+
- `uv` package manager
- Google Gemini API key in `.env` file
- Supabase database connection configured

## Architecture

These scripts use the core modules in `../core/`:
- `image_processor.py` - Image processing and LLM description
- `prompt_generator.py` - Writing prompt generation
- `database_manager.py` - Database operations
