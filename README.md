# SSAT Question Generator

An AI-powered SSAT question generator for elementary level students. This project generates customized SSAT questions and answers using AI. Explore tools like VEGA AI (PDF/image-to-question conversion) and Khanmigo (standards-aligned assessments) 

## Features

- Generate SSAT questions for elementary level (grades 3-4)
- Support for multiple question types:
  - Multiple choice
  - Reading comprehension
  - Math
  - Verbal (vocabulary and analogies)
- Adjustable difficulty levels
- Detailed explanations for all answers
- Command-line interface

## Setup

This project uses UV for dependency management (fast, modern Python package manager).

1. Clone this repository
2. Install UV if you don't have it already:
   ```bash
   curl -LsSf https://astral.sh/uv/install.sh | sh
   ```
   Then add to your PATH:
   ```bash
   source $HOME/.local/bin/env
   ```
3. Install dependencies:
   ```bash
   uv sync
   ```

**IDE Setup**: If your IDE shows "import could not be resolved" errors, make sure it's using the correct Python interpreter:
- Find your UV virtual environment path: `uv env --path`
- In your IDE, search for "Python: Select Interpreter"
- Click "Enter interpreter path..."
- Paste the path from step 1, and append `/bin/python` (on Mac/Linux) or `\Scripts\python.exe` (on Windows)

4. Create a `.env` file and configure at least one LLM provider:
   ```bash
   # Required database settings
   SUPABASE_URL=your_supabase_url_here
   SUPABASE_KEY=your_supabase_key_here
   
   # Configure at least one LLM provider
   
   # Google Gemini (FREE tier: 15 requests/min, 1500/day) - Recommended!
   GEMINI_API_KEY=your_gemini_api_key_here
   
   # DeepSeek (Affordable with competitive pricing)
   DEEPSEEK_API_KEY=your_deepseek_api_key_here
   
   # OpenAI (PAID service, excellent quality)
   OPENAI_API_KEY=your_openai_api_key_here
   ```

5. Get API keys:
   - **Gemini**: https://ai.google.dev/ (FREE - Recommended for testing!)
   - **DeepSeek**: https://platform.deepseek.com/ (Very affordable pricing)
   - **OpenAI**: https://platform.openai.com/api-keys (paid)

## Usage

Generate questions using the command-line interface:

```bash
# Generate 3 math questions (uses first available provider)
uv run python src/main.py --type math --count 3

# Generate math questions with a specific provider
uv run python src/main.py --type math --count 3 --provider gemini
uv run python src/main.py --type math --count 3 --provider deepseek
uv run python src/main.py --type math --count 3 --provider openai

# Generate with specific topic and difficulty
uv run python src/main.py --type math --difficulty standard --topic addition --count 3 --provider gemini

# Save questions to JSON file
uv run python src/main.py --type verbal --count 5 --output questions.json --provider deepseek

# Generate reading comprehension questions
uv run python src/main.py --type reading --level elementary --count 2 --provider gemini
```

### Available Options

- `--type`: "math", "reading", "verbal", "analogy", "synonym", "writing"
- `--difficulty`: "standard", "advanced"
- `--topic`: Any specific topic to focus on (optional, e.g. 'fractions', 'geometry')
- `--count`: Number of questions to generate
- `--level`: "elementary", "middle", "high"
- `--provider`: LLM provider to use ("openai", "gemini", "deepseek")
- `--output`: File path to save the questions as JSON

### LLM Provider Comparison

| Provider | Cost | Speed | Quality | Free Tier |
|----------|------|--------|---------|-----------|
| **Gemini** | FREE | Fast | High | 15 req/min, 1500/day |
| **DeepSeek** | Very Cheap | Fast | High | Pay-per-use, very affordable |
| **OpenAI** | Paid | Fast | Excellent | No |

**Recommendations**: 
- **Free Testing**: Use **Gemini** (completely free tier)
- **Production**: Use **DeepSeek** (excellent value for money)
- **Premium**: Use **OpenAI** (highest quality, most expensive)

### Why UV?

This project uses **UV** instead of Poetry for faster, more reliable dependency management:
- **10-100x faster** dependency resolution
- **5-20x faster** package installation
- **Better compatibility** with existing Python tooling
- **Modern architecture** written in Rust
- **Active development** and community support

## Folder Structure
```
ssat/
├── src/
│   ├── ssat/
│   │   ├── config.py              # config
│   │   ├── models.py              # Question models
│   │   ├── generator.py           # AI question generation logic
│   │   ├── validate.py            # question validation - quality control
│   │   ├── api/                   # web endpoint (future)
│   │   │   ├── __init__.py
│   │   │   ├── app.py             # FastAPI application setup
│   │   │   ├── routes.py          # API endpoints
│   └── main.py                    # CLI entry point
│   └── server.py                  # Web server entry point (future)
├── examples/                      # Real-world questions examples
├── tests/                         # Test
├── pyproject.toml                 # Project configuration
├── uv.lock                        # UV dependency lock file
└── README.md
```