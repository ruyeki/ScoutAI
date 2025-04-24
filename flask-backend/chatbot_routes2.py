import os
from typing import Annotated, TypedDict, Literal, List
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
from langchain.schema import AIMessage
from sqlalchemy import create_engine, inspect
from datetime import datetime



chatbot_bp = Blueprint("chatbot_bp1", __name__)

load_dotenv()

def log_with_time(msg):
    now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    print(f"{msg} [Time: {now}]")

# # ----- LLM and Database Setup ----- #

#db_username = os.getenv('DB_USERNAME') # admin
#db_password = os.getenv('DB_PASSWORD') # asabasketball
#db_name = os.getenv('DB_NAME') # game_stats
#db_host = os.getenv('DB_HOST') # ucd-basketball.cduqug2e0o83.us-east-2.rds.amazonaws.comprompt_template = hub.pull("langchain-ai/sql-agent-system-prompt")


llm = ChatOpenAI(model="gpt-3.5-turbo", temperature=0.3)
#db_uri = f"mysql+mysqlconnector://{db_username}:{db_password}@{db_host}/{db_name}"
#db = SQLDatabase.from_uri(db_uri)
#table_info = db.get_table_info()


#THIS IS THE NEW SQLITE DATABASE CONNECTION CODE
base_dir = os.path.abspath(os.path.dirname(__file__))
db_path = os.path.join(base_dir, "ucd-basketball.db")
db_uri = f"sqlite:///{db_path}"
db = SQLDatabase.from_uri(db_uri)


#THIS IS JUST TO TEST TO SEE IF SQLITE DATABASE IS CONNECTED AND WORKING
engine = create_engine(db_uri)
inspector = inspect(engine)
table_names = inspector.get_table_names()
print(table_names)

if db: 
    try: 
        print("DB connection successful from chatbot routes 2")
            # Try running a basic test query to make sure the DB is responsive
        table_names = db.get_usable_table_names()
        print("✅ DB connection successful. Tables found:", table_names)
    except Exception as e:
        print("❌ Failed to connect to DB:", str(e))

table_info = db.get_table_info()
print(table_info)

MAX_RETRIES = 3

class State(TypedDict):
    question: str
    query: str
    result: str
    answer: str
    retry: bool  # flag indicating to retry if there's an error
    retry_count: int   # counter for retry attempts
    error: str 


# ---- Query Agent (State Graph) Setup ----- #

prompt_template = hub.pull("langchain-ai/sql-agent-system-prompt")
# system_message.messages[0].pretty_print()
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

toolkit = SQLDatabaseToolkit(db=db, llm=llm)
tools = toolkit.get_tools()


class QueryQuestionsOutput(TypedDict):
    questions: List[str]

def query_decision_agent(state: dict) -> Command[Literal["generate_answer", END]]:
    """
    Given the user's question, determine which specific database queries would help answer it.
    If the question is directly about a specific stat, output a single query.
    If it's general, output multiple query questions.
    
    Expected output format:
      { "questions": ["<SQL-like question 1>", "<SQL-like question 2>", ...] }
    """

    #breakpoint()

    prompt = (
        "You are a UC Davis Basketball analyst and scout. Your task is to determine which database queries will provide the most useful insights based on the user’s input. \n\n"
        "- If the question is already a direct request for a single piece of data (for example: \"Who is the leading scorer on UC Davis?\"), return the original question unchanged.  \n"
        "- If the question is more general or exploratory (for example: \"Give me a scouting report on UC Riverside\"), break it down into multiple detailed query questions that would cover relevant trends, player statistics, and performance metrics.  \n"
        "- The output should always be a JSON object with a list of questions. \n\n"
        "You have access to the following table information:\n"
        "{table_info}\n\n"
        "Based on this, for the given user question below, decide whether to return it as-is or to break it down into multiple queries, then provide your output in the specified JSON format.\n\n"
        "User Question:\n"
        f"{state.get('question')}\n\n"
        "Output format:\n"
        "{ \"questions\": [\"<query question 1>\", \"<query question 2>\", ...] }"
    )

    structured_llm = llm.with_structured_output(QueryQuestionsOutput)
    result = structured_llm.invoke(prompt)
    log_with_time(f"[QueryDecisionAgent] Agent generated query questions: {result}")
    return result

def generate_answer(state: dict) -> Command[Literal["end"]]:
    """
    Generate the final answer to the user's question using the database query results.
    """

    prompt = (
        "You are a UC Davis Basketball analyst and scout. "
        "Given the following question and the results of the database queries, generate a detailed and actionable insight that answers the user's question.\n\n"
        f"Question: {state.get('question')}\n"
        f"Database result: {state.get('relevant_stats')}\n\n"
        "Output your answer in a clear and concise manner, and only use stats that are relevant to the question."
    )

    response = llm.invoke(prompt)
    log_with_time(f"[GenerateAnswer] LLM generated answer: {response.content}")
    return response.content

def direct_answer(question: str) -> str:
    """
    Generate direct answer to user input, no sql query.
    """
    prompt = f"As a UC Davis Basketball analyst, answer the following question: {question}"
    response = llm.invoke(prompt)
    log_with_time(f"[DirectAnswer] LLM generated direct answer: {response.content}")
    return response.content

# ----- Supervisor Agent ----- #

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
    log_with_time(f"[Supervisor] Supervisor agent decided next step: {next_agent}")
    return Command(goto=next_agent)

def overarching_supervisor(state: dict) -> dict:
    # State
    try:
        cmd = supervisor(state)
        if cmd.goto == "direct_answer":
            # Call the direct answer function
            answer = direct_answer(state["question"])
            log_with_time(f"[OverarchingSupervisor] Direct answer generated: {answer}")
            return {"response": answer, "path": "direct"}
        elif cmd.goto == "db_query":
            # Run the query graph and extract the answer
            query_spec_output = query_decision_agent(state)
            query_questions = query_spec_output.get("questions", [])
            log_with_time(f"[OverarchingSupervisor] Query questions to execute: {query_questions}")
            system_message = prompt_template.format(dialect="MySQL", top_k=5)
            agent_executor = create_react_agent(llm, tools, prompt=system_message)

            relevant_stats = []
            query_errors = []

            for question in query_questions:
                try:
                    result = agent_executor.invoke({
                        "messages": [
                            {
                                "role": "user",
                                "content": question
                            }
                        ]
                    })
                    ai_message = next(
                        (msg.content for msg in reversed(result['messages']) if isinstance(msg, AIMessage)), 
                        None
                    )
                    log_with_time(f"[OverarchingSupervisor] Agent executed query: {question} Response: {ai_message}")
                    if ai_message:
                        relevant_stats.append(ai_message)
                    
                except Exception as e:
                    query_errors.append(f"Error querying '{question}': {str(e)}")

            state["relevant_stats"] = relevant_stats
            state["query_errors"] = query_errors

            if relevant_stats:
                answer = generate_answer(state)
                log_with_time(f"[OverarchingSupervisor] Final answer generated from DB queries: {answer}")
                return {
                        "response": answer,
                        "path": "db_query",
                        "status": "success",
                        "metadata": {
                            "queries_executed": len(query_questions),
                            "successful_queries": len(relevant_stats),
                            "failed_queries": len(query_errors)
                        }
                    }
            else:
                log_with_time(f"[OverarchingSupervisor] All queries failed. Errors: {query_errors}")
                return {
                        "response": "I encountered issues while querying the database. Please try rephrasing your question.",
                        "path": "db_query",
                        "status": "error",
                        "errors": query_errors
                    }
    except Exception as e:
        log_with_time(f"[OverarchingSupervisor] Unexpected error: {str(e)}")
        return {
            "response": "I apologize, but I encountered an unexpected error while processing your request.",
            "path": "error",
            "status": "error",
            "error": str(e)
        }



@chatbot_bp.route('/chat', methods=['POST', 'OPTIONS'])
def chat():
    if request.method == "OPTIONS":
        return jsonify({"status": "ok"}), 200
        
    try:
        #breakpoint()

        data = request.json
        user_message = data.get("message")

        state: State = { # initial state
            "question": user_message,
            "relevant_stats": "",
            "result": "",
            "answer": "",
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