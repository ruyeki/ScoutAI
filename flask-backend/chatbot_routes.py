import os
from typing import Annotated, TypedDict
from dotenv import load_dotenv
from langchain import hub
from flask import request, jsonify,Blueprint
from flask_cors import CORS
import uuid
from langchain_openai import ChatOpenAI
#from llm_tools import db, tools, llm, query_prompt_template
from langgraph.prebuilt import create_react_agent
from llm import Chatbot
from langgraph.graph import START, StateGraph, END
from langchain_community.utilities import SQLDatabase
from langchain_community.agent_toolkits.sql.toolkit import SQLDatabaseToolkit
from langchain_community.tools.sql_database.tool import QuerySQLDatabaseTool
from llm_classes import State, Assistant, is_statistical_question, start_node

chatbot_bp = Blueprint("chatbot_bp", __name__)

load_dotenv()

db_username = os.getenv('DB_USERNAME') # admin
db_password = os.getenv('DB_PASSWORD') # asabasketball
db_name = os.getenv('DB_NAME') # game_stats
db_host = os.getenv('DB_HOST') # ucd-basketball.cduqug2e0o83.us-east-2.rds.amazonaws.comprompt_template = hub.pull("langchain-ai/sql-agent-system-prompt")

prompt_template = hub.pull("langchain-ai/sql-agent-system-prompt")

llm = ChatOpenAI(model="gpt-3.5-turbo", temperature=0.3)
db_uri = f"mysql+mysqlconnector://{db_username}:{db_password}@{db_host}/{db_name}"
db = SQLDatabase.from_uri(db_uri)


query_prompt_template = hub.pull("langchain-ai/sql-query-system-prompt")

MAX_RETRIES = 3

class State(TypedDict):
    question: str
    query: str
    result: str
    answer: str
    retry: bool  # flag indicating to retry if there's an error
    retry_count: int   # counter for retry attempts
    error: str


class QueryOutput(TypedDict):
    """Generated SQL query."""

    query: Annotated[str, ..., "Syntactically valid SQL query."]


def write_query(state: State):
    """Generate SQL query to fetch information.
    If previous attempt has error, retry"""
    # breakpoint()  

    if state["retry"] and state.get("retry_count", 0) < MAX_RETRIES:
        state["retry_count"] += 1
        prompt_text = (
            "The previous SQL query resulted in the error: "
            f"{state.get('error', 'Unknown error')}\n"
            "Please generate an alternative SQL query that avoids this error. "
            f"Question: {state['question']}"
        )
    else:
        prompt_text = query_prompt_template.invoke({
            "dialect": db.dialect,
            "top_k": 10,
            "table_info": db.get_table_info(),
            "input": state["question"],
        })
    structured_llm = llm.with_structured_output(QueryOutput)
    result = structured_llm.invoke(prompt_text)
    return {"query": result["query"]}

def execute_query(state: State):
    """Execute SQL query.
    If an error is detected (e.g. missing column), set a retry flag.
    """
    # breakpoint()  

    execute_query_tool = QuerySQLDatabaseTool(db=db)
    result = execute_query_tool.invoke(state["query"])

    if isinstance(result, str) and ("unknown column" in result.lower() or "error" in result.lower()):
        state["retry"] = True
        state["error"] = result
        state["retry_count"] = state.get("retry_count", 0) + 1
        return {"result": "", "retry": state["retry"], "retry_count": state["retry_count"], "error": state["error"]}
    else:
        state["retry"] = False
        return {"result": result, "retry": state["retry"], "retry_count": state["retry_count"], "error": state["error"]}

def generate_answer(state: State):
    """Answer question using retrieved information as context."""
    # breakpoint()

    prompt = (
        "Given the following user question, corresponding SQL query, "
        "and SQL result, answer the user question.\n\n"
        f'Question: {state["question"]}\n'
        f'SQL Query: {state["query"]}\n'
        f'SQL Result: {state["result"]}'
    )
    response = llm.invoke(prompt)

    if isinstance(response, str) and ("error" in response.lower() or "unknown column" in response.lower() or "modify" in response.lower()):
        state["retry"] = True
        state["error"] = response
        state["retry_count"] = state.get("retry_count", 0) + 1
        return {"answer": "", "retry": state["retry"], "retry_count": state["retry_count"], "error": state["error"]}
    state["answer"] = response.content
    return {"answer": response.content}

def get_next_node1(state: State):
    """Determine the next node based on state conditions"""
    if state.get("retry", False) and state.get("retry_count", 0) < MAX_RETRIES:
        return "write_query"
    return "generate_answer"

def get_next_node2(state: State):
    """Determine the next node based on state conditions"""
    if state.get("retry", False) and state.get("retry_count", 0) < MAX_RETRIES:
        return "write_query"
    return END


graph_builder = StateGraph(State)
graph_builder.add_node("write_query", write_query)
graph_builder.add_node("execute_query", execute_query)
graph_builder.add_node("generate_answer", generate_answer)

graph_builder.add_edge(START, "write_query")
graph_builder.add_edge("write_query", "execute_query")
graph_builder.add_conditional_edges("execute_query", get_next_node1)
graph_builder.add_conditional_edges("generate_answer", get_next_node2)
graph = graph_builder.compile()

@chatbot_bp.route('/chat', methods=['POST', 'OPTIONS'])
def chat():
    if request.method == "OPTIONS":
        return jsonify({"status": "ok"}), 200
        
    try:
        # breakpoint()

        data = request.json
        user_message = data.get('message')

        state: State = {
            "question": user_message,
            "query": "",
            "result": "",
            "answer": "",
            "retry": False,
            "retry_count": 0,
            "error": ""
        }

        # Track complete state through stream
        current_state = state.copy()
        steps = []
        
        for step in graph.stream(state):
            steps.append(step)
            print(step)
            # Merge new state information
            if isinstance(step, dict):
                current_state.update(step)

        # Get final answer from accumulated state
        final_response = current_state.get("generate_answer", {}).get("answer")
        
        if not final_response and steps:
            final_response = "I'm sorry, I couldn't generate a response."

        return jsonify({
            "response": final_response,
            "thread_id": str(uuid.uuid4()),
            "debug_info": {
                "steps": steps,
                "final_state": current_state
            }
        })
        
    except Exception as e:
        return jsonify({
            "error": "An error occurred while processing your request",
            "details": str(e)
        }), 500

