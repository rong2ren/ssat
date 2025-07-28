# Use Python 3.11 slim image
FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Install system dependencies first (rarely changes)
RUN apt-get update && apt-get install -y \
    gcc \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy only dependency files first (for better caching)
COPY pyproject.toml uv.lock ./

# Install dependencies with better caching
RUN pip install --upgrade pip && \
    pip install --no-cache-dir fastapi uvicorn python-multipart pydantic pydantic-settings email-validator PyJWT supabase openai google-generativeai sentence-transformers python-dotenv loguru

# Copy application code last (changes frequently)
COPY . .

# Expose port
EXPOSE 8080

# Set environment variable for port
ENV PORT=8080

# Run the application directly
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8080", "--timeout-keep-alive", "75"] 