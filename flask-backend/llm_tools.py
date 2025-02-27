import os
from dotenv import load_dotenv
from langchain_openai import ChatOpenAI
from langchain_community.utilities import SQLDatabase
from typing_extensions import TypedDict
from langchain import hub
from typing_extensions import Annotated
from langchain_community.tools.sql_database.tool import QuerySQLDatabaseTool
from langgraph.graph import START, StateGraph
from langchain_community.agent_toolkits import SQLDatabaseToolkit
from langgraph.prebuilt import create_react_agent

load_dotenv()

db_username = os.getenv('DB_USERNAME') # admin
db_password = os.getenv('DB_PASSWORD') # asabasketball
db_name = os.getenv('DB_NAME') # game_stats
db_host = os.getenv('DB_HOST') # ucd-basketball.cduqug2e0o83.us-east-2.rds.amazonaws.com

llm = ChatOpenAI(model_name="gpt-3.5-turbo", temperature=0.7)

# Set up database connection using environment variables
db_uri = f"mysql+mysqlconnector://admin:asabasketball@ucd-basketball.cduqug2e0o83.us-east-2.rds.amazonaws.com/game_stats"
#db_uri = f"mysql+mysqlconnector://{db_username}:{db_password}@{db_host}/{db_name}"
db = SQLDatabase.from_uri(db_uri)
# print(db.dialect)
# print(db.get_usable_table_names())
# db.run("SELECT * FROM Artist LIMIT 10;")
toolkit = SQLDatabaseToolkit(db=db, llm=llm)
tools = toolkit.get_tools()

class State(TypedDict):
    question: str
    query: str
    result: str
    answer: str

query_prompt_template = hub.pull("langchain-ai/sql-query-system-prompt")


assert len(query_prompt_template.messages) == 1
query_prompt_template.messages[0].pretty_print()


class QueryOutput(TypedDict):
    """Generated SQL query."""

    query: Annotated[str, ..., "Syntactically valid SQL query."]


def write_query(state: State):
    """Generate SQL query to fetch information."""
    table_info = db.get_table_info()
    prompt = query_prompt_template.invoke(
        {
            "dialect": db.dialect,
            "top_k": 10,
            "table_info": table_info,
            "input": state["question"],
        }
    )
    structured_llm = llm.with_structured_output(QueryOutput, method="function_calling")
    result = structured_llm.invoke(prompt)
    return {"query": result["query"]}

# print(write_query({"question": "How many Employees are there?"}))

def execute_query(state: State):
    """Execute SQL query."""
    execute_query_tool = QuerySQLDatabaseTool(db=db)
    return {"result": execute_query_tool.invoke(state["query"])}

# print(execute_query({"query": "SELECT COUNT(EmployeeId) AS EmployeeCount FROM Employee;"}))

def generate_answer(state: State):
    """Answer question using retrieved information as context."""
    prompt = (
        "Given the following user question, corresponding SQL query, "
        "and SQL result, answer the user question.\n\n"
        f'Question: {state["question"]}\n'
        f'SQL Query: {state["query"]}\n'
        f'SQL Result: {state["result"]}'
    )
    response = llm.invoke(prompt)
    return {"answer": response.content}

graph_builder = StateGraph(State).add_sequence(
    [write_query, execute_query, generate_answer]
)

graph_builder.add_edge(START, "write_query")
graph = graph_builder.compile()

for step in graph.stream(
    {"question": "How many players on the ucsb men's basketball team are there?"}, stream_mode="updates"
):
    print(step)


# question = "Who's the leading scorer on UC Santa Barbara, and how many points?"

# system_message = query_prompt_template.format(dialect="MySQL", top_k=5, table_info=db.get_table_info(), input=question)

# agent_executor = create_react_agent(llm, tools, prompt=system_message)

# for step in agent_executor.stream(
#     {"messages": [{"role": "user", "content": question}]},
#     stream_mode="values",
# ):
#     step["messages"][-1].pretty_print()