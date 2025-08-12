# app.py
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import logging
from fastmcp import Client

# Import the chatbot orchestration and your Amadeus service
from Agent.chatbot import process_user_message
from hotel_service import AmadeusHotelService

app = FastAPI()


logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# MCP client setup
mcp_client = Client("http://localhost:9000/mcp")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],  # or ["*"] while dev
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Instantiate your Amadeus wrapper (assumes you have AmadeusHotelService implemented)
hotel_service = AmadeusHotelService.AmadeusHotelService()

# Single in-memory state for demo. For multi-user, map session_id -> state.
state = {
    "destination": None,   # ideally this will hold a city code or a city name depending on your lookup process
    "check_in": None,
    "check_out": None,
    "guests": None,
    "hotels": None,
    "awaiting_selection": False,
    "selected_hotel": None,
    "booking_details": None
}

class BookingRequest(BaseModel):
    message: str

def reset_conversation():
    global state, conversation_history
    state = {
        "destination": None,
        "check_in": None,
        "check_out": None,
        "guests": None,
        "awaiting_selection": False,
        "hotels": [],
        "selected_hotel": None
    }
    conversation_history = []

@app.post("/request_hotel")
async def request_hotel(req: BookingRequest):
    user_message = req.message
    logger.info("Received user message: %s", user_message)

    # Delegate to Agent.chatbot to handle a single user turn.
    async with Client("http://localhost:9000/mcp") as mcp_client:
        assistant_text, new_state = await process_user_message(user_message, state, mcp_client)
    # assistant_text, new_state = await process_user_message(user_message, state, mcp_client)
    # state is mutated in-place by process_user_message, but return it for clarity
    return {"reply": assistant_text, "state": new_state}

