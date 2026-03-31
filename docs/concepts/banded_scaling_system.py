#!/usr/bin/env python3
"""
Demonstrate the core CDL insight with a runnable experiment.

Core insight
------------
The curvature score kappa(n) is more stable as a size-banded rarity filter
("keep the sparsest q% in each size band") than as one fixed global threshold.

What this script shows
----------------------
1. A fixed threshold tau=1.5 quickly stops admitting candidates as n grows.
2. A banded equal-coverage filter keeps the admitted fraction stable.
3. The banded threshold must rise with size.
4. For a low enough target coverage, the accepted set keeps a stable structural
   profile: mean divisor count stays near 2, meaning the survivors are mostly
   or entirely primes.

This script uses only the Python standard library.
"""

from __future__ import annotations

import argparse
import math
from typing import Dict, Iterable, List, Sequence, Tuple

E_SQUARED = math.e ** 2


def build_bands(max_n: int) -> List[Tuple[int, int]]:
    """Create human-readable size bands.

    Bands start with the original small seed window 2-49, then move to
    decade-like ranges: 50-99, 100-999, 1000-9999, ...
    """
    if max_n < 2:
        return []

    bands: List[Tuple[int, int]] = [(2, min(49, max_n))]
    if max_n <= 49:
        return bands

    bands.append((50, min(99, max_n)))
    start = 100
    end = 999
    while start <= max_n:
        bands.append((start, min(end, max_n)))
        start *= 10
        end = end * 10 + 9
    return bands


def smallest_prime_factors(limit: int) -> List[int]:
    """Smallest prime factor sieve."""
    spf = list(range(limit + 1))
    if limit >= 0:
        spf[0] = 0
    if limit >= 1:
        spf[1] = 1

    root = int(limit ** 0.5)
    for p in range(2, root + 1):
        if spf[p] != p:
            continue
        start = p * p
        for multiple in range(start, limit + 1, p):
            if spf[multiple] == multiple:
                spf[multiple] = p
    return spf


def divisor_counts_and_primes(limit: int) -> Tuple[List[int], List[bool]]:
    """Compute d(n) and a primality flag for 0..limit.

    Uses the recurrence implied by the smallest-prime-factor sieve.
    """
    spf = smallest_prime_factors(limit)
    divisors = [0] * (limit + 1)
    prime_power = [0] * (limit + 1)
    reduced = [0] * (limit + 1)
    is_prime = [False] * (limit + 1)

    divisors[1] = 1
    for n in range(2, limit + 1):
        p = spf[n]
        m = n // p
        if spf[m] == p:
            prime_power[n] = prime_power[m] + 1
            reduced[n] = reduced[m]
            divisors[n] = divisors[reduced[n]] * (prime_power[n] + 1)
        else:
            prime_power[n] = 1
            reduced[n] = m
            divisors[n] = divisors[m] * 2
        is_prime[n] = divisors[n] == 2

    return divisors, is_prime


def kappas(limit: int, divisors: Sequence[int]) -> List[float]:
    """Compute kappa(n) = d(n) * ln(n) / e^2 for 0..limit."""
    values = [0.0] * (limit + 1)
    for n in range(2, limit + 1):
        values[n] = divisors[n] * math.log(n) / E_SQUARED
    return values


def quantile_threshold(values: Sequence[float], coverage: float) -> float:
    """Return the smallest threshold that admits about `coverage` of the values."""
    if not 0.0 < coverage <= 1.0:
        raise ValueError("coverage must be in the interval (0, 1].")
    if not values:
        raise ValueError("values must not be empty.")

    sorted_values = sorted(values)
    index = math.ceil(coverage * len(sorted_values)) - 1
    index = max(0, min(index, len(sorted_values) - 1))
    return sorted_values[index]


def summarize_band(
    start: int,
    end: int,
    kappa_values: Sequence[float],
    is_prime: Sequence[bool],
    divisors: Sequence[int],
    threshold: float,
    use_strict_less_than: bool,
) -> Dict[str, float]:
    """Summarize one band under one threshold rule."""
    total = end - start + 1
    prime_total = 0
    survivors = 0
    true_positives = 0
    divisor_sum = 0.0

    for n in range(start, end + 1):
        prime_flag = is_prime[n]
        if prime_flag:
            prime_total += 1

        admitted = kappa_values[n] < threshold if use_strict_less_than else kappa_values[n] <= threshold
        if not admitted:
            continue

        survivors += 1
        divisor_sum += divisors[n]
        if prime_flag:
            true_positives += 1

    coverage = survivors / total if total else 0.0
    recall = true_positives / prime_total if prime_total else 0.0
    precision = true_positives / survivors if survivors else 0.0
    mean_divisors = divisor_sum / survivors if survivors else float("nan")

    return {
        "coverage": coverage,
        "recall": recall,
        "precision": precision,
        "survivors": float(survivors),
        "primes": float(prime_total),
        "mean_divisors": mean_divisors,
    }


def format_float(value: float, digits: int = 3) -> str:
    if math.isnan(value):
        return "nan"
    return f"{value:.{digits}f}"


def run_demo(max_n: int, fixed_tau: float, target_coverage: float) -> None:
    bands = build_bands(max_n)
    if not bands:
        raise ValueError("max_n must be at least 2.")

    divisor_counts, prime_flags = divisor_counts_and_primes(max_n)
    kappa_values = kappas(max_n, divisor_counts)

    print("CDL equal-coverage demo")
    print("=" * 80)
    print(f"max_n           : {max_n}")
    print(f"fixed threshold : {fixed_tau}")
    print(f"target coverage : {target_coverage:.3f}")
    print()
    print("Part A: fixed global threshold")
    print("-" * 80)
    print(
        f"{'band':>14} | {'coverage':>8} | {'recall':>8} | {'precision':>9} | {'survivors':>9}"
    )
    print("-" * 80)

    fixed_rows: List[Tuple[int, int, Dict[str, float]]] = []
    for start, end in bands:
        row = summarize_band(
            start,
            end,
            kappa_values,
            prime_flags,
            divisor_counts,
            fixed_tau,
            use_strict_less_than=True,
        )
        fixed_rows.append((start, end, row))
        print(
            f"{f'{start}-{end}':>14} | "
            f"{format_float(row['coverage']):>8} | "
            f"{format_float(row['recall']):>8} | "
            f"{format_float(row['precision']):>9} | "
            f"{int(row['survivors']):>9}"
        )

    print()
    print("Part B: banded equal-coverage filter")
    print("-" * 80)
    print(
        f"{'band':>14} | {'tau_band':>8} | {'coverage':>8} | {'recall':>8} | {'precision':>9} | {'mean d(n)':>9}"
    )
    print("-" * 80)

    adaptive_thresholds: List[float] = []
    adaptive_mean_divisors: List[float] = []
    for start, end in bands:
        band_kappas = kappa_values[start : end + 1]
        tau_band = quantile_threshold(band_kappas, target_coverage)
        adaptive_thresholds.append(tau_band)
        row = summarize_band(
            start,
            end,
            kappa_values,
            prime_flags,
            divisor_counts,
            tau_band,
            use_strict_less_than=False,
        )
        adaptive_mean_divisors.append(row["mean_divisors"])
        print(
            f"{f'{start}-{end}':>14} | "
            f"{format_float(tau_band):>8} | "
            f"{format_float(row['coverage']):>8} | "
            f"{format_float(row['recall']):>8} | "
            f"{format_float(row['precision']):>9} | "
            f"{format_float(row['mean_divisors']):>9}"
        )

    fixed_coverages = [row["coverage"] for _, _, row in fixed_rows]
    print()
    print("Takeaways")
    print("-" * 80)
    print(
        "1. Fixed tau survivor coverage shrinks with size: "
        f"{format_float(fixed_coverages[0])} -> {format_float(fixed_coverages[-1])}."
    )
    print(
        "2. Equal-coverage keeps the admitted width stable while tau_band rises: "
        f"{format_float(adaptive_thresholds[0])} -> {format_float(adaptive_thresholds[-1])}."
    )
    print(
        "3. The accepted set keeps a stable structural profile when mean d(n) stays near 2. "
        f"Observed range: {format_float(min(adaptive_mean_divisors), 3)} to {format_float(max(adaptive_mean_divisors), 3)}."
    )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Demonstrate the equal-coverage CDL insight.")
    parser.add_argument(
        "--max-n",
        type=int,
        default=99_999,
        help="Largest n to analyze. Default: 99999",
    )
    parser.add_argument(
        "--fixed-tau",
        type=float,
        default=1.5,
        help="Global fixed threshold to test. Default: 1.5",
    )
    parser.add_argument(
        "--target-coverage",
        type=float,
        default=0.05,
        help="Fraction to keep in each band for the equal-coverage filter. Default: 0.05",
    )
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()
    run_demo(max_n=args.max_n, fixed_tau=args.fixed_tau, target_coverage=args.target_coverage)
