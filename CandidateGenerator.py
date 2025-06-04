import sqlite3
from langchain_groq import ChatGroq
from langchain.prompts import PromptTemplate
import os
from dotenv import load_dotenv
import re
load_dotenv()
groq_api_key = os.getenv('GROQ_API_KEY')

class CandidateGenerator:
    """
    CandidateGenerator (CG) synthesizes SQL queries to answer a natural language question.
    
    It uses two LLM-based tools:
      - generate_candidate_query: Generates an initial SQL query given the question, schema, and context.
      - revise_query: Revises the SQL query if execution produces an error or empty result.
    """
    
    def __init__(self, llm, max_revisions=3):
        self.llm = llm
        self.max_revisions = max_revisions

        # Prompt template for generating the candidate SQL query.
        self.gen_prompt = PromptTemplate(
            input_variables=["question", "schema", "context"],
            template="""
You are an expert SQL developer. Given the following inputs, generate a SQL query that answers the question.
Before generating the SQL query, carefully analyze the question to determine whether it refers to a single entity or multiple entities.
- If the question indicates a single entity (using terms like "the", "one", "first", "single", etc.), ensure the query is limited to return one record (for example, by including 'LIMIT 1').
- If the question refers to multiple or all entities, do not include a limiting clause unless explicitly requested.
Do not include any explanation or text besides the SQL code.

Question: {question}
Schema: {schema}
Context: {context}

Please provide only the SQL query.
"""
        )

        # Prompt template for revising a faulty query.
        self.revise_prompt = PromptTemplate(
            input_variables=["question", "schema", "context", "faulty_query", "error_description"],
            template="""
The previously generated SQL query produced the following error:
Error: {error_description}

Faulty Query:
{faulty_query}

Before revising, carefully analyze the question to determine whether it refers to a single entity or multiple entities.
- If the question indicates a single entity (using terms like "the", "one", "first", "single", etc.), ensure the revised query is limited to one record (e.g., by including 'LIMIT 1').
- If the question refers to multiple or all entities, do not include a limiting clause unless explicitly requested.

Given the Question: {question}
Schema: {schema}
Context: {context}

Please revise the SQL query to fix the error and correctly answer the question.
Return only the revised SQL query.
"""
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



def clean_sql(sql_str: str) -> str:
    """
    Removes markdown code fences (e.g., ```sql ... ```) and any <think>...</think> blocks from the LLM output.
    """
    sql_str = sql_str.strip()
    # Remove markdown code fences
    if sql_str.startswith("```sql") and sql_str.endswith("```"):
        lines = sql_str.splitlines()
        if lines[0].startswith("```"):
            lines = lines[1:]
        if lines and lines[-1].endswith("```"):
            lines = lines[:-1]
        sql_str = "\n".join(lines).strip()
    # Remove <think>...</think> blocks
    sql_str = re.sub(r"<think>.*?</think>", "", sql_str, flags=re.DOTALL).strip()
    #print("Cleaned query: ",sql_str)
    return sql_str


def execute_query(db_path, query):

    conn = sqlite3.connect(db_path)
    try:
        cursor = conn.cursor()
        cursor.execute(query)
        results = cursor.fetchall()
        conn.commit()
        return results, None
    except Exception as e:
        return None, str(e)
    finally:
        conn.close()


def execute_query_rows_columns(db_path, query):
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    try:
        cursor.execute(query)
        rows    = cursor.fetchall()
        columns = [d[0] for d in cursor.description]  # ← NEW
        return rows, columns, None
    except Exception as e:
        return None, None, str(e)
    finally:
        conn.close()

def get_schema_and_context(db_path):
    """
    Introspects the SQLite database to extract the schema and generate context.
    
    Returns:
      - schema: A string with each table's name and its columns in the format:
                "table_name(col1 type, col2 type, ...)"
      - context: A summary string listing the available tables.
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

def run_candidate_generator(question, db_path):
    """
    candidate query generation and revision process.
    
    It first extracts the schema and context from the database, then:
      1. Generates an initial candidate query.
      2. Executes it on the SQLite database.
      3. If a syntax error occurs or the result is empty, revises the query.
      4. Repeats until a working query is found or the maximum number of revisions is reached.
    """
    # Extract schema and context from the SQLite DB.
    schema, context = get_schema_and_context(db_path)
    
    # Initialize the LLM. Here we use ChatOpenAI with temperature=0 for deterministic outputs.
    llm = ChatGroq(groq_api_key=groq_api_key, model_name="deepseek-r1-distill-llama-70b",temperature=0) 
    candidate_generator = CandidateGenerator(llm=llm)

    candidate_query = candidate_generator.generate_candidate_query(question, schema, context)
    print("Generated Candidate Query:")
    print(candidate_query)
    
    results, error = execute_query(db_path, candidate_query)
    revision_count = 0

    # Loop until the query executes successfully (non-error and non-empty result)
    while (error is not None or (results is not None and len(results) == 0)) and revision_count < candidate_generator.max_revisions:
        issue_description = error if error is not None else "Empty result returned"
        print("\nIssue encountered: ", issue_description)
        
        candidate_query = candidate_generator.revise_query(
            question=question,
            schema=schema,
            context=context,
            faulty_query=candidate_query,
            error_description=issue_description
        )
        print("\nRevised Candidate Query (Attempt {}):".format(revision_count + 1))
        print(candidate_query)
        
        results, error = execute_query(db_path, candidate_query)
        revision_count += 1

    print("\nFinal Query:")
    print(candidate_query)
    print("\nQuery Results:")
    print(results)


def run_candidate_generator(question, db_path, num_candidates=3):
    """
    Orchestrates the generation of multiple candidate queries.
    
    For each candidate:
      1. Extracts the schema and context from the database.
      2. Generates an initial candidate query.
      3. Executes it on the SQLite database.
      4. If a syntax error occurs or the result is empty, revises the query until a working query
         is found or the maximum number of revisions is reached.
    
    Returns:
      A list of tuples: (final_query, results, error) for each candidate query.
    """
    # Extract schema and context from the SQLite DB.
    schema, context = get_schema_and_context(db_path)
    
    # Initialize the LLM (ChatGroq in this case).
    llm = ChatGroq(groq_api_key=groq_api_key, model_name="deepseek-r1-distill-llama-70b", temperature=0)
    candidate_generator = CandidateGenerator(llm=llm)
    
    all_candidates = []
    
    for i in range(num_candidates):
        print(f"\n--- Processing candidate {i+1} ---")
        candidate_query = candidate_generator.generate_candidate_query(question, schema, context)
        print("Generated Candidate Query:")
        print(candidate_query)
        
        results, error = execute_query(db_path, candidate_query)
        revision_count = 0
        
        while (error is not None or (results is not None and len(results) == 0)) and revision_count < candidate_generator.max_revisions:
            issue_description = error if error is not None else "Empty result returned"
            print("\nIssue encountered: ", issue_description)
            
            candidate_query = candidate_generator.revise_query(
                question=question,
                schema=schema,
                context=context,
                faulty_query=candidate_query,
                error_description=issue_description
            )
            print(f"\nRevised Candidate Query (Attempt {revision_count + 1}):")
            print(candidate_query)
            
            results, error = execute_query(db_path, candidate_query)
            revision_count += 1
        
        print("\nFinal Query for candidate", i+1, ":")
        print(candidate_query)
        print("\nQuery Results:")
        print(results)
        
        all_candidates.append((candidate_query, results, error))
    
    return all_candidates


if __name__ == "__main__":

    question = "What is the average rating for movie titled 'When Will I Be Loved'?"
    db_path = "datasets/train/train_databases/movie_platform/movie_platform.sqlite"
    schema, context = get_schema_and_context(db_path)
    print("Extracted Schema:")
    print(schema)
    print("\nExtracted Context:")
    print(context)

    res = run_candidate_generator(question, db_path, 3)
    print("\n final candidates:")
    print(res)