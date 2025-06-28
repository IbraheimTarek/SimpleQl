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
    
    def __init__(self, llm, max_revisions=MAX_REVISIONS):
        self.llm = llm
        self.max_revisions = max_revisions

        self.gen_prompt = PromptTemplate(
            input_variables=["question", "schema", "context"],
            template=FIRST_PROMPT
        )

        self.revise_prompt = PromptTemplate(
            input_variables=["question", "schema", "context", "faulty_query", "error_description"],
            template= REVISION_PROMPT
        )

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
        response = clean_sql(response)
        return response



def is_safe_select(sql: str) -> bool:


    sql_no_comments = re.sub(r"--.*?$|/\*.*?\*/", "", sql, flags=re.S | re.M).strip()

    first_word = re.match(r"^\s*(\w+)", sql_no_comments, flags=re.I)
    if not first_word or first_word.group(1).upper() not in {"SELECT", "WITH"}:
        return False

    if FORBIDDEN_TOKENS.search(sql_no_comments):
        return False

    parts = re.split(r";", sql_no_comments)
    if len(parts) > 2:
        return False
    if len(parts) == 2 and parts[1].strip():
        return False

    return True

def clean_sql(sql_str: str) -> str:

    fence = re.search(r"```(?:\w+)?\s*(.*?)\s*```", sql_str, flags=re.S)
    if fence:
        sql_str = fence.group(1)

    sql_str = re.sub(r"<think>.*?</think>", "", sql_str, flags=re.S | re.I)

    quote_map: Dict[int, str] = {
        0x2018: "'", 0x2019: "'", 0x201A: "'", 0x201B: "'",
        0x201C: '"', 0x201D: '"', 0x201E: '"', 0x201F: '"',
        0x2032: "'", 0x2033: '"', 0x0060: "'", 
    }
    sql_str = sql_str.translate(quote_map)


    def _escape_in_literal(match: re.Match) -> str:

        literal = match.group(0)          
        body = literal[1:-1]

        sentinel = "\x00"
        body = body.replace("''", sentinel)
        body = body.replace("'", "''")
        body = body.replace(sentinel, "''")

        return f"'{body}'"

    sql_str = re.sub(r"'[^']*'", _escape_in_literal, sql_str, flags=re.S)

    return sql_str.strip()

def execute_query(db_path, query, timeout_sec: int = 10):

    conn = sqlite3.connect(db_path)
    try:
        start = time.time()

        def _watchdog():
            return 1 if time.time() - start > timeout_sec else 0

        conn.set_progress_handler(_watchdog, 1_000)

        cursor = conn.cursor()
        cursor.execute(query)
        results = cursor.fetchall()
        conn.commit()
        return results, None

    except sqlite3.OperationalError as e:
        if "interrupted" in str(e).lower():
            return None, "timeout"
        return None, str(e)

    finally:
        conn.set_progress_handler(None, 0)  
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
    conn = sqlite3.connect(db_path)
    schema_parts = []
    table_names = []
    
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%';")
        tables = cursor.fetchall()
        for table_tuple in tables:
            table_name = table_tuple[0]
            table_names.append(table_name)
            cursor.execute(f"PRAGMA table_info({table_name});")
            columns = cursor.fetchall()
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

    _, context = get_schema_and_context(db_path)
    llm = ChatGroq(groq_api_key=groq_api_key, model_name=CANDIDATE_MODEL, temperature=0)
    candidate_generator = CandidateGenerator(llm=llm)
    
    all_candidates = []
    
    for i in range(num_candidates):
        candidate_query = candidate_generator.generate_candidate_query(question, schema, context)
        if not is_safe_select(candidate_query):
            break

        results, error = execute_query(db_path, candidate_query)
        revision_count = 0
        while (error is not None or (results is not None and len(results) == 0)) and revision_count < candidate_generator.max_revisions:
            issue_description = error if error is not None else "Empty result returned"
            
            candidate_query = candidate_generator.revise_query(
                question=question,
                schema=schema,
                context=context,
                faulty_query=candidate_query,
                error_description=issue_description
            )

            
            results, error = execute_query(db_path, candidate_query)
            revision_count += 1

        all_candidates.append((candidate_query, results, error))

    return all_candidates


    res = run_candidate_generator(question, db_path, new_schema, 3)
    print("\n final candidates:")
    print(res)