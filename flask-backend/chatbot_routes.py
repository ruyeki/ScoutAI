import os, json
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
from langchain.chains import ConversationChain
from langchain.chains.conversation.memory import ConversationBufferMemory
from langchain.chains.conversation.memory import ConversationSummaryMemory
from langchain_community.memory.kg import ConversationKGMemory
from langchain_community.graphs import NetworkxEntityGraph
from langchain.schema import HumanMessage

chatbot_bp = Blueprint("chatbot_bp1", __name__)
CORS(chatbot_bp)



load_dotenv()

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

engine = create_engine(db_uri)
inspector = inspect(engine)

table_names = inspector.get_table_names()
#print(table_names)

try:
    print("✅ DB connection successful. Tables found:", db.get_usable_table_names())
except Exception as e:
    print("❌ Failed to connect to DB:", str(e))

table_info = db.get_table_info()
prompt_template = hub.pull("langchain-ai/sql-agent-system-prompt")


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
    relevant_stats: str
    result: str
    answer: str
    chart: str
    retry: bool
    retry_count: int
    error: str
    relevant_stats: any
    memory: str


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

def is_chart_request(question: str) -> bool:
    keywords = ["chart", "graph", "plot", "bar", "line", "visualize", "draw"]
    return any(kw in question.lower() for kw in keywords)

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
        if cmd.goto == "direct_answer":
            raw = direct_answer(state["question"], state["memory"])
            formatted = format_output(raw)
            return {"response": formatted, "path": "direct"}
        elif cmd.goto == "db_query":
            query_spec = query_decision_agent(state, state["memory"])
            queries = query_spec.get("questions", [])
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
        data = request.json
        user_message = data.get("message")
        custom_memory.add_user_message(user_message)

        memory = custom_memory.get_context()

        print(memory)

        state: State = {"question": user_message, "relevant_stats": "", "result": "", "answer": "", "memory": memory}
        result = overarching_supervisor(state)

        custom_memory.add_ai_message(result["response"])

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
