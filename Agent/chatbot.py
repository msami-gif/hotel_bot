# llm_extraction.py
import re
from langchain_ollama import OllamaLLM
from langchain_core.prompts import ChatPromptTemplate
import json

# Load model
model = OllamaLLM(model="llama3")

# Load prompt
with open("Template/template.txt", "r", encoding="utf-8") as f:
    template = f.read()

prompt = ChatPromptTemplate.from_template(template)
chain = prompt | model

def extract_booking_info(user_input):
    response = chain.invoke({"question": user_input})
    raw = response.content if hasattr(response, 'content') else str(response)

    match = re.search(r"\{[\s\S]*?\}", raw)
    if not match:
        print("❌ No JSON block found in response.")
        print("Raw response:", raw)
        return None

    json_str = match.group(0)

    try:
        data = json.loads(json_str)
        return data
    except Exception as e:
        print(f"Error parsing model response: {e}")
        print("Raw response:", response)
        return None
