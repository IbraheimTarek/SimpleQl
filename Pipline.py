from langchain_groq import ChatGroq
import pandas as pd
from CandidateGenerator import *
from Plotter import *
from ValidateQueries import UnitTester 


if __name__ == "__main__":

    question = "For movie titled 'Welcome to the Dollhouse', what is the percentage of the ratings were rated with highest score."
    db_path = "datasets/train/train_databases/movie_platform/movie_platform.sqlite"
    candidates = []
    schema, context = get_schema_and_context(db_path)
    print("Extracted Schema:", schema[:300], "...")

    res = run_candidate_generator(question, db_path, 3)
    print("\nFinal candidates:", res)

    for candidate_query, rows, error in res:
        candidates.append(candidate_query)

    print("\nCandidates:", candidates)
    tester = UnitTester(k_unit_tests=4)
    best_query = tester.choose_best((question), candidates)
    print("\nBest query after validation:", best_query)
    rows, columns, _ = execute_query_rows_columns(db_path, best_query)

    df_result = pd.DataFrame(rows, columns=columns)
    print(df_result.head())


    viz_tool = DataVizTool(df_result)

    img_path = viz_tool.run("Plot the distribution of ratings")

    print("Saved chart to ", img_path)


    # if inside Streamlit:
    #st.image(img_path, caption="Auto-generated plot")