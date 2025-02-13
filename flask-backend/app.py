import os
from dotenv import load_dotenv
from langchain_openai import ChatOpenAI
from langchain import hub
from flask import Flask, request, jsonify
from flask_cors import CORS


app = Flask(__name__)
# Configure CORS to allow requests from your React app
CORS(app, resources={
    r"/*": {
        "origins": ["http://localhost:3000"],
        "methods": ["GET", "POST", "OPTIONS"],
        "allow_headers": ["Content-Type"]
    }
})

load_dotenv()
llm = ChatOpenAI(model_name="gpt-3.5-turbo", temperature=0.7)
query_prompt_template = hub.pull("langchain-ai/sql-query-system-prompt")

@app.route('/chat', methods=['POST', 'OPTIONS'])
def chat():
    if request.method == "OPTIONS":
        return jsonify({"status": "ok"}), 200
        
    data = request.json
    user_message = data.get('message')
    
    messages = [
        {"role": "system", "content": "You are a coaching and analytics assistant for the UC Davis Men's Basketball team.."},
        {"role": "user", "content": user_message}
    ]
    
    response = llm.invoke(messages)
    
    return jsonify({
        "response": response.content
    })

if __name__ == "__main__":
    app.run(debug=True, port=5001)