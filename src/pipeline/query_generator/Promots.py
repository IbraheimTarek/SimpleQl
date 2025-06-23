FIRST_PROMPT = """
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
REVISION_PROMPT = """
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

VALIDATION_PROMPT = (
                "You are an expert SQL test engineer.  Devise "
                "**{k} independent unit tests** that will run on SQLite "
                "and separate correct from incorrect candidate queries. Each unit test should be designed in a way that it can distinguishes at lease two candidate responses from each other.\n\n"
                "Each unit-test **MUST** be a JSON object with the following "
                "keys:\n"
                "  . schema_sql   - DDL to create the schema.\n"
                "  . data_sql     - INSERTs that populate just enough rows to "
                "                   make wrong queries fail.\n"
                "  . expected     - The exact result set (array-of-rows, where "
                "                   each row is an array) the *correct* query "
                "                   should return.\n"
                "  . order_matters - Boolean; default false.\n\n"
                "Return the unit-tests as *one* top-level JSON array, nothing "
                "else.  Keep schemas minimal and data small."
            )