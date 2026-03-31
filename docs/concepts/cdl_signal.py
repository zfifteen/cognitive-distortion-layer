#!/usr/bin/env python3
"""
Demonstrate the core CDL insight:

1. kappa(n), together with n, reversibly encodes divisor count:
   round(e^2 * kappa(n) / ln(n)) == d(n)
2. The full-recall threshold for a range ceiling N has a closed form:
   tau(N) = 2 * ln(N) / e^2
3. Under that threshold, false positives from divisor class d are confined to:
   n <= N^(2/d)

This script validates those claims against the repository's canonical
`src/python/cdl.py` implementation and prints the observed behavior on a target
range.
"""

from __future__ import annotations

import argparse
import math
import sys
from collections import defaultdict
from pathlib import Path
from typing import Dict, Iterable, List, Tuple


REPO_ROOT = Path(__file__).resolve().parents[2]
SOURCE_DIR = REPO_ROOT / "src" / "python"
if str(SOURCE_DIR) not in sys.path:
    sys.path.insert(0, str(SOURCE_DIR))

import cdl


E_SQUARED = math.e ** 2


def recovered_divisor_count(n: int) -> int:
    """Recover d(n) from kappa(n) and n."""
    if n <= 1:
        return 0
    return int(round(E_SQUARED * cdl.kappa(n) / math.log(n)))


def derived_threshold(range_ceiling: int) -> float:
    """Closed-form threshold for full prime recall through range_ceiling."""
    if range_ceiling < 2:
        raise ValueError("range_ceiling must be >= 2")
    return 2.0 * math.log(range_ceiling) / E_SQUARED


def implied_prime_ceiling(threshold: float) -> float:
    """Invert threshold -> implied prime ceiling."""
    if threshold <= 0:
        raise ValueError("threshold must be > 0")
    return math.exp(threshold * E_SQUARED / 2.0)


def verify_divisor_recovery(limit: int) -> List[Tuple[int, int, int, float]]:
    """Return any recovery mismatches up to limit."""
    mismatches: List[Tuple[int, int, int, float]] = []
    for n in range(2, limit + 1):
        recovered = recovered_divisor_count(n)
        actual = cdl.divisor_count(n)
        if recovered != actual:
            mismatches.append((n, recovered, actual, cdl.kappa(n)))
    return mismatches


def evaluate_threshold(
    range_min: int,
    range_max: int,
    threshold: float,
) -> Dict[str, object]:
    """Evaluate cdl.classify on a range and group false positives by divisor class."""
    tp = fp = tn = fn = 0
    false_positives: Dict[int, List[int]] = defaultdict(list)
    passing_primes: List[int] = []

    for n in range(range_min, range_max + 1):
        predicted = cdl.classify(n, threshold)
        actual_prime = cdl.is_prime(n)

        if predicted == "prime" and actual_prime:
            tp += 1
            passing_primes.append(n)
        elif predicted == "prime" and not actual_prime:
            fp += 1
            false_positives[cdl.divisor_count(n)].append(n)
        elif predicted == "composite" and actual_prime:
            fn += 1
        else:
            tn += 1

    precision = tp / (tp + fp) if (tp + fp) else 0.0
    recall = tp / (tp + fn) if (tp + fn) else 0.0
    accuracy = (tp + tn) / (tp + fp + tn + fn) if (tp + fp + tn + fn) else 0.0

    groups = []
    for divisor_class in sorted(false_positives):
        values = sorted(false_positives[divisor_class])
        groups.append(
            {
                "divisor_class": divisor_class,
                "count": len(values),
                "min_n": values[0],
                "max_n": values[-1],
            }
        )

    return {
        "threshold": threshold,
        "tp": tp,
        "fp": fp,
        "tn": tn,
        "fn": fn,
        "accuracy": accuracy,
        "precision": precision,
        "recall": recall,
        "passing_primes": passing_primes,
        "false_positive_groups": groups,
    }


def print_recovery_report(limit: int) -> None:
    mismatches = verify_divisor_recovery(limit)
    print("1. Exact divisor recovery from kappa(n)")
    print(f"   Checked n = 2..{limit}")
    print(f"   Mismatches: {len(mismatches)}")
    if mismatches:
        print("   First mismatches:")
        for n, recovered, actual, kappa_value in mismatches[:10]:
            print(
                f"     n={n}: recovered={recovered}, actual={actual}, "
                f"kappa={kappa_value:.12f}"
            )
    else:
        print("   Verified: round(e^2 * kappa(n) / ln(n)) == d(n) across the full check range.")
    print()


def print_threshold_report(range_max: int) -> None:
    tau = derived_threshold(range_max)
    print("2. Closed-form threshold for full prime recall")
    print(f"   Range ceiling N: {range_max}")
    print(f"   Derived tau(N) = 2 ln(N) / e^2 = {tau:.6f}")
    print(f"   Implied prime ceiling from tau(N): {implied_prime_ceiling(tau):.6f}")
    print(f"   Seed reference tau(49): {derived_threshold(49):.6f}")
    print()


def print_evaluation_report(
    label: str,
    range_min: int,
    range_max: int,
    threshold: float,
) -> None:
    report = evaluate_threshold(range_min, range_max, threshold)
    print(f"3. {label}")
    print(f"   Range: {range_min}..{range_max}")
    print(f"   Threshold: {threshold:.6f}")
    print(f"   Accuracy: {report['accuracy']:.4%}")
    print(f"   Precision: {report['precision']:.4%}")
    print(f"   Recall: {report['recall']:.4%}")
    print(
        f"   Counts: TP={report['tp']}, FP={report['fp']}, "
        f"TN={report['tn']}, FN={report['fn']}"
    )

    passing_primes = report["passing_primes"]
    if passing_primes:
        print(
            f"   Passing prime band: {passing_primes[0]}..{passing_primes[-1]} "
            f"({len(passing_primes)} total)"
        )
    else:
        print("   Passing prime band: none")

    groups = report["false_positive_groups"]
    if not groups:
        print("   False positives: none")
    else:
        print("   False positives by divisor class:")
        for group in groups:
            divisor_class = group["divisor_class"]
            predicted_ceiling = range_max ** (2.0 / divisor_class)
            print(
                f"     d={divisor_class}: count={group['count']}, "
                f"observed_n={group['min_n']}..{group['max_n']}, "
                f"predicted_max_n={predicted_ceiling:.3f}"
            )
    print()


def parse_args(argv: Iterable[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Demonstrate the core CDL insight on a target range."
    )
    parser.add_argument(
        "--range-min",
        type=int,
        default=50,
        help="Lower bound of the evaluation range (default: 50).",
    )
    parser.add_argument(
        "--range-max",
        type=int,
        default=10000,
        help="Upper bound of the evaluation range (default: 10000).",
    )
    parser.add_argument(
        "--verify-limit",
        type=int,
        default=10000,
        help="Upper bound for exact divisor recovery verification (default: 10000).",
    )
    parser.add_argument(
        "--reference-threshold",
        type=float,
        default=1.5,
        help="Reference threshold to compare against (default: 1.5).",
    )
    return parser.parse_args(list(argv))


def main(argv: Iterable[str]) -> int:
    args = parse_args(argv)

    if args.range_min < 2:
        raise ValueError("--range-min must be >= 2")
    if args.range_max < args.range_min:
        raise ValueError("--range-max must be >= --range-min")
    if args.verify_limit < 2:
        raise ValueError("--verify-limit must be >= 2")

    derived_tau = derived_threshold(args.range_max)

    print("CDL CORE INSIGHT DEMONSTRATION")
    print("=" * 32)
    print()

    print_recovery_report(args.verify_limit)
    print_threshold_report(args.range_max)
    print_evaluation_report(
        "Evaluation with derived full-recall threshold",
        args.range_min,
        args.range_max,
        derived_tau,
    )
    print_evaluation_report(
        f"Evaluation with reference threshold tau={args.reference_threshold}",
        args.range_min,
        args.range_max,
        args.reference_threshold,
    )

    print("4. Interpretation")
    print(
        f"   tau={args.reference_threshold:.6f} implies a prime ceiling of "
        f"{implied_prime_ceiling(args.reference_threshold):.3f}"
    )
    print(
        "   The derived threshold is not fitted from data. It is the exact "
        "range-conditioned cutoff implied by the prime sheet."
    )
    print(
        "   Under that cutoff, false positives are forced into low-divisor "
        "bands with analytically predicted ceilings."
    )

    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
