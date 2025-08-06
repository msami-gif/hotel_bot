# import ollama
# from langchain_ollama import OllamaLLM
# from langchain_core.prompts import ChatPromptTemplate


# # template = """
# # Answer the quesitons below.

# # Question: {question}

# # Answer:
# # """


# #Initialize the model
# model = OllamaLLM(model="llama3")

# # Initialize chat prompt template 
# with open("Template/template.txt", "r", encoding="utf-8") as intents:
#     template = intents.read()
# # Create a chain that combines the prompt and the model
# prompt = ChatPromptTemplate.from_template(template)
# chain = prompt | model

# def handle_conversation():
#     print("Welcome to the Hotel Bot! Type 'exit' to end the conversation.")
#     while True:
#         user_input = input("You: ")
#         if user_input.lower() == 'exit':
#             print("Ending conversation. Goodbye!")
#             break
        
#         # Invoke the model with the user's question
#         response = chain.invoke({"question": user_input})
#         print(030302"Chatbot: ", response)


# if __name__ == "__main__":
#     handle_conversation()
# main.py
from Agent.chatbot import extract_booking_info
from hotel_service import AmadeusHotelService

hotel_service = AmadeusHotelService.AmadeusHotelService()

# Booking state
state = {
    "destination": None,
    "check_in_date": None,
    "check_out_date": None,
    "adults": None
}

def is_booking_complete(state):
    return all(state.values())

def update_state(extracted_data):
    for key in state:
        if extracted_data.get(key):
            state[key] = extracted_data[key]

def ask_for_missing_info():
    missing = [key.replace('_', ' ') for key, value in state.items() if not value]
    return f"Please provide: {', '.join(missing)}."

def search_and_display_results():
    print(f"\nSearching for hotels in {state["destination"]}...")
    hotels = hotel_service.search_hotels_by_city(
        city_code=city_name_to_code(state["destination"]),
        check_in_date=state["check_in_date"],
        check_out_date=state["check_out_date"],
        adults=state["adults"]
    )

    if not hotels:
        return "Sorry, no hotels found."

    reply = "\nHere are some hotel options:\n\n"
    for hotel in hotels[:10]:
        print(f"Available" if hotel.get('available', True) else "Not available")
        h = hotel["hotel"]
        o = hotel["offers"][0]
        print(f"Offers: {hotel['offers']}")
        # reply += f"- {h['name']}, {h['address']['lines'][0]} – {o['price']['total']} {o['price']['currency']}\n"
        name = h.get('name', 'Unnamed Hotel')
        address = h.get('address', {}).get('lines', ['Address not available'])[0]
        price = o.get('price', {}).get('total', 'N/A')
        currency = o.get('price', {}).get('currency', '')
        availability = "Available" if hotel.get('available', True) else "Not available"
        policies = o.get('policies', {}).get('cancellations')[0].get('description').get('text', 'No cancellation policy available')
        reply += f" Hotel: {name}, Address: {address} – \n Price: {price} {currency} \n Availibility: {availability} \n Policy: {policies}\n\n"
    return reply

def city_name_to_code(name):
    # Simplified mapping (extend as needed)
    mapping = {
        "cape town": "CPT",
        "johannesburg": "JNB",
        "durban": "DUR"
    }
    return mapping.get(name.lower(), name.upper())  # fallback

def handle_conversation():
    print("👋 Welcome to Hotel Bot! Type 'exit' to quit.")
    while True:
        user_input = input("You: ")
        if user_input.lower() == "exit":
            print("Goodbye!")
            break

        extracted = extract_booking_info(user_input)
        if extracted:
            update_state(extracted)

        if is_booking_complete(state):
            print(f"\nThanks! You're booking for {state['adults']} adult(s) in {state['destination']} from {state['check_in_date']} to {state['check_out_date']}.")
            print(search_and_display_results())
            break
        else:
            print(ask_for_missing_info())

if __name__ == "__main__":
    handle_conversation()
