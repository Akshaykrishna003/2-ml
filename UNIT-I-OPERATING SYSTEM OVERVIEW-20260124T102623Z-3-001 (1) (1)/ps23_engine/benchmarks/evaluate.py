"""Evaluate fixed similarity baselines on a group-disjoint synthetic holdout."""

import argparse
import json
from pathlib import Path
from typing import Dict, List

from benchmarks.synthetic_corpus import build_pairs, build_records
from ps23_engine.core.ast_analysis import ASTAnalyzer
from ps23_engine.core.baseline import TokenBaseline


SPLITS = {
    "train": ["sum_values", "count_even", "reverse_sequence", "factorial", "linear_search", "digit_sum"],
    "validation": ["is_palindrome", "gcd"],
    "test": ["maximum", "fibonacci", "word_count", "average"],
}
THRESHOLD = 0.5


def _metrics(rows: List[Dict[str, object]]) -> Dict[str, object]:
    tp = sum(row["label"] == 1 and row["prediction"] == 1 for row in rows)
    fp = sum(row["label"] == 0 and row["prediction"] == 1 for row in rows)
    tn = sum(row["label"] == 0 and row["prediction"] == 0 for row in rows)
    fn = sum(row["label"] == 1 and row["prediction"] == 0 for row in rows)
    precision = tp / float(tp + fp) if tp + fp else 0.0
    recall = tp / float(tp + fn) if tp + fn else 0.0
    f1 = 2 * precision * recall / (precision + recall) if precision + recall else 0.0
    false_positive_rate = fp / float(fp + tn) if fp + tn else 0.0
    return {
        "pair_count": len(rows),
        "confusion_matrix": {"tn": tn, "fp": fp, "fn": fn, "tp": tp},
        "precision": precision,
        "recall": recall,
        "f1": f1,
        "false_positive_rate": false_positive_rate,
    }


def evaluate() -> Dict[str, object]:
    records = build_records()
    pairs = build_pairs(records)
    test_tasks = set(SPLITS["test"])
    test_pairs = [pair for pair in pairs if pair["task_id"] in test_tasks]
    by_family: Dict[str, List[Dict[str, str]]] = {}
    for record in records:
        if record["task_id"] in test_tasks:
            by_family.setdefault(record["family_id"], []).append(record)

    for task_id in SPLITS["test"]:
        original = next(
            record for record in by_family[task_id + ":solution_a"]
            if record["variant"] == "original"
        )
        next_task = SPLITS["test"][(SPLITS["test"].index(task_id) + 1) % len(SPLITS["test"])]
        unrelated = next(
            record for record in by_family[next_task + ":solution_a"]
            if record["variant"] == "original"
        )
        test_pairs.append({
            "task_id": task_id,
            "left_id": original["source_id"],
            "right_id": unrelated["source_id"],
            "left_source": original["source"],
            "right_source": unrelated["source"],
            "label": "0",
            "pair_type": "unrelated_programs",
        })

    token = TokenBaseline()
    ast_analyzer = ASTAnalyzer()
    score_rows: Dict[str, List[Dict[str, object]]] = {
        "token_only": [],
        "ast_only": [],
        "combined": [],
    }
    for pair in test_pairs:
        token_score = token.compute_similarity(pair["left_source"], pair["right_source"])
        ast_score = ast_analyzer.compute_structural_similarity(
            pair["left_source"], pair["right_source"]
        )
        actual = int(pair["label"])
        for method, score in (
            ("token_only", token_score),
            ("ast_only", ast_score),
            ("combined", (token_score + ast_score) / 2.0),
        ):
            score_rows[method].append({
                "label": actual,
                "prediction": int(score >= THRESHOLD),
                "score": score,
                "pair_type": pair["pair_type"],
            })

    methods = {}
    for method, rows in score_rows.items():
        summary = _metrics(rows)
        summary["threshold"] = THRESHOLD
        summary["by_transformation"] = {
            pair_type: _metrics([row for row in rows if row["pair_type"] == pair_type])
            for pair_type in sorted({row["pair_type"] for row in rows})
        }
        methods[method] = summary

    return {
        "dataset": "PS-23 synthetic controlled corpus v1",
        "dataset_origin": "Synthetic, hand-authored Python examples; no external dataset used.",
        "seed": 23,
        "split_policy": "Task-grouped fixed split; every variant and independent solution for a task remains in one split.",
        "splits": SPLITS,
        "test_task_count": len(test_tasks),
        "test_pair_count": len(test_pairs),
        "threshold": THRESHOLD,
        "threshold_policy": "Fixed before measurement; no test-set tuning.",
        "methods": methods,
        "feature_schema": {
            "token_only": "Set Jaccard similarity over Python tokens excluding comments and layout.",
            "ast_only": "Cosine similarity over AST node-type count vectors.",
            "combined": "Unweighted arithmetic mean of token-only and AST-only scores.",
            "decision_rule": "Score >= 0.5 predicts a positive pair.",
        },
        "trained_model": {
            "available": False,
            "reason": "No trained classifier artifact exists. The small synthetic corpus is suitable for controlled baseline checks, not defensible model training or claims of generalization.",
        },
        "limitations": [
            "Synthetic labels encode known source provenance and controlled transformations, not real plagiarism judgments.",
            "Only four task groups are in the held-out test split; metrics are not representative of deployment.",
            "Similarity thresholds are fixed diagnostic baselines, not calibrated plagiarism decisions.",
            "The AST distribution cosine is structural evidence, not semantic equivalence.",
        ],
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--output",
        type=Path,
        default=Path(__file__).resolve().parents[1] / "reports" / "evaluation.json",
    )
    args = parser.parse_args()
    result = evaluate()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print("Wrote evaluation report to {}".format(args.output))
    for method, metrics in result["methods"].items():
        print(
            "{}: precision={:.3f} recall={:.3f} F1={:.3f} FPR={:.3f}".format(
                method,
                metrics["precision"],
                metrics["recall"],
                metrics["f1"],
                metrics["false_positive_rate"],
            )
        )


if __name__ == "__main__":
    main()
