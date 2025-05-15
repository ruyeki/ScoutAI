import os, json
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

chatbot_bp = Blueprint("chatbot_bp1", __name__)
CORS(chatbot_bp)

load_dotenv()

def log_with_time(msg):
    now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    print(f"{msg} [Time: {now}]")

# ----- LLM and Database Setup ----- #
llm = ChatOpenAI(model="gpt-3.5-turbo", temperature=0.3)

# SQLITE Database Connection
base_dir = os.path.abspath(os.path.dirname(__file__))
db_path = os.path.join(base_dir, "ucd-basketball.db")
db_uri = f"sqlite:///{db_path}"
db = SQLDatabase.from_uri(db_uri)

# Test DB connection
engine = create_engine(db_uri)
inspector = inspect(engine)
table_names = inspector.get_table_names()
print(table_names)

try:
    table_names = db.get_usable_table_names()
    print("✅ DB connection successful. Tables found:", table_names)
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

# ----- Relevant Team Extraction Agent ----- #
def relevant_team_extraction_agent(state: dict) -> str:
    TEAM_LIST = [
        "UCDavis", "CalPolySLO", "CalStateBakersfield", "CalStateFullerton",
        "CalStateNorthridge", "LongBeachState", "UCIrvine", "UCRiverside",
        "UCSanDiego", "UCSantaBarbara", "UniversityOfHawaii", "Conference Average"
    ]

    prompt = (
        "You are a UC Davis Basketball analyst and scout. "
        "Given the following question, extract the relevant team name(s) from the question."
        "If no team is mentioned, assume the user is asking about UC Davis."
        "If only one team is mentioned, assume the other team is the conference average or UC Davis."
        f"Teams: {', '.join(TEAM_LIST)}\n\n"
        f"Question: {state.get('question')}\n\n"
        "Output format: [\"TEAM1\", \"TEAM2\"]"
    )

    response = llm.invoke(prompt)
    try:
        teams = json.loads(response.content)
        if isinstance(teams, list) and len(teams) == 2:
            return teams
    except Exception:
        pass
    return ["UCDavis", "Conference Average"]

# ---- Formatting Agent ----- #
def format_output(text: str) -> str:
    """
    Ask the LLM to best format the given text for clarity and presentation.
    """
    fmt_prompt = (
        "You are an expert content formatter. "
        "Please take the following answer and format it for clarity, readability, and presentation. "
        "Use headings, bullet points, or tables as appropriate. Don't use bold (***text***) or italics (___text___) or headings (### Heading).\n\n"
        f"Answer:\n{text}"
    )
    response = llm.invoke(fmt_prompt)
    log_with_time(f"[FormatOutput] Formatted answer generated.")
    return response.content

# ---- Query Agent (State Graph) ----- #
class QueryQuestionsOutput(TypedDict):
    questions: List[str]

def query_decision_agent(state: dict) -> QueryQuestionsOutput:
    prompt = (
        "You are a UC Davis Basketball analyst and scout. Your task is to determine which database queries will provide the most useful insights based on the user's input. \n\n"
        "- If the question is already a direct request for a single piece of data (for example: \"Who is the leading scorer on UC Davis?\"), just rephrase the question (if necessary).  \n"
        "- Keep in mind, per game stats are generally more useful than season totals."
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

# ---- Answer Generators ----- #
def generate_answer(state: dict) -> str:
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
    prompt = f"As a UC Davis Basketball analyst, answer the following question: {question}"
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
            raw = direct_answer(state["question"])
            formatted = format_output(raw)
            return {"response": formatted, "path": "direct"}
        elif cmd.goto == "db_query":
            query_spec = query_decision_agent(state)
            queries = query_spec.get("questions", [])
            system_msg = prompt_template.format(dialect="MySQL", top_k=5)
            agent = create_react_agent(llm, tools, prompt=system_msg)

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
        state = {"question": user_message, "relevant_stats": "", "result": "", "answer": ""}
        result = overarching_supervisor(state)
        answer = result["response"] if "response" in result else ""
        # Use your agent function here:
        relevant_teams = relevant_team_extraction_agent({"question": user_message})
        return jsonify({
            "response": answer,
            "relevant_teams": relevant_teams,
            "thread_id": str(uuid.uuid4())
        })
    except Exception as e:
        return jsonify({
            "error": "An error occurred while processing your request",
            "details": str(e)
        }), 500
