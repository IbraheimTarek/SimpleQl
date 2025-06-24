# Compare our CHESS-based pipeline against BIRD train answers.
import json, random, csv, argparse, collections, sys
from pathlib import Path
import pandas as pd
import time, itertools
from datetime import datetime
from Params import *
from Pipline import run_pipeline
from database_manager import DBManager
from pipeline.query_generator.CandidateGenerator import execute_query_rows_columns, execute_query   

DATASET_ROOT = Path("datasets/train")
TRAIN_JSON = DATASET_ROOT / "train.json"
DB_ROOT = DATASET_ROOT / "train_databases"
REPORT_ROOT = Path("reports")
CSV_OUT= REPORT_ROOT/"mismatches.csv"

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

def set_f1(pred_rows, gt_rows):
    """Return precision, recall, f1 for one sample (set-based)."""
    pred_set, gt_set = set(pred_rows), set(gt_rows)
    tp = len(pred_set & gt_set)
    prec = tp / len(pred_set) if pred_set else 0.0
    rec  = tp / len(gt_set)   if gt_set   else 0.0
    f1   = 2*prec*rec/(prec+rec) if prec+rec else 0.0
    return prec, rec, f1

def count_tokens(text: str) -> int:
    return len(text.split())

def next_metrics_path(base= REPORT_ROOT/ "metrics.txt") -> Path:
    p = Path(base)
    if not p.exists():
        return p
    stem, suf = p.stem, p.suffix
    for i in itertools.count(1):
        alt = p.with_name(f"{stem}_{i}{suf}")
        if not alt.exists():
            return alt

def rows_to_multiset(rows):
    """Return a Counter of rows converted to hashable tuples."""
    return collections.Counter(tuple(r) for r in (rows or []))


def evaluate(max_samples=MAX_SAMPLES):
    # ---------- load dataset ---------------------------------
    with open(TRAIN_JSON, encoding="utf-8") as f:
        dataset = json.load(f)

    samples = uniform_sample(dataset, max_samples)
    print(f"Running evaluation on {len(samples)} samples (≤{MAX_SAMPLES}).\n")

    # ---------- main loop ------------------------------------
    good, bad = 0, 0
    mismatch_rows = []
    latencies = []
    f1_scores = []
    token_costs = []

    tp_sum = pred_total = gt_total = 0

    for idx, item in enumerate(samples, 1):
        db_id    = item["db_id"]
        question = item["question"]
        gt_sql   = item["SQL"]

        db_path = DB_ROOT / db_id / f"{db_id}.sqlite"

        
        if not db_path.exists():
            print(f"[{idx:03}] X DB file not found for {db_id}; skipping.")
            bad += 1
            continue

        dbm = DBManager(str(db_path))

        try:
            # our pipeline
            start_time = time.perf_counter()
            pred_sql, pred_rows, pred_cols = run_pipeline(question, dbm, similarity_threshold=0)
            latencies.append(time.perf_counter() - start_time)
            token_costs.append(count_tokens(pred_sql or "")) 

        except Exception as e:   # hard failure inside pipeline
            print(f"[{idx:03}] X Pipeline crashed: {e}")
            bad += 1
            mismatch_rows.append(
                (db_id, question, "pipeline-crash", str(e))
            )
            continue

        # pipeline returned None -> skip
        if pred_rows is None:
            print(f"[{idx:03}] X Pipeline produced no answer.")
            bad += 1
            mismatch_rows.append(
                (db_id, question, "pipeline-empty", "")
            )
            continue

        # ---- ground-truth execution --------------------------
        gt_rows, gt_cols, err = execute_query_rows_columns(str(db_path), gt_sql)
        if err:
            print(f"[{idx:03}] ! GT SQL failed ({err}); skipping.")
            continue  # not counted

        # compare 
        # F1 for this sample
        prec, rec, f1 = set_f1(pred_rows, gt_rows)
        f1_scores.append(f1)

        # accumulate for micro
        tp_sum += len(set(pred_rows) & set(gt_rows))
        pred_total += len(set(pred_rows))
        gt_total += len(set(gt_rows))

        print(f"{db_id} the rows of each output: pipeline {rows_to_multiset(pred_rows)}, true {rows_to_multiset(gt_rows)}")

        correct = rows_to_multiset(pred_rows) == rows_to_multiset(gt_rows)

        tag = "/" if correct else "X"
        print(f"[{idx:03}] {tag}  {question[:]}")

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

    macro_f1 = sum(f1_scores) / len(f1_scores) if f1_scores else 0.0
    micro_prec = tp_sum / pred_total if pred_total else 0.0
    micro_rec  = tp_sum / gt_total   if gt_total   else 0.0
    micro_f1   = 2*micro_prec*micro_rec/(micro_prec+micro_rec) if micro_prec+micro_rec else 0.0

    avg_latency = sum(latencies)/len(latencies) if latencies else 0.0
    avg_tokens  = sum(token_costs)/len(token_costs) if token_costs else 0.0

    print("\n-----------------------------")
    print(f"Correct      : {good}")
    print(f"Wrong        : {bad}")
    print(f"Accuracy     : {accuracy:.2%}")
    print(f"Macro F1     : {macro_f1:.3f}")
    print(f"Micro F1     : {micro_f1:.3f}")
    print(f"Avg Latency  : {avg_latency:.2f}s")
    print(f"Avg SQL Tokens: {avg_tokens:.1f}")
    print("-----------------------------\n")

    # ---------- metrics CSV ------------------------------

    metrics_path = next_metrics_path(REPORT_ROOT/"metrics.txt")
    with open(metrics_path, "w", encoding="utf-8") as f:
        now = datetime.now().isoformat(sep=" ", timespec="seconds")
        f.write(f"Candidate Generator: {CANDIDATE_MODEL}\n")
        f.write(f"Validator          : {VALIDATION_MODEL}\n")
        f.write(f"Run at             : {now}\n")
        f.write(f"Samples            : {total}\n")
        f.write(f"Correct            : {good}\n")
        f.write(f"Wrong              : {bad}\n")
        f.write(f"Accuracy           : {accuracy:.4f}\n")
        f.write(f"Macro_F1           : {macro_f1:.4f}\n")
        f.write(f"Micro_F1           : {micro_f1:.4f}\n")
        f.write(f"Avg_Latency_sec    : {avg_latency:.3f}\n")
        f.write(f"Avg_SQL_Tokens     : {avg_tokens:.1f}\n")
        
    print(f"Metrics saved to {metrics_path}")

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
        with open(CSV_OUT, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow(header)
            writer.writerows(mismatch_rows)
        print(f"Mismatches written to {CSV_OUT}")


if __name__ == "__main__":
## reading the arguments from the command line
    parser = argparse.ArgumentParser(description="Evaluate CHESS pipeline on BIRD subset.")
    parser.add_argument("--k", type=int, default=MAX_SAMPLES, help="number of questions to sample (<=100)")
    parser.add_argument("--out", default="mismatches.csv", help="CSV path for mismatched answers")
    args = parser.parse_args()
##to run this file
##python evaluate_pipeline.py                        # 100 samples
##python evaluate_pipeline.py --k 60  # custom
    evaluate(max_samples=min(args.k, MAX_SAMPLES))
