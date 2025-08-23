# SSAT Scripts

DevOps and maintenance scripts for the SSAT project. These scripts handle data management, database operations, and system maintenance tasks.

## 🚀 Quick Start

```bash
# Navigate to scripts directory
cd scripts

# Install dependencies
pip install -r requirements.txt

# Set up environment variables
cp ../backend/.env.example ../backend/.env
# Edit ../backend/.env with your actual values

# Test connection
python test_connection.py
```

## 📦 Available Scripts

| Script                | Purpose                                           | Usage                        |
| --------------------- | ------------------------------------------------- | ---------------------------- |
| `upload_data.py`      | Upload SSAT questions from JSON files to database | `python upload_data.py`      |
| `test_connection.py`  | Test database connection and show statistics      | `python test_connection.py`  |
| `extract_pdf_text.py` | Extract text from SSAT PDF files                  | `python extract_pdf_text.py` |

## 🔧 Setup

### Prerequisites
- Python 3.11+
- Access to Supabase project
- SSAT training data files

### Installation

```bash
# Navigate to scripts directory
cd scripts

# Install dependencies
pip install -r requirements.txt

# Or with virtual environment (recommended)
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt
```

### Environment Variables

Scripts use the same `.env` file as the backend. Create `../backend/.env` with:

```env
# Supabase Configuration (required)
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_KEY=your_service_role_key

# AI API Keys (at least one required)
GEMINI_API_KEY=your_gemini_key
DEEPSEEK_API_KEY=your_deepseek_key
OPENAI_API_KEY=your_openai_key
```

## 📋 Script Details

### 1. `upload_data.py`

Uploads SSAT training questions to the database for AI training.

**Features:**
- Processes JSON files with SSAT questions
- Generates embeddings for semantic search
- Validates question format and quality
- Tracks upload progress and statistics

**Usage:**
```bash
# Upload all training data
python upload_data.py

# Upload specific file
python upload_data.py --file data/questions.json

# Upload with validation only
python upload_data.py --validate-only
```

**Options:**
- `--file`: Specific file to upload
- `--validate-only`: Validate without uploading
- `--dry-run`: Show what would be uploaded
- `--verbose`: Detailed output

### 2. `test_connection.py`

Tests database connection and displays system statistics.

**Features:**
- Verifies Supabase connection
- Shows database statistics
- Displays table row counts
- Tests embedding functionality

**Usage:**
```bash
# Basic connection test
python test_connection.py

# Detailed statistics
python test_connection.py --detailed

# Test specific functionality
python test_connection.py --test-embeddings
```

**Output:**
```
✅ Database connection successful
📊 Database Statistics:
  - Users: 15
  - Questions: 1,234
  - Embeddings: 1,234
  - Generation Jobs: 45
```

### 3. `extract_pdf_text.py`

Extracts text content from SSAT PDF files for processing.

**Features:**
- OCR support for scanned PDFs
- Text cleaning and formatting
- Question extraction and parsing
- Output to JSON format

**Usage:**
```bash
# Extract from single PDF
python extract_pdf_text.py --input ssat_practice.pdf

# Extract from directory
python extract_pdf_text.py --input-dir pdfs/

# Extract with OCR
python extract_pdf_text.py --input scanned.pdf --ocr
```

**Options:**
- `--input`: Input PDF file
- `--input-dir`: Directory of PDF files
- `--output`: Output JSON file
- `--ocr`: Enable OCR for scanned PDFs
- `--clean`: Apply text cleaning

## 🔍 Usage Examples

### Database Operations

```bash
# Test database connection
python test_connection.py

# Upload training data
python upload_data.py --file data/elementary_math.json

# Extract questions from PDF
python extract_pdf_text.py --input ssat_practice.pdf --output questions.json
```

### Data Validation

```bash
# Validate data without uploading
python upload_data.py --validate-only --file data/questions.json

# Check database statistics
python test_connection.py --detailed
```

### Batch Processing

```bash
# Process multiple PDF files
for file in pdfs/*.pdf; do
    python extract_pdf_text.py --input "$file" --output "extracted/${file%.pdf}.json"
done

# Upload multiple JSON files
for file in data/*.json; do
    python upload_data.py --file "$file"
done
```

## 🐛 Troubleshooting

### Common Issues

#### 1. "SUPABASE_URL and SUPABASE_KEY must be set"
```bash
# Check if .env file exists
ls -la ../backend/.env

# Verify environment variables
cat ../backend/.env
```

#### 2. "Database connection failed"
- Verify Supabase project is active
- Check service role key has proper permissions
- Ensure network connectivity

#### 3. "Import errors"
```bash
# Reinstall dependencies
pip install -r requirements.txt --force-reinstall
```

#### 4. "PDF extraction failed"
- Install required system dependencies (Tesseract for OCR)
- Check PDF file is not corrupted
- Verify file permissions

### Debug Mode
```bash
# Enable debug logging
DEBUG=1 python upload_data.py

# Verbose output
python upload_data.py --verbose
```

## 📊 Data Formats

### Input JSON Format (for upload_data.py)

```json
{
  "questions": [
    {
      "question_type": "quantitative",
      "difficulty": "easy",
      "question": "What is 5 + 3?",
      "options": ["6", "7", "8", "9"],
      "correct_answer": "8",
      "explanation": "5 + 3 = 8",
      "topic": "addition"
    }
  ]
}
```

### Output JSON Format (from extract_pdf_text.py)

```json
{
  "extracted_questions": [
    {
      "text": "What is 5 + 3?",
      "options": ["6", "7", "8", "9"],
      "correct_answer": "C",
      "page": 1,
      "confidence": 0.95
    }
  ],
  "metadata": {
    "file": "ssat_practice.pdf",
    "pages_processed": 10,
    "questions_found": 25
  }
}
```

## 🔒 Security Considerations

- **Service Role Key**: Scripts use Supabase service role key for admin operations
- **File Permissions**: Ensure sensitive files are not world-readable
- **API Keys**: Never commit API keys to version control
- **Data Validation**: Always validate data before uploading

## 📚 Dependencies

### Required Python Packages
- `supabase` - Supabase client
- `pandas` - Data processing
- `numpy` - Numerical operations
- `requests` - HTTP requests

### Optional Dependencies
- `PyMuPDF` - PDF processing
- `pytesseract` - OCR functionality
- `Pillow` - Image processing

## 🔄 Maintenance

### Regular Tasks
- **Weekly**: Run `test_connection.py` to verify system health
- **Monthly**: Update training data with `upload_data.py`
- **As needed**: Extract new PDF content with `extract_pdf_text.py`

### Data Backup
```bash
# Export database statistics
python test_connection.py --detailed > backup_stats_$(date +%Y%m%d).txt

# Backup extracted data
cp extracted/*.json backups/
```

## 📚 Additional Resources

- [Backend README](../backend/README.md)
- [Frontend README](../frontend/README.md)
- [Supabase Documentation](https://supabase.com/docs)
- [Python Documentation](https://docs.python.org/)

---

**Note**: These scripts require proper environment setup and database access. Always test in a development environment before running in production.