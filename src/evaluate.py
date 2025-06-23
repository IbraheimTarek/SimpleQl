# Compare our CHESS-based pipeline against BIRD train answers.
import json, random, csv, argparse, collections, sys
from pathlib import Path
import pandas as pd

from Pipline import run_pipeline
from database_manager import DBManager
from pipeline.query_generator.CandidateGenerator import execute_query_rows_columns, execute_query   

DATASET_ROOT = Path("datasets/train")
TRAIN_JSON = DATASET_ROOT / "train.json"
DB_ROOT = DATASET_ROOT / "train_databases"
MAX_SAMPLES = 100          
SEED = 42

random.seed(SEED)


def uniform_sample(entries, k):
    """
    Pick =k examples, distributed as evenly as possible across db_ids.
    """
    buckets = collections.defaultdict(list)
    for e in entries:
        buckets[e["db_id"]].append(e)

    # shuffle
    for lst in buckets.values():
        random.shuffle(lst)

    selected = []
    while len(selected) < k and buckets:
        for db in list(buckets.keys()):
            if buckets[db]:
                selected.append(buckets[db].pop())
                if len(selected) == k:
                    break
            else:
                buckets.pop(db)   # empty bucket
    return selected


def rows_to_multiset(rows):
    """Return a Counter of rows converted to hashable tuples."""
    return collections.Counter(tuple(r) for r in (rows or []))


def evaluate(max_samples=MAX_SAMPLES, csv_out="mismatches.csv"):
    # ---------- load dataset ---------------------------------
    with open(TRAIN_JSON, encoding="utf-8") as f:
        dataset = json.load(f)

    samples = uniform_sample(dataset, max_samples)
    print(f"Running evaluation on {len(samples)} samples (≤{MAX_SAMPLES}).\n")

    # ---------- main loop ------------------------------------
    good, bad = 0, 0
    mismatch_rows = []

    for idx, item in enumerate(samples, 1):
        db_id    = item["db_id"]
        question = item["question"]
        gt_sql   = item["SQL"]

        db_path = DB_ROOT / db_id / f"{db_id}.sqlite"
        if not db_path.exists():
            print(f"[{idx:03}] ❌  DB file not found for {db_id}; skipping.")
            bad += 1
            continue

        dbm = DBManager(str(db_path))

        try:
            # ---- our pipeline ----------------------------------
            pred_sql, pred_rows, pred_cols = run_pipeline(question, dbm)
        except Exception as e:   # hard failure inside pipeline
            print(f"[{idx:03}] ❌  Pipeline crashed: {e}")
            bad += 1
            mismatch_rows.append(
                (db_id, question, "pipeline-crash", str(e))
            )
            continue

        # pipeline returned None -> skip
        if pred_rows is None:
            print(f"[{idx:03}] ❌  Pipeline produced no answer.")
            bad += 1
            mismatch_rows.append(
                (db_id, question, "pipeline-empty", "")
            )
            continue

        # ---- ground-truth execution --------------------------
        gt_rows, gt_cols, err = execute_query_rows_columns(str(db_path), gt_sql)
        if err:
            print(f"[{idx:03}] ⚠️  GT SQL failed ({err}); skipping.")
            continue  # not counted

        # ---- compare ----------------------------------------
        print(f"the rows of each output: pipeline {rows_to_multiset(pred_rows)}, true {rows_to_multiset(gt_rows)}")

        correct = rows_to_multiset(pred_rows) == rows_to_multiset(gt_rows)

        tag = "✓" if correct else "X"
        print(f"[{idx:03}] {tag}  {question[:60]}")

        if correct:
            good += 1
        else:
            bad += 1
            mismatch_rows.append(
                (
                    db_id,
                    question,
                    pred_sql,
                    gt_sql,
                    pd.DataFrame(pred_rows, columns=pred_cols).to_json(orient="records"),
                    pd.DataFrame(gt_rows,   columns=gt_cols).to_json(orient="records"),
                )
            )

    # ---------- report --------------------------------------
    total = good + bad
    accuracy = good / total if total else 0.0
    print("\n-----------------------------")
    print(f"Correct : {good}")
    print(f"Wrong   : {bad}")
    print(f"Accuracy: {accuracy:.2%}")
    print("-----------------------------\n")

    # ---------- mismatches CSV ------------------------------
    if mismatch_rows:
        header = [
            "db_id",
            "question",
            "pred_sql",
            "gt_sql",
            "pred_rows",
            "gt_rows",
        ]
        with open(csv_out, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow(header)
            writer.writerows(mismatch_rows)
        print(f"Mismatches written to {csv_out}")


if __name__ == "__main__":
## reading the arguments from the command line
    parser = argparse.ArgumentParser(description="Evaluate CHESS pipeline on BIRD subset.")
    parser.add_argument("--k", type=int, default=MAX_SAMPLES, help="number of questions to sample (<=100)")
    parser.add_argument("--out", default="mismatches.csv", help="CSV path for mismatched answers")
    args = parser.parse_args()
##to run this file
##python evaluate_pipeline.py                        # 100 samples
##python evaluate_pipeline.py --k 60 --out diff.csv  # custom
    evaluate(max_samples=min(args.k, MAX_SAMPLES), csv_out=args.out)
