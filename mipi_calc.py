"""Mantle Cell Lymphoma International Prognostic Index (MIPI).

Original MIPI: Hoster et al., Blood 2008;111:558–565.
Scores are prognostic groupings, not treatment recommendations.
"""
from __future__ import annotations

import argparse
import csv
import json
import math
import sys
from pathlib import Path
from typing import Any


def _number(name: str, value: Any, *, low: float, high: float, integer: bool = False) -> float:
    if value is None or isinstance(value, bool) or (isinstance(value, str) and not value.strip()):
        raise ValueError(f"{name} is required")
    try:
        num = float(value)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{name} must be numeric") from exc
    if not math.isfinite(num) or not low <= num <= high or (integer and not num.is_integer()):
        raise ValueError(f"{name} must be {'an integer ' if integer else ''}between {low:g} and {high:g}")
    return num


def calculate_metrics(*, age: Any, ecog: Any, wbc: Any, ldh: Any = None,
                      ldh_uln: Any = None, ldh_ratio: Any = None,
                      ki67: Any = None) -> dict[str, Any]:
    """Calculate original, simplified and optional biological MIPI.

    WBC is in 10^9/L (equivalently 10^3/µL); raw LDH/ULN must share units.
    If ldh_ratio is given, neither ldh nor ldh_uln may be supplied.
    Risk group comparisons use unrounded scores.
    """
    age_n = _number('age (years)', age, low=18, high=120)
    ecog_n = int(_number('ECOG', ecog, low=0, high=4, integer=True))
    wbc_n = _number('WBC (10^9/L)', wbc, low=0.001, high=1000)
    if ldh_ratio is not None:
        if ldh is not None or ldh_uln is not None:
            raise ValueError('Supply either ldh_ratio or both ldh and ldh_uln')
        ratio = _number('LDH/ULN', ldh_ratio, low=0.001, high=1000)
    else:
        ldh_n = _number('LDH', ldh, low=0.001, high=100000)
        uln_n = _number('LDH ULN', ldh_uln, low=0.001, high=100000)
        ratio = ldh_n / uln_n
    ki67_n = None if ki67 is None or ki67 == '' else _number('Ki-67 (%)', ki67, low=0, high=100)

    # Original MIPI WBC term is per 10^6/L, i.e. 1000 × WBC(10^9/L).
    score = (0.03535 * age_n + (0.6978 if ecog_n > 1 else 0.0)
             + 1.367 * math.log10(ratio) + 0.9393 * math.log10(wbc_n * 1000))
    risk = 'Low' if score < 5.7 else ('Intermediate' if score < 6.2 else 'High')
    simplified = ((0 if age_n < 50 else 1 if age_n < 60 else 2 if age_n < 70 else 3)
                  + (2 if ecog_n >= 2 else 0)
                  + (0 if ratio < 0.67 else 1 if ratio < 1 else 2 if ratio < 1.5 else 3)
                  + (0 if wbc_n < 6.7 else 1 if wbc_n < 10 else 2 if wbc_n < 15 else 3))
    simple_risk = 'Low' if simplified <= 3 else ('Intermediate' if simplified <= 5 else 'High')
    result: dict[str, Any] = {
        'tool': 'mipi-mantle-cell-calculator', 'score': round(score, 4),
        'classification': risk, 'simplified_score': simplified,
        'simplified_classification': simple_risk,
        'ldh_ratio': round(ratio, 6), 'inputs_evaluated': 4 + (ki67_n is not None),
        'clinical_recommendation': 'Prognostic stratification only; interpret with a hematology specialist.',
    }
    if ki67_n is not None:
        biological = score + 0.02142 * ki67_n
        result['biological_score'] = round(biological, 4)
        result['biological_classification'] = ('Low' if biological < 5.7 else
                                                'Intermediate' if biological < 6.5 else 'High')
    return result


def _escape_spreadsheet(value: Any) -> Any:
    """Prevent text fields from becoming formulas in spreadsheet programs."""
    if isinstance(value, str) and value.lstrip().startswith(("=", "+", "-", "@")):
        return "'" + value
    return value


def process_batch(input_csv: str, output_csv: str) -> int:
    """Process CSV with age,ecog,wbc and ldh_ratio or ldh,ldh_uln.

    Invalid records produce an error column instead of fabricated scores.
    """
    if Path(input_csv).resolve() == Path(output_csv).resolve():
        raise ValueError('Input and output files must differ')
    with open(input_csv, encoding='utf-8-sig', newline='') as f:
        reader = csv.DictReader(f)
        fields = list(reader.fieldnames or [])
        if not fields or len(fields) != len(set(fields)):
            raise ValueError('CSV must have nonempty, unique headers')
        required = {'age', 'ecog', 'wbc'}
        if not required.issubset(fields) or not ('ldh_ratio' in fields or {'ldh', 'ldh_uln'}.issubset(fields)):
            raise ValueError('CSV requires age,ecog,wbc and ldh_ratio (or ldh and ldh_uln)')
        outputs = []
        for row in reader:
            if None in row:
                raise ValueError('CSV row has more columns than header')
            kwargs = {k: row[k] for k in ('age', 'ecog', 'wbc', 'ldh', 'ldh_uln', 'ldh_ratio', 'ki67')
                      if k in fields and row[k] not in ('', None)}
            try:
                result = calculate_metrics(**kwargs)
                results = {k: result.get(k, '') for k in ('score', 'classification', 'simplified_score',
                    'simplified_classification', 'biological_score', 'biological_classification')}
                results['error'] = ''
            except (ValueError, TypeError) as exc:
                results = {'error': str(exc)}
            outputs.append({**{key: _escape_spreadsheet(val) for key, val in row.items()}, **results})
    out_fields = [*fields, *[k for k in ('score', 'classification', 'simplified_score',
        'simplified_classification', 'biological_score', 'biological_classification', 'error') if k not in fields]]
    with open(output_csv, 'w', encoding='utf-8', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=out_fields, extrasaction='ignore')
        writer.writeheader()
        writer.writerows(outputs)
    return len(outputs)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description='Mantle Cell Lymphoma International Prognostic Index')
    sub = parser.add_subparsers(dest='command', required=True)
    single = sub.add_parser('single', help='Calculate one case')
    single.add_argument('--age', type=float, required=True, help='Years, 18–120')
    single.add_argument('--ecog', type=int, required=True, help='ECOG 0–4')
    single.add_argument('--wbc', type=float, required=True, help='WBC in 10^9/L')
    ldh_group = single.add_mutually_exclusive_group(required=True)
    ldh_group.add_argument('--ldh', type=float, help='LDH value; requires --ldh-uln')
    ldh_group.add_argument('--ldh-ratio', type=float, help='LDH / laboratory ULN')
    single.add_argument('--ldh-uln', type=float, help='Laboratory upper limit of normal for LDH')
    single.add_argument('--ki67', type=float, help='Optional Ki-67 index (%)')
    batch = sub.add_parser('batch', help='Score local CSV (no network transmission)')
    batch.add_argument('-i', '--input', required=True)
    batch.add_argument('-o', '--output', default='results.csv')
    args = parser.parse_args(argv)
    try:
        if args.command == 'single':
            print(json.dumps(calculate_metrics(age=args.age, ecog=args.ecog, wbc=args.wbc,
                ldh=args.ldh, ldh_uln=args.ldh_uln, ldh_ratio=args.ldh_ratio, ki67=args.ki67), indent=2))
        else:
            print(f'Processed {process_batch(args.input, args.output)} rows into {args.output}')
        return 0
    except (ValueError, OSError, csv.Error) as exc:
        print(f'Error: {exc}', file=sys.stderr)
        return 2


if __name__ == '__main__':
    sys.exit(main())
