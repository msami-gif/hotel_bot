# llm_extraction.py
import re
import os
import difflib
import subprocess
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

TEMPLATE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "Template"))

def load_template(filename):
    path = os.path.join("Template", filename)
    with open(path, "r", encoding="utf-8") as f:
        return f.read()

def invoke_template(template_name: str, variables: dict):
    template = load_template(template_name)
    prompt = ChatPromptTemplate.from_template(template)
    chain = prompt | model
    response = chain.invoke(variables)
    return response.content if hasattr(response, 'content') else str(response)

def format_hotels_for_prompt(hotels):
    lines = []
    for i, hotel in enumerate(hotels[:10]):
        h = hotel.get("hotel", {})
        o = hotel.get("offers", [{}])[0]
        name = h.get('name', 'Unnamed Hotel')
        address = h.get('address', {}).get('lines', ['Address not available'])[0]
        price = o.get('price', {}).get('total', 'N/A')
        currency = o.get('price', {}).get('currency', '')
        availability = "Available" if hotel.get('available', True) else "Not available"
        cancellations = o.get('policies', {}).get('cancellations', [])
        if cancellations and 'description' in cancellations[0]:
            policy = cancellations[0]['description'].get('text', 'No policy')
        else:
            policy = 'No cancellation policy available'

        lines.append(f"{i+1}. {name} — {address}, {price} {currency}, {availability}, Policy: {policy}")

    return "\n".join(lines)

def normalize_name(name: str) -> str:
        if not name:
            return ""
        return name.lower().strip().replace(".", "").replace(",", "")

def chat_completion(prompt: str, model: str = "llama3") -> str:
    """
    Send a fresh prompt to a local LLaMA 3 instance (via Ollama) and return the output.
    """
    # Run Ollama command
    result = subprocess.run(
        ["ollama", "run", model, prompt],
        capture_output=True,
        text=True
    )

    return result.stdout.strip()

def extract_booking_info(user_input):
    response = chain.invoke({
        "question": user_input
    })
    raw = invoke_template("template.txt", {"question": user_input})
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
    
def hotel_booking_response(state, hotel_list):
    # // PROMPT: I would like to book a hotel in Paris from the 15th to the 20th of September 2025 for two adults
    with open("Template/hotel_options.txt", "r", encoding="utf-8") as f:
        booking_template = f.read()

    prompt = ChatPromptTemplate.from_template(booking_template)
    chain = prompt | model  # using your OllamaLLM model

    hotel_text = format_hotels_for_prompt(hotel_list).strip()
    print("Formatted hotel list for prompt:" + hotel_text)
    
    response = chain.invoke({
        "destination": state["destination"],
        "check_in_date": state["check_in_date"],
        "check_out_date": state["check_out_date"],
        "adults": state["adults"],
        "hotel_list": hotel_text
    })

    print("Generated LLM prompt for hotel selection:")
    print(hotel_list)
    print("Response from LLM:")
    print(response)
    return response.content if hasattr(response, "content") else str(response)

def extract_selected_hotel_name(user_input: str, hotel_list: list):
    # Use LLM to extract name string from user input 
    # // PROMPT: I would like to book a room at The Ritz Hotel
    if not hotel_list:
        raise ValueError("❌ Hotel list is empty. Cannot match selection.")

    response = invoke_template(
        "extract_selected_hotel.txt",
        {"user_input": user_input, "hotel_list": hotel_list}
    )

    # Send the user prompt to the LLM and get the response
    result = chat_completion(response)

    extracted_name = result.strip().split("\n")[0].strip()
    normalized_extracted = normalize_name(extracted_name)
    print("🔎 LLM Extracted Hotel Name:", extracted_name)

    # Step 2: Try to find a close match among the normalized hotel names
    hotel_names = [normalize_name(hotel.get("hotel", {}).get("name")) for hotel in hotel_list]
    close_matches = difflib.get_close_matches(normalized_extracted, hotel_names, n=1, cutoff=0.5)

    print("🔎 Extracted hotel name from LLM:", extracted_name)
    print("🧾 Normalized user input:", normalized_extracted)
    print("🏨 Available hotels:", [normalize_name(hotel.get("hotel", {}).get("name")) for hotel in hotel_list])

    if close_matches:
        for hotel in hotel_list:
            if normalize_name(hotel.get("hotel", {}).get("name")) == close_matches[0]:
                return hotel

    # Step 3: Raise an error if nothing matched
    raise ValueError("Hotel was identified but not found in available options.")

# === Extract Personal Info (name, email, phone) ===
def extract_personal_info(user_input: str):
    raw = invoke_template("extract_personal_info.txt", {"user_input": user_input})
    match = re.search(r"\{[\s\S]*?\}", raw)
    if not match:
        print("❌ No JSON found in personal info response.")
        return None
    try:
        return json.loads(match.group(0))
    except Exception as e:
        print(f"❌ JSON parse error: {e}")
        return None