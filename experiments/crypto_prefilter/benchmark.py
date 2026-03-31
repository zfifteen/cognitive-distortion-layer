#!/usr/bin/env python3
"""Deterministic benchmark for exact CDL calibration and Miller-Rabin control."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import statistics
import sys
import time
from pathlib import Path
from typing import Dict, Iterable, List, Sequence

from sympy import isprime


ROOT = Path(__file__).resolve().parents[2]
SOURCE_DIR = ROOT / "src" / "python"
if str(SOURCE_DIR) not in sys.path:
    sys.path.insert(0, str(SOURCE_DIR))

import cdl


DEFAULT_EXACT_BITS = 24
DEFAULT_EXACT_COUNT = 256
DEFAULT_CRYPTO_BITS = 2048
DEFAULT_CRYPTO_COUNT = 512
DEFAULT_MR_BASES = [2, 3, 5, 7, 11, 13, 17, 19]
DEFAULT_NAMESPACE = "cdl-crypto-prefilter"
SWEET_SPOT_V = math.e ** 2 / 2.0
FIXED_POINT_TOLERANCE = 1e-12


def deterministic_odd_candidate(
    bit_length: int,
    index: int,
    namespace: str = DEFAULT_NAMESPACE,
) -> int:
    """Build one deterministic odd candidate with the requested bit length."""
    if bit_length < 2:
        raise ValueError("bit_length must be at least 2")
    if index < 0:
        raise ValueError("index must be non-negative")

    byte_length = (bit_length + 7) // 8
    digest = bytearray()
    counter = 0
    while len(digest) < byte_length:
        payload = f"{namespace}:{bit_length}:{index}:{counter}".encode("utf-8")
        digest.extend(hashlib.sha256(payload).digest())
        counter += 1

    value = int.from_bytes(digest[:byte_length], "big")
    value &= (1 << bit_length) - 1
    value |= 1 << (bit_length - 1)
    value |= 1
    return value


def deterministic_odd_candidates(
    bit_length: int,
    count: int,
    namespace: str = DEFAULT_NAMESPACE,
) -> List[int]:
    """Build a deterministic, duplicate-free odd candidate corpus."""
    if count < 1:
        raise ValueError("count must be at least 1")

    candidates: List[int] = []
    seen = set()
    index = 0
    while len(candidates) < count:
        candidate = deterministic_odd_candidate(bit_length, index, namespace=namespace)
        index += 1
        if candidate in seen:
            continue
        seen.add(candidate)
        candidates.append(candidate)
    return candidates


def miller_rabin_fixed_bases(n: int, bases: Sequence[int]) -> bool:
    """Run a fixed-base Miller-Rabin probable-prime test."""
    if n < 2:
        return False

    small_primes = (2, 3, 5, 7, 11, 13, 17, 19, 23, 29, 31, 37)
    if n in small_primes:
        return True
    for p in small_primes:
        if n % p == 0:
            return False

    d = n - 1
    s = 0
    while d % 2 == 0:
        d //= 2
        s += 1

    for base in bases:
        a = base % n
        if a in (0, 1, n - 1):
            continue

        x = pow(a, d, n)
        if x in (1, n - 1):
            continue

        witness_failed = True
        for _ in range(s - 1):
            x = pow(x, 2, n)
            if x == n - 1:
                witness_failed = False
                break

        if witness_failed:
            return False

    return True


def summarize_durations_ms(durations_ns: Sequence[int]) -> Dict[str, float]:
    """Summarize timing samples in milliseconds."""
    durations_ms = [value / 1_000_000.0 for value in durations_ns]
    return {
        "mean": statistics.fmean(durations_ms),
        "median": statistics.median(durations_ms),
        "min": min(durations_ms),
        "max": max(durations_ms),
    }


def compact_hex(n: int, edge: int = 16) -> str:
    """Render a compact hex preview for reports."""
    text = format(n, "x")
    if len(text) <= edge * 2:
        return f"0x{text}"
    return f"0x{text[:edge]}...{text[-edge:]}"


def run_exact_calibration(
    candidates: Sequence[int],
    mr_bases: Sequence[int],
) -> Dict:
    """Benchmark the current exact CDL path on a tractable corpus."""
    z_durations_ns: List[int] = []
    mr_durations_ns: List[int] = []
    prime_kappas: List[float] = []
    composite_kappas: List[float] = []

    prime_count = 0
    composite_count = 0
    algebraic_fixed_points = 0
    numeric_fixed_points = 0
    numeric_false_fixed_points = 0
    strict_contractions = 0
    mr_true_positives = 0
    mr_true_negatives = 0
    mr_false_positives = 0
    mr_false_negatives = 0

    for n in candidates:
        start_ns = time.perf_counter_ns()
        z_value = cdl.z_normalize(n, v=SWEET_SPOT_V)
        z_durations_ns.append(time.perf_counter_ns() - start_ns)

        divisor_count = cdl.divisor_count(n)
        kappa_value = divisor_count * math.log(n) / (math.e ** 2)
        truth_is_prime = bool(isprime(n))
        fixed_point_by_divisor_count = divisor_count == 2
        fixed_point_by_numeric_z = math.isclose(
            z_value,
            1.0,
            rel_tol=FIXED_POINT_TOLERANCE,
            abs_tol=FIXED_POINT_TOLERANCE,
        )

        if truth_is_prime:
            prime_count += 1
            prime_kappas.append(kappa_value)
        else:
            composite_count += 1
            composite_kappas.append(kappa_value)

        if fixed_point_by_divisor_count:
            algebraic_fixed_points += 1
        if fixed_point_by_numeric_z:
            numeric_fixed_points += 1
            if not truth_is_prime:
                numeric_false_fixed_points += 1
        elif not truth_is_prime and z_value < 1.0:
            strict_contractions += 1

        start_ns = time.perf_counter_ns()
        mr_passed = miller_rabin_fixed_bases(n, mr_bases)
        mr_durations_ns.append(time.perf_counter_ns() - start_ns)

        if mr_passed and truth_is_prime:
            mr_true_positives += 1
        elif mr_passed and not truth_is_prime:
            mr_false_positives += 1
        elif not mr_passed and truth_is_prime:
            mr_false_negatives += 1
        else:
            mr_true_negatives += 1

    total = len(candidates)
    prime_mean = statistics.fmean(prime_kappas) if prime_kappas else 0.0
    composite_mean = statistics.fmean(composite_kappas) if composite_kappas else 0.0
    separation_ratio = composite_mean / prime_mean if prime_mean else 0.0
    mr_accuracy = (mr_true_positives + mr_true_negatives) / total if total else 0.0

    return {
        "candidate_source": "deterministic_sha256_odd_stream",
        "candidate_count": total,
        "bit_length": max(n.bit_length() for n in candidates),
        "prime_count": prime_count,
        "composite_count": composite_count,
        "sweet_spot_v": SWEET_SPOT_V,
        "prime_kappa_mean": prime_mean,
        "composite_kappa_mean": composite_mean,
        "separation_ratio": separation_ratio,
        "algebraic_fixed_points": algebraic_fixed_points,
        "numeric_fixed_points": numeric_fixed_points,
        "numeric_false_fixed_points": numeric_false_fixed_points,
        "strict_contractions": strict_contractions,
        "z_timing_ms": summarize_durations_ms(z_durations_ns),
        "miller_rabin_control": {
            "bases": list(mr_bases),
            "timing_ms": summarize_durations_ms(mr_durations_ns),
            "accuracy": mr_accuracy,
            "true_positives": mr_true_positives,
            "true_negatives": mr_true_negatives,
            "false_positives": mr_false_positives,
            "false_negatives": mr_false_negatives,
        },
        "candidate_preview": [compact_hex(n) for n in candidates[:3]],
    }


def run_crypto_control(
    candidates: Sequence[int],
    mr_bases: Sequence[int],
    truth_check: bool = False,
) -> Dict:
    """Benchmark fixed-base Miller-Rabin on cryptographic-size candidates."""
    durations_ns: List[int] = []
    pass_count = 0
    first_pass_index = None
    sympy_prime_count = 0
    disagreements = 0

    for index, n in enumerate(candidates):
        start_ns = time.perf_counter_ns()
        mr_passed = miller_rabin_fixed_bases(n, mr_bases)
        durations_ns.append(time.perf_counter_ns() - start_ns)

        if mr_passed:
            pass_count += 1
            if first_pass_index is None:
                first_pass_index = index

        if truth_check:
            truth_is_prime = bool(isprime(n))
            if truth_is_prime:
                sympy_prime_count += 1
            if truth_is_prime != mr_passed:
                disagreements += 1

    results = {
        "candidate_source": "deterministic_sha256_odd_stream",
        "candidate_count": len(candidates),
        "bit_length": max(n.bit_length() for n in candidates),
        "miller_rabin_bases": list(mr_bases),
        "miller_rabin_pass_count": pass_count,
        "miller_rabin_pass_rate": pass_count / len(candidates),
        "first_pass_index": first_pass_index,
        "timing_ms": summarize_durations_ms(durations_ns),
        "candidate_preview": [compact_hex(n) for n in candidates[:3]],
    }

    if truth_check:
        results["sympy_truth"] = {
            "prime_count": sympy_prime_count,
            "disagreements": disagreements,
        }

    return results


def build_report_markdown(results: Dict) -> str:
    """Build a concise markdown report for the benchmark run."""
    calibration = results["exact_calibration"]
    crypto = results["crypto_control"]
    mr_small = calibration["miller_rabin_control"]
    mean_ratio = calibration["z_timing_ms"]["mean"] / mr_small["timing_ms"]["mean"]
    ratio_text = f"{mean_ratio:.2f}x"
    first_pass_text = (
        str(crypto["first_pass_index"])
        if crypto["first_pass_index"] is not None
        else "none in corpus"
    )

    lines = [
        "# Crypto Prefilter Benchmark Report",
        "",
        f"Date: {results['experiment_date']}",
        "",
        "This report benchmarks the exact sweet-spot CDL path where the current implementation is executable,",
        "and fixed-base Miller-Rabin on deterministic cryptographic-scale odd candidates.",
        "",
        "## Configuration",
        "",
        f"- `sweet_spot_v`: {SWEET_SPOT_V:.12f}",
        f"- `exact_bits`: {results['configuration']['exact_bits']}",
        f"- `exact_count`: {results['configuration']['exact_count']}",
        f"- `crypto_bits`: {results['configuration']['crypto_bits']}",
        f"- `crypto_count`: {results['configuration']['crypto_count']}",
        f"- `miller_rabin_bases`: {results['configuration']['mr_bases']}",
        f"- `truth_check`: {results['configuration']['truth_check']}",
        "",
        "## Headline Findings",
        "",
        f"- Sweet-spot Z-space hit the fixed-point band for `{calibration['numeric_fixed_points']}` of `{calibration['prime_count']}` calibration primes within numeric tolerance, with `{calibration['numeric_false_fixed_points']}` fixed-point composites.",
        f"- On the same `{calibration['bit_length']}`-bit calibration corpus, fixed-base Miller-Rabin matched exact primality with accuracy `{mr_small['accuracy']:.2%}`.",
        f"- Mean runtime on the calibration corpus was `{calibration['z_timing_ms']['mean']:.6f}` ms per candidate for exact sweet-spot `z_normalize` versus `{mr_small['timing_ms']['mean']:.6f}` ms for Miller-Rabin, a ratio of `{ratio_text}`.",
        f"- On the `{crypto['bit_length']}`-bit control corpus, Miller-Rabin averaged `{crypto['timing_ms']['mean']:.6f}` ms per candidate and passed `{crypto['miller_rabin_pass_count']}` of `{crypto['candidate_count']}` odd candidates; first pass index: `{first_pass_text}`.",
        f"- The current exact CDL path was intentionally not run on `{results['configuration']['crypto_bits']}`-bit arbitrary candidates because `src/python/cdl.py` computes divisor count by `O(sqrt n)` enumeration; the implied trial space is about `2^{results['exact_scaling_boundary']['sqrt_space_bits']}` divisibility checks per worst-case candidate.",
        "",
        "## Exact Calibration",
        "",
        "| Metric | Value |",
        "|---|---:|",
        f"| Candidate count | {calibration['candidate_count']} |",
        f"| Prime count | {calibration['prime_count']} |",
        f"| Composite count | {calibration['composite_count']} |",
        f"| Prime mean kappa | {calibration['prime_kappa_mean']:.6f} |",
        f"| Composite mean kappa | {calibration['composite_kappa_mean']:.6f} |",
        f"| Separation ratio | {calibration['separation_ratio']:.6f} |",
        f"| Algebraic fixed points | {calibration['algebraic_fixed_points']} |",
        f"| Numeric fixed points | {calibration['numeric_fixed_points']} |",
        f"| Numeric false fixed points | {calibration['numeric_false_fixed_points']} |",
        f"| Strict composite contractions | {calibration['strict_contractions']} |",
        f"| Mean exact `z_normalize` time (ms) | {calibration['z_timing_ms']['mean']:.6f} |",
        f"| Mean Miller-Rabin time (ms) | {mr_small['timing_ms']['mean']:.6f} |",
        "",
        "## Crypto Control",
        "",
        "| Metric | Value |",
        "|---|---:|",
        f"| Candidate count | {crypto['candidate_count']} |",
        f"| Miller-Rabin pass count | {crypto['miller_rabin_pass_count']} |",
        f"| Miller-Rabin pass rate | {crypto['miller_rabin_pass_rate']:.6%} |",
        f"| First pass index | {first_pass_text} |",
        f"| Mean Miller-Rabin time (ms) | {crypto['timing_ms']['mean']:.6f} |",
        "",
        "## Reproduction",
        "",
        "Run the benchmark again with:",
        "",
        "```bash",
        results["reproduction_command"],
        "```",
        "",
        "The JSON artifact in this directory is the machine-readable record of the run.",
        "",
    ]
    return "\n".join(lines) + "\n"


def run_benchmark(
    output_dir: Path,
    exact_bits: int,
    exact_count: int,
    crypto_bits: int,
    crypto_count: int,
    mr_bases: Sequence[int],
    truth_check: bool,
) -> Dict:
    """Run the exact calibration and crypto control benchmark."""
    exact_candidates = deterministic_odd_candidates(exact_bits, exact_count)
    crypto_candidates = deterministic_odd_candidates(crypto_bits, crypto_count)

    exact_calibration = run_exact_calibration(exact_candidates, mr_bases=mr_bases)
    crypto_control = run_crypto_control(
        crypto_candidates,
        mr_bases=mr_bases,
        truth_check=truth_check,
    )

    output_dir.mkdir(parents=True, exist_ok=True)
    results = {
        "experiment_date": time.strftime("%Y-%m-%d"),
        "configuration": {
            "exact_bits": exact_bits,
            "exact_count": exact_count,
            "crypto_bits": crypto_bits,
            "crypto_count": crypto_count,
            "mr_bases": list(mr_bases),
            "truth_check": truth_check,
        },
        "exact_scaling_boundary": {
            "divisor_count_implementation": "O(sqrt n) enumeration",
            "sqrt_space_bits": crypto_bits // 2,
            "worst_case_candidate_bits": crypto_bits,
        },
        "exact_calibration": exact_calibration,
        "crypto_control": crypto_control,
        "reproduction_command": (
            "python3 experiments/crypto_prefilter/benchmark.py "
            f"--exact-bits {exact_bits} "
            f"--exact-count {exact_count} "
            f"--crypto-bits {crypto_bits} "
            f"--crypto-count {crypto_count} "
            f"--mr-bases {' '.join(str(base) for base in mr_bases)}"
            + (" --truth-check" if truth_check else "")
        ),
    }

    json_path = output_dir / "benchmark_results.json"
    markdown_path = output_dir / "BENCHMARK_REPORT.md"
    json_path.write_text(json.dumps(results, indent=2) + "\n", encoding="utf-8")
    markdown_path.write_text(build_report_markdown(results), encoding="utf-8")

    return results


def parse_args(argv: Iterable[str] | None = None) -> argparse.Namespace:
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(
        description="Deterministic benchmark for exact CDL calibration and Miller-Rabin control."
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=ROOT / "experiments" / "crypto_prefilter",
        help="Directory for JSON and Markdown artifacts.",
    )
    parser.add_argument(
        "--exact-bits",
        type=int,
        default=DEFAULT_EXACT_BITS,
        help=f"Bit length for the tractable exact calibration corpus (default: {DEFAULT_EXACT_BITS}).",
    )
    parser.add_argument(
        "--exact-count",
        type=int,
        default=DEFAULT_EXACT_COUNT,
        help=f"Candidate count for the exact calibration corpus (default: {DEFAULT_EXACT_COUNT}).",
    )
    parser.add_argument(
        "--crypto-bits",
        type=int,
        default=DEFAULT_CRYPTO_BITS,
        help=f"Bit length for the cryptographic control corpus (default: {DEFAULT_CRYPTO_BITS}).",
    )
    parser.add_argument(
        "--crypto-count",
        type=int,
        default=DEFAULT_CRYPTO_COUNT,
        help=f"Candidate count for the cryptographic control corpus (default: {DEFAULT_CRYPTO_COUNT}).",
    )
    parser.add_argument(
        "--mr-bases",
        type=int,
        nargs="+",
        default=DEFAULT_MR_BASES,
        help=f"Fixed Miller-Rabin bases (default: {' '.join(str(base) for base in DEFAULT_MR_BASES)}).",
    )
    parser.add_argument(
        "--truth-check",
        action="store_true",
        help="Cross-check the cryptographic control corpus with sympy.isprime.",
    )
    return parser.parse_args(argv)


def main(argv: Iterable[str] | None = None) -> int:
    """Run the benchmark and print a compact summary."""
    args = parse_args(argv)
    results = run_benchmark(
        output_dir=args.output_dir,
        exact_bits=args.exact_bits,
        exact_count=args.exact_count,
        crypto_bits=args.crypto_bits,
        crypto_count=args.crypto_count,
        mr_bases=args.mr_bases,
        truth_check=args.truth_check,
    )

    calibration = results["exact_calibration"]
    crypto = results["crypto_control"]
    print("crypto prefilter benchmark complete")
    print(
        "exact calibration:",
        f"{calibration['numeric_fixed_points']} fixed points,",
        f"{calibration['numeric_false_fixed_points']} composite fixed points,",
        f"{calibration['z_timing_ms']['mean']:.6f} ms/candidate",
    )
    print(
        "crypto control:",
        f"{crypto['miller_rabin_pass_count']} MR passes in {crypto['candidate_count']} candidates,",
        f"{crypto['timing_ms']['mean']:.6f} ms/candidate",
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
