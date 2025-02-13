import os
from dotenv import load_dotenv
from langchain_openai import ChatOpenAI
from langchain.chains import create_sql_query_chain
from langchain.prompts import PromptTemplate
from sqlalchemy import create_engine
from langchain_community.utilities import SQLDatabase

load_dotenv()

llm = ChatOpenAI(model_name="gpt-3.5-turbo", temperature=0.7)

# Set up database connection (Modify this based on your database)
db = SQLDatabase.from_uri("sqlite:///Chinook.db")
print(db.dialect)
print(db.get_usable_table_names())
db.run("SELECT * FROM Artist LIMIT 10;")


def query_database(user_question):
    """
    Uses LangChain's SQL query system to process a natural language question
    and return a database result.
    """
    try:
        response = sql_chain.invoke({"question": user_question})
        return response
    except Exception as e:
        return str(e)
