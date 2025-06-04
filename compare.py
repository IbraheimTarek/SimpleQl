import os
import json
import sqlite3
from pathlib import Path
from dotenv import load_dotenv
from sqlalchemy import create_engine
from langchain.sql_database import SQLDatabase
from langchain.agents import create_sql_agent
from langchain.agents.agent_toolkits import SQLDatabaseToolkit
from langchain.agents.agent_types import AgentType
from langchain_groq import ChatGroq

# ------------------------------------------------------------------------------
# 1. Load environment variables (for GROQ_API_KEY).
# ------------------------------------------------------------------------------
load_dotenv()
groq_api_key = os.getenv('GROQ_API_KEY')
if not groq_api_key:
    raise ValueError("Please set GROQ_API_KEY in your environment variables.")

# ------------------------------------------------------------------------------
# 2. Configure the LLM (ChatGroq).
# ------------------------------------------------------------------------------
llm = ChatGroq(
    groq_api_key=groq_api_key,
    model_name="Llama3-8b-8192", 
    streaming=True  # Turn off streaming unless you specifically want output tokens in real-time
)

# ------------------------------------------------------------------------------
# 3. Function to configure/connect to the database (SQLite example shown).
#    Modify this or add MySQL logic as you see fit.
# ------------------------------------------------------------------------------
def configure_sqlite_db(db_path: str) -> SQLDatabase:
    """
    Configure a read/write or read-only SQLite database.
    In this example, we assume read-only by using the `?mode=ro` trick.
    If you need read/write, just remove `?mode=ro`.
    """
    if not Path(db_path).exists():
        raise ValueError(f"Invalid SQLite database path: {db_path}")
    creator = lambda: sqlite3.connect(f"file:{db_path}?mode=ro", uri=True)
    engine = create_engine("sqlite://", creator=creator)
    return SQLDatabase(engine)

# ------------------------------------------------------------------------------
# 4. Connect to the DB
#    Modify the path or switch to MySQL if needed.
# ------------------------------------------------------------------------------
DB_PATH = "datasets/train/train_databases/movie_platform/movie_platform.sqlite"  # <-- replace with your actual path
db = configure_sqlite_db(DB_PATH)

# ------------------------------------------------------------------------------
# 5. Create the LangChain agent that will generate SQL queries.
# ------------------------------------------------------------------------------
toolkit = SQLDatabaseToolkit(db=db, llm=llm)
agent = create_sql_agent(
    llm=llm,
    toolkit=toolkit,
    verbose=True,
    agent_type=AgentType.ZERO_SHOT_REACT_DESCRIPTION
)

# ------------------------------------------------------------------------------
# 6. Read your train.json data. Adjust the file path as needed.
# ------------------------------------------------------------------------------
TRAIN_JSON_PATH = "datasets/train/train.json"  # Replace with your own path
with open(TRAIN_JSON_PATH, "r", encoding="utf-8") as f:
    train_data = json.load(f)

# ------------------------------------------------------------------------------
# 7. Helper function to execute SQL and return results as a list of tuples.
# ------------------------------------------------------------------------------
def run_sql_query(sql_query: str, db_engine: SQLDatabase) -> list:
    """Execute the given SQL query and return a list of row tuples."""
    try:
        results = db_engine.run(sql_query)
        # `results` is often a list of tuples from the underlying DB driver.
        return results
    except Exception as e:
        print(f"[ERROR running SQL] {e}")
        return []

# ------------------------------------------------------------------------------
# 8. Main loop to:
#    - Prompt the LLM with the question to get generated SQL
#    - Execute that SQL, execute original (gold) SQL from the dataset
#    - Compare and track how often they match.
# ------------------------------------------------------------------------------
def main():
    total = 0
    matches = 0

    for item in train_data:
        question = item["question"]
        original_sql = item["SQL"]

        # a) Generate SQL via LangChain + ChatGroq
        try:
            # We instruct the agent with a prompt, e.g.:
            # "Generate SQL for this question without any additional text."
            # Or you can directly use `agent.run(question)`
            gen_sql = agent.run(question)
        except Exception as e:
            print(f"[ERROR generating SQL for question] {question}\n{e}")
            continue

        # b) Execute both queries
        generated_results = run_sql_query(gen_sql, db)
        original_results  = run_sql_query(original_sql, db)

        # c) Compare results
        #    For a simple approach, compare as sets of tuples (order-independent)
        generated_set = set(generated_results)
        original_set  = set(original_results)

        is_match = (generated_set == original_set)

        total += 1
        if is_match:
            matches += 1

        # d) Print each step's info
        print("Question:", question)
        print("Generated SQL:", gen_sql)
        print("Generated Results:", generated_results)
        print("Original SQL:", original_sql)
        print("Original Results:", original_results)
        print("Match:", is_match)
        print("-"*60)

    # e) Print final stats
    print(f"Final: {matches}/{total} answers matched.")

if __name__ == "__main__":
    main()
