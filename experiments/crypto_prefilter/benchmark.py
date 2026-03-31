#!/usr/bin/env python3
"""Deterministic benchmark for exact CDL, proxy CDL, and Miller-Rabin control."""

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


DEFAULT_EXACT_BITS = 20
DEFAULT_EXACT_COUNT = 256
DEFAULT_CRYPTO_BITS = 2048
DEFAULT_CRYPTO_COUNT = 1024
DEFAULT_MR_BASES = [2, 3, 5, 7, 11, 13, 17, 19]
DEFAULT_NAMESPACE = "cdl-crypto-prefilter"
DEFAULT_PROXY_TRIAL_PRIME_LIMIT = 7001
SWEET_SPOT_V = math.e ** 2 / 2.0
FIXED_POINT_TOLERANCE = 1e-12
LOG_FLOAT_MIN = math.log(sys.float_info.min)


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


def sieve_primes(limit: int) -> List[int]:
    """Generate primes up to limit with a deterministic sieve."""
    if limit < 2:
        return []

    flags = bytearray(b"\x01") * (limit + 1)
    flags[:2] = b"\x00\x00"
    primes: List[int] = []
    for value in range(2, limit + 1):
        if not flags[value]:
            continue
        primes.append(value)
        start = value * value
        if start <= limit:
            flags[start : limit + 1 : value] = b"\x00" * (((limit - start) // value) + 1)
    return primes


def cheap_cdl_proxy(
    n: int,
    trial_primes: Sequence[int],
) -> Dict[str, float | int | bool | None]:
    """
    Deterministic CDL proxy using a small-prime divisor lower bound.

    This is the narrow deterministic slice of Path 2: reject candidates only when a
    concrete small factor is found. When no small factor is found, the proxy leaves
    the candidate on the prime band (`z_hat = 1.0`) and defers to Miller-Rabin.
    """
    if n < 2:
        return {
            "z_hat": 0.0,
            "d_est": 0.0,
            "rejected": True,
            "smallest_factor": None,
            "residual_bits": 0,
        }

    original_n = n
    residual = n
    d_est = 1.0
    smallest_factor = None
    found_factor = False

    for prime in trial_primes:
        if prime * prime > residual:
            break

        exponent = 0
        while residual % prime == 0:
            residual //= prime
            exponent += 1

        if exponent == 0:
            continue

        found_factor = True
        if smallest_factor is None:
            smallest_factor = prime
        d_est *= exponent + 1

    if found_factor:
        if residual > 1:
            d_est *= 2.0
        log_z = (1.0 - d_est / 2.0) * math.log(original_n)
        z_hat = 0.0 if log_z < LOG_FLOAT_MIN else math.exp(log_z)
    else:
        d_est = 2.0
        z_hat = 1.0

    return {
        "z_hat": z_hat,
        "d_est": d_est,
        "rejected": bool(z_hat < 1.0 - FIXED_POINT_TOLERANCE),
        "smallest_factor": smallest_factor,
        "residual_bits": residual.bit_length() if residual > 0 else 0,
    }


def summarize_binary_classification(
    predicted_primes: Sequence[bool],
    truth_primes: Sequence[bool],
) -> Dict[str, float | int]:
    """Summarize binary prime/composite predictions."""
    tp = fp = tn = fn = 0
    for predicted_prime, truth_prime in zip(predicted_primes, truth_primes):
        if predicted_prime and truth_prime:
            tp += 1
        elif predicted_prime and not truth_prime:
            fp += 1
        elif not predicted_prime and truth_prime:
            fn += 1
        else:
            tn += 1

    total = len(predicted_primes)
    accuracy = (tp + tn) / total if total else 0.0
    precision = tp / (tp + fp) if (tp + fp) else 0.0
    recall = tp / (tp + fn) if (tp + fn) else 0.0
    f1 = 2.0 * precision * recall / (precision + recall) if (precision + recall) else 0.0
    return {
        "accuracy": accuracy,
        "precision": precision,
        "recall": recall,
        "f1_score": f1,
        "true_positives": tp,
        "false_positives": fp,
        "true_negatives": tn,
        "false_negatives": fn,
    }


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


def run_proxy_calibration(
    candidates: Sequence[int],
    trial_primes: Sequence[int],
) -> Dict:
    """Benchmark the deterministic CDL proxy on the tractable calibration corpus."""
    proxy_durations_ns: List[int] = []
    proxy_prime_predictions: List[bool] = []
    truth_primes: List[bool] = []
    fixed_points = 0
    false_fixed_points = 0
    strict_contractions = 0

    for n in candidates:
        truth_is_prime = bool(isprime(n))
        truth_primes.append(truth_is_prime)

        start_ns = time.perf_counter_ns()
        proxy = cheap_cdl_proxy(n, trial_primes)
        proxy_durations_ns.append(time.perf_counter_ns() - start_ns)

        predicted_prime = not bool(proxy["rejected"])
        proxy_prime_predictions.append(predicted_prime)

        z_hat = float(proxy["z_hat"])
        if math.isclose(z_hat, 1.0, rel_tol=FIXED_POINT_TOLERANCE, abs_tol=FIXED_POINT_TOLERANCE):
            fixed_points += 1
            if not truth_is_prime:
                false_fixed_points += 1
        elif not truth_is_prime and z_hat < 1.0:
            strict_contractions += 1

    metrics = summarize_binary_classification(proxy_prime_predictions, truth_primes)
    return {
        "candidate_source": "deterministic_sha256_odd_stream",
        "candidate_count": len(candidates),
        "bit_length": max(n.bit_length() for n in candidates),
        "trial_prime_limit": max(trial_primes) if trial_primes else 0,
        "trial_prime_count": len(trial_primes),
        "fixed_points": fixed_points,
        "false_fixed_points": false_fixed_points,
        "strict_contractions": strict_contractions,
        "timing_ms": summarize_durations_ms(proxy_durations_ns),
        "classification": metrics,
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


def run_proxy_crypto_pipeline(
    candidates: Sequence[int],
    trial_primes: Sequence[int],
    mr_bases: Sequence[int],
    truth_check: bool = False,
) -> Dict:
    """Benchmark the deterministic proxy followed by Miller-Rabin on survivors."""
    proxy_durations_ns: List[int] = []
    mr_durations_ns: List[int] = []
    pipeline_durations_ns: List[int] = []
    rejected_by_proxy = 0
    survivors = 0
    pass_count = 0
    first_pass_index = None
    truth_primes: List[bool] = []
    predicted_primes: List[bool] = []

    for index, n in enumerate(candidates):
        truth_is_prime = bool(isprime(n)) if truth_check else False
        if truth_check:
            truth_primes.append(truth_is_prime)

        start_ns = time.perf_counter_ns()
        proxy = cheap_cdl_proxy(n, trial_primes)
        proxy_duration = time.perf_counter_ns() - start_ns
        proxy_durations_ns.append(proxy_duration)

        if bool(proxy["rejected"]):
            rejected_by_proxy += 1
            pipeline_durations_ns.append(proxy_duration)
            if truth_check:
                predicted_primes.append(False)
            continue

        survivors += 1
        start_ns = time.perf_counter_ns()
        mr_passed = miller_rabin_fixed_bases(n, mr_bases)
        mr_duration = time.perf_counter_ns() - start_ns
        mr_durations_ns.append(mr_duration)
        pipeline_durations_ns.append(proxy_duration + mr_duration)

        if mr_passed:
            pass_count += 1
            if first_pass_index is None:
                first_pass_index = index

        if truth_check:
            predicted_primes.append(mr_passed)

    results = {
        "candidate_source": "deterministic_sha256_odd_stream",
        "candidate_count": len(candidates),
        "bit_length": max(n.bit_length() for n in candidates),
        "trial_prime_limit": max(trial_primes) if trial_primes else 0,
        "trial_prime_count": len(trial_primes),
        "rejected_by_proxy": rejected_by_proxy,
        "rejection_rate": rejected_by_proxy / len(candidates),
        "survivors_to_miller_rabin": survivors,
        "survivor_rate": survivors / len(candidates),
        "miller_rabin_pass_count": pass_count,
        "first_pass_index": first_pass_index,
        "proxy_timing_ms": summarize_durations_ms(proxy_durations_ns),
        "miller_rabin_survivor_timing_ms": (
            summarize_durations_ms(mr_durations_ns)
            if mr_durations_ns
            else {"mean": 0.0, "median": 0.0, "min": 0.0, "max": 0.0}
        ),
        "pipeline_timing_ms": summarize_durations_ms(pipeline_durations_ns),
        "candidate_preview": [compact_hex(n) for n in candidates[:3]],
    }

    if truth_check:
        results["classification"] = summarize_binary_classification(predicted_primes, truth_primes)

    return results


def build_report_markdown(results: Dict) -> str:
    """Build a concise markdown report for the benchmark run."""
    calibration = results["exact_calibration"]
    proxy_calibration = results["proxy_calibration"]
    crypto = results["crypto_control"]
    proxy_crypto = results["proxy_crypto_pipeline"]
    mr_small = calibration["miller_rabin_control"]
    exact_to_mr_ratio = calibration["z_timing_ms"]["mean"] / mr_small["timing_ms"]["mean"]
    proxy_speedup = crypto["timing_ms"]["mean"] / proxy_crypto["pipeline_timing_ms"]["mean"]
    first_pass_text = (
        str(crypto["first_pass_index"])
        if crypto["first_pass_index"] is not None
        else "none in corpus"
    )
    proxy_first_pass_text = (
        str(proxy_crypto["first_pass_index"])
        if proxy_crypto["first_pass_index"] is not None
        else "none in corpus"
    )
    proxy_metrics = proxy_calibration["classification"]

    lines = [
        "# Crypto Prefilter Benchmark Report",
        "",
        f"Date: {results['experiment_date']}",
        "",
        "This report benchmarks the exact sweet-spot CDL path where the current implementation is executable,",
        "a deterministic CDL proxy based on small-prime divisor lower bounds,",
        "and fixed-base Miller-Rabin on deterministic cryptographic-scale odd candidates.",
        "",
        "## Configuration",
        "",
        f"- `sweet_spot_v`: {SWEET_SPOT_V:.12f}",
        f"- `exact_bits`: {results['configuration']['exact_bits']}",
        f"- `exact_count`: {results['configuration']['exact_count']}",
        f"- `crypto_bits`: {results['configuration']['crypto_bits']}",
        f"- `crypto_count`: {results['configuration']['crypto_count']}",
        f"- `proxy_trial_prime_limit`: {results['configuration']['proxy_trial_prime_limit']}",
        f"- `miller_rabin_bases`: {results['configuration']['mr_bases']}",
        f"- `truth_check`: {results['configuration']['truth_check']}",
        "",
        "## Headline Findings",
        "",
        f"- Sweet-spot Z-space hit the fixed-point band for `{calibration['numeric_fixed_points']}` of `{calibration['prime_count']}` calibration primes within numeric tolerance, with `{calibration['numeric_false_fixed_points']}` fixed-point composites.",
        f"- The deterministic proxy hit `{proxy_calibration['fixed_points']}` fixed points on the same calibration corpus with `{proxy_calibration['false_fixed_points']}` composite fixed points and calibration accuracy `{proxy_metrics['accuracy']:.2%}`.",
        f"- On the same `{calibration['bit_length']}`-bit calibration corpus, fixed-base Miller-Rabin matched exact primality with accuracy `{mr_small['accuracy']:.2%}`.",
        f"- Mean runtime on the calibration corpus was `{calibration['z_timing_ms']['mean']:.6f}` ms per candidate for exact sweet-spot `z_normalize`, `{proxy_calibration['timing_ms']['mean']:.6f}` ms for the deterministic proxy, and `{mr_small['timing_ms']['mean']:.6f}` ms for Miller-Rabin.",
        f"- On the `{crypto['bit_length']}`-bit control corpus, Miller-Rabin averaged `{crypto['timing_ms']['mean']:.6f}` ms per candidate and passed `{crypto['miller_rabin_pass_count']}` of `{crypto['candidate_count']}` odd candidates; first pass index: `{first_pass_text}`.",
        f"- The deterministic proxy rejected `{proxy_crypto['rejected_by_proxy']}` of `{proxy_crypto['candidate_count']}` cryptographic candidates before Miller-Rabin (`{proxy_crypto['rejection_rate']:.2%}`), cut the end-to-end pipeline to `{proxy_crypto['pipeline_timing_ms']['mean']:.6f}` ms per candidate, and delivered a measured `{proxy_speedup:.2f}x` speedup over Miller-Rabin alone on this corpus.",
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
        "## Proxy Calibration",
        "",
        "| Metric | Value |",
        "|---|---:|",
        f"| Trial prime limit | {proxy_calibration['trial_prime_limit']} |",
        f"| Trial prime count | {proxy_calibration['trial_prime_count']} |",
        f"| Fixed points | {proxy_calibration['fixed_points']} |",
        f"| Composite false fixed points | {proxy_calibration['false_fixed_points']} |",
        f"| Strict composite contractions | {proxy_calibration['strict_contractions']} |",
        f"| Accuracy | {proxy_metrics['accuracy']:.6%} |",
        f"| Precision | {proxy_metrics['precision']:.6%} |",
        f"| Recall | {proxy_metrics['recall']:.6%} |",
        f"| Mean proxy time (ms) | {proxy_calibration['timing_ms']['mean']:.6f} |",
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
        "## Proxy + Miller-Rabin Pipeline",
        "",
        "| Metric | Value |",
        "|---|---:|",
        f"| Trial prime limit | {proxy_crypto['trial_prime_limit']} |",
        f"| Trial prime count | {proxy_crypto['trial_prime_count']} |",
        f"| Rejected before Miller-Rabin | {proxy_crypto['rejected_by_proxy']} |",
        f"| Rejection rate | {proxy_crypto['rejection_rate']:.6%} |",
        f"| Survivors to Miller-Rabin | {proxy_crypto['survivors_to_miller_rabin']} |",
        f"| Survivor rate | {proxy_crypto['survivor_rate']:.6%} |",
        f"| Miller-Rabin passes after proxy | {proxy_crypto['miller_rabin_pass_count']} |",
        f"| First pass index after proxy | {proxy_first_pass_text} |",
        f"| Mean proxy time (ms) | {proxy_crypto['proxy_timing_ms']['mean']:.6f} |",
        f"| Mean survivor Miller-Rabin time (ms) | {proxy_crypto['miller_rabin_survivor_timing_ms']['mean']:.6f} |",
        f"| Mean pipeline time (ms) | {proxy_crypto['pipeline_timing_ms']['mean']:.6f} |",
        f"| Speedup vs MR-only | {proxy_speedup:.6f}x |",
        "",
        "## Calibration Timing Ratios",
        "",
        "| Ratio | Value |",
        "|---|---:|",
        f"| Exact CDL / Miller-Rabin | {exact_to_mr_ratio:.6f}x |",
        f"| Exact CDL / Proxy | {calibration['z_timing_ms']['mean'] / proxy_calibration['timing_ms']['mean']:.6f}x |",
        f"| Proxy / Miller-Rabin | {proxy_calibration['timing_ms']['mean'] / mr_small['timing_ms']['mean']:.6f}x |",
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
    proxy_trial_prime_limit: int,
    mr_bases: Sequence[int],
    truth_check: bool,
) -> Dict:
    """Run the exact calibration and crypto control benchmark."""
    exact_candidates = deterministic_odd_candidates(exact_bits, exact_count)
    crypto_candidates = deterministic_odd_candidates(crypto_bits, crypto_count)
    proxy_trial_primes = [prime for prime in sieve_primes(proxy_trial_prime_limit) if prime != 2]

    exact_calibration = run_exact_calibration(exact_candidates, mr_bases=mr_bases)
    proxy_calibration = run_proxy_calibration(exact_candidates, trial_primes=proxy_trial_primes)
    crypto_control = run_crypto_control(
        crypto_candidates,
        mr_bases=mr_bases,
        truth_check=truth_check,
    )
    proxy_crypto_pipeline = run_proxy_crypto_pipeline(
        crypto_candidates,
        trial_primes=proxy_trial_primes,
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
            "proxy_trial_prime_limit": proxy_trial_prime_limit,
            "mr_bases": list(mr_bases),
            "truth_check": truth_check,
        },
        "exact_scaling_boundary": {
            "divisor_count_implementation": "O(sqrt n) enumeration",
            "sqrt_space_bits": crypto_bits // 2,
            "worst_case_candidate_bits": crypto_bits,
        },
        "exact_calibration": exact_calibration,
        "proxy_calibration": proxy_calibration,
        "crypto_control": crypto_control,
        "proxy_crypto_pipeline": proxy_crypto_pipeline,
        "reproduction_command": (
            "python3 experiments/crypto_prefilter/benchmark.py "
            f"--exact-bits {exact_bits} "
            f"--exact-count {exact_count} "
            f"--crypto-bits {crypto_bits} "
            f"--crypto-count {crypto_count} "
            f"--proxy-trial-prime-limit {proxy_trial_prime_limit} "
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
        "--proxy-trial-prime-limit",
        type=int,
        default=DEFAULT_PROXY_TRIAL_PRIME_LIMIT,
        help=(
            "Largest odd prime tested by the deterministic proxy before falling through "
            f"to Miller-Rabin (default: {DEFAULT_PROXY_TRIAL_PRIME_LIMIT})."
        ),
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
        proxy_trial_prime_limit=args.proxy_trial_prime_limit,
        mr_bases=args.mr_bases,
        truth_check=args.truth_check,
    )

    calibration = results["exact_calibration"]
    proxy_calibration = results["proxy_calibration"]
    crypto = results["crypto_control"]
    proxy_crypto = results["proxy_crypto_pipeline"]
    print("crypto prefilter benchmark complete")
    print(
        "exact calibration:",
        f"{calibration['numeric_fixed_points']} fixed points,",
        f"{calibration['numeric_false_fixed_points']} composite fixed points,",
        f"{calibration['z_timing_ms']['mean']:.6f} ms/candidate",
    )
    print(
        "proxy calibration:",
        f"{proxy_calibration['fixed_points']} fixed points,",
        f"{proxy_calibration['false_fixed_points']} composite fixed points,",
        f"{proxy_calibration['timing_ms']['mean']:.6f} ms/candidate",
    )
    print(
        "crypto control:",
        f"{crypto['miller_rabin_pass_count']} MR passes in {crypto['candidate_count']} candidates,",
        f"{crypto['timing_ms']['mean']:.6f} ms/candidate",
    )
    print(
        "proxy pipeline:",
        f"{proxy_crypto['rejected_by_proxy']} rejected before MR,",
        f"{proxy_crypto['pipeline_timing_ms']['mean']:.6f} ms/candidate",
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
