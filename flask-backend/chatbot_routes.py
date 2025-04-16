import os
from typing import Annotated, TypedDict, Literal
from dotenv import load_dotenv
from langchain import hub
from flask import request, jsonify,Blueprint
from flask_cors import CORS
import uuid
from langchain_openai import ChatOpenAI
#from llm_tools import db, tools, llm, query_prompt_template
from langgraph.prebuilt import create_react_agent
from llm import Chatbot
from langgraph.graph import START, StateGraph, MessagesState, END
from langchain_community.utilities import SQLDatabase
from langchain_community.agent_toolkits.sql.toolkit import SQLDatabaseToolkit
from langchain_community.tools.sql_database.tool import QuerySQLDatabaseTool
from llm_classes import State, Assistant, is_statistical_question, start_node
from langgraph.types import Command


chatbot_bp = Blueprint("chatbot_bp", __name__)

load_dotenv()

# # ----- LLM and Database Setup ----- #

db_username = os.getenv('DB_USERNAME') # admin
db_password = os.getenv('DB_PASSWORD') # asabasketball
db_name = os.getenv('DB_NAME') # game_stats
db_host = os.getenv('DB_HOST') # ucd-basketball.cduqug2e0o83.us-east-2.rds.amazonaws.comprompt_template = hub.pull("langchain-ai/sql-agent-system-prompt")


prompt_template = hub.pull("langchain-ai/sql-agent-system-prompt")
prompt_template.messages[0].pretty_print()
"""
You are an agent designed to interact with a SQL database.
Given an input question, create a syntactically correct {dialect} query to run, then look at the results of the query and return the answer.
Unless the user specifies a specific number of examples they wish to obtain, always limit your query to at most {top_k} results.
You can order the results by a relevant column to return the most interesting examples in the database.
Never query for all the columns from a specific table, only ask for the relevant columns given the question.
You have access to tools for interacting with the database.
Only use the below tools. Only use the information returned by the below tools to construct your final answer.
You MUST double check your query before executing it. If you get an error while executing a query, rewrite the query and try again.

DO NOT make any DML statements (INSERT, UPDATE, DELETE, DROP etc.) to the database.

To start you should ALWAYS look at the tables in the database to see what you can query.
Do NOT skip this step.
Then you should query the schema of the most relevant tables.
"""


llm = ChatOpenAI(model="gpt-3.5-turbo", temperature=0.3)
#db_uri = f"mysql+mysqlconnector://{db_username}:{db_password}@{db_host}/{db_name}"
#db = SQLDatabase.from_uri(db_uri)

base_dir = os.path.abspath(os.path.dirname(__file__))
db_path = os.path.join(base_dir, "ucd-basketball.db")
db_uri = f"sqlite:///{db_path}"

# Use it to initialize SQLDatabase
db = SQLDatabase.from_uri(db_uri)
if db: 
    print("db connection successful from chatbot routes")


#app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///ucd-basketball.db'

table_info = db.get_table_info()
print(table_info)


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


# ---- Query Agent (State Graph) Setup ----- #

def determine_relevant_stats(state: State) -> str:
    """Determine relevant stats to query based on the user question."""
    prompt = (
        "You are a UC Davis basketball analyst and scout. "
        "Given the following user question, determine the relevant stats that should be queried to provide an insightful answer. "
        "If the user question is asking for a specific stat, output that stat in a way that can be easily translated into a SQL query. "
        "If the question is ambiguous, list a few relevant stats that would help provide a detailed response.\n\n"
        f"Question: {state['question']}"
    )
    response = llm.invoke(prompt)
    return response.content

def write_query(state: State):
    """Generate SQL query to fetch information, informed by relevant stats."""
    relevant_stats = determine_relevant_stats(state)
    # You might log or print the relevant stats for debugging:
    print("Relevant stats determined:", relevant_stats)
    
    if state["retry"] and state.get("retry_count", 0) < MAX_RETRIES:
        state["retry_count"] += 1
        prompt_text = (
            "The previous SQL query resulted in the error: "
            f"{state.get('error', 'Unknown error')}\n"
            "Please generate an alternative SQL query that avoids this error. "
            f"Question: {state['question']} "
            f"and consider these relevant stats: {relevant_stats}"
        )
    else:
        table_info = db.get_table_info()
        prompt_text = query_prompt_template.invoke({
            "dialect": db.dialect,
            "top_k": 10,
            "table_info": table_info,
            "input": f"{state['question']} Relevant stats: {relevant_stats}",
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
        "You are a UC Davis basketball analyst and scout."
        "Given the following user question, corresponding SQL query, "
        "and SQL result, provide a nuanced answer to the question. "
        "Only mention the stats in you response, do not mention the SQL query."
        "\n\n"
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

def execute_checker(state: State):
    """Determine the next node based on state conditions"""
    if state.get("retry", False) and state.get("retry_count", 0) < MAX_RETRIES:
        return "write_query"
    return "generate_answer"

def answer_checker(state: State):
    """Determine the next node based on state conditions"""
    if state.get("retry", False) and state.get("retry_count", 0) < MAX_RETRIES:
        return "write_query"
    return END

def needs_db_query(state: State) -> bool:
    """
    Function to determine if a database query is needed based on keywords in user input
    """
    keywords = ["scorer", "points", "stat", "game", "compare", "leader"]
    question = state["question"].lower()
    if any(keyword in question for keyword in keywords):
        return "write_query"
    return "generate_answer"

graph_builder = StateGraph(State)
graph_builder.add_node("write_query", write_query)
graph_builder.add_node("execute_query", execute_query)
graph_builder.add_node("generate_answer", generate_answer)

graph_builder.add_edge(START, "write_query")
graph_builder.add_edge("write_query", "execute_query")
graph_builder.add_conditional_edges("execute_query", execute_checker)
graph_builder.add_conditional_edges("generate_answer", answer_checker)
query_graph = graph_builder.compile()

# ----- Supervisor Agent ----- #


def direct_answer(question: str) -> str:
    """
    Generate direct answer to user input, no sql query.
    """
    prompt = f"As a UC Davis Basketball analyst, answer the following question: {question}"
    response = llm.invoke(prompt)
    return response.content

def supervisor(state: dict) -> Command[Literal["direct_answer", "db_query", END]]:
    """
    The supervisor examines the state (e.g., the user's messages or question)
    and returns a Command that directs the flow to either:
      - "direct_answer": Answer directly using the LLM,
      - "db_query": Delegate to the DB query chain,
      - END: End the conversation.
    """

    prompt = (
        "You are a UC Davis Basketball analyst and scout. Based on the following question, "
        "decide whether to answer directly or to query the database for stats.\n\n"
        f'Question: {state.get("question")}\n'
        "If the question is about a comparison, stats, or trends, output \"db_query\". "
        "Otherwise, output \"direct_answer\". If no further action is needed, output \"__end__\"."
    )

    response = llm.invoke(prompt)
    # Assume response is parsed to a dictionary with a "next_agent" key.
    response_text = response.content.lower().strip()
    
    # Determine next agent based on response content
    if "db_query" in response_text:
        next_agent = "db_query"
    elif "__end__" in response_text:
        next_agent = END
    else:
        next_agent = "direct_answer"
    return Command(goto=next_agent)

def overarching_supervisor(state: dict) -> dict:
    
    cmd = supervisor(state)
    if cmd.goto == "direct_answer":
        # Call the direct answer function
        answer = direct_answer(state["question"])
        return {"response": answer, "path": "direct"}
    elif cmd.goto == "db_query":
        # Run the query graph and extract the answer
        current_state = state.copy()
        steps = []
        for step in query_graph.stream(state):
            steps.append(step)
            print(step)
            if isinstance(step, dict):
                current_state.update(step)
        answer = current_state.get("generate_answer", {}).get("answer", "")
        print(current_state)
        if not answer:
            answer = "I'm sorry, I couldn't generate a response from the database."
        return {"response": answer, "path": "db_query", "debug_info": {"steps": steps, "final_state": current_state}}
    else:  # if END or other commands
        return {"response": "Goodbye!", "path": "end"}


@chatbot_bp.route('/chat', methods=['POST', 'OPTIONS'])
def chat():
    if request.method == "OPTIONS":
        return jsonify({"status": "ok"}), 200
        
    try:
        breakpoint()

        data = request.json
        user_message = data.get("message")

        state: State = { # initial state
            "question": user_message,
            "query": "",
            "result": "",
            "answer": "",
            "retry": False,
            "retry_count": 0,
            "error": ""
        }

        #call overarching agent
        result = overarching_supervisor(state)
        result["thread_id"] = str(uuid.uuid4())
        return jsonify(result)
        
    except Exception as e:
        return jsonify({
            "error": "An error occurred while processing your request",
            "details": str(e)
        }), 500

