# SSAT Question Generator

An AI-powered SSAT question generator for elementary level students. This project generates customized SSAT questions and answers using OpenAI's API.

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

This project uses Poetry for dependency management.

1. Clone this repository
2. Install Poetry if you don't have it already:
   ```
   curl -sSL https://install.python-poetry.org | python3 -
   ```
3. Install dependencies:
   ```
   poetry install
   ```
sometimes, when you installed dependency in your Poetry Environment but it still show "import could not be resolved" error is likly due to your IDE still use computer python environment.
Make sure your editor is using the correct Python interpreter (the one from Poetry's virtual environment)
- find your poetry virtual environment path: ```poetry env info --path```
- press Cmd+Shift+P (Mac) or Ctrl+Shift+P (Windows/Linux) and Search for "Python: Select Interpreter"
- Click "Enter interpreter path..."
- Paste the path from step 1, and append /bin/python (on Mac/Linux) or \Scripts\python.exe (on Windows)


4. Create a `.env` file based on `.env.example` and add your OpenAI API key
5. Activate the virtual environment:


## Usage

Generate questions using the command-line interface:

```bash
# Generate 3 easy math questions about addition
python src/main.py --type math --difficulty standard --topic addition --count 3
python src/main.py --type math --count 3

# Save the generated questions to a JSON file
python src/main.py --type verb --count 5 --output questions.json

# Generate reading comprehension questions for grade 4
python src/main.py --type reading --level elementary --count 2

poetry run python
```

### Available Options

- `--type`: "math", "reading", "verbal", "analogy", "synonym", "writing"
- `--difficulty`: "standard", "advanced"
- `--topic`: Any specific topic to focus on (optional, e.g. 'fractions', 'geometry')
- `--count`: Number of questions to generate
- `--level`: "elementary", "middle", "high"
- `--output`: File path to save the questions as JSON

## Environment

The project requires a valid OpenAI API key or similar model.

```
poetry init
poetry install
poetry shell
``` 

### Virtual Environment
```
poetry config --list
poetry env info
```


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
├── pyproject.toml
└── README.md
```