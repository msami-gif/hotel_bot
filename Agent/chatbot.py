# Agent/chatbot.py
import re
import json
import logging
from langchain_ollama import OllamaLLM
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.chat_history import InMemoryChatMessageHistory
from langchain.chains import LLMChain
from fastmcp import Client

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

# ========== LLM & conversation setup ==========
MODEL_NAME = "llama3"   # adjust if your local model name differs
model = OllamaLLM(model=MODEL_NAME)

# System prompt (single stable instruction). Keep short and high-level so the assistant is free to converse.
system_text = (
    "You are a friendly hotel-booking assistant. "
    "Engage naturally with the user to gather booking details, suggest hotels, and help complete bookings. "
    "Ask clarifying questions if necessary."
)

conversation_prompt = ChatPromptTemplate.from_messages([
    ("system", system_text),
    MessagesPlaceholder(variable_name="history"),
    ("human", "{input}")
])

chat_history = InMemoryChatMessageHistory()
conversation_chain = LLMChain(llm=model, prompt=conversation_prompt)


# ========== Helpers ==========
def llm_respond(user_input: str) -> str:
    """
    Generate a natural assistant reply using the conversation history.
    This is the text shown to the user.
    """
    logger.info("LLM generating a conversational reply.")
    chat_history.add_user_message(user_input)
    # run the chain - giving it the current history so LLM can reference past messages
    response = conversation_chain.run(history=chat_history.messages, input=user_input)
    chat_history.add_ai_message(response)
    logger.info("LLM reply generated.")
    return response


def _find_json_block(text: str) -> str | None:
    """
    Returns the first {...} block found in text, or None.
    """
    match = re.search(r"\{[\s\S]*?\}", text)
    return match.group(0) if match else None


def extract_booking_info_with_llm(text: str) -> dict:
    """
    Hidden extractor: ask the LLM (via a focused extractor prompt) to return a JSON
    with keys: destination, check_in, check_out, guests.
    Returns a dict with those keys (value or None).
    """
    extractor_template = """
You are a JSON extractor. From the following user message, extract:
- destination (city name)
- check_in (ISO date YYYY-MM-DD if available)
- check_out (ISO date YYYY-MM-DD if available)
- guests (integer number of guests if available)

Return only a JSON object with these keys. Use null for unknown values.

Message:
{input}
"""
    prompt = ChatPromptTemplate.from_template(extractor_template)
    chain = LLMChain(llm=model, prompt=prompt)
    raw = chain.run(input=text).strip()

    # Try to find a JSON block inside the LLM output
    json_block = _find_json_block(raw)
    if not json_block:
        # If the LLM returned raw JSON (no surrounding text) try to parse raw itself
        json_block = raw if raw.startswith("{") else None

    if not json_block:
        logger.warning("No JSON block found in extractor output. Returning empty fields.")
        return {"destination": None, "check_in": None, "check_out": None, "guests": None}

    try:
        parsed = json.loads(json_block)
        # Normalize keys and ensure expected shape
        return {
            "destination": parsed.get("destination"),
            "check_in": parsed.get("check_in"),
            "check_out": parsed.get("check_out"),
            "guests": parsed.get("guests")
        }
    except Exception as e:
        logger.error("Failed to parse extracted JSON: %s\nRaw: %s", e, json_block)
        return {"destination": None, "check_in": None, "check_out": None, "guests": None}


def format_hotels_for_prompt(hotels: list) -> str:
    """
    Turn Amadeus-style hotel objects into a short text list the LLM can present.
    Tries to be concise and readable.
    """
    hotel_lines  = []
    logger.info(f"hotels, {json.dumps(hotels, indent=2)}")

    if isinstance(hotels, str):
        hotels = json.loads(hotels)
    for idx, hotel_offer in enumerate(hotels, start=1):
        print("DEBUG: Type of hotel_offer:", type(hotel_offer))
        hotel_data = hotel_offer.get("hotel", {})
        name = hotel_data.get("name", "Unknown Hotel")
        address = hotel_data.get("address", {}).get("lines", ["No address"])[0]

        # Ensure offers_list always exists
        offers_list = hotel_offer.get("offers", [])
        logger.info(f"Offers for hotel {name}: {offers_list}")
        room_details = []
        for room_offer in offers_list:
            price = room_offer.get("price", {}).get("total", "N/A")
            currency = room_offer.get("price", {}).get("currency", "")
            room_details.append(f"{price} {currency}")

        hotel_lines.append(f"{idx}. {name} - {address} | Offers: {', '.join(room_details) if room_details else 'No offers available'}")
    logger.info(f"Formatted hotel lines: {hotel_lines}")
    return "\n".join(hotel_lines)


def inject_hotels_into_history(hotels: list):
    """
    Add an assistant message into conversation history that lists hotels.
    This allows subsequent LLM replies to reference the list naturally.
    """
    if not hotels:
        chat_history.add_ai_message("I couldn't find any hotels for those dates.")
        return

    hotel_text = format_hotels_for_prompt(hotels)
    message = "Here are some hotel options I found:\n\n" + hotel_text + "\n\nPlease tell me which one you'd like (give the number or name)."
    chat_history.add_ai_message(message)


# ========== Public process function ==========
async def process_user_message(user_input: str, state: dict, mcp_client: Client) -> tuple[str, dict]:
    """
    Orchestrates a single turn:
    - Ask LLM for the visible reply (free-form).
    - Run the hidden extractor on the user's message and update state.
    - If we now have all required booking info and haven't searched yet -> call hotel_service and inject hotels.
    - Returns (assistant_text_to_show_user, updated_state)
    """
    # 1) Generate visible LLM reply right away (keeps conversation natural)
    assistant_text = llm_respond(user_input)

    # 2) Background: extract booking info from user's raw message
    extracted = extract_booking_info_with_llm(user_input)
    logger.info("Extracted booking info from user: %s", extracted)

    # Update backend state with anything new
    updated = False
    for key in ("destination", "check_in", "check_out", "guests"):
        if extracted.get(key) and not state.get(key):
            state[key] = extracted[key]
            updated = True

    # 3) If booking info complete and we haven't searched yet -> search & inject hotels
    required = ("destination", "check_in", "check_out", "guests")
    if all(state.get(k) for k in required) and not state.get("hotels"):
        logger.info("All required fields present. Searching hotels via Amadeus.")
        try:
            result = await mcp_client.call_tool(
                "search_hotel",
                arguments={
                    "city_code": state.get("destination"),  # if your city->code step is separate, ensure state stores code
                    "check_in": state.get("check_in"),
                    "check_out": state.get("check_out"),
                    "adults": state.get("guests")
                }
                )
            hotels = result.content[0].text if result.content else []
        except Exception as e:
            logger.exception(f"Hotel search via the MCP server failed: {e}")
            hotels = []
        
        state["hotels"] = hotels
        state["awaiting_selection"] = True

        inject_hotels_into_history(hotels)
        
        listing_text = "I found some hotels for your trip:\n\n" + format_hotels_for_prompt(hotels) + "\n\nPlease tell me which one you'd like (number or name)."
        assistant_text = listing_text
    return assistant_text, state
