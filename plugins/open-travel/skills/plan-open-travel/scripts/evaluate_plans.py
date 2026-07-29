#!/usr/bin/env python3
"""Evaluate normalized trip plans from JSON."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from travel_core import evaluate_payload


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Calculate complete costs, risks, Pareto frontier, and representative plans."
    )
    parser.add_argument("input", type=Path, help="UTF-8 JSON payload")
    parser.add_argument("--output", type=Path, help="Write UTF-8 JSON to this path")
    args = parser.parse_args()

    try:
        payload = json.loads(args.input.read_text(encoding="utf-8"))
        result = evaluate_payload(payload)
    except (OSError, json.JSONDecodeError, ValueError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2

    rendered = json.dumps(result, ensure_ascii=False, indent=2)
    if args.output:
        args.output.write_text(rendered + "\n", encoding="utf-8")
    else:
        print(rendered)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
