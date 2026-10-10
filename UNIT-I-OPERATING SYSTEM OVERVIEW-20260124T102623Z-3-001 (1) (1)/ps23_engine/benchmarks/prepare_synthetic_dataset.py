"""Write a deterministic, explicitly synthetic pairwise evaluation corpus."""

import argparse
import json
from pathlib import Path
from typing import Dict, List


SYNTHETIC_TASKS = [
    {
        "task": "sum_values",
        "first": "def solve(values):\n    total = 0\n    for value in values:\n        total += value\n    return total\n",
        "second": "def solve(values):\n    return sum(values)\n",
        "loop": "def solve(values):\n    total = 0\n    index = 0\n    while index < len(values):\n        total += values[index]\n        index += 1\n    return total\n",
        "changed": "def solve(values):\n    total = 0\n    for value in values:\n        total -= value\n    return total\n",
    },
    {
        "task": "maximum",
        "first": "def solve(values):\n    best = values[0]\n    for value in values[1:]:\n        if value > best:\n            best = value\n    return best\n",
        "second": "def solve(values):\n    return max(values)\n",
        "changed": "def solve(values):\n    best = values[0]\n    for value in values[1:]:\n        if value < best:\n            best = value\n    return best\n",
    },
    {
        "task": "count_even",
        "first": "def solve(values):\n    count = 0\n    for value in values:\n        if value % 2 == 0:\n            count += 1\n    return count\n",
        "second": "def solve(values):\n    return sum(value % 2 == 0 for value in values)\n",
        "changed": "def solve(values):\n    count = 0\n    for value in values:\n        if value % 2 != 0:\n            count += 1\n    return count\n",
    },
    {
        "task": "reverse_sequence",
        "first": "def solve(values):\n    result = []\n    for value in values:\n        result.insert(0, value)\n    return result\n",
        "second": "def solve(values):\n    return values[::-1]\n",
        "changed": "def solve(values):\n    return values[:]\n",
    },
    {
        "task": "factorial",
        "first": "def solve(value):\n    result = 1\n    for factor in range(2, value + 1):\n        result *= factor\n    return result\n",
        "second": "def solve(value):\n    if value <= 1:\n        return 1\n    return value * solve(value - 1)\n",
        "changed": "def solve(value):\n    result = 0\n    for factor in range(2, value + 1):\n        result += factor\n    return result\n",
    },
    {
        "task": "linear_search",
        "first": "def solve(values, target):\n    for index, value in enumerate(values):\n        if value == target:\n            return index\n    return -1\n",
        "second": "def solve(values, target):\n    try:\n        return values.index(target)\n    except ValueError:\n        return -1\n",
        "changed": "def solve(values, target):\n    for index, value in enumerate(values):\n        if value != target:\n            return index\n    return -1\n",
    },
    {
        "task": "digit_sum",
        "first": "def solve(value):\n    total = 0\n    while value:\n        total += value % 10\n        value //= 10\n    return total\n",
        "second": "def solve(value):\n    return sum(int(digit) for digit in str(abs(value)))\n",
        "changed": "def solve(value):\n    total = 0\n    while value:\n        total *= value % 10\n        value //= 10\n    return total\n",
    },
    {
        "task": "is_palindrome",
        "first": "def solve(text):\n    return text == text[::-1]\n",
        "second": "def solve(text):\n    left = 0\n    right = len(text) - 1\n    while left < right:\n        if text[left] != text[right]:\n            return False\n        left += 1\n        right -= 1\n    return True\n",
        "changed": "def solve(text):\n    return text != text[::-1]\n",
    },
]


def build_records() -> List[Dict[str, str]]:
    records = []
    for task in SYNTHETIC_TASKS:
        for solution_name in ("first", "second"):
            family = f"{task['task']}:{solution_name}"
            source = task[solution_name]
            records.extend([
                {"task_id": task["task"], "family_id": family, "variant": "original", "label": "source", "source": source},
                {
                    "task_id": task["task"], "family_id": family, "variant": "renamed",
                    "label": "identifier_renamed",
                    "source": source.replace("solve", "compute_result").replace("values", "items").replace("value", "element"),
                },
                {
                    "task_id": task["task"], "family_id": family, "variant": "comment_format",
                    "label": "format_and_comments",
                    "source": "# synthetic formatting variant\n" + "\n".join(line.rstrip() for line in source.splitlines()) + "\n",
                },
                {
                    "task_id": task["task"], "family_id": family, "variant": "partial",
                    "label": "partial_overlap",
                    "source": source + "\ndef helper(data):\n    return len(data)\n",
                },
            ])
            if solution_name == "first" and task["task"] == "sum_values":
                records.append({
                    "task_id": task["task"], "family_id": family, "variant": "loop_rewrite",
                    "label": "equivalent_loop_rewrite", "source": task["loop"],
                })
            records.append({
                "task_id": task["task"], "family_id": family, "variant": "behavior_change",
                "label": "behavior_changed", "source": task["changed"],
            })
    return records


def write_dataset(destination: Path) -> int:
    records = build_records()
    destination.parent.mkdir(parents=True, exist_ok=True)
    with destination.open("w", encoding="utf-8", newline="\n") as output:
        for record in records:
            output.write(json.dumps(record, sort_keys=True) + "\n")
    return len(records)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--output",
        type=Path,
        default=Path(__file__).resolve().parents[1] / "data" / "synthetic_programs.jsonl",
    )
    args = parser.parse_args()
    print(f"Wrote {write_dataset(args.output)} synthetic source variants to {args.output}")


if __name__ == "__main__":
    main()
