from langchain_groq import ChatGroq
import pandas as pd
from CandidateGenerator import *
from Plotter import *


if __name__ == "__main__":

    question = "Name the movie with the most ratings. What is its rating?"
    db_path = "datasets/train/train_databases/movie_platform/movie_platform.sqlite"
    schema, context = get_schema_and_context(db_path)
    print("Extracted Schema:", schema[:300], "...")

    res = run_candidate_generator(question, db_path, 3)
    print("\nFinal candidates:", res)

    best_query, rows, error = next( # choose the first candidate that has no error
        (q, r, e) for q, r, e in res if e is None
    )
    rows, columns, _ = execute_query_rows_columns(db_path, best_query)

    df_result = pd.DataFrame(rows, columns=columns)
    print(df_result.head())


    viz_tool = DataVizTool(df_result)

    img_path = viz_tool.run("Plot the distribution of ratings")

    print("Saved chart to ", img_path)
    # if inside Streamlit:
    #st.image(img_path, caption="Auto-generated plot")