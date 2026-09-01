#!/usr/bin/env python3
"""Lightweight local retrieval for the design prompt library.

Uses Unicode-aware token overlap so the skill can work offline without a vector
database. The JSONL library is intentionally editable by a design team.
"""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
LIBRARY = ROOT / "references" / "design-prompt-library.jsonl"


def tokens(text: str) -> set[str]:
    lowered = text.lower()
    english = set(re.findall(r"[a-z0-9][a-z0-9-]*", lowered))
    cjk = re.findall(r"[\u4e00-\u9fff]", lowered)
    bigrams = {"".join(cjk[i : i + 2]) for i in range(len(cjk) - 1)}
    return english | set(cjk) | bigrams


def load_rows() -> list[dict]:
    rows = []
    with LIBRARY.open("r", encoding="utf-8") as handle:
        for line in handle:
            line = line.strip()
            if line:
                rows.append(json.loads(line))
    return rows


def score(query_tokens: set[str], row: dict, category: str | None) -> float:
    searchable = " ".join(
        str(row.get(field, ""))
        for field in ("category", "zh", "en", "use")
    )
    row_tokens = tokens(searchable)
    overlap = query_tokens & row_tokens
    value = float(len(overlap))
    if category and row.get("category") == category:
        value += 4.0
    if row.get("zh") and any(term in row["zh"] for term in query_tokens if len(term) > 1):
        value += 1.5
    return value


def main() -> int:
    parser = argparse.ArgumentParser(description="Retrieve design terms from the local JSONL library.")
    parser.add_argument("--query", required=True, help="Design brief or visual keywords")
    parser.add_argument("--top-k", type=int, default=12)
    parser.add_argument("--category", help="Optional category filter")
    parser.add_argument("--json", action="store_true", help="Return JSON instead of Markdown")
    args = parser.parse_args()

    query_tokens = tokens(args.query)
    ranked = sorted(
        [
            (score(query_tokens, row, args.category), row)
            for row in load_rows()
        ],
        key=lambda item: item[0],
        reverse=True,
    )
    results = [row for value, row in ranked if value > 0][: max(1, args.top_k)]

    if args.json:
        print(json.dumps(results, ensure_ascii=False, indent=2))
    else:
        for row in results:
            print(f"- [{row['category']}] {row['zh']} | {row['en']} — {row['use']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
