from pipeline.query_generator.CandidateGenerator import *
from plotter.Plotter import *
from plotter.schema_explorer import *
from pipeline.query_generator.ValidateQueries import UnitTester 
from pipeline.question_processing.schema_selector import *
from models import get_spacy_model, get_embedding_model
from database_manager import DBManager
from pipeline.translator.Translator import translate

def run_pipeline(question : str, db_manager : DBManager, fuzz_threshold=80, similarity_threshold=0):

    # Translate the question if in arabic
    question = translate(question)

    # Load pre-trained language models
    spacy_model = get_spacy_model()
    bert_model = get_embedding_model()

    schema = db_manager.schema
    embeddings = db_manager.embeddings

    # Select the schema related to the question
    selected_schema = select_schema(question, schema, embeddings, spacy_model, bert_model, fuzz_threshold=fuzz_threshold, similarity_threshold=similarity_threshold)

    # Genrate SQL queries
    res = run_candidate_generator(question, db_manager.db_path, selected_schema, 3)

    candidates = [
        query for query, rows_, err in res
        if err is None and rows_ and len(rows_) > 0
    ]

    if not candidates:
        raise Exception

    # Select the best SQL query
    if len(candidates) == 1:
        best_query = candidates[0]
    else:
        tester = UnitTester(k_unit_tests=4)
        best_query = tester.choose_best(question, candidates)

    rows, columns, _ = execute_query_rows_columns(db_manager.db_path, best_query)

    return best_query, rows, columns
