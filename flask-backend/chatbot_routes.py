import os
from typing import Annotated, TypedDict, Literal, List
from dotenv import load_dotenv
from langchain import hub
from flask import request, jsonify, Blueprint
from flask_cors import CORS
import uuid
from langchain_openai import ChatOpenAI
from langgraph.prebuilt import create_react_agent
from langgraph.graph import START, StateGraph, MessagesState, END
from langchain_community.utilities import SQLDatabase
from langchain_community.agent_toolkits.sql.toolkit import SQLDatabaseToolkit
from langchain_community.tools.sql_database.tool import QuerySQLDatabaseTool
from langchain.schema import AIMessage
from sqlalchemy import create_engine, inspect
from datetime import datetime
from llm_tools import tools, generate_chart

chatbot_bp = Blueprint("chatbot_bp1", __name__)
CORS(chatbot_bp)

load_dotenv()

llm = ChatOpenAI(model="gpt-3.5-turbo", temperature=0.3)

base_dir = os.path.abspath(os.path.dirname(__file__))
db_path = os.path.join(base_dir, "ucd-basketball.db")
db_uri = f"sqlite:///{db_path}"
db = SQLDatabase.from_uri(db_uri)

engine = create_engine(db_uri)
inspector = inspect(engine)
print(inspector.get_table_names())

try:
    print("✅ DB connection successful. Tables found:", db.get_usable_table_names())
except Exception as e:
    print("❌ Failed to connect to DB:", str(e))

table_info = db.get_table_info()
prompt_template = hub.pull("langchain-ai/sql-agent-system-prompt")

class State(TypedDict):
    question: str
    relevant_stats: str
    result: str
    answer: str
    chart: str

def is_chart_request(question: str) -> bool:
    keywords = ["chart", "graph", "plot", "bar", "line", "visualize", "draw"]
    return any(kw in question.lower() for kw in keywords)

def query_decision_agent(state: dict) -> dict:
    structured_llm = llm.with_structured_output({"questions": List[str]})
    prompt = (
        "You are a UC Davis Basketball analyst and scout. Decide what queries to run...\n"
        "- If the question is a direct request (e.g., 'Who is the leading scorer?'), rephrase it.\n"
        "- If it's general (e.g., 'Give me a scouting report'), break it into multiple questions.\n"
        "Output should be a JSON list of questions."
    )
    return structured_llm.invoke(prompt)

def generate_answer(state: dict) -> str:
    response = llm.invoke(
        f"Question: {state.get('question')}\nStats: {state.get('relevant_stats')}\nGive an insight."
    )
    return response.content

def direct_answer(question: str) -> str:
    return llm.invoke(f"Answer this as a UC Davis analyst: {question}").content

def supervisor(state: dict) -> dict:
    response = llm.invoke(
        f"Should this be a DB query or direct answer?\nQuestion: {state.get('question')}"
    ).content.lower().strip()
    if "db_query" in response:
        return {"goto": "db_query"}
    elif "__end__" in response:
        return {"goto": END}
    return {"goto": "direct_answer"}

def overarching_supervisor(state: dict) -> dict:
    try:
        if is_chart_request(state["question"]):
            chart_b64 = generate_chart.invoke(state["question"])
            return {
                "type": "image",
                "text": "Here is your chart:",
                "data": chart_b64,
                "path": "chart"
            }

        cmd = supervisor(state)
        if cmd["goto"] == "direct_answer":
            return {"response": direct_answer(state["question"]), "path": "direct"}

        elif cmd["goto"] == "db_query":
            queries = query_decision_agent(state).get("questions", [])
            system_msg = prompt_template.format(dialect="MySQL", top_k=5)
            agent = create_react_agent(llm, tools, prompt=system_msg)
            stats = []
            for q in queries:
                try:
                    result = agent.invoke({"messages": [{"role": "user", "content": q}]})
                    msg = next((m.content for m in reversed(result['messages']) if isinstance(m, AIMessage)), None)
                    if msg: stats.append(msg)
                except Exception as e:
                    print(f"Query failed: {str(e)}")
            state["relevant_stats"] = stats
            return {"response": generate_answer(state), "path": "db_query"} if stats else {"response": "No useful stats found."}
    except Exception as e:
        return {"response": "Unexpected error.", "error": str(e)}

@chatbot_bp.route('/chat', methods=['POST', 'OPTIONS'])
def chat():
    if request.method == "OPTIONS":
        return jsonify({"status": "ok"})
    try:
        user_message = request.json.get("message")
        state: State = {"question": user_message, "relevant_stats": "", "result": "", "answer": "", "chart": ""}
        result = overarching_supervisor(state)
        result["thread_id"] = str(uuid.uuid4())
        return jsonify(result)
    except Exception as e:
        return jsonify({"error": "Error occurred", "details": str(e)}), 500
