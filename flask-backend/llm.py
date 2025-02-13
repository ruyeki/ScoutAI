import os
from dotenv import load_dotenv
from langchain_openai import ChatOpenAI

def main():
    # Load environment variables (e.g., your OPENAI_API_KEY)
    load_dotenv()
    
    # Initialize the OpenAI chat model (using GPT-3.5-turbo, adjust temperature if desired)
    llm = ChatOpenAI(model_name="gpt-3.5-turbo", temperature=0.7)
    
    # Start with a system message that defines the assistant's role.
    messages = [
        {"role": "system", "content": "You are a helpful assistant."}
    ]
    
    print("Welcome to your interactive assistant! Type 'quit' to exit.\n")
    
    while True:
        # Get user input from the terminal.
        user_input = input("User: ").strip()
        if user_input.lower() in ["quit", "exit", "q"]:
            print("Goodbye!")
            break
        
        # Append the user message to the conversation history.
        messages.append({"role": "user", "content": user_input})
        
        # Query the LLM with the full conversation history.
        response = llm.invoke(messages)
        
        # Retrieve the assistant's reply.
        assistant_reply = response.content
        
        # Append the assistant's response to the conversation history.
        messages.append({"role": "assistant", "content": assistant_reply})
        
        # Print the assistant's reply.
        print("\nAssistant:", assistant_reply, "\n")

if __name__ == "__main__":
    main()
