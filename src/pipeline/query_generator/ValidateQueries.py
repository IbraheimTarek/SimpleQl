import os
import json
import re
import ast
import sqlite3
from typing import List, Sequence, Dict, Any
from collections import Counter
from langchain_groq import ChatGroq
from langchain.schema import SystemMessage, HumanMessage, AIMessage
from Params import *
from pipeline.query_generator.Promots import *
JSONTest = Dict[str, Any]

try:
    import json5
except ImportError:
    json5 = None

try:
    import yaml
except ImportError:
    yaml = None


def _extract_json_array(raw: str) -> List[Dict[str, Any]]:
    """
    Pull the first JSON_looking array out of the LLM response and return it as Python object.  Work s even if the block is JSON5 or YAML.
    Raises ValueError if no array found or if every parseing fails.
    """
    # grab the first ```json ... ``` block, else the first bare [ ... ]
    code_blocks = re.findall(
        r"```(?:json|json5)?\s*(\[\s*{.*?}\s*])\s*```",
        raw,
        flags=re.S,
    )
    candidates = code_blocks or re.findall(r"(\[\s*{.*?}\s*])", raw, flags=re.S)
    if not candidates:
        raise ValueError("No JSON-like array found in LLM output.")

    text = candidates[0]

    # Try  json first (fast path)
    try:
        return json.loads(text)
    except Exception:
        pass  

    # Fallback parsers, in order of availability
    parsers = []
    if json5:
        parsers.append(("json5", json5.loads))
    if yaml:
        parsers.append(("yaml", yaml.safe_load))
    parsers.append(("ast", ast.literal_eval))   # always available

    for name, fn in parsers:
        try:
            data = fn(text)
            if isinstance(data, list):
                return data
        except Exception:
            continue

    # Still here?  Everything failed.
    raise ValueError("Failed parse any JSON/JSON5/YAML from LLM output.")


class UnitTester:
    """
    agent that ranks SQL queries for a given question by executing LLM-synthesised unit tests on SQLite database.
    """

    def __init__(
        self,
        groq_api_key: str | None = None,
        *,
        model_name: str = VALIDATION_MODEL,
        k_unit_tests: int = 5,
        temperature_gen: float = 0.2,
    ) -> None:
        self.k = k_unit_tests
        groq_api_key = groq_api_key or os.getenv("GROQ_API_KEY")
        if not groq_api_key:
            raise ValueError("Set GROQ_API_KEY env-var or pass groq_api_key.")

        self.llm_gen = ChatGroq(
            groq_api_key=groq_api_key,
            model_name=model_name,
            temperature=temperature_gen,
        )

    def choose_best(
        self,
        question: str,
        candidates: Sequence[str],
    ) -> str:
        """
        Returns the candidate SQL string that passes the most unit tests.
        Stable tie-break: first in the list.
        """
        if len(candidates) < 2:
            raise ValueError("Pass *at least two* candidate queries.")

        unit_tests = self._generate_unit_tests(question, candidates)

        scores = [0] * len(candidates)
        for ut in unit_tests:
            results = self._run_unit_test(ut, candidates)
            for i, passed in enumerate(results):
                scores[i] += int(passed)

        best_idx = max(range(len(scores)), key=scores.__getitem__)
        return candidates[best_idx]


    def _generate_unit_tests(
        self,
        question: str,
        candidates: Sequence[str],
    ) -> List[JSONTest]:
        """
        Calls the LLM once and expects it to respond with a JSON array of
        exactly `self.k` objects in the schema.
        """
        system = SystemMessage(
            content=VALIDATION_PROMPT.format(k=self.k)  # VALIDATION_PROMPT uses {k} for formatting
        )

        cand_block = "\n\n".join(f"-- Candidate {i+1}\n{sql}" for i, sql in enumerate(candidates))
        human = HumanMessage(
            content=f"QUESTION:\n{question}\n\nHere are {len(candidates)} candidate SQL queries:\n{cand_block}"
        )
        resp: AIMessage = self.llm_gen.invoke([system, human])

        tests = _extract_json_array(resp.content)
        if len(tests) != self.k:
            raise RuntimeError(f"Expected {self.k} tests, got {len(tests)}.")

        # sanity-check mandatory keys
        for i, t in enumerate(tests, 1):
            for key in ("schema_sql", "data_sql", "expected"):
                if key not in t:
                    raise RuntimeError(f"Test {i} missing '{key}'.")

        return tests

    def _run_unit_test(
            self,
            test: JSONTest,
            candidates: Sequence[str],
        ) -> List[bool]:
            order = bool(test.get("order_matters", False))

            # normalise the expected results 
            expected_rows = test["expected"]
            if expected_rows and not isinstance(expected_rows[0], list):
                expected_rows = [[x] for x in expected_rows]     # 1-col shortcut
            expected_rows = [tuple(r) for r in expected_rows]

            # Decide comparison strategy based on order_matters flag.
            # If order matters, we compare lists directly; otherwise, we use a multiset comparison.
            if order:
                def equal(a: list[tuple]) -> bool:   # keep order
                    return a == expected_rows
            else:
                expected_multiset = Counter(expected_rows)

                def equal(a: list[tuple]) -> bool:   # order-insensitive
                    return Counter(a) == expected_multiset

            passes: list[bool] = []
            for sql in candidates:
                try:
                    with sqlite3.connect(":memory:") as conn:
                        cur = conn.cursor()
                        cur.executescript(test["schema_sql"])
                        cur.executescript(test["data_sql"])
                        cur.execute(sql)
                        rows = [tuple(r) for r in cur.fetchall()]
                        passes.append(equal(rows))
                except Exception:
                    passes.append(False)

            #self._print_unit_test_results(test, candidates, passes)
            return passes

    def _print_unit_test_results(self, test: JSONTest, candidates: Sequence[str], passes: List[bool]) -> None:
        print(f"Unit test schema (first 50 chars): {test['schema_sql'][:50]}...")
        print(f"Expected result: {test['expected']}")
        print(f"Order matters: {test.get('order_matters', False)}")
        print(f"Candidates: {len(candidates)} | Passed: {sum(passes)}")
        for i, (sql, passed) in enumerate(zip(candidates, passes), 1):
            print(f"  Candidate {i}: {'PASSED' if passed else 'FAILED'}")
            print(sql.strip())
            print("-" * 40)



if __name__ == "__main__":

    QUESTION = (
        "List the names of customers who have placed more than three orders "
        "in the last 30 days."
    )

    CANDIDATES = [
        # Likely correct
        """
        SELECT c.name
        FROM customers c
        JOIN orders o ON o.customer_id = c.id
        WHERE o.order_date >= DATE('now', '-30 day')
        GROUP BY c.name
        HAVING COUNT(*) > 3;
        """,
        # Missing HAVING
        """
        SELECT c.name
        FROM customers c
        JOIN orders o ON o.customer_id = c.id
        WHERE o.order_date >= DATE('now', '-30 day')
        GROUP BY c.name;
        """,
        # Counts all-time
        """
        SELECT DISTINCT c.name
        FROM customers c
        WHERE (SELECT COUNT(*) FROM orders o WHERE o.customer_id = c.id) > 3;
        """,
    ]

    tester = UnitTester(k_unit_tests=4)
    best = tester.choose_best(QUESTION, CANDIDATES)

    print("-------- BEST CANDIDATE ---------")
    print(best.strip())
    print("---------------------------------")
