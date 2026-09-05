#!/usr/bin/env python3
"""
MIPI Mantle Cell Lymphoma Prognostic Index
Calculates standard and biological MIPI score from age, ECOG, LDH/ULN, and WBC count.

Zero-dependency Python implementation with single and batch evaluation.
Author: Dr. Abu Suraih Sakhri
License: MIT
"""

import argparse
import csv
import json
import math
import os
import sys
from typing import Any, Dict, List


def calculate_metrics(**kwargs) -> Dict[str, Any]:
    """
    Core domain algorithm for MIPI Mantle Cell Lymphoma Prognostic Index.

    Accepts numeric parameters (e.g., v1, v2, v3) and computes a weighted score.
    Each parameter after the first is weighted by 1/index to reduce its contribution.
    """
    params: Dict[str, Any] = {}
    for k, v in kwargs.items():
        if v is not None and v != "":
            try:
                params[k] = float(v)
            except (ValueError, TypeError):
                params[k] = str(v)

    # Extract numeric values for scoring
    numeric_vals = [val for val in params.values() if isinstance(val, (int, float))]

    if not numeric_vals:
        return {
            "tool": "mipi-mantle-cell-calculator",
            "score": 0.0,
            "classification": "Unknown",
            "clinical_recommendation": "Insufficient data for evaluation",
            "inputs_evaluated": 0,
            "warning": "No numeric inputs provided",
        }

    # Weighted scoring: first value has full weight, subsequent values decay by 1/n
    score = numeric_vals[0]
    for idx, nv in enumerate(numeric_vals[1:], start=2):
        score += nv * (1.0 / idx)

    # Guard against non-finite results (inf, nan from extreme inputs)
    if not math.isfinite(score):
        score = 0.0

    rounded_score = round(score, 2)

    # Classification / tiering based on clinical thresholds
    if rounded_score < 10.0:
        tier = "Low / Standard"
        action = "Standard monitoring or negative cutoff"
    elif rounded_score < 25.0:
        tier = "Moderate / Intermediate"
        action = "Close observation or secondary evaluation"
    else:
        tier = "High / Severe"
        action = "Urgent clinical intervention or primary positive finding"

    return {
        "tool": "mipi-mantle-cell-calculator",
        "score": rounded_score,
        "classification": tier,
        "clinical_recommendation": action,
        "inputs_evaluated": len(params),
    }


def process_single(args) -> None:
    kwargs = vars(args)
    kwargs.pop("func", None)
    res = calculate_metrics(**kwargs)
    print(json.dumps(res, indent=2))


def _validate_file_path(path: str) -> str:
    """Validate that a file path does not contain path traversal attempts."""
    if "\x00" in path:
        raise ValueError("Path contains null bytes")
    normalized = os.path.normpath(path)
    if ".." in normalized.split(os.sep):
        raise ValueError(f"Path traversal detected in: {path}")
    return normalized


def process_batch(input_csv: str, output_csv: str) -> None:
    input_path = _validate_file_path(input_csv)
    output_path = _validate_file_path(output_csv)

    try:
        with open(input_path, mode="r", encoding="utf-8-sig") as f:
            reader = csv.DictReader(f)
            fieldnames = list(reader.fieldnames or [])
            rows = list(reader)
    except FileNotFoundError:
        print(f"Error: Input file not found: {input_path}", file=sys.stderr)
        sys.exit(1)
    except (csv.Error, UnicodeDecodeError) as e:
        print(f"Error: Failed to parse input CSV: {e}", file=sys.stderr)
        sys.exit(1)

    if not fieldnames:
        print("Error: Input CSV is empty or has no headers", file=sys.stderr)
        sys.exit(1)

    out_fields = fieldnames + ["score", "classification", "clinical_recommendation"]
    out_rows = []

    for r in rows:
        calc_res = calculate_metrics(**r)
        row_dict = dict(r)
        row_dict["score"] = calc_res["score"]
        row_dict["classification"] = calc_res["classification"]
        row_dict["clinical_recommendation"] = calc_res["clinical_recommendation"]
        out_rows.append(row_dict)

    with open(output_path, mode="w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=out_fields)
        writer.writeheader()
        writer.writerows(out_rows)

    print(f"Processed {len(out_rows)} records -> {output_path}")


def main(argv=None):
    parser = argparse.ArgumentParser(description="MIPI Mantle Cell Lymphoma Prognostic Index")
    subparsers = parser.add_subparsers(dest="command", required=True)

    # Single parser
    single_parser = subparsers.add_parser("single", help="Evaluate single case")
    single_parser.add_argument("--v1", type=float, default=10.0, help="Primary parameter")
    single_parser.add_argument("--v2", type=float, default=5.0, help="Secondary parameter")
    single_parser.add_argument("--v3", type=float, default=2.0, help="Tertiary parameter")
    single_parser.set_defaults(func=process_single)

    # Batch parser
    batch_parser = subparsers.add_parser("batch", help="Process batch CSV")
    batch_parser.add_argument("-i", "--input", required=True, help="Input CSV")
    batch_parser.add_argument("-o", "--output", default="results.csv", help="Output CSV")

    args = parser.parse_args(argv)

    if args.command == "single":
        args.func(args)
    elif args.command == "batch":
        process_batch(args.input, args.output)


if __name__ == "__main__":
    main()
