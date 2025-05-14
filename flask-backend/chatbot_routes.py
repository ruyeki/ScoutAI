import os
from typing import Annotated, TypedDict, Literal, List
from dotenv import load_dotenv
from langchain import hub
from flask import request, jsonify, Blueprint
from flask_cors import CORS
import uuid
from langchain_openai import ChatOpenAI
# from llm_tools import db, tools, llm, query_prompt_template
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
from langchain.chains import ConversationChain
from langchain.chains.conversation.memory import ConversationBufferMemory
from langchain.chains.conversation.memory import ConversationSummaryMemory

chatbot_bp = Blueprint("chatbot_bp1", __name__)
CORS(chatbot_bp)

load_dotenv()

def log_with_time(msg):
    now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    print(f"{msg} [Time: {now}]")

# ----- LLM and Database Setup ----- #
llm = ChatOpenAI(model="gpt-3.5-turbo", temperature=0.3)
#db_uri = f"mysql+mysqlconnector://{db_username}:{db_password}@{db_host}/{db_name}"
#db = SQLDatabase.from_uri(db_uri)
#table_info = db.get_table_info()

conversation = ConversationChain(llm=llm)

conversation_sum = ConversationChain(
    llm=llm,
    memory=ConversationBufferMemory()
)

# SQLITE Database Connection
base_dir = os.path.abspath(os.path.dirname(__file__))
db_path = os.path.join(base_dir, "ucd-basketball.db")
db_uri = f"sqlite:///{db_path}"
db = SQLDatabase.from_uri(db_uri)

# Test DB connection
engine = create_engine(db_uri)
inspector = inspect(engine)
table_names = inspector.get_table_names()
#print(table_names)

if db: 
    try: 
        #print("DB connection successful from chatbot routes 2")
            # Try running a basic test query to make sure the DB is responsive
        table_names = db.get_usable_table_names()
        #print("✅ DB connection successful. Tables found:", table_names)
    except Exception as e:
        print("❌ Failed to connect to DB:", str(e))

table_info = db.get_table_info()

# SQL Toolkit
toolkit = SQLDatabaseToolkit(db=db, llm=llm)
tools = toolkit.get_tools()

MAX_RETRIES = 3

class State(TypedDict):
    question: str
    query: str
    result: str
    answer: str
    retry: bool
    retry_count: int
    error: str

# Load system prompt for SQL agent
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
Only refer to players you find in the tables. If the player is not mentioned, respond with 'I don’t have data on that player.' Do not make up names.
When referencing stats for players, avoid including any statistics or details that pertain to team performance. Focus solely on the player's individual attributes and achievements. Do not make up names or stats.
DO NOT make any DML statements (INSERT, UPDATE, DELETE, DROP etc.) to the database.

To start you should ALWAYS look at the tables in the database to see what you can query.
Do NOT skip this step.
Then you should query the schema of the most relevant tables.
"""

toolkit = SQLDatabaseToolkit(db=db, llm=llm)
tools = toolkit.get_tools()


class QueryQuestionsOutput(TypedDict):
    questions: List[str]



def query_decision_agent(state: dict, memory: str = "")  -> QueryQuestionsOutput:
    """
    Given the user's question, determine which specific database queries would help answer it.
    If the question is directly about a specific stat, output a single query.
    If it's general, output multiple query questions.
    
    Expected output format:
      { "questions": ["<SQL-like question 1>", "<SQL-like question 2>", ...] }
    """

    #breakpoint()

    prompt = (
        "You are a UC Davis Basketball analyst and scout. Your task is to determine which database queries will provide the most useful insights based on the user's input.\n\n"
        
        "Guidelines:\n"
        "- If the question is a direct request for a single data point (e.g., 'Who is the leading scorer on UC Davis?'), just rephrase it slightly if needed and return it as a single query.\n"
        "- If the question is general or exploratory (e.g., 'Give me a scouting report on UC Riverside'), break it down into multiple specific query questions that cover relevant trends, stats, and performance insights.\n"
        "- Prefer per-game stats over season totals whenever applicable.\n"
        "- The output should always be a JSON object in the format: { \"questions\": [\"<query 1>\", \"<query 2>\", ...] }\n\n"

        "Memory usage:\n"
        "- Use the following past context to help interpret the current question.\n"
        "- If the user's question contains vague references (e.g., 'he', 'that player', 'those guys', 'him'), resolve those references using memory.\n"
        "- For example: if the user asks 'How many assists does he average?' and the memory says 'TY Johnson plays for UC Davis', then rephrase the question as 'How many assists does TY Johnson average?'\n"
        "– Make sure to consider both the AI's and the human's responses, not just the AI's. Understanding the full context of the conversation is important. \n"
        "- If there's no useful information in memory, proceed with the question as-is.\n\n"

        "Table info available:\n"
        "{table_info}\n\n"

        f"Past context (memory):\n{memory}\n\n"

        "Now, given the user question below, decide whether to return it as a single query or break it into multiple useful sub-questions. Output must follow the format shown below.\n\n"

        f"User Question:\n{state.get('question')}\n\n"

        "Output format:\n"
        "{ \"questions\": [\"<query question 1>\", \"<query question 2>\", ...] }"
    )



    structured_llm = llm.with_structured_output(QueryQuestionsOutput)
    result = structured_llm.invoke(prompt)
    log_with_time(f"[QueryDecisionAgent] Agent generated query questions: {result}")
    return result

def generate_answer(state: dict, memory: str = "") -> Command[Literal["end"]]:
    """
    Generate the final answer to the user's question using the database query results.
    """
    prompt = (
        "You are a UC Davis Basketball analyst and scout.\n\n"
        "Your task is to generate a detailed and actionable insight in response to the user's question, based on the database query results.\n"
        "- Use the memory to resolve vague references (e.g., 'he', 'him', 'those players', 'compare to before').\n"
        "- For example, if the user asks, “How many assists does he average?” and the memory indicates “he” refers to TY Johnson, rephrase and answer as if the user asked, “How many assists does TY Johnson average?”\n"
        "- If there’s no relevant context in memory, interpret the question as a standalone.\n"
        "– Make sure to consider both the AI's and the human's responses, not just the AI's. Understanding the full context of the conversation is important. \n"
        "- Use only relevant stats from the database results to answer the question.\n"
        "- The answer should be clear, detailed, and focused on the user’s intent.\n\n"
        f"Question: {state.get('question')}\n\n"
        f"Past context:\n{memory}\n\n"
        f"Database result:\n{state.get('relevant_stats')}\n\n"
        "Answer:"
    )
    response = llm.invoke(prompt)
    log_with_time(f"[GenerateAnswer] LLM generated answer: {response.content}")
    return response.content


def direct_answer(question: str, memory: str = "") -> str:
    """
    Generate a direct answer to the user's question without using a SQL query.
    """
    prompt = (
        "You are a UC Davis Basketball analyst.\n\n"
        "Your task is to answer questions directly, using context from previous interactions (provided as 'Past context') to clarify references. "
        "If the user's question includes vague terms like 'that', 'those players', or refers to previous questions implicitly, resolve them using the memory.\n\n"
        "– Make sure to consider both the AI's and the human's responses, not just the AI's. Understanding the full context of the conversation is important. \n"
        "If the user is asking about a player's statistics (e.g., points, assists, rebounds, shooting percentage), route to `db_query` instead of answering directly — even if the player's name is only implied in the memory.\n\n"
        "If no relevant context is found in memory, treat the question as standalone and proceed as normal.\n\n"
        f"Past context:\n{memory}\n\n"
        f"Current question:\n{question}"
    )
    response = llm.invoke(prompt)
    log_with_time(f"[DirectAnswer] LLM generated direct answer: {response.content}")
    return response.content
# ----- Supervisor Agent ----- #
def supervisor(state: dict) -> Command[Literal["direct_answer", "db_query", END]]:
    prompt = (
        "You are a UC Davis Basketball analyst and scout. Based on the following question, "
        "decide whether to answer directly or to query the database for stats.\n\n"
        f'Question: {state.get("question")}\n'
        "If the question is about a comparison, stats, or trends, output \"db_query\". "
        "Otherwise, output \"direct_answer\". If no further action is needed, output \"__end__\"."
    )
    response = llm.invoke(prompt)
    text = response.content.lower().strip()
    if "db_query" in text:
        next_agent = "db_query"
    elif "__end__" in text:
        next_agent = END
    else:
        next_agent = "direct_answer"
    log_with_time(f"[Supervisor] Next step: {next_agent}")
    return Command(goto=next_agent)

# ----- Overarching Supervisor ----- #
def overarching_supervisor(state: dict) -> dict:
    try:
        cmd = supervisor(state)

        if cmd.goto == "direct_answer":
            # Call the direct answer function
            answer = direct_answer(state["question"], state.get("memory", ""))
            log_with_time(f"[OverarchingSupervisor] Direct answer generated: {answer}")
            return {"response": answer, "path": "direct"}
        
        elif cmd.goto == "db_query":
            # Run the query graph and extract the answer
            query_spec_output = query_decision_agent(state, state.get("memory", ""))
            query_questions = query_spec_output.get("questions", [])
            log_with_time(f"[OverarchingSupervisor] Query questions to execute: {query_questions}")
            system_message = prompt_template.format(dialect="MySQL", top_k=5)
            agent_executor = create_react_agent(llm, tools, prompt=system_message)

            stats, errors = [], []
            for q in queries:
                try:
                    result = agent.invoke({"messages": [{"role": "user", "content": q}]})
                    msg = next((m.content for m in reversed(result['messages']) if isinstance(m, AIMessage)), None)
                    if msg: stats.append(msg)
                    log_with_time(f"Executed query '{q}': {msg}")
                except Exception as e:
                    errors.append(f"Error querying '{q}': {str(e)}")

            state["relevant_stats"] = stats
            state["query_errors"] = errors

            if stats:
                raw = generate_answer(state)
                formatted = format_output(raw)
                return {"response": formatted, "path": "db_query", "status": "success", "metadata": {"queries_executed": len(queries), "successful_queries": len(stats), "failed_queries": len(errors)}}
            else:
                log_with_time(f"All queries failed: {errors}")
                return {"response": "I encountered issues while querying the database. Please try rephrasing your question.", "path": "db_query", "status": "error", "errors": errors}
    except Exception as e:
        log_with_time(f"[OverarchingSupervisor] Unexpected error: {e}")
        return {"response": "I apologize, but I encountered an unexpected error while processing your request.", "path": "error", "status": "error", "error": str(e)}

@chatbot_bp.route('/chat', methods=['POST', 'OPTIONS'])
def chat():
    if request.method == "OPTIONS":
        return jsonify({"status": "ok"}), 200
    try:
        data = request.json
        user_message = data.get("message")

        _ = conversation_sum.predict(input=user_message)  # To update memory/summarization
        print(_)
        memory = conversation_sum.memory.buffer
        print(memory)

        # Initialize state
        state: dict = {
            "question": user_message,
            "memory": memory
        }
        
        #call overarching agent
        result = overarching_supervisor(state)
        result["thread_id"] = str(uuid.uuid4())
        return jsonify(result)
    except Exception as e:
        return jsonify({"error": "An error occurred while processing your request", "details": str(e)}), 500
