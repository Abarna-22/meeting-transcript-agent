"""Measure the system against data/test_questions.json (for the results chapter of the report).

Reports, per run:
  retrieval hit rate  - did at least one expected meeting appear in the cited sources?
  keyword coverage    - fraction of expected keywords found in the answer + sources
  mean latency        - seconds per question

    python scripts/evaluate.py [--api http://localhost:8000] [--top-k 6]
"""
import argparse
import json
import statistics
import time
from pathlib import Path

import httpx

QUESTIONS = Path(__file__).resolve().parents[2] / "data" / "test_questions.json"


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--api", default="http://localhost:8000")
    ap.add_argument("--top-k", type=int, default=None)
    args = ap.parse_args()

    qs = json.loads(QUESTIONS.read_text())
    hits, kw_scores, lat = 0, [], []
    print(f"{'#':>2}  {'hit':<4} {'kw':<5} {'sec':<5} question")
    with httpx.Client(base_url=args.api, timeout=300) as c:
        for i, q in enumerate(qs, 1):
            t0 = time.perf_counter()
            r = c.post("/api/query", json={"question": q["question"], "top_k": args.top_k}).json()
            dt = time.perf_counter() - t0
            lat.append(dt)
            titles = {s["title"] for s in r["sources"]}
            hit = bool(titles & set(q["expected_meetings"]))
            hits += hit
            haystack = (r["answer"] + " " + " ".join(s["snippet"] for s in r["sources"])).lower()
            kw = sum(k.lower() in haystack for k in q["keywords"]) / len(q["keywords"])
            kw_scores.append(kw)
            print(f"{i:>2}  {'yes' if hit else 'NO':<4} {kw:<5.0%} {dt:<5.2f} {q['question']}")

    print("\n--- summary ---")
    print(f"questions            : {len(qs)}")
    print(f"retrieval hit rate   : {hits}/{len(qs)} = {hits / len(qs):.0%}")
    print(f"keyword coverage     : {statistics.mean(kw_scores):.0%}")
    print(f"mean latency         : {statistics.mean(lat):.2f}s (max {max(lat):.2f}s)")


if __name__ == "__main__":
    main()
