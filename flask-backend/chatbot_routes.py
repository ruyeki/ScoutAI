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
from langchain_community.memory.kg import ConversationKGMemory
from langchain_community.graphs import NetworkxEntityGraph
from langchain.schema import HumanMessage

chatbot_bp = Blueprint("chatbot_bp1", __name__)
CORS(chatbot_bp)



load_dotenv()

def log_with_time(msg):
    now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    print(f"{msg} [Time: {now}]")

# ----- LLM and Database Setup ----- #
llm = ChatOpenAI(model="gpt-3.5-turbo", temperature=0.3)


'''
conversation = ConversationChain(llm=llm)
memory = ConversationSummaryMemory(llm=llm)

conversation_sum = ConversationChain(
    llm=llm,
    memory=ConversationSummaryMemory(llm=llm)
)
'''

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


#Create a custom memory buffer since Langchain Memory class doesnt work well
class customMemory: 
    def __init__(self): 
        self.memory = []
    
    def add_user_message(self, message:str): 
        self.memory.append({"actor": "human", "content": message})
    
    def add_ai_message(self, message:str): 
        self.memory.append({"actor": "ai", "content": message})
    
    def get_context(self, limit=10) -> str: 
        recent = self.memory[-limit:]
        return "\n".join([f"{m['actor'].upper()}: {m['content']}" for m in recent])

custom_memory = customMemory()

class State(TypedDict, total=False):
    question: str
    query: str
    result: str
    answer: str
    retry: bool
    retry_count: int
    error: str
    relevant_stats: any
    memory: str


# Load system prompt for SQL agent
prompt_template = hub.pull("langchain-ai/sql-agent-system-prompt")

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

def query_decision_agent(state: dict, memory: str = "") -> QueryQuestionsOutput:
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
        "- Treat pronouns like “I”, “me”, or “my” as references to the human user.\n"
        "- For example: if the user asks 'How many assists does he average?' and the memory says 'TY Johnson plays for UC Davis', then rephrase the question as 'How many assists does TY Johnson average?'\n"
        "– Make sure to consider both the AI's and the human's responses, not just the AI's. Understanding the full context of the conversation is important. \n"
        "- If there's no useful information in memory, proceed with the question as-is.\n\n"

        "Database usage:\n"
        "- If a player is not found in one table, try other relevant tables. For example, if you cannot find a certain player in UCDavis_player_stats, check other player stats tables like UCIrvine_player_stats. \n"

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

# ---- Answer Generators ----- #
def generate_answer(state: dict, memory: str = "") -> str:
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
    log_with_time(f"[GenerateAnswer] LLM generated answer: {response}")
    return response.content

def direct_answer(question: str, memory: str = "") -> str:
    prompt = (
        "You are a UC Davis Basketball analyst.\n\n"
        "Your task is to answer questions directly, using context from previous interactions (provided as 'Past context') to clarify references. "
        "If the user's question includes vague terms like 'that', 'those players', or refers to previous questions implicitly, resolve them using the memory.\n\n"
        "– Make sure to consider both the AI's and the human's responses, not just the AI's. Understanding the full context of the conversation is important. \n"
        "If the user is asking about a player's statistics (e.g., points, assists, rebounds, shooting percentage), route to db_query instead of answering directly — even if the player's name is only implied in the memory.\n\n"
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
            raw = direct_answer(state["question"], state["memory"])
            formatted = format_output(raw)
            return {"response": formatted, "path": "direct"}
        elif cmd.goto == "db_query":
            query_spec = query_decision_agent(state, state["memory"])
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
        custom_memory.add_user_message(user_message)

        memory = custom_memory.get_context()

        #print(memory)

        state: State = {"question": user_message, "relevant_stats": "", "result": "", "answer": "", "memory": memory}
        result = overarching_supervisor(state)

        custom_memory.add_ai_message(result["response"])

        final_answer = result["response"]

        result["thread_id"] = str(uuid.uuid4())
        return jsonify(result)
    except Exception as e:
        return jsonify({"error": "An error occurred while processing your request", "details": str(e)}), 500