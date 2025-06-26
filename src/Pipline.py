import pandas as pd
from pipeline.query_generator.CandidateGenerator import *
from plotter.Plotter import *
from plotter.schema_explorer import *
from pipeline.query_generator.ValidateQueries import UnitTester 
from pipeline.question_processing.schema_selector import *
from models import get_spacy_model, get_embedding_model
from database_manager import DBManager
from src.pipeline.translator import translate

def run_pipeline(question : str, db_manager : DBManager, fuzz_threshold=80, similarity_threshold=0):
    spacy_model = get_spacy_model()
    bert_model = get_embedding_model()
    schema = db_manager.schema
    embeddings = db_manager.embeddings
    selected_schema = select_schema(question, schema, embeddings, spacy_model, bert_model, fuzz_threshold=fuzz_threshold, similarity_threshold=similarity_threshold)
    candidates = []
    _, context = get_schema_and_context(db_manager.db_path)
    # print("Extracted Schema:")
    # print(selected_schema)
    # print("\nExtracted Context:")
    # print(context)

    res = run_candidate_generator(question, db_manager.db_path, selected_schema, 3)
    # print("\nFinal candidates:")
    # print(res)

    # keep only candidates that returned non-empty results & no error
    candidates = [
        query for query, rows_, err in res
        if err is None and rows_ and len(rows_) > 0
    ]

    print("\nAccepted (non-empty) candidates:", candidates)

    if not candidates:                       # nothing usable
        return None, None,None                          # or raise/custom-handle

    # choose the best query
    if len(candidates) == 1:
        best_query = candidates[0]
    else:
        tester = UnitTester(k_unit_tests=4)
        best_query = tester.choose_best(question, candidates)

    print("\nBest query after validation:", best_query)

    # execute the winner to get rows & columns
    rows, columns, _ = execute_query_rows_columns(db_manager.db_path, best_query)

    return best_query, rows, columns

    
if __name__ == "__main__":

    question = translate("ما هو العنوان الكامل للمطعم المسمى 'sanuki restraunt' ؟")
    db_path = DB_PATH
    db_manager = DBManager(db_path)
    schema_explorer = SchemaExplorer(db_manager)
    print("key tuples:", db_manager.foreign_keys)
    schema_explorer.run()
    _, rows, columns = run_pipeline(question, db_manager)

    if rows is None:
        print("No results found for the question.")
        exit(0)
    df_result = pd.DataFrame(rows, columns=columns)
    viz_tool = DataVizTool(df_result)
    result = viz_tool.run("Plot automatically")
    print(result)