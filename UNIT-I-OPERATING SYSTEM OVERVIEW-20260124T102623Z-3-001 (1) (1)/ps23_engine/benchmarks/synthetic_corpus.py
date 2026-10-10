"""Deterministic, synthetic source programs and controlled variants."""

import ast
import builtins
import io
import keyword
import tokenize
from typing import Dict, List, Optional, Tuple


TASKS: List[Tuple[str, str, str, str, Optional[str]]] = [
    (
        "sum_values",
        "def solve(values):\n    total = 0\n    for value in values:\n        total += value\n    return total\n",
        "def solve(values):\n    return sum(values)\n",
        "def solve(values):\n    total = 0\n    for value in values:\n        total -= value\n    return total\n",
        "def solve(values):\n    total = 0\n    index = 0\n    while index < len(values):\n        total += values[index]\n        index += 1\n    return total\n",
    ),
    (
        "maximum",
        "def solve(values):\n    best = values[0]\n    for value in values[1:]:\n        if value > best:\n            best = value\n    return best\n",
        "def solve(values):\n    return max(values)\n",
        "def solve(values):\n    best = values[0]\n    for value in values[1:]:\n        if value < best:\n            best = value\n    return best\n",
        "def solve(values):\n    best = values[0]\n    index = 1\n    while index < len(values):\n        if values[index] > best:\n            best = values[index]\n        index += 1\n    return best\n",
    ),
    (
        "count_even",
        "def solve(values):\n    count = 0\n    for value in values:\n        if value % 2 == 0:\n            count += 1\n    return count\n",
        "def solve(values):\n    return sum(value % 2 == 0 for value in values)\n",
        "def solve(values):\n    count = 0\n    for value in values:\n        if value % 2 != 0:\n            count += 1\n    return count\n",
        None,
    ),
    (
        "reverse_sequence",
        "def solve(values):\n    result = []\n    for value in values:\n        result.insert(0, value)\n    return result\n",
        "def solve(values):\n    return values[::-1]\n",
        "def solve(values):\n    return values[:]\n",
        None,
    ),
    (
        "factorial",
        "def solve(value):\n    result = 1\n    for factor in range(2, value + 1):\n        result *= factor\n    return result\n",
        "def solve(value):\n    if value <= 1:\n        return 1\n    return value * solve(value - 1)\n",
        "def solve(value):\n    result = 0\n    for factor in range(2, value + 1):\n        result += factor\n    return result\n",
        None,
    ),
    (
        "linear_search",
        "def solve(values, target):\n    for index, value in enumerate(values):\n        if value == target:\n            return index\n    return -1\n",
        "def solve(values, target):\n    try:\n        return values.index(target)\n    except ValueError:\n        return -1\n",
        "def solve(values, target):\n    for index, value in enumerate(values):\n        if value != target:\n            return index\n    return -1\n",
        None,
    ),
    (
        "digit_sum",
        "def solve(value):\n    total = 0\n    while value:\n        total += value % 10\n        value //= 10\n    return total\n",
        "def solve(value):\n    return sum(int(digit) for digit in str(abs(value)))\n",
        "def solve(value):\n    total = 0\n    while value:\n        total *= value % 10\n        value //= 10\n    return total\n",
        None,
    ),
    (
        "is_palindrome",
        "def solve(text):\n    return text == text[::-1]\n",
        "def solve(text):\n    left = 0\n    right = len(text) - 1\n    while left < right:\n        if text[left] != text[right]:\n            return False\n        left += 1\n        right -= 1\n    return True\n",
        "def solve(text):\n    return text != text[::-1]\n",
        None,
    ),
    (
        "gcd",
        "def solve(left, right):\n    while right:\n        left, right = right, left % right\n    return left\n",
        "def solve(left, right):\n    if right == 0:\n        return left\n    return solve(right, left % right)\n",
        "def solve(left, right):\n    while right:\n        left, right = right, left // right\n    return left\n",
        None,
    ),
    (
        "fibonacci",
        "def solve(n):\n    first, second = 0, 1\n    for _ in range(n):\n        first, second = second, first + second\n    return first\n",
        "def solve(n):\n    if n < 2:\n        return n\n    return solve(n - 1) + solve(n - 2)\n",
        "def solve(n):\n    first, second = 0, 1\n    for _ in range(n):\n        first, second = second, first - second\n    return first\n",
        None,
    ),
    (
        "word_count",
        "def solve(words):\n    counts = {}\n    for word in words:\n        counts[word] = counts.get(word, 0) + 1\n    return counts\n",
        "def solve(words):\n    return {word: words.count(word) for word in set(words)}\n",
        "def solve(words):\n    counts = {}\n    for word in words:\n        counts[word] = counts.get(word, 0) - 1\n    return counts\n",
        None,
    ),
    (
        "average",
        "def solve(values):\n    total = 0\n    count = 0\n    for value in values:\n        total += value\n        count += 1\n    return total / count\n",
        "def solve(values):\n    return sum(values) / len(values)\n",
        "def solve(values):\n    total = 0\n    count = 0\n    for value in values:\n        total -= value\n        count += 1\n    return total / count\n",
        None,
    ),
]


def _identifier_variant(source: str) -> str:
    tree = ast.parse(source)
    names = {
        node.id for node in ast.walk(tree)
        if isinstance(node, ast.Name)
        and node.id not in dir(builtins)
        and not keyword.iskeyword(node.id)
    }
    names.update(
        node.arg for node in ast.walk(tree)
        if isinstance(node, ast.arg)
    )
    names.update(
        node.name for node in ast.walk(tree)
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef))
    )
    mapping = {name: "renamed_" + str(index) for index, name in enumerate(sorted(names))}
    offsets = [0]
    for line in source.splitlines(keepends=True):
        offsets.append(offsets[-1] + len(line))

    edits = []
    for item in tokenize.generate_tokens(io.StringIO(source).readline):
        if item.type != tokenize.NAME or item.string not in mapping:
            continue
        start = offsets[item.start[0] - 1] + item.start[1]
        end = offsets[item.end[0] - 1] + item.end[1]
        edits.append((start, end, mapping[item.string]))
    result = source
    for start, end, replacement in reversed(edits):
        result = result[:start] + replacement + result[end:]
    return result


def build_records() -> List[Dict[str, str]]:
    records: List[Dict[str, str]] = []
    for task_id, first, second, changed, loop_rewrite in TASKS:
        solutions = [("solution_a", first), ("solution_b", second)]
        for family_id, source in solutions:
            def add(variant: str, transformation: str, code: str) -> None:
                records.append({
                    "dataset": "PS-23 synthetic controlled corpus v1",
                    "task_id": task_id,
                    "family_id": task_id + ":" + family_id,
                    "source_id": task_id + ":" + family_id + ":" + variant,
                    "variant": variant,
                    "transformation": transformation,
                    "source": code,
                })

            add("original", "original", source)
            add("renamed", "identifier_renamed", _identifier_variant(source))
            formatted = "# Synthetic comment and formatting variant.\n\n" + source.replace("\n", "\n\n")
            add("format_comments", "formatting_and_comments", formatted)
            add(
                "partial_overlap",
                "partial_overlap",
                source + "\ndef helper(data):\n    return len(data)\n",
            )
            if family_id == "solution_a" and changed:
                add("behavior_change", "similar_looking_different_behavior", changed)
            if family_id == "solution_a" and loop_rewrite:
                add("loop_rewrite", "equivalent_loop_rewrite", loop_rewrite)
    return records


def build_pairs(records: List[Dict[str, str]]) -> List[Dict[str, str]]:
    by_family: Dict[str, List[Dict[str, str]]] = {}
    by_task: Dict[str, List[Dict[str, str]]] = {}
    for record in records:
        by_family.setdefault(record["family_id"], []).append(record)
        by_task.setdefault(record["task_id"], []).append(record)

    pairs: List[Dict[str, str]] = []

    def add(left, right, label: int, pair_type: str) -> None:
        pairs.append({
            "task_id": left["task_id"],
            "left_id": left["source_id"],
            "right_id": right["source_id"],
            "left_source": left["source"],
            "right_source": right["source"],
            "label": str(label),
            "pair_type": pair_type,
        })

    for task_id, _, _, _, _ in TASKS:
        task_records = by_task[task_id]
        for family_id in (task_id + ":solution_a", task_id + ":solution_b"):
            family = by_family[family_id]
            original = next(item for item in family if item["variant"] == "original")
            add(original, original, 1, "identical_program")
            for variant in family:
                if variant["variant"] == "original":
                    continue
                positive = variant["transformation"] != "similar_looking_different_behavior"
                add(
                    original,
                    variant,
                    1 if positive else 0,
                    variant["transformation"],
                )
        first = next(item for item in task_records if item["variant"] == "original" and item["family_id"].endswith("solution_a"))
        second = next(item for item in task_records if item["variant"] == "original" and item["family_id"].endswith("solution_b"))
        add(first, second, 0, "independently_written_same_problem")

    for index, task in enumerate(TASKS):
        next_task_id = TASKS[(index + 1) % len(TASKS)][0]
        left = by_family[task[0] + ":solution_a"][0]
        right = by_family[next_task_id + ":solution_a"][0]
        add(left, right, 0, "unrelated_programs")
    return pairs
