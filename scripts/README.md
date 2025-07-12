# SSAT Scripts

DevOps and maintenance scripts for the SSAT project.

## Setup

```bash
# Install dependencies
pip install -r requirements.txt

# Or with virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt
```

## Available Scripts

- `upload_data.py` - Upload SSAT questions from JSON files to database
- `test_connection.py` - Test database connection and show statistics  
- `extract_pdf_text.py` - Extract text from SSAT PDF files

## Usage

```bash
# Test database connection
python test_connection.py

# Upload training data  
python upload_data.py

# Extract text from PDFs
python extract_pdf_text.py
```

## Environment Variables

Scripts use the same `.env` file as the backend:

```env
SUPABASE_URL=your_supabase_url
SUPABASE_KEY=your_supabase_key
```