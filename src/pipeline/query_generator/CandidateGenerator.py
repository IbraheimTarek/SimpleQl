import sqlite3
from langchain_groq import ChatGroq
from langchain.prompts import PromptTemplate
import os
from dotenv import load_dotenv
import re
from typing import Dict
import time
from Params import *
from database_manager import DBManager
from pipeline.query_generator.Promots import *
from pipeline.question_processing.schema_selector import *

load_dotenv()
groq_api_key = os.getenv('GROQ_API_KEY')

FORBIDDEN_TOKENS = re.compile(
    r"\b("
    r"INSERT|UPDATE|DELETE|DROP|ALTER|TRUNCATE|CREATE|REPLACE|MERGE|"
    r"GRANT|REVOKE|PRAGMA|ATTACH|DETACH|EXEC|EXECUTE|CALL"
    r")\b",
    flags=re.I,
)

class CandidateGenerator:
    """
    CandidateGenerator (CG) synthesizes SQL queries to answer a natural language question.
    
    It uses two LLM tools:
      -> generate_candidate_query: Generate an initial SQL query given the question, schema, and context.
      -> revise_query: Revises the SQL query if execution produces an error or empty result or timeout. until it finds a working query or reaches the maximum number of revisions.
    """
    
    def __init__(self, llm, max_revisions=MAX_REVISIONS):
        self.llm = llm
        self.max_revisions = max_revisions

        # Prompt template for generating the candidate SQL query.
        self.gen_prompt = PromptTemplate(
            input_variables=["question", "schema", "context"],
            template=FIRST_PROMPT
        )

        # Prompt template for revising a faulty query.
        self.revise_prompt = PromptTemplate(
            input_variables=["question", "schema", "context", "faulty_query", "error_description"],
            template= REVISION_PROMPT
        )

        # LLMChains for generation and revision
        self.gen_chain = self.gen_prompt | self.llm
        self.revise_chain = self.revise_prompt | self.llm


    def generate_candidate_query(self, question, schema, context):
        response = self.gen_chain.invoke({
            "question": question,
            "schema": schema,
            "context": context
        })
        if hasattr(response, "content"):
            response = response.content
        # Clean the output to remove any markdown formatting or code fences
        response = clean_sql(response)
        return response

    def revise_query(self, question, schema, context, faulty_query, error_description):
        response = self.revise_chain.invoke({
            "question": question,
            "schema": schema,
            "context": context,
            "faulty_query": faulty_query,
            "error_description": error_description
        })
        if hasattr(response, "content"):
            response = response.content
        # Clean the output to remove any markdown formatting or code fences
        response = clean_sql(response)
        return response



def is_safe_select(sql: str) -> bool:
    """
    Return True iff `sql` appears to be a single read-only statement.
    Rules
    -----
    1. First non-comment token must be SELECT or WITH.
    2. No forbidden keywords (DML / DDL / admin) anywhere outside strings.
    3. At most one semicolon, and only as the final char (optional).
    """

    # strip leading comments / whitespace
    sql_no_comments = re.sub(r"--.*?$|/\*.*?\*/", "", sql, flags=re.S | re.M).strip()

    # first word
    first_word = re.match(r"^\s*(\w+)", sql_no_comments, flags=re.I)
    if not first_word or first_word.group(1).upper() not in {"SELECT", "WITH"}:
        return False

    #  forbidden tokens 
    if FORBIDDEN_TOKENS.search(sql_no_comments):
        return False

    parts = re.split(r";", sql_no_comments)
    if len(parts) > 2:                       # more than one semicolon
        return False
    if len(parts) == 2 and parts[1].strip(): # trailing text after last semicolon
        return False

    return True

def clean_sql(sql_str: str) -> str:

    fence = re.search(r"```(?:\w+)?\s*(.*?)\s*```", sql_str, flags=re.S)
    if fence:
        sql_str = fence.group(1)

    sql_str = re.sub(r"<think>.*?</think>", "", sql_str, flags=re.S | re.I)

    quote_map: Dict[int, str] = {
        0x2018: "'", 0x2019: "'", 0x201A: "'", 0x201B: "'",   # ‘ ’ ‚ ‛
        0x201C: '"', 0x201D: '"', 0x201E: '"', 0x201F: '"',   # “ ” „ ‟
        0x2032: "'", 0x2033: '"', 0x0060: "'",                # ′ ″ `
    }
    sql_str = sql_str.translate(quote_map)


    def _escape_in_literal(match: re.Match) -> str:
        """
        Receives a single-quoted literal (e.g.  'McDonald's')
        and doubles any *un-escaped* apostrophes inside it.
        Already-doubled quotes remain doubled.
        """
        literal = match.group(0)          # full match including outer quotes
        body = literal[1:-1]              # strip leading ands trailing quote

        sentinel = "\x00"                 # temp placeholder unlikely in text
        body = body.replace("''", sentinel)   # protect correctly-escaped ones
        body = body.replace("'", "''")        # escape the rest
        body = body.replace(sentinel, "''")   # restore originals man

        return f"'{body}'"

    sql_str = re.sub(r"'[^']*'", _escape_in_literal, sql_str, flags=re.S)

    return sql_str.strip()

def execute_query(db_path, query, timeout_sec: int = 10):

    conn = sqlite3.connect(db_path)
    try:
        start = time.time()

        # progress-handler gets invoked every 1000 ms (1 second) my guy
        def _watchdog():
            return 1 if time.time() - start > timeout_sec else 0

        conn.set_progress_handler(_watchdog, 1_000)

        cursor = conn.cursor()
        cursor.execute(query)
        results = cursor.fetchall()
        conn.commit()
        return results, None

    except sqlite3.OperationalError as e:
        # The handler aborts the query with "interrupted". and we catch it here.
        if "interrupted" in str(e).lower():
            return None, "timeout"
        return None, str(e)

    finally:
        conn.set_progress_handler(None, 0)   # clear handler so it doesn't linger
        conn.close()


def execute_query_rows_columns(db_path, query):
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    try:
        cursor.execute(query)
        rows    = cursor.fetchall()
        columns = [d[0] for d in cursor.description]  # NEW
        return rows, columns, None
    except Exception as e:
        return None, None, str(e)
    finally:
        conn.close()

def get_schema_and_context(db_path):
    """
    extract SQLite database's schema and generate their context.
    
    Returns:
      - schema: string with each table's name and its columns in the format: "table_name(col1 type, col2 type, ...)"
      - context: summary string listing tables.
    """
    conn = sqlite3.connect(db_path)
    schema_parts = []
    table_names = []
    
    try:
        cursor = conn.cursor()
        # Retrieve table names from the database
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%';")
        tables = cursor.fetchall()
        for table_tuple in tables:
            table_name = table_tuple[0]
            table_names.append(table_name)
            # Retrieve table info (columns and types)
            cursor.execute(f"PRAGMA table_info({table_name});")
            columns = cursor.fetchall()
            # Format each table's schema as: table_name(col1 type, col2 type, ...)
            col_defs = ", ".join([f"{col[1]} {col[2]}" for col in columns])
            schema_parts.append(f"{table_name}({col_defs})")
    except Exception as e:
        print("Error extracting schema:", e)
    finally:
        conn.close()
    
    schema_str = "; ".join(schema_parts)
    context_str = f"The database contains the following tables: {', '.join(table_names)}."
    return schema_str, context_str



def run_candidate_generator(question, db_path, schema, num_candidates=3):
    """
    generating multiple candidate queries....
    
    For each candidate:
      1. Extracts the schema and context from the database.
      2. Generates an initial candidate query.
      3. Executes it on the SQLite database.
      4. If a syntax error occurs or the result is empty, revises the query until a working query
         is found or the maximum number of revisions is reached.
    
    Returns:
      A list of tuples: (final_query, results, error) for each candidate query.
    """
    unsafe = False
    # 1
    _, context = get_schema_and_context(db_path)
    
    # 2
    llm = ChatGroq(groq_api_key=groq_api_key, model_name=CANDIDATE_MODEL, temperature=0)
    candidate_generator = CandidateGenerator(llm=llm)
    
    all_candidates = []
    
    for i in range(num_candidates):
        print(f"\n--- Processing candidate {i+1} ---")
        candidate_query = candidate_generator.generate_candidate_query(question, schema, context)
        print("Generated Candidate Query:")
        print(candidate_query)
        # 3
        if not is_safe_select(candidate_query):
            unsafe = True         # execution failed
            break

        results, error = execute_query(db_path, candidate_query)
        revision_count = 0
        # 4
        while (error is not None or (results is not None and len(results) == 0)) and revision_count < candidate_generator.max_revisions:
            issue_description = error if error is not None else "Empty result returned"
            # print("\nIssue encountered: ", issue_description)
            
            candidate_query = candidate_generator.revise_query(
                question=question,
                schema=schema,
                context=context,
                faulty_query=candidate_query,
                error_description=issue_description
            )
            # print(f"\nRevised Candidate Query (Attempt {revision_count + 1}):")
            # print(candidate_query)
            
            results, error = execute_query(db_path, candidate_query)
            revision_count += 1
        
        # print("\nFinal Query for candidate", i+1, ":")
        # print(candidate_query)
        # print("\nQuery Results:")
        # print(results)
        # done
        all_candidates.append((candidate_query, results, error))

    if unsafe:
        print("Unsafe query detected. Stopping further processing.")
        return all_candidates

    return all_candidates


if __name__ == "__main__":

    question = "What is the average rating score of the movie \"When Will I Be Loved\" and who was its director?"
    db_path = DB_PATH
    db_manager = DBManager(db_path)
    schema = db_manager.schema

    spacy_model = spacy.load("en_core_web_sm")
    bert_model = SentenceTransformer("all-MiniLM-L6-v2")
    print("loaded models mf")
    selected_schema = select_schema(question, schema, spacy_model, bert_model, fuzz_threshold=80, similarity_threshold=0.4)
    new_schema = {}
    for table in selected_schema:
        cols = []
        for col in selected_schema[table]:
            cols.append(col)
        new_schema[table] = cols
    
    _, context = get_schema_and_context(db_path)
    print("Extracted Schema:")
    print(new_schema)
    print("\nExtracted Context:")
    print(context)

    res = run_candidate_generator(question, db_path, new_schema, 3)
    print("\n final candidates:")
    print(res)