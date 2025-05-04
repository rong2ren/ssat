import csv
import time
from ssat.llm import call_openai_chat, extract_json_from_text

# You can customize this
NUM_QUESTIONS = 5
OUTPUT_CSV = "generated_ssat_questions.csv"

# --- System prompt (make LLM behave properly) ---
SYSTEM_PROMPT = """You are an expert SSAT Elementary Level question writer.
For every prompt, you must respond ONLY with a clean JSON object, structured exactly like this:

{
    "category": "Word Problem",
    "question": "Samantha has 48 crayons. She gives 12 crayons to her friend and buys 20 more. How many crayons does Samantha have now?",
    "options": {
        "A": "56",
        "B": "80",
        "C": "60",
        "D": "36"
    },
    "answer": "A",
    "solution": "1. 48 - 12 = 36 crayons after giving. 2. 36 + 20 = 56 crayons after buying."
}
Only return valid JSON. No explanation, no extra text outside JSON.
"""

# --- Base prompt for each question generation ---
BASE_USER_PROMPT = """Generate one SSAT Elementary Level math question following the CCSS standards for Grades 3-4.
Strictly follow the structure and difficulty similar to the example given.
Use different numbers, wording, and situations each time.
"""

def generate_single_question() -> dict:
    """Generate a single SSAT question and parse the JSON."""
    raw_response = call_openai_chat(
        system_message=SYSTEM_PROMPT,
        prompt=BASE_USER_PROMPT,
        model="gpt-3.5-turbo",
        temperature=0.4,
        max_tokens=500
    )

    if not raw_response:
        print("❌ Failed to get response.")
        return {}

    parsed = extract_json_from_text(raw_response)

    if not parsed:
        print("❌ Failed to parse JSON.")
        return {}

    return parsed

def main():
    all_questions = []

    for i in range(NUM_QUESTIONS):
        print(f"✨ Generating question {i + 1}/{NUM_QUESTIONS}...")
        question_data = generate_single_question()
        if question_data:
            all_questions.append(question_data)
        else:
            print(f"⚠️ Skipped question {i + 1} due to error.")
        time.sleep(1)  # Be polite to the API

    if not all_questions:
        print("❌ No questions generated. Exiting.")
        return

    # --- Save to CSV ---
    fieldnames = ["category", "question", "option_A", "option_B", "option_C", "option_D", "answer", "solution"]

    with open(OUTPUT_CSV, mode="w", newline='', encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()

        for q in all_questions:
            writer.writerow({
                "category": q.get("category", ""),
                "question": q.get("question", ""),
                "option_A": q.get("options", {}).get("A", ""),
                "option_B": q.get("options", {}).get("B", ""),
                "option_C": q.get("options", {}).get("C", ""),
                "option_D": q.get("options", {}).get("D", ""),
                "answer": q.get("answer", ""),
                "solution": q.get("solution", "")
            })

    print(f"✅ Successfully saved {len(all_questions)} questions to {OUTPUT_CSV}.")

if __name__ == "__main__":
    main()
