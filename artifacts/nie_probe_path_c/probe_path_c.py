#!/usr/bin/env python3
"""
Path C probe: Local curvature jump field J(n) as a signal separate from kappa level.

Hypothesis:
  Primes are characterized not only by low kappa but by asymmetric jump structure
  (entry/exit from geodesic band). Jump variance intensity in a window may predict
  gap structure or classification residual better than level alone.

Falsifier:
  If (kappa, J-features) adds no AUROC/accuracy lift over kappa-only at matched
  complexity, and jump variance does not beat kappa-level for gap residual, FAIL.

Usage:
  PYTHONPATH=src/python python3 artifacts/nie_probe_path_c/probe_path_c.py
"""
from __future__ import annotations

import json
import math
import os
import sys
import time
from collections import defaultdict
from pathlib import Path
from typing import Any, Dict, List, Tuple

import numpy as np

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src" / "python"))
import cdl  # noqa: E402

OUT = Path(__file__).resolve().parent
E2 = math.e ** 2


def sieve_divisor_counts(n_max: int) -> np.ndarray:
    """d[n] for n in 0..n_max (d[0]=d[1]=0)."""
    d = np.zeros(n_max + 1, dtype=np.int32)
    for i in range(1, n_max + 1):
        for j in range(i, n_max + 1, i):
            d[j] += 1
    return d


def sieve_primes(n_max: int) -> np.ndarray:
    is_p = np.ones(n_max + 1, dtype=bool)
    is_p[:2] = False
    for i in range(2, int(n_max**0.5) + 1):
        if is_p[i]:
            is_p[i * i :: i] = False
    return is_p


def omega_and_semiprime(n_max: int, is_prime: np.ndarray) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
    """omega(n), Omega(n), is_semiprime (exactly two prime factors counting multiplicity: p*q or p^2)."""
    omega = np.zeros(n_max + 1, dtype=np.int16)
    Omega = np.zeros(n_max + 1, dtype=np.int16)
    spf = np.zeros(n_max + 1, dtype=np.int32)
    for i in range(2, n_max + 1):
        if spf[i] == 0:
            spf[i] = i
            if i * i <= n_max:
                for j in range(i * i, n_max + 1, i):
                    if spf[j] == 0:
                        spf[j] = i
    for n in range(2, n_max + 1):
        x = n
        seen = set()
        while x > 1:
            p = spf[x]
            Omega[n] += 1
            seen.add(p)
            x //= p
        omega[n] = len(seen)
    # semiprime: Omega==2 (p*q distinct or p^2)
    is_semi = (Omega == 2) & (~is_prime)
    return omega, Omega, is_semi


def kappa_from_d(n: int, d_n: int) -> float:
    if n <= 1:
        return 0.0
    return d_n * math.log(n) / E2


def auroc(y_true: np.ndarray, scores: np.ndarray) -> float:
    """AUROC for binary labels; higher score => positive class (prime=1). Mann-Whitney form."""
    y = y_true.astype(bool)
    pos = scores[y]
    neg = scores[~y]
    n_pos = len(pos)
    n_neg = len(neg)
    if n_pos == 0 or n_neg == 0:
        return float("nan")
    # rank all scores
    order = np.argsort(scores, kind="mergesort")
    ranks = np.empty_like(scores, dtype=np.float64)
    ranks[order] = np.arange(1, len(scores) + 1, dtype=np.float64)
    # average ranks for ties
    sorted_scores = scores[order]
    i = 0
    while i < len(scores):
        j = i
        while j + 1 < len(scores) and sorted_scores[j + 1] == sorted_scores[i]:
            j += 1
        if j > i:
            avg = 0.5 * (i + 1 + j + 1)
            ranks[order[i : j + 1]] = avg
        i = j + 1
    sum_ranks_pos = ranks[y].sum()
    # U = sum_ranks_pos - n_pos*(n_pos+1)/2
    u = sum_ranks_pos - n_pos * (n_pos + 1) / 2.0
    return float(u / (n_pos * n_neg))


def best_threshold_accuracy(y_true: np.ndarray, scores: np.ndarray, higher_is_positive: bool = False) -> Tuple[float, float]:
    """Scan thresholds on unique scores; for kappa, lower => prime so higher_is_positive=False means score below thr => pos."""
    # Convert so higher score => predict positive
    s = scores if higher_is_positive else -scores
    order = np.argsort(s)
    y = y_true[order]
    # cumulative: predict top-k as positive from high end
    # scan all cut points
    best_acc = 0.0
    best_t = float(s[order[0]]) if len(s) else 0.0
    n = len(y)
    # For each possible threshold (mid between consecutive), count
    # Use: predict positive if s >= t. Try each unique s as t.
    uniq = np.unique(s)
    n_pos = int(y.sum())
    n_neg = n - n_pos
    # prefix of positives when sorted ascending
    # at threshold t, pos_pred = those with s >= t
    # sort descending
    order_desc = np.argsort(-s)
    y_desc = y[order_desc]
    s_desc = s[order_desc]
    tp = 0
    fp = 0
    # start with none predicted positive
    # also evaluate all-negative
    best_acc = max(n_neg / n, n_pos / n) if n else 0.0
    for i in range(n):
        if y_desc[i]:
            tp += 1
        else:
            fp += 1
        # if next same score, continue
        if i + 1 < n and s_desc[i + 1] == s_desc[i]:
            continue
        tn = n_neg - fp
        acc = (tp + tn) / n
        if acc > best_acc:
            best_acc = acc
            # map back to original score space
            raw = s_desc[i] if higher_is_positive else -s_desc[i]
            best_t = float(raw)
    return best_t, float(best_acc)


def logistic_2d_auc(
    x1: np.ndarray, x2: np.ndarray, y: np.ndarray, n_grid: int = 41
) -> Dict[str, float]:
    """
    Lightweight linear score: s = a*x1 + b*x2 + c, grid over a,b with c chosen as median
    of decision boundary. Actually: normalize features, grid weights on unit circle, pick
    best AUROC orientation (sign free via auroc of ±s).
    """
    z1 = (x1 - x1.mean()) / (x1.std() + 1e-12)
    z2 = (x2 - x2.mean()) / (x2.std() + 1e-12)
    best = -1.0
    best_w = (1.0, 0.0)
    for i in range(n_grid):
        theta = math.pi * i / n_grid  # half-circle; auroc handles flip via max
        w1, w2 = math.cos(theta), math.sin(theta)
        s = w1 * z1 + w2 * z2
        auc = auroc(y, s)
        auc_flip = auroc(y, -s)
        if auc_flip > auc:
            auc = auc_flip
            w1, w2 = -w1, -w2
        if auc > best:
            best = auc
            best_w = (w1, w2)
    s = best_w[0] * z1 + best_w[1] * z2
    # accuracy via best threshold on s
    _, acc = best_threshold_accuracy(y, s, higher_is_positive=True)
    return {
        "auroc": float(best),
        "accuracy_best_thr": float(acc),
        "w1": float(best_w[0]),
        "w2": float(best_w[1]),
    }


def logistic_nd_auc(X: np.ndarray, y: np.ndarray, n_random: int = 400, seed: int = 0) -> Dict[str, float]:
    """Random-direction linear probe on standardized features; best AUROC."""
    rng = np.random.default_rng(seed)
    mu = X.mean(axis=0)
    sd = X.std(axis=0) + 1e-12
    Z = (X - mu) / sd
    d = Z.shape[1]
    best = -1.0
    best_w = np.zeros(d)
    # axis-aligned baselines
    for j in range(d):
        s = Z[:, j]
        for flip in (1, -1):
            auc = auroc(y, flip * s)
            if auc > best:
                best = auc
                best_w = flip * np.eye(d)[j]
    for _ in range(n_random):
        w = rng.normal(size=d)
        w = w / (np.linalg.norm(w) + 1e-12)
        s = Z @ w
        auc = auroc(y, s)
        if auc > best:
            best = auc
            best_w = w
    s = Z @ best_w
    _, acc = best_threshold_accuracy(y, s, higher_is_positive=True)
    return {"auroc": float(best), "accuracy_best_thr": float(acc), "weights": best_w.tolist()}


def pearson(x: np.ndarray, y: np.ndarray) -> float:
    if len(x) < 3:
        return float("nan")
    x = x.astype(np.float64)
    y = y.astype(np.float64)
    x = x - x.mean()
    y = y - y.mean()
    den = np.sqrt((x * x).sum() * (y * y).sum())
    if den < 1e-15:
        return float("nan")
    return float((x * y).sum() / den)


def spearman(x: np.ndarray, y: np.ndarray) -> float:
    # rank then pearson
    def rankdata(a):
        order = np.argsort(a, kind="mergesort")
        ranks = np.empty_like(a, dtype=np.float64)
        ranks[order] = np.arange(1, len(a) + 1, dtype=np.float64)
        # ties average
        sa = a[order]
        i = 0
        while i < len(a):
            j = i
            while j + 1 < len(a) and sa[j + 1] == sa[i]:
                j += 1
            if j > i:
                ranks[order[i : j + 1]] = 0.5 * (i + 1 + j + 1)
            i = j + 1
        return ranks

    return pearson(rankdata(x), rankdata(y))


def summarize(arr: np.ndarray) -> Dict[str, float]:
    if len(arr) == 0:
        return {"n": 0, "mean": float("nan"), "std": float("nan"), "median": float("nan"), "p10": float("nan"), "p90": float("nan")}
    return {
        "n": int(len(arr)),
        "mean": float(np.mean(arr)),
        "std": float(np.std(arr)),
        "median": float(np.median(arr)),
        "p10": float(np.percentile(arr, 10)),
        "p90": float(np.percentile(arr, 90)),
    }


def class_mask_labels(n_max: int, is_prime: np.ndarray, is_semi: np.ndarray) -> Dict[str, np.ndarray]:
    """Boolean masks for n in 2..n_max-1 usable with J."""
    ns = np.arange(n_max + 1)
    # p-1, p+1 for primes in range
    primes = np.where(is_prime)[0]
    is_p_minus = np.zeros(n_max + 1, dtype=bool)
    is_p_plus = np.zeros(n_max + 1, dtype=bool)
    for p in primes:
        if p - 1 >= 2:
            is_p_minus[p - 1] = True
        if p + 1 <= n_max:
            is_p_plus[p + 1] = True
    is_composite = (~is_prime) & (ns >= 2)
    # pure composite not adjacent to prime (optional)
    return {
        "prime": is_prime.copy(),
        "p_minus_1": is_p_minus,
        "p_plus_1": is_p_plus,
        "semiprime": is_semi.copy(),
        "composite": is_composite,
        "composite_not_adj": is_composite & (~is_p_minus) & (~is_p_plus),
    }


def main() -> None:
    t0 = time.time()
    # Ranges: train/calibrate on 2..N_train, holdout N_train+1..N_hold
    N = 30000
    N_TRAIN = 10000
    # need kappa up to N+1 for J, and n-1 for J_prev; use N+2
    N_MAX = N + 2
    print(f"Sieving to {N_MAX}...", flush=True)
    d = sieve_divisor_counts(N_MAX)
    is_prime = sieve_primes(N_MAX)
    omega, Omega, is_semi = omega_and_semiprime(N_MAX, is_prime)

    # Validate kappa vs cdl on sample
    for n in (2, 3, 12, 97, 1000, 9999):
        k_cdl = cdl.kappa(n)
        k_loc = kappa_from_d(n, int(d[n]))
        if abs(k_cdl - k_loc) > 1e-9:
            raise RuntimeError(f"kappa mismatch at {n}: {k_cdl} vs {k_loc}")

    ns = np.arange(N_MAX + 1, dtype=np.float64)
    ln = np.zeros(N_MAX + 1)
    ln[1:] = np.log(np.maximum(ns[1:], 1.0))
    kappa = d.astype(np.float64) * ln / E2
    # J(n) = kappa(n+1) - kappa(n) for n=1..N_MAX-1
    J = np.zeros(N_MAX + 1)
    J[:N_MAX] = kappa[1:] - kappa[:N_MAX]
    # J_prev at n: kappa(n)-kappa(n-1)
    J_prev = np.zeros(N_MAX + 1)
    J_prev[1:] = kappa[1:] - kappa[:-1]
    # At n, exit jump J(n)=kappa(n+1)-kappa(n), entry jump J_prev(n)=kappa(n)-kappa(n-1)
    # Asymmetry: for a local well, entry negative, exit positive: A = -J_prev + J (both large positive when deep well)
    # Well depth indicator: -J_prev (drop into n) and J (rise leaving n)
    drop_in = -J_prev  # positive if kappa falls into n
    rise_out = J  # positive if kappa rises after n
    well_score = np.minimum(drop_in, rise_out)  # both sides drop/rise
    abs_J = np.abs(J)
    # neighborhood max |J| at n: max over J(n-1), J(n), J(n+1) approximately using abs J at n-1,n
    max_abs_J_nbhd = np.zeros(N_MAX + 1)
    for n in range(2, N_MAX):
        max_abs_J_nbhd[n] = max(abs(J[n - 1]), abs(J[n]), abs(J[n + 1]) if n + 1 < N_MAX else 0.0)

    # local jump variance in window w about n (excluding endpoints issues)
    def rolling_var(arr: np.ndarray, half: int) -> np.ndarray:
        out = np.full_like(arr, np.nan, dtype=np.float64)
        for n in range(half, len(arr) - half):
            w = arr[n - half : n + half + 1]
            out[n] = float(np.var(w))
        return out

    W = 5  # half-window => 11 points
    J_var_win = rolling_var(J, W)
    kappa_var_win = rolling_var(kappa, W)
    kappa_mean_win = np.full(N_MAX + 1, np.nan)
    for n in range(W, N_MAX - W):
        kappa_mean_win[n] = float(np.mean(kappa[n - W : n + W + 1]))

    masks = class_mask_labels(N_MAX, is_prime, is_semi)

    # -------- Conditional statistics (valid n in 3..N) --------
    lo, hi = 3, N
    cond: Dict[str, Any] = {}
    feature_names = [
        "kappa",
        "J",
        "J_prev",
        "abs_J",
        "drop_in",
        "rise_out",
        "well_score",
        "max_abs_J_nbhd",
        "J_var_win",
    ]
    for cls, m in masks.items():
        idx = np.where(m & (np.arange(N_MAX + 1) >= lo) & (np.arange(N_MAX + 1) <= hi))[0]
        feat = {
            "kappa": kappa[idx],
            "J": J[idx],
            "J_prev": J_prev[idx],
            "abs_J": abs_J[idx],
            "drop_in": drop_in[idx],
            "rise_out": rise_out[idx],
            "well_score": well_score[idx],
            "max_abs_J_nbhd": max_abs_J_nbhd[idx],
            "J_var_win": J_var_win[idx],
        }
        cond[cls] = {name: summarize(feat[name][~np.isnan(feat[name])]) for name in feature_names}
        # asymmetry: fraction with drop_in>0 and rise_out>0 (local kappa valley)
        if len(idx):
            valley = (drop_in[idx] > 0) & (rise_out[idx] > 0)
            cond[cls]["valley_fraction"] = float(np.mean(valley))
            # signed asymmetry S = rise_out - drop_in
            S = rise_out[idx] - drop_in[idx]
            cond[cls]["asymmetry_S"] = summarize(S)

    # -------- Classification: train 2..N_TRAIN, holdout N_TRAIN+1..N --------
    def slice_range(a: int, b: int) -> np.ndarray:
        return np.arange(a, b + 1)

    def eval_range(a: int, b: int) -> Dict[str, Any]:
        idx = slice_range(a, b)
        # need features defined
        idx = idx[(idx >= W + 1) & (idx <= N_MAX - W - 1)]
        y = is_prime[idx].astype(np.int32)
        k = kappa[idx]
        j = J[idx]
        jp = J_prev[idx]
        aj = abs_J[idx]
        ws = well_score[idx]
        mj = max_abs_J_nbhd[idx]
        jv = J_var_win[idx]
        # score for primes: lower kappa better => use -kappa for auroc positive
        results = {
            "range": [int(a), int(b)],
            "n": int(len(idx)),
            "n_primes": int(y.sum()),
            "n_composites": int(len(y) - y.sum()),
            "auroc_kappa": auroc(y, -k),  # higher -kappa => more prime-like
            "auroc_abs_J": auroc(y, aj),
            "auroc_well_score": auroc(y, ws),
            "auroc_max_abs_J_nbhd": auroc(y, mj),
            "auroc_J_var_win": auroc(y, jv),
            "auroc_drop_in": auroc(y, drop_in[idx]),
            "auroc_rise_out": auroc(y, rise_out[idx]),
        }
        # kappa-only best accuracy (lower kappa => prime)
        thr_k, acc_k = best_threshold_accuracy(y, k, higher_is_positive=False)
        results["acc_kappa_only"] = acc_k
        results["thr_kappa"] = thr_k
        # well_score only
        thr_w, acc_w = best_threshold_accuracy(y, ws, higher_is_positive=True)
        results["acc_well_only"] = acc_w
        thr_aj, acc_aj = best_threshold_accuracy(y, aj, higher_is_positive=True)
        results["acc_abs_J_only"] = acc_aj

        # 2D: kappa + well
        r_kw = logistic_2d_auc(k, ws, y)
        results["kappa_well"] = r_kw
        r_kj = logistic_2d_auc(k, aj, y)
        results["kappa_abs_J"] = r_kj
        r_kjp = logistic_2d_auc(k, jp, y)
        results["kappa_J_prev"] = r_kjp
        r_kjx = logistic_2d_auc(k, j, y)
        results["kappa_J"] = r_kjx

        # multi-feature
        X = np.column_stack([k, j, jp, aj, ws, mj, jv])
        r_multi = logistic_nd_auc(X, y, n_random=600, seed=42)
        results["multi_jump_features"] = {
            "auroc": r_multi["auroc"],
            "accuracy_best_thr": r_multi["accuracy_best_thr"],
            "weights": r_multi["weights"],
            "feature_order": ["kappa", "J", "J_prev", "abs_J", "well_score", "max_abs_J_nbhd", "J_var_win"],
        }
        # kappa alone is already in auroc_kappa; lift
        results["auroc_lift_multi_vs_kappa"] = results["multi_jump_features"]["auroc"] - results["auroc_kappa"]
        results["auroc_lift_kappa_well_vs_kappa"] = r_kw["auroc"] - results["auroc_kappa"]
        results["auroc_lift_kappa_absJ_vs_kappa"] = r_kj["auroc"] - results["auroc_kappa"]
        results["acc_lift_multi_vs_kappa"] = results["multi_jump_features"]["accuracy_best_thr"] - results["acc_kappa_only"]
        return results

    print("Evaluating classifiers...", flush=True)
    class_train = eval_range(2, N_TRAIN)
    class_hold = eval_range(N_TRAIN + 1, N)
    class_seed = eval_range(2, 49)
    class_mid = eval_range(50, 999)
    class_hi = eval_range(1000, 9999)
    class_xhi = eval_range(10000, N)

    # Adaptive-tau style: kappa alone with range-adaptive thr vs well-augmented rule
    # Rule: predict prime if kappa < tau(n) OR (kappa < tau*1.15 and well_score > median well of primes)
    # Simpler matched-complexity: compare kappa threshold vs kappa+well linear on holdout

    # -------- Hard subset: low-kappa composites vs primes (where jump might help) --------
    def hard_subset_eval(a: int, b: int) -> Dict[str, Any]:
        idx = np.arange(max(a, W + 1), min(b, N_MAX - W - 1) + 1)
        y = is_prime[idx]
        k = kappa[idx]
        # composites with kappa below 90th percentile of prime kappa in range
        prime_k = k[y]
        if len(prime_k) == 0:
            return {"n": 0}
        k_cut = float(np.percentile(prime_k, 95))
        # hard set: all primes + composites with kappa <= k_cut (prime-like kappa)
        hard = y | ((~y) & (k <= k_cut))
        hidx = idx[hard]
        hy = is_prime[hidx].astype(np.int32)
        hk = kappa[hidx]
        hws = well_score[hidx]
        haj = abs_J[hidx]
        out = {
            "range": [int(a), int(b)],
            "k_cut": k_cut,
            "n": int(len(hidx)),
            "n_primes": int(hy.sum()),
            "n_low_kappa_composites": int(len(hy) - hy.sum()),
            "auroc_kappa": auroc(hy, -hk),
            "auroc_well": auroc(hy, hws),
            "auroc_abs_J": auroc(hy, haj),
        }
        r = logistic_2d_auc(hk, hws, hy)
        out["kappa_well"] = r
        out["auroc_lift"] = r["auroc"] - out["auroc_kappa"]
        X = np.column_stack([hk, J[hidx], J_prev[hidx], haj, hws, max_abs_J_nbhd[hidx], J_var_win[hidx]])
        rm = logistic_nd_auc(X, hy, n_random=500, seed=7)
        out["multi"] = {"auroc": rm["auroc"], "acc": rm["accuracy_best_thr"]}
        out["multi_lift"] = rm["auroc"] - out["auroc_kappa"]
        thr, acc = best_threshold_accuracy(hy, hk, higher_is_positive=False)
        out["acc_kappa"] = acc
        out["acc_multi"] = rm["accuracy_best_thr"]
        out["acc_lift"] = rm["accuracy_best_thr"] - acc
        return out

    hard_hold = hard_subset_eval(N_TRAIN + 1, N)
    hard_all = hard_subset_eval(100, N)

    # -------- Gap structure prediction --------
    # For each prime p_i, gap g_i = p_{i+1}-p_i
    # Predictors at p_i or mid-gap: window jump variance vs kappa level
    primes_list = np.where(is_prime[2 : N + 1])[0] + 2
    gaps = np.diff(primes_list.astype(np.float64))
    p_left = primes_list[:-1]
    # features at left prime
    valid = (p_left >= W + 1) & (p_left <= N - W - 1)
    p_left = p_left[valid]
    gaps = gaps[valid]
    feat_jvar = J_var_win[p_left]
    feat_k = kappa[p_left]
    feat_kmean = kappa_mean_win[p_left]
    feat_ws = well_score[p_left]
    feat_mj = max_abs_J_nbhd[p_left]
    # also jump variance in the open gap interval (p, p+g) if g>1 — more PGS-like; keep sharp delta
    gap_jvar = np.full(len(p_left), np.nan)
    for i, p in enumerate(p_left):
        g = int(gaps[i])
        if g <= 1:
            gap_jvar[i] = 0.0
            continue
        segment = J[p : p + g]  # jumps inside gap
        gap_jvar[i] = float(np.var(segment)) if len(segment) else np.nan

    gap_corrs = {
        "spearman_gap_vs_J_var_win_at_prime": spearman(feat_jvar, gaps),
        "spearman_gap_vs_kappa_at_prime": spearman(feat_k, gaps),
        "spearman_gap_vs_kappa_mean_win": spearman(feat_kmean[~np.isnan(feat_kmean)], gaps[~np.isnan(feat_kmean)]),
        "spearman_gap_vs_well_score": spearman(feat_ws, gaps),
        "spearman_gap_vs_max_abs_J_nbhd": spearman(feat_mj, gaps),
        "spearman_gap_vs_in_gap_J_var": spearman(gap_jvar[~np.isnan(gap_jvar)], gaps[~np.isnan(gap_jvar)]),
        "pearson_gap_vs_J_var_win_at_prime": pearson(feat_jvar, gaps),
        "pearson_gap_vs_kappa_at_prime": pearson(feat_k, gaps),
        "n_gaps": int(len(gaps)),
        "gap_mean": float(np.mean(gaps)),
        "gap_std": float(np.std(gaps)),
    }
    # residual: predict gap from log n (trivial growth), residual correlation with jump var
    logp = np.log(p_left.astype(np.float64))
    # linear residual of gap ~ a + b log p
    A = np.column_stack([np.ones_like(logp), logp])
    coef, _, _, _ = np.linalg.lstsq(A, gaps, rcond=None)
    gap_resid = gaps - A @ coef
    gap_corrs["spearman_resid_vs_J_var"] = spearman(feat_jvar, gap_resid)
    gap_corrs["spearman_resid_vs_kappa"] = spearman(feat_k, gap_resid)
    gap_corrs["spearman_resid_vs_in_gap_J_var"] = spearman(gap_jvar[~np.isnan(gap_jvar)], gap_resid[~np.isnan(gap_jvar)])
    gap_corrs["spearman_resid_vs_well"] = spearman(feat_ws, gap_resid)

    # Holdout gap corrs on large primes only
    mask_large = p_left > N_TRAIN
    gap_corrs_hold = {}
    if mask_large.sum() > 50:
        gap_corrs_hold = {
            "spearman_gap_vs_J_var": spearman(feat_jvar[mask_large], gaps[mask_large]),
            "spearman_gap_vs_kappa": spearman(feat_k[mask_large], gaps[mask_large]),
            "spearman_resid_vs_J_var": spearman(feat_jvar[mask_large], gap_resid[mask_large]),
            "spearman_resid_vs_kappa": spearman(feat_k[mask_large], gap_resid[mask_large]),
            "spearman_resid_vs_in_gap_J_var": spearman(
                gap_jvar[mask_large & ~np.isnan(gap_jvar)], gap_resid[mask_large & ~np.isnan(gap_jvar)]
            ),
            "n_gaps": int(mask_large.sum()),
        }

    # -------- Classification residual analysis --------
    # Fit adaptive kappa threshold on train, residual = misclassification on holdout
    # Does jump feature predict residual better?
    thr_map = cdl.ADAPTIVE_THRESHOLD_MAP

    def adaptive_tau(n: int) -> float:
        return cdl.lookup_adaptive_threshold(n)

    hold_idx = np.arange(N_TRAIN + 1, N + 1)
    hold_idx = hold_idx[(hold_idx >= W + 1) & (hold_idx <= N_MAX - W - 1)]
    y_h = is_prime[hold_idx]
    k_h = kappa[hold_idx]
    pred_prime = np.array([k_h[i] < adaptive_tau(int(hold_idx[i])) for i in range(len(hold_idx))])
    # residual: error indicator
    err = pred_prime != y_h
    # Among composites predicted prime (FP) and primes predicted composite (FN)
    fp = pred_prime & (~y_h)
    fn = (~pred_prime) & y_h
    residual_stats = {
        "n": int(len(hold_idx)),
        "error_rate": float(np.mean(err)),
        "fp_rate": float(np.mean(fp)),
        "fn_rate": float(np.mean(fn)),
        "n_fp": int(fp.sum()),
        "n_fn": int(fn.sum()),
        # Does well_score separate errors? AUROC for error prediction
        "auroc_err_from_well": auroc(err.astype(np.int32), well_score[hold_idx]),
        "auroc_err_from_abs_J": auroc(err.astype(np.int32), abs_J[hold_idx]),
        "auroc_err_from_J_var": auroc(err.astype(np.int32), J_var_win[hold_idx]),
        "auroc_err_from_kappa": auroc(err.astype(np.int32), k_h),
        "auroc_err_from_dist_to_tau": auroc(
            err.astype(np.int32),
            np.array([abs(k_h[i] - adaptive_tau(int(hold_idx[i]))) for i in range(len(hold_idx))]),
        ),
    }
    # FP-specific: among low-kappa candidates (pred prime), does well help re-rank true primes?
    cand = pred_prime
    if cand.sum() > 10 and y_h[cand].sum() > 0 and (~y_h[cand]).sum() > 0:
        residual_stats["auroc_prime_among_cand_kappa"] = auroc(y_h[cand].astype(np.int32), -k_h[cand])
        residual_stats["auroc_prime_among_cand_well"] = auroc(y_h[cand].astype(np.int32), well_score[hold_idx][cand])
        residual_stats["auroc_prime_among_cand_multi"] = logistic_2d_auc(
            k_h[cand], well_score[hold_idx][cand], y_h[cand].astype(np.int32)
        )["auroc"]

    # -------- Z-map style quantities --------
    # a = observable: classification residual rate or gap residual std
    # b = jump variance intensity (rate of curvature change)
    # c = kappa level scale (or log n bound)
    # effective intensity I = a * (b/c) — here compute phase indicators
    # For primes: mean well_score / mean kappa as dimensionless
    zmap = {
        "description": (
            "a = mean |classification error indicator| on holdout; "
            "b = mean J_var_win on holdout; c = mean kappa on holdout; "
            "I = a * (b/c). Also per-class well_intensity = mean(well_score)/mean(kappa)."
        ),
        "holdout_a_error_rate": residual_stats["error_rate"],
        "holdout_b_mean_J_var": float(np.nanmean(J_var_win[hold_idx])),
        "holdout_c_mean_kappa": float(np.mean(k_h)),
        "I_error_jump_intensity": residual_stats["error_rate"]
        * (float(np.nanmean(J_var_win[hold_idx])) / (float(np.mean(k_h)) + 1e-12)),
        "prime_well_over_kappa": float(
            np.mean(well_score[is_prime & (np.arange(N_MAX + 1) >= 3) & (np.arange(N_MAX + 1) <= N)])
            / (np.mean(kappa[is_prime & (np.arange(N_MAX + 1) >= 3) & (np.arange(N_MAX + 1) <= N)]) + 1e-12)
        ),
        "composite_well_over_kappa": float(
            np.mean(well_score[(~is_prime) & (np.arange(N_MAX + 1) >= 3) & (np.arange(N_MAX + 1) <= N)])
            / (
                np.mean(kappa[(~is_prime) & (np.arange(N_MAX + 1) >= 3) & (np.arange(N_MAX + 1) <= N)])
                + 1e-12
            )
        ),
        "semiprime_well_over_kappa": float(
            np.mean(well_score[is_semi & (np.arange(N_MAX + 1) >= 3) & (np.arange(N_MAX + 1) <= N)])
            / (
                np.mean(kappa[is_semi & (np.arange(N_MAX + 1) >= 3) & (np.arange(N_MAX + 1) <= N)])
                + 1e-12
            )
        ),
    }

    # -------- Partial correlation style: is well_score just proxy for low kappa? --------
    # Cor(well, is_prime) controlling for kappa via residual of well ~ kappa
    idx_all = np.arange(100, N + 1)
    y_all = is_prime[idx_all].astype(np.float64)
    k_all = kappa[idx_all]
    w_all = well_score[idx_all]
    # residual well after linear kappa
    A2 = np.column_stack([np.ones_like(k_all), k_all])
    coef_w, _, _, _ = np.linalg.lstsq(A2, w_all, rcond=None)
    w_resid = w_all - A2 @ coef_w
    partial = {
        "corr_well_is_prime": pearson(w_all, y_all),
        "corr_kappa_is_prime": pearson(k_all, y_all),
        "corr_well_resid_is_prime": pearson(w_resid, y_all),
        "corr_well_kappa": pearson(w_all, k_all),
        "auroc_well_resid": auroc(y_all.astype(np.int32), w_resid),
        "auroc_kappa": auroc(y_all.astype(np.int32), -k_all),
        "note": "well residual after linear kappa regression; if auroc_well_resid ~0.5, jump adds no independent signal",
    }

    # -------- Example local profiles around primes / semiprimes --------
    examples = []
    for n in [11, 12, 30, 31, 48, 49, 100, 101, 114, 127, 2047, 2048, 9998, 9999, 10007]:
        if n < 2 or n > N:
            continue
        examples.append(
            {
                "n": n,
                "prime": bool(is_prime[n]),
                "semiprime": bool(is_semi[n]),
                "d": int(d[n]),
                "kappa": float(kappa[n]),
                "J": float(J[n]),
                "J_prev": float(J_prev[n]),
                "well_score": float(well_score[n]),
                "max_abs_J_nbhd": float(max_abs_J_nbhd[n]),
                "neighbors_kappa": [float(kappa[n - 1]), float(kappa[n]), float(kappa[n + 1])],
            }
        )

    # -------- Verdict logic --------
    lifts = {
        "hold_auroc_lift_multi": class_hold["auroc_lift_multi_vs_kappa"],
        "hold_auroc_lift_well": class_hold["auroc_lift_kappa_well_vs_kappa"],
        "hold_acc_lift_multi": class_hold["acc_lift_multi_vs_kappa"],
        "hard_auroc_lift": hard_hold.get("auroc_lift", float("nan")),
        "hard_multi_lift": hard_hold.get("multi_lift", float("nan")),
        "hard_acc_lift": hard_hold.get("acc_lift", float("nan")),
        "gap_resid_J_beats_kappa": abs(gap_corrs.get("spearman_resid_vs_J_var", 0))
        > abs(gap_corrs.get("spearman_resid_vs_kappa", 0)) + 0.05,
        "partial_well_resid_auroc": partial["auroc_well_resid"],
    }
    # Survival criteria: meaningful AUROC lift > 0.01 on holdout multi OR hard multi, OR gap residual clear win
    AUROC_LIFT_MIN = 0.01
    ACC_LIFT_MIN = 0.005
    survive_class = (
        lifts["hold_auroc_lift_multi"] > AUROC_LIFT_MIN
        or lifts["hold_auroc_lift_well"] > AUROC_LIFT_MIN
        or lifts["hard_multi_lift"] > AUROC_LIFT_MIN
        or lifts["hard_acc_lift"] > ACC_LIFT_MIN
    )
    survive_partial = partial["auroc_well_resid"] > 0.55  # independent of kappa
    survive_gap = bool(lifts["gap_resid_J_beats_kappa"]) and abs(
        gap_corrs.get("spearman_resid_vs_J_var", 0)
    ) > 0.1

    if survive_class and survive_partial:
        verdict = "SURVIVOR"
        strength = "strong"
        summary = (
            "Jump/well features add independent classification signal beyond kappa level "
            "on holdout and hard low-kappa subsets."
        )
    elif survive_class or survive_gap:
        verdict = "SURVIVOR"
        strength = "weak"
        summary = (
            "Marginal lift detected in one regime (class or gap residual); "
            "effect size small or not fully independent of kappa."
        )
    else:
        verdict = "FAILURE"
        strength = "falsified"
        summary = (
            "Jump field J(n) does not materially improve prime classification AUROC/accuracy "
            "beyond kappa level at matched linear complexity, and does not outperform kappa "
            "for gap residual prediction. Local wells at primes are largely a restatement of "
            "kappa local minima (d(n)=2)."
        )

    elapsed = time.time() - t0
    report = {
        "path": "C",
        "title": "Local curvature jump field J(n)=kappa(n+1)-kappa(n)",
        "hypothesis": (
            "Primes characterized by asymmetric jump structure (entry/exit from geodesic band) "
            "beyond low kappa; jump variance predicts gaps/residuals better than level alone."
        ),
        "definitions": {
            "kappa": "d(n)*ln(n)/e^2",
            "J(n)": "kappa(n+1)-kappa(n)",
            "J_prev(n)": "kappa(n)-kappa(n-1)",
            "drop_in": "-J_prev (positive when falling into n)",
            "rise_out": "J (positive when rising after n)",
            "well_score": "min(drop_in, rise_out)",
            "max_abs_J_nbhd": "max |J| on {n-1,n,n+1}",
            "J_var_win": f"variance of J over window half-width {W}",
        },
        "ranges": {"N": N, "N_TRAIN": N_TRAIN, "window_half": W},
        "conditional_stats": cond,
        "classification": {
            "seed_2_49": class_seed,
            "mid_50_999": class_mid,
            "hi_1000_9999": class_hi,
            "xhi_10000_N": class_xhi,
            "train_2_Ntrain": class_train,
            "holdout": class_hold,
        },
        "hard_subset": {"holdout": hard_hold, "all_from_100": hard_all},
        "gap_prediction": {"all": gap_corrs, "holdout_primes": gap_corrs_hold},
        "classification_residuals": residual_stats,
        "partial_independence": partial,
        "zmap": zmap,
        "examples": examples,
        "lifts": lifts,
        "verdict": verdict,
        "strength": strength,
        "summary": summary,
        "falsifier": (
            f"FAIL if holdout multi AUROC lift <= {AUROC_LIFT_MIN} and hard multi lift <= {AUROC_LIFT_MIN} "
            f"and gap residual |rho| J_var not clearly > kappa, and partial well residual AUROC <= 0.55."
        ),
        "elapsed_sec": elapsed,
        "kappa_validation": "matched cdl.kappa on sample n",
    }

    out_json = OUT / "path_c_results.json"
    with open(out_json, "w") as f:
        json.dump(report, f, indent=2, allow_nan=True)
    print(f"Wrote {out_json}", flush=True)
    print(f"VERDICT: {verdict} ({strength})", flush=True)
    print(f"Holdout kappa AUROC={class_hold['auroc_kappa']:.4f} multi={class_hold['multi_jump_features']['auroc']:.4f} "
          f"lift={class_hold['auroc_lift_multi_vs_kappa']:.4f}", flush=True)
    print(f"Hard multi lift={hard_hold.get('multi_lift')}", flush=True)
    print(f"Partial well_resid AUROC={partial['auroc_well_resid']:.4f}", flush=True)
    print(f"Gap resid spearman J_var={gap_corrs['spearman_resid_vs_J_var']:.4f} "
          f"kappa={gap_corrs['spearman_resid_vs_kappa']:.4f}", flush=True)
    print(f"Elapsed {elapsed:.1f}s", flush=True)


if __name__ == "__main__":
    main()
