from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from Agent.chatbot import extract_booking_info
from hotel_service import AmadeusHotelService
from pydantic import BaseModel

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
    "adults": None
}

# Request model
class BookingRequest(BaseModel):
    message: str

# Utilities
def is_booking_complete(state):
    return all(state.values())

def update_state(extracted_data):
    for key in state:
        if extracted_data.get(key):
            state[key] = extracted_data[key]

def ask_for_missing_info():
    missing = [key.replace('_', ' ') for key, value in state.items() if not value]
    return f"Please provide: {', '.join(missing)}."

def city_name_to_code(name):
    mapping = {
        "cape town": "CPT",
        "johannesburg": "JNB",
        "durban": "DUR"
    }
    return mapping.get(name.lower(), name.upper())

def search_and_display_results():
    hotels = hotel_service.search_hotels_by_city(
        city_code=city_name_to_code(state["destination"]),
        check_in_date=state["check_in_date"],
        check_out_date=state["check_out_date"],
        adults=state["adults"]
    )

    if not hotels:
        return "Sorry, no hotels found."

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

    return reply

# Endpoint for frontend to call
@app.post("/book")
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