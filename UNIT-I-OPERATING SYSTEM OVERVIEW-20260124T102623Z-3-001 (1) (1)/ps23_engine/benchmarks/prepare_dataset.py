"""Write the versioned synthetic source corpus as deterministic JSON Lines."""

import argparse
import json
from pathlib import Path

from benchmarks.synthetic_corpus import build_records


def write_dataset(destination: Path) -> int:
    records = build_records()
    destination.parent.mkdir(parents=True, exist_ok=True)
    with destination.open("w", encoding="utf-8", newline="\n") as output:
        for record in records:
            output.write(json.dumps(record, sort_keys=True, ensure_ascii=True) + "\n")
    return len(records)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--output",
        type=Path,
        default=Path(__file__).resolve().parents[1] / "data" / "synthetic_programs.jsonl",
    )
    args = parser.parse_args()
    count = write_dataset(args.output)
    print("Wrote {} synthetic source variants to {}".format(count, args.output))


if __name__ == "__main__":
    main()
