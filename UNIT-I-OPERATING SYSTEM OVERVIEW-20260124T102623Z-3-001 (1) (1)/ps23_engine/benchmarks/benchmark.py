"""Measure parsing, feature extraction, all-pairs time, and Python peak memory."""

import argparse
import ctypes
import gc
import json
import os
import platform
import tempfile
import time
import tracemalloc
from pathlib import Path
from typing import Dict, List

from benchmarks.synthetic_corpus import build_records
from ps23_engine.core.ast_analysis import ASTAnalyzer, _cached_ast_features
from ps23_engine.core.baseline import TokenBaseline, _cached_ngrams, _cached_tokens


def _hardware() -> Dict[str, object]:
    result = {
        "platform": platform.platform(),
        "processor": platform.processor(),
        "logical_cpus": os.cpu_count(),
        "python": platform.python_version(),
    }
    if os.name == "nt":
        class MemoryStatus(ctypes.Structure):
            _fields_ = [
                ("dwLength", ctypes.c_ulong),
                ("dwMemoryLoad", ctypes.c_ulong),
                ("ullTotalPhys", ctypes.c_ulonglong),
                ("ullAvailPhys", ctypes.c_ulonglong),
                ("ullTotalPageFile", ctypes.c_ulonglong),
                ("ullAvailPageFile", ctypes.c_ulonglong),
                ("ullTotalVirtual", ctypes.c_ulonglong),
                ("ullAvailVirtual", ctypes.c_ulonglong),
                ("ullAvailExtendedVirtual", ctypes.c_ulonglong),
            ]

        status = MemoryStatus()
        status.dwLength = ctypes.sizeof(status)
        if ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(status)):
            result["physical_memory_gib"] = round(status.ullTotalPhys / (1024 ** 3), 2)
    return result


def _cosine(left: Dict[str, int], right: Dict[str, int]) -> float:
    if not left or not right:
        return 0.0
    keys = set(left).union(right)
    dot = sum(left.get(key, 0) * right.get(key, 0) for key in keys)
    left_norm = sum(value * value for value in left.values()) ** 0.5
    right_norm = sum(value * value for value in right.values()) ** 0.5
    return dot / (left_norm * right_norm) if left_norm and right_norm else 0.0


def run_size(count: int) -> Dict[str, object]:
    _cached_ast_features.cache_clear()
    _cached_tokens.cache_clear()
    _cached_ngrams.cache_clear()
    gc.collect()
    records = build_records()
    source_texts = [
        records[index % len(records)]["source"] + "\n# benchmark file {}\n".format(index)
        for index in range(count)
    ]

    tracemalloc.start()
    with tempfile.TemporaryDirectory(prefix="ps23-benchmark-") as temp_dir:
        root = Path(temp_dir)
        for index, source in enumerate(source_texts):
            (root / "source_{:04d}.py".format(index)).write_text(source, encoding="utf-8")
        del source_texts

        total_start = time.perf_counter()
        paths = sorted(root.glob("*.py"))
        sources = [path.read_text(encoding="utf-8") for path in paths]

        started = time.perf_counter()
        for source in sources:
            import ast
            ast.parse(source)
        parse_seconds = time.perf_counter() - started

        analyzer = ASTAnalyzer()
        baseline = TokenBaseline()
        started = time.perf_counter()
        features = []
        for source in sources:
            tokens = baseline.tokenize(source)
            features.append({
                "ngrams": baseline._get_ngrams(tokens),
                "nodes": analyzer.extract_features(source)["node_distribution"],
            })
        extraction_seconds = time.perf_counter() - started

        started = time.perf_counter()
        comparisons = 0
        checksum = 0.0
        for left_index in range(count):
            left = features[left_index]
            for right_index in range(left_index + 1, count):
                right = features[right_index]
                left_grams = left["ngrams"]
                right_grams = right["ngrams"]
                union_size = len(left_grams.union(right_grams))
                token_score = (
                    len(left_grams.intersection(right_grams)) / float(union_size)
                    if union_size else 0.0
                )
                checksum += token_score + _cosine(left["nodes"], right["nodes"])
                comparisons += 1
        pairwise_seconds = time.perf_counter() - started
        total_seconds = time.perf_counter() - total_start
        _, peak_bytes = tracemalloc.get_traced_memory()
    tracemalloc.stop()
    return {
        "file_count": count,
        "pair_count": comparisons,
        "parse_seconds": parse_seconds,
        "feature_extraction_seconds": extraction_seconds,
        "pairwise_comparison_seconds": pairwise_seconds,
        "total_runtime_seconds": total_seconds,
        "peak_traced_memory_mib": peak_bytes / float(1024 ** 2),
        "pair_score_checksum": checksum,
        "fixture_generation_included_in_total": False,
        "file_read_included_in_total": True,
        "memory_measurement": "tracemalloc Python allocations; native allocations and OS page cache excluded",
    }


def run_benchmarks(sizes: List[int]) -> Dict[str, object]:
    return {
        "benchmark": "PS-23 synthetic exhaustive pairwise benchmark v1",
        "hardware": _hardware(),
        "method": (
            "Synthetic Python files generated from controlled source variants with unique comments; "
            "file creation excluded, file reads included, every unordered file pair compared."
        ),
        "results": [run_size(size) for size in sizes],
        "caveats": [
            "Synthetic source files are not a representative distribution of student submissions.",
            "All-pairs comparison is O(n^2); results depend on source size and hardware.",
            "Peak memory is Python-traced allocation, not full process resident memory.",
        ],
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--sizes", nargs="+", type=int, default=[100, 500, 1000])
    parser.add_argument(
        "--output",
        type=Path,
        default=Path(__file__).resolve().parents[1] / "reports" / "performance.json",
    )
    args = parser.parse_args()
    if any(size <= 0 for size in args.sizes):
        parser.error("sizes must all be positive")
    result = run_benchmarks(args.sizes)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print("Wrote performance report to {}".format(args.output))
    for row in result["results"]:
        print(
            "{file_count} files: parse={parse_seconds:.3f}s features={feature_extraction_seconds:.3f}s "
            "pairs={pairwise_comparison_seconds:.3f}s total={total_runtime_seconds:.3f}s "
            "peak={peak_traced_memory_mib:.1f}MiB".format(**row)
        )


if __name__ == "__main__":
    main()
