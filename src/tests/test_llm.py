# main.py

from ssat.llm import call_openai_chat, extract_json_from_text
from loguru import logger

def simple_test():
    system_message = "You are a helpful assistant that returns short answers."
    prompt = "What is 2 + 3?"

    response = call_openai_chat(
        system_message=system_message,
        prompt=prompt,
        model="gpt-3.5-turbo",
        temperature=0.2,
        max_tokens=50
    )

    if response:
        logger.info("✅ Response received:")
        logger.info(response)
    else:
        logger.error("❌ No response (error or retries failed)")


def llm_test():
    system_message = "You are a helpful assistant that returns information in JSON format."
    prompt = "Return a JSON object with fields 'answer' and 'explanation' for the question: What is 45 / 9?"

    response = call_openai_chat(
        system_message=system_message,
        prompt=prompt,
        model="gpt-3.5-turbo",
        temperature=0.2,
        max_tokens=100
    )

    if not response:
        logger.error("❌ No response (error or retries failed)")
        return

    logger.info("✅ Raw response received:")
    logger.info(response)
    
    # Try to extract JSON
    json_data = extract_json_from_text(response)
    
    if json_data:
        logger.info("✅ Extracted JSON:")
        logger.info(f"Answer: {json_data.get('answer')}")
        logger.info(f"Explanation: {json_data.get('explanation')}")
    else:
        logger.error("❌ Failed to extract JSON from response")


if __name__ == "__main__":
    logger.info("=== LLM Test ===")
    llm_test()
