#!/usr/bin/env python3
"""
Path A probe: Kappa vs divisor Gap-Winner divergence (empirical only).

Inside each prime gap (p, q), compare:
  w_d = leftmost argmin of d(n) among p < n < q   (PGS Gap Winner)
  w_k = leftmost argmin of kappa(n) among p < n < q

Hypothesis under test:
  w_d and w_k coincide on short gaps, and systematically diverge when gap
  length is long enough that ln(n) variation competes with discrete d(n) jumps.

Also records the theoretical inversion condition:
  an earlier m < w_d can beat w_d under kappa only if
  d(m)/d(w_d) < ln(w_d)/ln(m).

Usage:
  PYTHONPATH=.../src/python python probe_kappa_vs_d_gap_winner.py
  PYTHONPATH=.../src/python python probe_kappa_vs_d_gap_winner.py --limit 500000
"""

from __future__ import annotations

import argparse
import json
import math
import os
import sys
import time
from collections import defaultdict
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

# Parent CDL import
_REPO = Path(__file__).resolve().parents[2]
_SRC = _REPO / "src" / "python"
if str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))

import cdl  # noqa: E402


def sieve_primes_and_divisors(limit: int) -> Tuple[List[int], List[int]]:
    """
    Return primes up to limit (inclusive if prime) and d(n) for n in 0..limit.
    d[0]=d[1]=0. Uses linear sieve style divisor accumulation.
    """
    if limit < 2:
        return [], [0] * (limit + 1)

    d = [0] * (limit + 1)
    d[1] = 1
    for i in range(1, limit + 1):
        for j in range(i, limit + 1, i):
            d[j] += 1

    primes: List[int] = []
    is_prime = [True] * (limit + 1)
    is_prime[0] = is_prime[1] = False
    for i in range(2, limit + 1):
        if is_prime[i]:
            primes.append(i)
            step = i
            start = i * i
            if start > limit:
                continue
            for j in range(start, limit + 1, step):
                is_prime[j] = False
    return primes, d


def analyze_gap(
    p: int,
    q: int,
    d: List[int],
) -> Optional[Dict[str, Any]]:
    """Analyze one open gap (p, q). Return None if empty interior."""
    if q <= p + 1:
        return None

    best_d = 10**18
    w_d = -1
    best_k = float("inf")
    w_k = -1
    # secondary: second-best kappa (for margin)
    second_k = float("inf")
    second_k_n = -1

    interiors: List[Tuple[int, int, float]] = []
    for n in range(p + 1, q):
        dn = d[n] if n < len(d) else cdl.divisor_count(n)
        kn = dn * math.log(n) / (math.e ** 2)
        interiors.append((n, dn, kn))
        if dn < best_d:
            best_d = dn
            w_d = n
        if kn < best_k:
            if best_k < float("inf"):
                second_k = best_k
                second_k_n = w_k
            best_k = kn
            w_k = n
        elif kn < second_k:
            second_k = kn
            second_k_n = n

    if not interiors:
        return None

    # verify kappa at w_d
    d_at_wd = best_d
    k_at_wd = d_at_wd * math.log(w_d) / (math.e ** 2)
    d_at_wk = next(dn for n, dn, kn in interiors if n == w_k)
    k_at_wk = best_k

    differ = w_d != w_k
    gap_len = q - p
    # Task wording "ln(q/p)-1" is near -1 for all ordinary gaps (useless as a scale).
    # Keep it for audit, and also report the meaningful relatives:
    #   log_gap = ln(q/p) ~ (q-p)/p
    #   rel_ln_variation = ln(q)/ln(p) - 1  (relative change of ln across endpoints)
    rel_ln_task = math.log(q / p) - 1.0
    log_gap = math.log(q / p)
    rel_ln = math.log(q) / math.log(p) - 1.0 if p > 1 else float("inf")
    # tighter interior relative log span
    left = p + 1
    right = q - 1
    ln_span_ratio = math.log(right) / math.log(left) if left > 1 else float("inf")
    # minimum d-step ratio that would be needed for inversion from left edge
    # vs actual max ln ratio in gap
    min_step_ratio = (best_d + 1) / best_d if best_d > 0 else float("inf")
    inversion_feasible_in_gap = ln_span_ratio > min_step_ratio

    # check whether any earlier m could theoretically beat w_d under kappa
    inversion_exists = False
    inversion_m = None
    if differ:
        inversion_exists = True
        inversion_m = w_k

    # margin: how much "room" before a +1 d-step could invert at left edge
    # room = min_step_ratio - ln_span_ratio (positive => locked)
    lock_margin = min_step_ratio - ln_span_ratio

    # kappa margin to second best (relative)
    if second_k < float("inf") and best_k > 0:
        kappa_rel_margin = (second_k - best_k) / best_k
    else:
        kappa_rel_margin = None

    # pure-d ties: count how many n achieve best_d
    n_min_d = sum(1 for n, dn, kn in interiors if dn == best_d)

    return {
        "p": p,
        "q": q,
        "gap_len": gap_len,
        "rel_ln": rel_ln,
        "rel_ln_task_ln_q_over_p_minus_1": rel_ln_task,
        "log_gap": log_gap,
        "ln_span_ratio": ln_span_ratio,
        "w_d": w_d,
        "w_k": w_k,
        "d_at_wd": d_at_wd,
        "d_at_wk": d_at_wk,
        "k_at_wd": k_at_wd,
        "k_at_wk": k_at_wk,
        "differ": differ,
        "offset_wk_minus_wd": w_k - w_d,
        "n_min_d_ties": n_min_d,
        "min_step_ratio": min_step_ratio,
        "inversion_feasible_in_gap": inversion_feasible_in_gap,
        "lock_margin": lock_margin,
        "kappa_rel_margin": kappa_rel_margin,
        "second_k_n": second_k_n,
        "inversion_m": inversion_m,
    }


def bin_key_gap_len(g: int) -> str:
    if g <= 2:
        return "g<=2"
    if g <= 6:
        return "g3-6"
    if g <= 12:
        return "g7-12"
    if g <= 30:
        return "g13-30"
    if g <= 100:
        return "g31-100"
    return "g>100"


def bin_key_rel_ln(r: float) -> str:
    # bins on rel_ln = ln(q)/ln(p) - 1
    if r < 1e-4:
        return "rl<1e-4"
    if r < 1e-3:
        return "rl1e-4-1e-3"
    if r < 1e-2:
        return "rl1e-3-1e-2"
    if r < 1e-1:
        return "rl1e-2-1e-1"
    return "rl>=1e-1"


def pearson(xs: List[float], ys: List[float]) -> Optional[float]:
    n = len(xs)
    if n < 3:
        return None
    mx = sum(xs) / n
    my = sum(ys) / n
    num = sum((x - mx) * (y - my) for x, y in zip(xs, ys))
    dx = math.sqrt(sum((x - mx) ** 2 for x in xs))
    dy = math.sqrt(sum((y - my) ** 2 for y in ys))
    if dx == 0 or dy == 0:
        return None
    return num / (dx * dy)


def run(limit: int) -> Dict[str, Any]:
    t0 = time.time()
    primes, d = sieve_primes_and_divisors(limit)
    # need next prime after last p < limit; if limit is not past a full gap, stop at last full gap
    # primes list only up to limit; for last prime p with next q also <= limit
    records: List[Dict[str, Any]] = []
    differ_examples: List[Dict[str, Any]] = []
    n_empty = 0
    n_feasible = 0

    for i in range(len(primes) - 1):
        p = primes[i]
        q = primes[i + 1]
        if q > limit:
            break
        row = analyze_gap(p, q, d)
        if row is None:
            n_empty += 1
            continue
        records.append(row)
        if row["inversion_feasible_in_gap"]:
            n_feasible += 1
        if row["differ"]:
            differ_examples.append(row)

    n_gaps = len(records)
    n_differ = len(differ_examples)
    diverge_rate = n_differ / n_gaps if n_gaps else 0.0

    # correlations: differ (0/1) vs gap_len and rel_ln
    y = [1.0 if r["differ"] else 0.0 for r in records]
    corr_gap = pearson([float(r["gap_len"]) for r in records], y)
    corr_rel = pearson([float(r["rel_ln"]) for r in records], y)
    corr_lock = pearson(
        [float(r["lock_margin"]) for r in records],
        y,
    )

    # binned rates
    by_gap: Dict[str, Dict[str, float]] = defaultdict(lambda: {"n": 0, "differ": 0})
    by_rl: Dict[str, Dict[str, float]] = defaultdict(lambda: {"n": 0, "differ": 0})
    for r in records:
        bg = bin_key_gap_len(r["gap_len"])
        br = bin_key_rel_ln(r["rel_ln"])
        by_gap[bg]["n"] += 1
        by_gap[bg]["differ"] += 1 if r["differ"] else 0
        by_rl[br]["n"] += 1
        by_rl[br]["differ"] += 1 if r["differ"] else 0

    def rate_table(d0: Dict[str, Dict[str, float]]) -> Dict[str, Any]:
        out = {}
        for k, v in sorted(d0.items()):
            n = int(v["n"])
            di = int(v["differ"])
            out[k] = {
                "n": n,
                "differ": di,
                "rate": (di / n) if n else 0.0,
            }
        return out

    # theoretical lock: min lock_margin, fraction with lock_margin > 0
    lock_margins = [r["lock_margin"] for r in records]
    min_lock = min(lock_margins) if lock_margins else None
    frac_locked = (
        sum(1 for m in lock_margins if m > 0) / n_gaps if n_gaps else None
    )

    # where differ: direction stats
    leftward = sum(1 for r in differ_examples if r["offset_wk_minus_wd"] < 0)
    rightward = sum(1 for r in differ_examples if r["offset_wk_minus_wd"] > 0)

    # max gap / max rel_ln in range
    max_gap = max((r["gap_len"] for r in records), default=None)
    max_rel = max((r["rel_ln"] for r in records), default=None)
    max_ln_span = max((r["ln_span_ratio"] for r in records), default=None)
    min_step_seen = min((r["min_step_ratio"] for r in records), default=None)

    # small-n regime: p < 100
    small = [r for r in records if r["p"] < 100]
    large = [r for r in records if r["p"] >= 1000]
    small_rate = (
        sum(1 for r in small if r["differ"]) / len(small) if small else None
    )
    large_rate = (
        sum(1 for r in large if r["differ"]) / len(large) if large else None
    )

    # analytic bound probe: for each gap, is max ln_span ever above min_step?
    # already n_feasible

    elapsed = time.time() - t0

    # keep only a few differ examples (full if few)
    differ_examples_out = []
    for r in differ_examples[:50]:
        differ_examples_out.append(
            {
                "p": r["p"],
                "q": r["q"],
                "gap_len": r["gap_len"],
                "rel_ln": r["rel_ln"],
                "ln_span_ratio": r["ln_span_ratio"],
                "w_d": r["w_d"],
                "w_k": r["w_k"],
                "d_at_wd": r["d_at_wd"],
                "d_at_wk": r["d_at_wk"],
                "k_at_wd": r["k_at_wd"],
                "k_at_wk": r["k_at_wk"],
                "offset_wk_minus_wd": r["offset_wk_minus_wd"],
                "lock_margin": r["lock_margin"],
            }
        )

    # Z-map quantities (measurable)
    # a = diverge_rate (observable selection mismatch rate)
    # b = mean rel_ln (rate-like log stretch per gap)
    # c = mean min_step_ratio - 1  (discrete jump capacity, lower bound ~ 1/d_min)
    mean_rel = sum(r["rel_ln"] for r in records) / n_gaps if n_gaps else 0.0
    mean_log_gap = sum(r["log_gap"] for r in records) / n_gaps if n_gaps else 0.0
    mean_rel_task = (
        sum(r["rel_ln_task_ln_q_over_p_minus_1"] for r in records) / n_gaps if n_gaps else 0.0
    )
    mean_step_excess = (
        sum(r["min_step_ratio"] - 1.0 for r in records) / n_gaps if n_gaps else 0.0
    )
    mean_lock = sum(lock_margins) / n_gaps if n_gaps else 0.0
    # effective intensity: how hard log stretch pushes relative to discrete capacity
    # use mean of (ln_span_ratio - 1) / (min_step_ratio - 1)
    intensities = []
    for r in records:
        denom = r["min_step_ratio"] - 1.0
        if denom > 0:
            intensities.append((r["ln_span_ratio"] - 1.0) / denom)
    mean_intensity = sum(intensities) / len(intensities) if intensities else None
    max_intensity = max(intensities) if intensities else None

    result: Dict[str, Any] = {
        "probe": "path_a_kappa_vs_d_gap_winner",
        "status": "empirical_only",
        "limit": limit,
        "n_primes": len(primes),
        "n_gaps": n_gaps,
        "n_empty_interiors": n_empty,
        "n_differ": n_differ,
        "diverge_rate": diverge_rate,
        "n_inversion_feasible_by_ln_span": n_feasible,
        "fraction_lock_margin_positive": frac_locked,
        "min_lock_margin": min_lock,
        "mean_lock_margin": mean_lock,
        "max_gap_len": max_gap,
        "max_rel_ln": max_rel,
        "mean_rel_ln": mean_rel,
        "mean_log_gap": mean_log_gap,
        "mean_rel_ln_task_near_minus_one": mean_rel_task,
        "max_ln_span_ratio": max_ln_span,
        "min_min_step_ratio": min_step_seen,
        "corr_differ_vs_gap_len": corr_gap,
        "corr_differ_vs_rel_ln": corr_rel,
        "corr_differ_vs_lock_margin": corr_lock,
        "rate_by_gap_len_bin": rate_table(by_gap),
        "rate_by_rel_ln_bin": rate_table(by_rl),
        "differ_direction": {
            "leftward_wk_lt_wd": leftward,
            "rightward_wk_gt_wd": rightward,
        },
        "regime_rates": {
            "p_lt_100": {"n": len(small), "rate": small_rate},
            "p_ge_1000": {"n": len(large), "rate": large_rate},
        },
        "z_map": {
            "a_observable": "diverge_rate (fraction of gaps with w_k != w_d)",
            "a_value": diverge_rate,
            "b_dynamic": "mean_rel_ln = mean(ln(q)/ln(p) - 1)",
            "b_value": mean_rel,
            "b_alt_log_gap": mean_log_gap,
            "c_constraint": "mean(min_step_ratio - 1) ~ mean(1/d_min)",
            "c_value": mean_step_excess,
            "effective_intensity": "mean((ln_span_ratio-1)/(min_step_ratio-1))",
            "effective_intensity_value": mean_intensity,
            "max_intensity": max_intensity,
            "formula": "effective_intensity = a is predicted near 0 when mean_intensity << 1",
            "interpretation": (
                "intensity << 1 means log stretch inside real gaps is far too weak "
                "to overcome a discrete +1 divisor-count step; argmin lock expected"
            ),
        },
        "falsifier": {
            "claim": (
                "w_d and w_k systematically diverge as gap_len or rel_ln grows "
                "within primes up to limit"
            ),
            "disconfirm_if": (
                "diverge_rate near 0 across all gap-length bins, OR no positive "
                "correlation of differ with gap_len/rel_ln, OR n_inversion_feasible=0"
            ),
            "observed": {
                "diverge_rate": diverge_rate,
                "corr_gap": corr_gap,
                "corr_rel_ln": corr_rel,
                "n_inversion_feasible": n_feasible,
            },
        },
        "differ_examples": differ_examples_out,
        "elapsed_sec": elapsed,
        "hypothesis_verdict": None,  # filled below
    }

    # Verdict
    if n_differ == 0 and n_feasible == 0:
        verdict = "FALSIFIED"
        note = (
            "No argmin divergence in range; theoretical inversion never feasible "
            "because max ln_span_ratio stays below min +1 d-step ratio."
        )
    elif n_differ > 0 and (corr_gap is None or corr_gap <= 0) and n_feasible == 0:
        verdict = "FALSIFIED"
        note = (
            "Sparse small-n differences only; no systematic long-gap divergence; "
            "inversion not feasible by ln-span vs d-step."
        )
    elif n_differ > 0 and corr_gap is not None and corr_gap > 0.2 and diverge_rate > 0.01:
        verdict = "SUPPORTED"
        note = "Positive correlation of divergence with gap length and non-trivial rate."
    else:
        verdict = "WEAK_OR_FALSIFIED"
        note = (
            "Some differences may exist but lack systematic long-gap structure "
            "predicted by the hypothesis."
        )

    result["hypothesis_verdict"] = verdict
    result["hypothesis_note"] = note

    # Surviving / failure insight payload (empirical)
    result["surviving_insight_or_failure"] = {
        "type": "explicit_failure" if verdict in ("FALSIFIED", "WEAK_OR_FALSIFIED") else "insight",
        "title": (
            "Kappa and d Gap Winners stay locked on real prime gaps"
            if verdict != "SUPPORTED"
            else "Kappa reorders long-gap winners via log stretch"
        ),
        "summary": note,
        "mechanism": (
            "kappa(n)=d(n)*ln(n)/e^2 can move the minimizer left of the d-winner only if "
            "an earlier higher-d composite satisfies d(m)/d(w_d) < ln(w_d)/ln(m). "
            "Inside actual prime gaps that log ratio never exceeds the discrete step "
            "1+1/d_min, so the continuous CDL warp cannot reorder the PGS Gap Winner."
        ),
        "measurable_prediction": (
            "For all primes p with p+gap <= limit, diverge_rate == 0 and "
            "max_ln_span_ratio < min_min_step_ratio."
        ),
        "what_would_revive_hypothesis": (
            "Find a prime gap where ln(q-1)/ln(p+1) > 1 + 1/d_min for the gap's min d, "
            "or observe diverge_rate rising with gap_len bins."
        ),
    }

    return result


def main() -> None:
    parser = argparse.ArgumentParser(description="Path A: kappa vs d Gap-Winner probe")
    parser.add_argument(
        "--limit",
        type=int,
        default=200_000,
        help="Sieve / prime upper bound (default 200000)",
    )
    parser.add_argument(
        "--out",
        type=str,
        default=None,
        help="Output JSON path (default: results.json beside this script)",
    )
    args = parser.parse_args()
    out_path = Path(args.out) if args.out else Path(__file__).resolve().parent / "results.json"

    result = run(args.limit)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(result, f, indent=2, sort_keys=False)
        f.write("\n")

    print(json.dumps({k: result[k] for k in (
        "limit", "n_gaps", "n_differ", "diverge_rate",
        "n_inversion_feasible_by_ln_span", "fraction_lock_margin_positive",
        "min_lock_margin", "max_ln_span_ratio", "min_min_step_ratio",
        "corr_differ_vs_gap_len", "corr_differ_vs_rel_ln",
        "hypothesis_verdict", "hypothesis_note", "elapsed_sec",
        "z_map", "regime_rates",
    )}, indent=2))
    print(f"\nWrote {out_path}")


if __name__ == "__main__":
    main()
