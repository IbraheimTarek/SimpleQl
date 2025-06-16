from langchain_groq import ChatGroq
import pandas as pd
from pipeline.query_generator.CandidateGenerator import *
from pipeline.plotter.Plotter import *
from pipeline.query_generator.ValidateQueries import UnitTester 
from database_manager import DBManager
from pipeline.question_processing.schema_selector import *


if __name__ == "__main__":

    question = "insert a new movie 'Inception' with rating 8.8 and release year 2010 into the database"
    db_path = "datasets/train/train_databases/movie_platform/movie_platform.sqlite"
    candidates = []
    db_manager = DBManager(db_path)
    schema = db_manager.schema
    spacy_model = spacy.load("en_core_web_sm")
    bert_model = SentenceTransformer("all-MiniLM-L6-v2")
    selected_schema = select_schema(question, schema, spacy_model, bert_model, fuzz_threshold=80, similarity_threshold=0.4)

    new_schema = {}
    for table in selected_schema:
        cols = []
        for col in selected_schema[table]:
            cols.append(col)
        new_schema[table] = cols

    new_schema, context = get_schema_and_context(db_path)
    print("Extracted Schema:")
    print(new_schema)
    print("\nExtracted Context:")
    print(context)

    res = run_candidate_generator(question, db_path, new_schema, 3)
    print("\n final candidates:")
    print(res)

    for candidate_query, rows, error in res:
        candidates.append(candidate_query)

    print("\nCandidates:", candidates)
    tester = UnitTester(k_unit_tests=4)
    best_query = tester.choose_best((question), candidates)
    print("\nBest query after validation:", best_query)
    rows, columns, _ = execute_query_rows_columns(db_path, best_query)

    df_result = pd.DataFrame(rows, columns=columns)
    print(df_result.head())


    # viz_tool = DataVizTool(df_result)

    # img_path = viz_tool.run("Plot the distribution of ratings")

    # print("Saved chart to ", img_path)


    # if inside Streamlit:
    #st.image(img_path, caption="Auto-generated plot")