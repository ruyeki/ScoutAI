from flask import Blueprint, request, jsonify 
import os
from dotenv import load_dotenv
from langchain_openai import ChatOpenAI
from langchain import hub

chatbot_bp = Blueprint("chatbot_bp", __name__)

load_dotenv()

llm = ChatOpenAI(model_name="gpt-3.5-turbo", temperature=0.7)
query_prompt_template = hub.pull("langchain-ai/sql-query-system-prompt")

@chatbot_bp.route('/chat', methods=['POST', 'OPTIONS'])
def chat():
    if request.method == "OPTIONS":
        return jsonify({"status": "ok"}), 200

    data = request.json
    user_message = data.get('message')

    messages = [
        {"role": "system", "content": "You are a coaching and analytics assistant for the UC Davis Men's Basketball team."},
        {"role": "user", "content": user_message}
    ]

    response = llm.invoke(messages)

    return jsonify({
        "response": response.content
    })
