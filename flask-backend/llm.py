import datetime, os
from langchain_experimental.sql import SQLDatabaseChain
from langchain.agents import Tool
from langchain_openai import ChatOpenAI
from langchain_community.utilities import SQLDatabase
from langchain import hub
from dotenv import load_dotenv
from typing import Annotated
from typing_extensions import TypedDict
from langgraph.graph import StateGraph, START, END
from langgraph.graph.message import add_messages, AnyMessage
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.runnables import Runnable, RunnableConfig
from langchain_community.agent_toolkits import SQLDatabaseToolkit
from langchain_core.runnables import RunnableLambda
from langgraph.prebuilt import ToolNode
from langchain_core.messages import ToolMessage
from langgraph.prebuilt import tools_condition
from langgraph.checkpoint.memory import InMemorySaver
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage

load_dotenv()

db_username = os.getenv('DB_USERNAME') # admin
db_password = os.getenv('DB_PASSWORD') # asabasketball
db_name = os.getenv('DB_NAME') # game_stats
db_host = os.getenv('DB_HOST') # ucd-basketball.cduqug2e0o83.us-east-2.rds.amazonaws.com

class State(TypedDict):
    # Messages have the type "list". The `add_messages` function
    # in the annotation defines how this state key should be updated
    # (in this case, it appends messages to the list, rather than overwriting them)
    messages: Annotated[list[AnyMessage], add_messages]

class Assistant:
    def __init__(self, runnable: Runnable):
        self.runnable = runnable

    def __call__(self, state: State, config: RunnableConfig):
        try:
            # Get the last message content
            last_message = state["messages"][-1]
            message_content = (
                last_message.content 
                if isinstance(last_message, (HumanMessage, AIMessage, SystemMessage)) 
                else last_message["content"]
            )

            # Format conversation history
            chat_history = "\n".join([
                f"{m.type if hasattr(m, 'type') else m['role']}: {m.content if hasattr(m, 'content') else m['content']}"
                for m in state["messages"][:-1]  # Exclude current message
            ]) if len(state["messages"]) > 1 else ""

            # Prepare input state with history
            input_state = {
                "input": message_content,
                "context": {
                    "domain": "basketball",
                    "team": "UC Davis",
                    "league": "Big West Conference",
                    "chat_history": chat_history  # Add conversation history
                }
            }

            # Get response from LLM
            result = self.runnable.invoke(input_state)

            # First-time greeting
            if not chat_history and (not hasattr(result, 'content') or not result.content):
                return {
                    "messages": [AIMessage(
                        content="Hello! I'm the UC Davis Basketball Analytics Assistant. "
                               "I can help you with player statistics, team performance, and game analysis. "
                               "What would you like to know?"
                    )]
                }

            # Handle tool calls for database queries
            if hasattr(result, 'tool_calls') and result.tool_calls:
                return {
                    "messages": [AIMessage(content=result.content)],
                    "tool_calls": result.tool_calls,
                    "next": "continue"
                }

            # Return normal response with context
            return {
                "messages": [AIMessage(
                    content=str(result.content) + (
                        "\n\nIs there anything specific you'd like to know about these statistics?" 
                        if "statistics" in str(result.content).lower() else ""
                    )
                )]
            }

        except Exception as e:
            print(f"Error in assistant: {str(e)}")
            return {
                "messages": [AIMessage(
                    content="I encountered an error while processing your request. "
                           "Could you please rephrase your question about UC Davis basketball?"
                )]
            }

def create_tool_node_with_fallback(tools: list) -> dict:
    return ToolNode(tools).with_fallbacks(
        [RunnableLambda(handle_tool_error)], exception_key="error"
    )
        
def handle_tool_error(state) -> dict:
    error = state.get("error")
    tool_calls = state["messages"][-1].tool_calls
    return {
        "messages": [
            ToolMessage(
                content=f"Error: {repr(error)}\n please fix your mistakes.",
                tool_call_id=tc["id"],
            )
            for tc in tool_calls
        ]
    }

def create_basketball_graph(llm, tools, primary_assistant_prompt):
    """Create the graph with proper edge handling"""
    builder = StateGraph(State)
    
    # Create nodes
    assistant = Assistant(primary_assistant_prompt | llm.bind_tools(tools))
    tool_node = create_tool_node_with_fallback(tools)
    
    # Add nodes
    builder.add_node("assistant", assistant)
    builder.add_node("tools", tool_node)
    
    # Add edges with custom router
    def router(state):
        if state.get("next") == "continue":
            return "continue"
        return "end"
    
    builder.add_edge(START, "assistant")
    builder.add_conditional_edges(
        "assistant",
        router,
        {
            "continue": "tools",
            "end": END
        }
    )
    builder.add_edge("tools", "assistant")
    
    return builder.compile()

class Chatbot:
    def __init__(self):
        self.llm = ChatOpenAI(model="gpt-3.5-turbo", temperature=0)
        
        # Create database connection
        #db_uri = f"mysql+mysqlconnector://{db_username}:{db_password}@{db_host}/{db_name}"
        #self.db = SQLDatabase.from_uri(db_uri)

        #NEW SQLITE DATABASE CONNECTION
        base_dir = os.path.abspath(os.path.dirname(__file__))
        db_path = os.path.join(base_dir, "ucd-basketball.db")
        db_uri = f"sqlite:///{db_path}"
        self.db = SQLDatabase.from_uri(db_uri)
        
        # Set up tools
        toolkit = SQLDatabaseToolkit(db=self.db, llm=self.llm)
        tools = toolkit.get_tools()
        
        # Create enhanced prompt
        primary_assistant_prompt = ChatPromptTemplate.from_messages([
            ("system", """You are a UC Davis Basketball Analytics Assistant specialized in:
                - Player statistics and performance analysis
                - Team comparisons and historical data
                - Game results and trends
                - Big West Conference insights
                
                Previous conversation:
                {context[chat_history]}
                
                Current context:
                Team: {context[team]}
                League: {context[league]}
                
                Provide specific statistical analysis when available.
                """),
            ("human", "{input}")
        ])
        
        # Initialize graph and memory
        self.memory = {}
        self.graph = create_basketball_graph(self.llm, tools, primary_assistant_prompt)

    def get_context(self, thread_id: str) -> list:
        """Get conversation context for a specific thread."""
        return self.memory.get(thread_id, [])

    def save_context(self, thread_id: str, messages: list):
        """Save conversation context for a thread."""
        self.memory[thread_id] = messages




