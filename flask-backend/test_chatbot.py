import requests

BASE_URL = "http://localhost:5001/chat"  

print("🤖 Chatbot is ready! Type your question (or 'exit' to quit).\n")

while True:
    user_input = input("You: ")
    if user_input.lower() in {"exit", "quit"}:
        print("👋 Ending chat.")
        break

    try:
        response = requests.post(BASE_URL, json={"message": user_input})
        if response.status_code == 200:
            reply = response.json().get("response", "")
            print(f"Bot: {reply}")
        else:
            print(f"❌ Error {response.status_code}: {response.text}")
    except Exception as e:
        print(f"⚠️ Request failed: {e}")
