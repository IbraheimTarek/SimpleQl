import pandas as pd
from pipeline.query_generator.CandidateGenerator import *
from plotter.Plotter import *
from pipeline.query_generator.ValidateQueries import UnitTester 
from pipeline.question_processing.schema_selector import *
from models import get_spacy_model, get_embedding_model
from database_manager import DBManager


def run_pipeline(question : str, db_manager : DBManager, fuzz_threshold=80, similarity_threshold=0.4):
    spacy_model = get_spacy_model()
    bert_model = get_embedding_model()
    schema = db_manager.schema
    embeddings = db_manager.embeddings
    selected_schema = select_schema(question, schema, embeddings, spacy_model, bert_model, fuzz_threshold=fuzz_threshold, similarity_threshold=similarity_threshold)
    candidates = []
    _, context = get_schema_and_context(db_manager.db_path)
    print("Extracted Schema:")
    print(selected_schema)
    print("\nExtracted Context:")
    print(context)

    res = run_candidate_generator(question, db_manager.db_path, selected_schema, 3)
    print("\n final candidates:")
    print(res)
    if res:
        for candidate_query, rows, error in res:
            candidates.append(candidate_query)

        print("\nCandidates:", candidates)
        tester = UnitTester(k_unit_tests=4)
        best_query = tester.choose_best((question), candidates)
        print("\nBest query after validation:", best_query)
        rows, columns, _ = execute_query_rows_columns(db_manager.db_path, best_query)

        df_result = pd.DataFrame(rows, columns=columns)
        print(df_result.head())

        return best_query, rows, columns
    else:
        # maybe return a type of error string
        return None
    
if __name__ == "__main__":

    question = "insert a new movie 'Inception' with rating 8.8 and release year 2010 into the database"
    db_path = "datasets/train/train_databases/movie_platform/movie_platform.sqlite"
    db_manager = DBManager(db_path)
    run_pipeline(question, db_manager)
    
    # viz_tool = DataVizTool(df_result)

    # img_path = viz_tool.run("Plot the distribution of ratings")

    # print("Saved chart to ", img_path)


    # if inside Streamlit:
    #st.image(img_path, caption="Auto-generated plot")