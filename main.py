import ollama
from langchain_ollama import OllamaLLM
from langchain_core.prompts import ChatPromptTemplate

# Function to start the chat with the hotel bot
# def start_chat():
template = """
Answer the quesitons below.

Question: {question}

Answer:
"""
#Initialize the model - model used is "llama3"
model = OllamaLLM(model="llama3")

# Initialize chat prompt template 
# prompt = ChatPromptTemplate.from_template(template)
with open("Template/template.txt", "r", encoding="utf-8") as intents:
    template = intents.read()
# Create a chain that combines the prompt and the model
chain = intents | model

def handle_conversation():
    print("Welcome to the Hotel Bot! Type 'exit' to end the conversation.")
    while True:
        user_input = input("You: ")
        if user_input.lower() == 'exit':
            print("Ending conversation. Goodbye!")
            break
        
        # Invoke the model with the user's question
        response = chain.invoke({"question": user_input})
        print("Chatbot: ", response)


if __name__ == "__main__":
    handle_conversation()