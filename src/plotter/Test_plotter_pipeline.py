import os
import pandas as pd
from langchain_groq import ChatGroq
from CandidateGenerator import *
from Plotter_v2_test import *
from ValidateQueries import UnitTester

# --------- Configuration ---------
DATASETS = {
    # "book_publishing_company": "Dataset\\train\\train\\train_databases\\train_databases\\book_publishing_company\\book_publishing_company.sqlite",
    # "computer_student": "Dataset\\train\\train\\train_databases\\train_databases\\computer_student\\computer_student.sqlite",
    # "university": "Dataset\\train\\train\\train_databases\\train_databases\\university\\university.sqlite",
}

QUERIES = {
    # "book_publishing_company": [
    #     "What are the total quantities ordered per book title?",
    #     "How many books were sold in each year?",
    #     "What is the average price of books by type?",
    #     "What is the count of employees in each job description?",
    #     "What is the average advance paid by each publisher?",
    #     "Which stores made the highest total sales quantities?",
    #     "What are the top 10 titles with the highest year-to-date sales?",
    #     "How many titles has each author written?",
    #     "What is the number of employees hired per year?",
    #     "What is the average discount per store?",
    #     "What are the quantities of each title sold in each store, along with the order date?",
    #     "What are the total sales quantities for each title grouped by store and order year?",
    #     "List all sales records with store name, book title, quantity, and pay terms.",
    #     "List all authors, their titles, and the royalty percentage they get.",
    #     "What are the titles, types, publishers, and prices of all books?"
    # ],

    # "computer_student": [
    #     "List all professors along with their position and years in the program.",
    #     "List students and their phase and years in the program.",
    #     "Which professor advises which student?",
    #     "Which professor teaches which course?",
    #     "List each student and whether they are advised by someone or not.",
    #     "What is the number of courses taught by each professor?",
    #     "Show all courses with their level and the professor who teaches them.",
    #     "List students along with the level of the course they are taught in.",
    # ],
    # "university": [
    #     "Show average student-staff ratio by country.",
    #     "Which ranking systems are used and how many criteria does each have?",
    #     "Show each university’s total number of ranking criteria scored in 2020.",
    # ],

}

# --------- Pipeline Runner ---------
def run_pipeline(question, db_path, dataset_name, query_index):
    print(f"\n--- Running: {dataset_name} Q{query_index + 1} ---")

    # Structure: Testing/database_name/Q1/
    base_folder = os.path.join("Testing", dataset_name)
    folder_name = os.path.join(base_folder, f"Q{query_index + 1}")
    os.makedirs(folder_name, exist_ok=True)

    candidates = []
    schema, context = get_schema_and_context(db_path)

    res = run_candidate_generator(question, db_path, 3)
    for candidate_query, rows, error in res:
        candidates.append(candidate_query)

    tester = UnitTester(k_unit_tests=4)
    best_query = tester.choose_best(question, candidates)

    rows, columns, _ = execute_query_rows_columns(db_path, best_query)
    df_result = pd.DataFrame(rows, columns=columns)

    # Save DataFrame
    df_path = os.path.join(folder_name, "result.csv")
    df_result.to_csv(df_path, index=False)
    print(f"Saved DataFrame to: {df_path}")

    # Plot
    viz_tool = DataVizToolTest(df_result)
    img_path = viz_tool.run({
    "pathX": folder_name,
    "request": f"Auto-Generated Plot for Q{query_index + 1}"
    })
    plot_path = os.path.join(folder_name, "plot.png")

    if os.path.exists(img_path):
        os.rename(img_path, plot_path)
        print(f"Saved plot to: {plot_path}")
    else:
        print("No plot image was generated.")

# --------- Main Loop ---------
if __name__ == "__main__":
    for dataset_name, query_list in QUERIES.items():
        db_path = DATASETS[dataset_name]
        for idx, query in enumerate(query_list):
            run_pipeline(query, db_path, dataset_name, idx+2)