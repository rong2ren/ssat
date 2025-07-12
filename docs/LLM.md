# Few shot Learning
Fundamentally involves adding examples to the prompt
Start with 2-3 high-quality examples per question type (max 5)
- Explicitly show distractor patterns
- Include Bloom's taxonomy in examples
- 

# Start with RAG
Build a knowledge base of validated questions
Implement semantic search for example retrieval

Costs: ~$100/month (FAISS + embeddings)

# Fine-Tuning
When you have >1k high-quality questions, progress to fine-tuning.
Use OpenAI's fine-tuning for GPT-3.5 (~$500 initial cost)

Maintain RAG for dynamic updates


# Long term
RAG for example retrieval + fine-tuned model for generation


# PDF
## PDF Extraction & Cleaning
Tools Needed:
- Free PDF parser: PyMuPDF
- OCR (if scanned PDFs): Tesseract
- Data cleaning: Python + RegEx

## Question Classification & Tagging
Zero-shot classification: transformers
Embedding model: all-MiniLM-L6-v2