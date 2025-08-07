from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from Agent.chatbot import extract_booking_info
from Agent.chatbot import hotel_booking_response
from Agent.chatbot import extract_selected_hotel_name
from Agent.chatbot import extract_personal_info
from hotel_service import AmadeusHotelService
from pydantic import BaseModel
import re
import difflib

# Initialize FastAPI app
app = FastAPI()

# Enable CORS for frontend development
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],  # Adjust as needed
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Instantiate the Amadeus service
hotel_service = AmadeusHotelService.AmadeusHotelService()

# In-memory state per session (simplified for now)
state = {
    "destination": None,
    "check_in_date": None,
    "check_out_date": None,
    "adults": None,
    "hotels": None,                    # List of hotel options retrieved
    "awaiting_selection": False,       # True after hotels are shown, waiting for user to choose one
    "selected_hotel_name": None,           # Name of hotel selected by the user
    "selected_hotel_id": None,             # ID of hotel selected by the user
    "awaiting_booking_details": False, # True after hotel is selected, waiting for user details
    "booking_details": None  
}

# Request model
class BookingRequest(BaseModel):
    message: str

# Utilities
def is_booking_complete(state):
    required_fields = ["destination", "check_in_date", "check_out_date", "adults"]
    return all(state.get(k) for k in required_fields)
    # return all(state.values())

def update_state(extracted_data):
    for key in state:
        if extracted_data.get(key):
            state[key] = extracted_data[key]

def ask_for_missing_info():
    required_fields = ["destination", "check_in_date", "check_out_date", "adults"]
    missing = [k.replace('_', ' ') for k in required_fields if not state.get(k)]
    return f"Please provide: {', '.join(missing)}."

def city_name_to_code(name):
    mapping = {
        "cape town": "CPT",
        "johannesburg": "JNB",
        "durban": "DUR"
    }
    return mapping.get(name.lower(), name.upper())

def search_and_display_results():
    print("Entering search and display results function")
    hotels = hotel_service.search_hotels_by_city(
        city_code=city_name_to_code(state["destination"]),
        check_in_date=state["check_in_date"],
        check_out_date=state["check_out_date"],
        adults=state["adults"]
    )
    print(f"Getting hotels method success")

    if not hotels:
        return "Sorry, no hotels found."
    
    state["hotels"] = hotels
    state["awaiting_selection"] = True

    print("formatting hotels for prompt")
    reply = "Here are some hotel options:\n\n"
    for hotel in hotels[:10]:
        h = hotel.get("hotel", {})
        o = hotel.get("offers", [{}])[0]
        name = h.get('name', 'Unnamed Hotel')
        address = h.get('address', {}).get('lines', ['Address not available'])[0]
        price = o.get('price', {}).get('total', 'N/A')
        currency = o.get('price', {}).get('currency', '')
        availability = "Available" if hotel.get('available', True) else "Not available"
        cancellations = o.get('policies', {}).get('cancellations', [])
        if cancellations and 'description' in cancellations[0]:
            policies = cancellations[0]['description'].get('text', 'No cancellation policy available')
        else:
            policies = 'No cancellation policy available'
        reply += f"Hotel: {name}, Address: {address}\nPrice: {price} {currency}\nAvailability: {availability}\nPolicy: {policies}\n\n"
    # return reply
    return hotel_booking_response(state, hotels)

# Endpoint for frontend to call
@app.post("/request_hotel")
async def book_hotel(req: BookingRequest):
    user_input = req.message
    extracted = extract_booking_info(user_input)

    if extracted:
        update_state(extracted)

    if is_booking_complete(state):
        summary = (f"Thanks! You're booking for {state['adults']} adult(s) in {state['destination']} "
                   f"from {state['check_in_date']} to {state['check_out_date']}.")
        results = search_and_display_results()
        
        return {"summary": summary, "results": results}
    else:
        return {"summary": ask_for_missing_info(), "results": None}
    

def normalize_name(s: str) -> str:
    """Lowercase + remove non-alphanumerics for stable comparisons."""
    if not s:
        return ""
    return re.sub(r"[^a-z0-9]+", "", s.lower().strip()) 
   
# 2. Handle hotel selection from user input
@app.post("/select_hotel")
async def select_hotel(req: BookingRequest):
    # Guard: are we expecting a selection right now?
    if not state.get("awaiting_selection") or not state.get("hotels"):
        return {"error": "Not currently awaiting hotel selection."}

    user_input = req.message

    # 1) Call your extractor (it may return a str or dict or None)
    try:
        raw_result = extract_selected_hotel_name(user_input, state["hotels"])
    except Exception as e:
        print("❌ Error during extraction:", e)
        return {"error": "Failed to interpret selection. Please type the hotel name exactly as shown."}

    # 2) Coerce raw_result to a hotel name string if possible
    selected_name = ""
    selected_hotel_obj = None

    if isinstance(raw_result, str):
        selected_name = raw_result.strip()
    elif isinstance(raw_result, dict):
        # If the extractor returned a full hotel-offer object (common):
        if "hotel" in raw_result and isinstance(raw_result["hotel"], dict):
            selected_hotel_obj = raw_result
            selected_name = raw_result["hotel"].get("name", "").strip()
        else:
            # If the extractor returned a dict like {"selection": "Name"} or {"name": "Name"}
            selected_name = (
                raw_result.get("selection")
                or raw_result.get("name")
                or raw_result.get("hotel_name")
                or ""
            )
            if isinstance(selected_name, str):
                selected_name = selected_name.strip()

    else:
        # Last resort: stringify
        try:
            selected_name = str(raw_result).strip() if raw_result is not None else ""
        except Exception:
            selected_name = ""

    # 3) Validate selected_name
    if not selected_name:
        return {
            "error": "Sorry, I couldn't identify a hotel from that message.",
            "options": [h.get("hotel", {}).get("name", "") for h in state["hotels"]]
        }

    # Respect "unknown" from LLM
    if selected_name.lower() == "unknown":
        return {"error": "Sorry, I couldn't identify which hotel you selected."}

    # 4) If extractor already gave us the object, accept it
    if selected_hotel_obj:
        name = selected_hotel_obj["hotel"].get("name", "")
        state["selected_hotel_name"] = name
        state["selected_hotel_id"] = selected_hotel_obj["hotel"].get("hotelId")
        state["awaiting_selection"] = False
        state["awaiting_booking_details"] = True
        return {
            "message": f"Great choice! You've selected {name}. Please provide your full name, email, and phone number to continue."
        }

    # 5) Try exact normalized match against the live hotel list
    norm_selected = normalize_name(selected_name)
    for hotel in state["hotels"]:
        hname = hotel.get("hotel", {}).get("name", "")
        if normalize_name(hname) == norm_selected:
            state["selected_hotel_name"] = hname
            state["selected_hotel_id"] = hotel.get("hotel", {}).get("hotelId")
            state["awaiting_selection"] = False
            state["awaiting_booking_details"] = True
            return {
                "message": f"Great choice! You've selected {hname}. Please provide your full name, email, and phone number to continue."
            }

    # 6) Try fuzzy match (suggestion) before failing
    hotel_names = [h.get("hotel", {}).get("name", "") for h in state["hotels"]]
    normalized_names = [normalize_name(n) for n in hotel_names]
    close = difflib.get_close_matches(norm_selected, normalized_names, n=1, cutoff=0.5)
    if close:
        idx = normalized_names.index(close[0])
        suggested = hotel_names[idx]
        # You can either auto-accept this or ask user to confirm. We'll ask to confirm:
        return {
            "message": f"Did you mean **{suggested}**? If yes, reply 'Yes' to confirm or type the exact hotel name.",
            "suggestion": suggested
        }

    # 7) Nothing found → return helpful error + options
    return {
        "error": "Hotel was identified but not found in available options.",
        "options": hotel_names
    }


# 3. Final booking step — extract name/email/phone and confirm booking
@app.post("/book_hotel")
async def book_selected_hotel(req: BookingRequest):
    if not state["awaiting_booking_details"]:
        return {"error": "Not currently awaiting booking details."}

    user_input = req.message
    info = extract_personal_info(user_input)

    if not info:
        return {"error": "Couldn't extract booking info. Please provide name, email, and phone number."}

    state["booking_details"] = info
    state["awaiting_booking_details"] = False

    # Simulate booking (replace with real API call later)
    return {
        "message": (
            f"✅ Booking confirmed for {info['name']} at {state['selected_hotel_name']}!\n\n"
            f"A confirmation email has been sent to {info['email']}.\n"
            f"Please complete your payment using the following link:\n"
            f"https://mock-payment.example.com/checkout"
        )
    }