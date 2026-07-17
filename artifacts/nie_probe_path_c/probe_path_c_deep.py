#!/usr/bin/env python3
"""
Path C deep follow-up: regimes where kappa AUROC < 1, prime-vs-semiprime,
local-minima rule, fixed-tau residuals, gap windows, asymmetry.
"""
from __future__ import annotations

import json
import math
import sys
import time
from pathlib import Path
from typing import Any, Dict, List

import numpy as np

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src" / "python"))
import cdl  # noqa: E402

OUT = Path(__file__).resolve().parent
E2 = math.e ** 2


def sieve_divisor_counts(n_max: int) -> np.ndarray:
    d = np.zeros(n_max + 1, dtype=np.int32)
    for i in range(1, n_max + 1):
        d[i::i] += 1
    return d


def sieve_primes(n_max: int) -> np.ndarray:
    is_p = np.ones(n_max + 1, dtype=bool)
    is_p[:2] = False
    for i in range(2, int(n_max**0.5) + 1):
        if is_p[i]:
            is_p[i * i :: i] = False
    return is_p


def factor_meta(n_max: int, is_prime: np.ndarray):
    spf = np.zeros(n_max + 1, dtype=np.int32)
    for i in range(2, n_max + 1):
        if spf[i] == 0:
            spf[i] = i
            if i * i <= n_max:
                for j in range(i * i, n_max + 1, i):
                    if spf[j] == 0:
                        spf[j] = i
    Omega = np.zeros(n_max + 1, dtype=np.int16)
    omega = np.zeros(n_max + 1, dtype=np.int16)
    for n in range(2, n_max + 1):
        x = n
        seen = set()
        while x > 1:
            p = spf[x]
            Omega[n] += 1
            seen.add(p)
            x //= p
        omega[n] = len(seen)
    is_semi = (Omega == 2) & (~is_prime)
    is_ppow = (omega == 1) & (~is_prime)  # p^k, k>=2
    return omega, Omega, is_semi, is_ppow


def auroc(y_true: np.ndarray, scores: np.ndarray) -> float:
    y = y_true.astype(bool)
    pos = scores[y]
    neg = scores[~y]
    n_pos, n_neg = len(pos), len(neg)
    if n_pos == 0 or n_neg == 0:
        return float("nan")
    order = np.argsort(scores, kind="mergesort")
    ranks = np.empty_like(scores, dtype=np.float64)
    ranks[order] = np.arange(1, len(scores) + 1, dtype=np.float64)
    sorted_scores = scores[order]
    i = 0
    while i < len(scores):
        j = i
        while j + 1 < len(scores) and sorted_scores[j + 1] == sorted_scores[i]:
            j += 1
        if j > i:
            ranks[order[i : j + 1]] = 0.5 * (i + 1 + j + 1)
        i = j + 1
    u = ranks[y].sum() - n_pos * (n_pos + 1) / 2.0
    return float(u / (n_pos * n_neg))


def best_acc(y: np.ndarray, scores: np.ndarray, higher_pos: bool) -> float:
    s = scores if higher_pos else -scores
    order = np.argsort(-s)
    y_d = y[order]
    s_d = s[order]
    n = len(y)
    n_pos = int(y.sum())
    n_neg = n - n_pos
    best = max(n_neg / n, n_pos / n) if n else 0.0
    tp = fp = 0
    for i in range(n):
        if y_d[i]:
            tp += 1
        else:
            fp += 1
        if i + 1 < n and s_d[i + 1] == s_d[i]:
            continue
        tn = n_neg - fp
        best = max(best, (tp + tn) / n)
    return float(best)


def logistic_nd(X: np.ndarray, y: np.ndarray, n_random: int = 800, seed: int = 0) -> Dict[str, float]:
    rng = np.random.default_rng(seed)
    mu, sd = X.mean(0), X.std(0) + 1e-12
    Z = (X - mu) / sd
    d = Z.shape[1]
    best, best_w = -1.0, np.zeros(d)
    for j in range(d):
        for flip in (1.0, -1.0):
            auc = auroc(y, flip * Z[:, j])
            if auc > best:
                best, best_w = auc, flip * np.eye(d)[j]
    for _ in range(n_random):
        w = rng.normal(size=d)
        w /= np.linalg.norm(w) + 1e-12
        auc = auroc(y, Z @ w)
        if auc > best:
            best, best_w = auc, w
    s = Z @ best_w
    return {"auroc": float(best), "acc": best_acc(y, s, True)}


def spearman(x, y):
    def rank(a):
        o = np.argsort(a, kind="mergesort")
        r = np.empty_like(a, dtype=np.float64)
        r[o] = np.arange(1, len(a) + 1, dtype=np.float64)
        sa = a[o]
        i = 0
        while i < len(a):
            j = i
            while j + 1 < len(a) and sa[j + 1] == sa[i]:
                j += 1
            if j > i:
                r[o[i : j + 1]] = 0.5 * (i + 1 + j + 1)
            i = j + 1
        return r

    x, y = np.asarray(x, float), np.asarray(y, float)
    if len(x) < 5:
        return float("nan")
    xr, yr = rank(x), rank(y)
    xr -= xr.mean()
    yr -= yr.mean()
    den = math.sqrt((xr * xr).sum() * (yr * yr).sum())
    return float((xr * yr).sum() / den) if den > 1e-15 else float("nan")


def pearson(x, y):
    x, y = np.asarray(x, float), np.asarray(y, float)
    x = x - x.mean()
    y = y - y.mean()
    den = math.sqrt((x * x).sum() * (y * y).sum())
    return float((x * y).sum() / den) if den > 1e-15 else float("nan")


def summarize(a):
    a = np.asarray(a, float)
    a = a[~np.isnan(a)]
    if len(a) == 0:
        return {"n": 0}
    return {
        "n": int(len(a)),
        "mean": float(a.mean()),
        "std": float(a.std()),
        "median": float(np.median(a)),
        "p10": float(np.percentile(a, 10)),
        "p90": float(np.percentile(a, 90)),
    }


def eval_binary(idx, y, features: Dict[str, np.ndarray]) -> Dict[str, Any]:
    y = y.astype(np.int32)
    out: Dict[str, Any] = {
        "n": int(len(y)),
        "n_pos": int(y.sum()),
        "n_neg": int(len(y) - y.sum()),
    }
    if out["n_pos"] == 0 or out["n_neg"] == 0:
        out["degenerate"] = True
        return out
    for name, s in features.items():
        # convention: for kappa, higher score = more composite; use -kappa for prime-positive
        score = -s if name == "kappa" else s
        out[f"auroc_{name}"] = auroc(y, score)
        out[f"acc_{name}"] = best_acc(y, score, True)
    names = list(features.keys())
    X = np.column_stack([features[n] for n in names])
    multi = logistic_nd(X, y, n_random=1000, seed=11)
    out["multi_auroc"] = multi["auroc"]
    out["multi_acc"] = multi["acc"]
    out["kappa_auroc"] = out["auroc_kappa"]
    out["auroc_lift"] = multi["auroc"] - out["auroc_kappa"]
    out["acc_lift"] = multi["acc"] - out["acc_kappa"]
    # kappa + well only
    if "well_score" in features:
        X2 = np.column_stack([features["kappa"], features["well_score"]])
        m2 = logistic_nd(X2, y, n_random=400, seed=3)
        out["kappa_well_auroc"] = m2["auroc"]
        out["kappa_well_lift"] = m2["auroc"] - out["auroc_kappa"]
    return out


def main():
    t0 = time.time()
    N = 50000
    N_MAX = N + 2
    print(f"Sieving {N_MAX}...", flush=True)
    d = sieve_divisor_counts(N_MAX)
    is_prime = sieve_primes(N_MAX)
    omega, Omega, is_semi, is_ppow = factor_meta(N_MAX, is_prime)

    ns = np.arange(N_MAX + 1, dtype=np.float64)
    ln = np.zeros(N_MAX + 1)
    ln[1:] = np.log(np.maximum(ns[1:], 1))
    kappa = d.astype(np.float64) * ln / E2
    J = np.zeros(N_MAX + 1)
    J[:N_MAX] = kappa[1:] - kappa[:N_MAX]
    J_prev = np.zeros(N_MAX + 1)
    J_prev[1:] = kappa[1:] - kappa[:-1]
    drop_in = -J_prev
    rise_out = J.copy()
    well_score = np.minimum(drop_in, rise_out)
    abs_J = np.abs(J)
    max_abs_J = np.zeros(N_MAX + 1)
    for n in range(2, N_MAX):
        max_abs_J[n] = max(abs(J[n - 1]), abs(J[n]), abs(J[n + 1]) if n + 1 < N_MAX else 0)

    # strict local minimum of kappa
    is_local_min = np.zeros(N_MAX + 1, dtype=bool)
    for n in range(2, N_MAX):
        is_local_min[n] = kappa[n] < kappa[n - 1] and kappa[n] < kappa[n + 1]

    W = 5
    J_var = np.full(N_MAX + 1, np.nan)
    k_var = np.full(N_MAX + 1, np.nan)
    for n in range(W, N_MAX - W):
        J_var[n] = np.var(J[n - W : n + W + 1])
        k_var[n] = np.var(kappa[n - W : n + W + 1])

    def feat_bundle(idx):
        return {
            "kappa": kappa[idx],
            "well_score": well_score[idx],
            "abs_J": abs_J[idx],
            "J": J[idx],
            "J_prev": J_prev[idx],
            "max_abs_J": max_abs_J[idx],
            "J_var": J_var[idx],
            "k_var": k_var[idx],
        }

    regimes = {}

    # 1) Full mixed ranges where scale mixes primes and small composites
    for a, b, name in [
        (2, 49, "seed_2_49"),
        (2, 200, "mix_2_200"),
        (2, 1000, "mix_2_1000"),
        (2, 10000, "mix_2_10000"),
        (50, 500, "mid_50_500"),
        (100, 5000, "mid_100_5000"),
        (1000, 10000, "hi_1k_10k"),
        (10000, 50000, "xhi_10k_50k"),
    ]:
        idx = np.arange(max(a, W + 1), min(b, N - W - 1) + 1)
        y = is_prime[idx].astype(np.int32)
        regimes[name] = eval_binary(idx, y, feat_bundle(idx))

    # 2) Prime vs semiprime only (exclude other composites) — hard structural
    for a, b, name in [
        (2, 1000, "p_vs_semi_2_1k"),
        (100, 5000, "p_vs_semi_100_5k"),
        (1000, 20000, "p_vs_semi_1k_20k"),
        (10000, 50000, "p_vs_semi_10k_50k"),
    ]:
        idx = np.arange(max(a, W + 1), min(b, N - W - 1) + 1)
        mask = is_prime[idx] | is_semi[idx]
        idx2 = idx[mask]
        y = is_prime[idx2].astype(np.int32)
        regimes[name] = eval_binary(idx2, y, feat_bundle(idx2))

    # 3) Prime vs prime-power only
    for a, b, name in [
        (2, 5000, "p_vs_ppow_2_5k"),
        (100, 20000, "p_vs_ppow_100_20k"),
    ]:
        idx = np.arange(max(a, W + 1), min(b, N - W - 1) + 1)
        mask = is_prime[idx] | is_ppow[idx]
        idx2 = idx[mask]
        y = is_prime[idx2].astype(np.int32)
        regimes[name] = eval_binary(idx2, y, feat_bundle(idx2))

    # 4) Low-d composites + primes: d(n) <= 4
    for a, b, name in [
        (2, 5000, "low_d_2_5k"),
        (100, 20000, "low_d_100_20k"),
        (1000, 50000, "low_d_1k_50k"),
    ]:
        idx = np.arange(max(a, W + 1), min(b, N - W - 1) + 1)
        mask = d[idx] <= 4
        idx2 = idx[mask]
        y = is_prime[idx2].astype(np.int32)
        regimes[name] = eval_binary(idx2, y, feat_bundle(idx2))

    # 5) Local-min rule performance
    local_min_stats = {}
    for a, b, name in [(2, 1000, "2_1k"), (2, 10000, "2_10k"), (1000, 50000, "1k_50k")]:
        idx = np.arange(a, b + 1)
        y = is_prime[idx]
        pred = is_local_min[idx]
        tp = int((pred & y).sum())
        fp = int((pred & ~y).sum())
        fn = int((~pred & y).sum())
        tn = int((~pred & ~y).sum())
        acc = (tp + tn) / len(idx)
        prec = tp / (tp + fp) if tp + fp else 0.0
        rec = tp / (tp + fn) if tp + fn else 0.0
        # compare to kappa adaptive classify
        correct_k = 0
        for n in idx:
            pred_p = kappa[n] < cdl.lookup_adaptive_threshold(int(n))
            if pred_p == bool(is_prime[n]):
                correct_k += 1
        # combined: local min AND kappa < adaptive * factor
        correct_comb = 0
        for n in idx:
            pred_p = is_local_min[n] and (kappa[n] < cdl.lookup_adaptive_threshold(int(n)) * 1.05)
            if pred_p == bool(is_prime[n]):
                correct_comb += 1
        # OR rule
        correct_or = 0
        for n in idx:
            tau = cdl.lookup_adaptive_threshold(int(n))
            pred_p = (kappa[n] < tau) or (is_local_min[n] and kappa[n] < tau * 1.2)
            if pred_p == bool(is_prime[n]):
                correct_or += 1
        local_min_stats[name] = {
            "acc_local_min": acc,
            "precision": prec,
            "recall": rec,
            "tp": tp,
            "fp": fp,
            "fn": fn,
            "tn": tn,
            "acc_adaptive_kappa": correct_k / len(idx),
            "acc_localmin_and_kappa": correct_comb / len(idx),
            "acc_localmin_or_kappa": correct_or / len(idx),
            "prime_valley_rate": float(np.mean(is_local_min[idx][y])) if y.any() else None,
            "composite_valley_rate": float(np.mean(is_local_min[idx][~y])) if (~y).any() else None,
        }

    # 6) Asymmetry entry/exit at primes, p-1, p+1
    asym = {}
    for label, mask_fn in [
        ("prime", lambda: is_prime),
        ("p_minus_1", lambda: np.roll(is_prime, -1)),  # n where n+1 prime
        ("p_plus_1", lambda: np.roll(is_prime, 1)),  # n where n-1 prime
        ("semiprime", lambda: is_semi),
        ("composite", lambda: (~is_prime) & (np.arange(N_MAX + 1) >= 2)),
    ]:
        m = mask_fn()
        idx = np.where(m & (np.arange(N_MAX + 1) >= 3) & (np.arange(N_MAX + 1) <= N))[0]
        S = rise_out[idx] - drop_in[idx]  # exit - entry magnitude
        valley = (drop_in[idx] > 0) & (rise_out[idx] > 0)
        asym[label] = {
            "n": int(len(idx)),
            "valley_fraction": float(valley.mean()) if len(idx) else None,
            "mean_drop_in": float(drop_in[idx].mean()) if len(idx) else None,
            "mean_rise_out": float(rise_out[idx].mean()) if len(idx) else None,
            "mean_asymmetry_S": float(S.mean()) if len(idx) else None,
            "mean_well_score": float(well_score[idx].mean()) if len(idx) else None,
            "mean_kappa": float(kappa[idx].mean()) if len(idx) else None,
            "well_over_kappa": float(well_score[idx].mean() / (kappa[idx].mean() + 1e-12)) if len(idx) else None,
        }

    # 7) Fixed-tau residual: thr=1.5 and thr=2.5 on 50-10000
    residual = {}
    for thr in (1.5, 2.0, 2.5, 3.0):
        idx = np.arange(50, 10001)
        y = is_prime[idx]
        pred = kappa[idx] < thr
        err = pred != y
        residual[f"fixed_tau_{thr}"] = {
            "error_rate": float(err.mean()),
            "fp": int((pred & ~y).sum()),
            "fn": int((~pred & y).sum()),
            "auroc_err_well": auroc(err.astype(np.int32), well_score[idx]),
            "auroc_err_Jvar": auroc(err.astype(np.int32), J_var[idx]),
            "auroc_err_kappa": auroc(err.astype(np.int32), kappa[idx]),
            "auroc_err_dist_tau": auroc(err.astype(np.int32), np.abs(kappa[idx] - thr)),
            # among predicted primes, re-rank
            "n_cand": int(pred.sum()),
        }
        if pred.sum() > 20 and y[pred].sum() > 0 and (~y[pred]).sum() > 0:
            residual[f"fixed_tau_{thr}"]["auroc_trueprime_among_cand_kappa"] = auroc(
                y[pred].astype(np.int32), -kappa[idx][pred]
            )
            residual[f"fixed_tau_{thr}"]["auroc_trueprime_among_cand_well"] = auroc(
                y[pred].astype(np.int32), well_score[idx][pred]
            )
            Xc = np.column_stack([kappa[idx][pred], well_score[idx][pred], abs_J[idx][pred]])
            residual[f"fixed_tau_{thr}"]["auroc_trueprime_among_cand_multi"] = logistic_nd(
                Xc, y[pred].astype(np.int32), n_random=500, seed=5
            )["auroc"]
            residual[f"fixed_tau_{thr}"]["cand_lift"] = (
                residual[f"fixed_tau_{thr}"]["auroc_trueprime_among_cand_multi"]
                - residual[f"fixed_tau_{thr}"]["auroc_trueprime_among_cand_kappa"]
            )

    # 8) Gap prediction deeper: next gap from window features BEFORE the gap
    primes = np.where(is_prime[2 : N + 1])[0] + 2
    gaps = np.diff(primes.astype(float))
    pL = primes[:-1]
    valid = (pL >= W + 1) & (pL + gaps.astype(int) < N)
    pL, gaps = pL[valid], gaps[valid]
    # mid-gap features
    mid = (pL + gaps / 2).astype(int)
    mid = np.clip(mid, W + 1, N - W - 1)
    gap_feat = {
        "spearman_gap_kappa_at_p": spearman(kappa[pL], gaps),
        "spearman_gap_Jvar_at_p": spearman(J_var[pL], gaps),
        "spearman_gap_well_at_p": spearman(well_score[pL], gaps),
        "spearman_gap_Jvar_at_mid": spearman(J_var[mid], gaps),
        "spearman_gap_kvar_at_mid": spearman(k_var[mid], gaps),
        "spearman_gap_mean_absJ_in_gap": None,
        "spearman_gap_max_absJ_in_gap": None,
    }
    mean_absJ_gap = np.zeros(len(pL))
    max_absJ_gap = np.zeros(len(pL))
    for i, p in enumerate(pL):
        g = int(gaps[i])
        seg = abs_J[p : p + g]
        mean_absJ_gap[i] = seg.mean() if len(seg) else 0
        max_absJ_gap[i] = seg.max() if len(seg) else 0
    gap_feat["spearman_gap_mean_absJ_in_gap"] = spearman(mean_absJ_gap, gaps)
    gap_feat["spearman_gap_max_absJ_in_gap"] = spearman(max_absJ_gap, gaps)
    # residual after log p
    A = np.column_stack([np.ones(len(pL)), np.log(pL.astype(float))])
    coef, _, _, _ = np.linalg.lstsq(A, gaps, rcond=None)
    resid = gaps - A @ coef
    gap_feat["spearman_resid_Jvar_p"] = spearman(J_var[pL], resid)
    gap_feat["spearman_resid_kappa_p"] = spearman(kappa[pL], resid)
    gap_feat["spearman_resid_mean_absJ_gap"] = spearman(mean_absJ_gap, resid)
    gap_feat["spearman_resid_max_absJ_gap"] = spearman(max_absJ_gap, resid)
    gap_feat["spearman_resid_Jvar_mid"] = spearman(J_var[mid], resid)
    gap_feat["n_gaps"] = int(len(gaps))
    # holdout large
    m = pL > 10000
    if m.sum() > 100:
        gap_feat["hold_resid_Jvar"] = spearman(J_var[pL[m]], resid[m])
        gap_feat["hold_resid_kappa"] = spearman(kappa[pL[m]], resid[m])
        gap_feat["hold_resid_mean_absJ_gap"] = spearman(mean_absJ_gap[m], resid[m])
        gap_feat["hold_n"] = int(m.sum())

    # 9) Independence: residual well after kappa AND log n
    idx = np.arange(100, 20001)
    y = is_prime[idx].astype(float)
    A3 = np.column_stack([np.ones(len(idx)), kappa[idx], np.log(idx.astype(float))])
    coef_w, _, _, _ = np.linalg.lstsq(A3, well_score[idx], rcond=None)
    w_res = well_score[idx] - A3 @ coef_w
    coef_j, _, _, _ = np.linalg.lstsq(A3, J_var[idx], rcond=None)
    j_res = J_var[idx] - A3 @ coef_j
    # also residual of local_min
    independence = {
        "auroc_kappa": auroc(y.astype(np.int32), -kappa[idx]),
        "auroc_well": auroc(y.astype(np.int32), well_score[idx]),
        "auroc_well_resid_kappa_logn": auroc(y.astype(np.int32), w_res),
        "auroc_Jvar_resid_kappa_logn": auroc(y.astype(np.int32), j_res),
        "corr_well_kappa": pearson(well_score[idx], kappa[idx]),
        "corr_localmin_is_prime": pearson(is_local_min[idx].astype(float), y),
        "localmin_precision": float(
            (is_local_min[idx] & is_prime[idx]).sum() / max(1, is_local_min[idx].sum())
        ),
        "localmin_recall": float(
            (is_local_min[idx] & is_prime[idx]).sum() / max(1, is_prime[idx].sum())
        ),
    }

    # 10) Z-map
    # a = gap residual std; b = mean jump intensity; c = mean kappa
    zmap = {
        "a_gap_resid_std": float(np.std(resid)),
        "b_mean_Jvar_at_primes": float(np.nanmean(J_var[pL])),
        "c_mean_kappa_primes": float(kappa[pL].mean()),
        "I_gap": float(np.std(resid) * np.nanmean(J_var[pL]) / (kappa[pL].mean() + 1e-12)),
        "prime_well_intensity": asym["prime"]["well_over_kappa"],
        "semi_well_intensity": asym["semiprime"]["well_over_kappa"],
        "composite_well_intensity": asym["composite"]["well_over_kappa"],
        "interpretation": (
            "High well_over_kappa at primes vs composites indicates deeper relative geodesic wells. "
            "If classification multi-lift ~0 while well_over_kappa differs, the jump geometry is real "
            "but redundant with level for ranking."
        ),
    }

    # Collect best lifts
    best_lifts = []
    for name, r in regimes.items():
        if r.get("degenerate"):
            continue
        best_lifts.append(
            {
                "regime": name,
                "kappa_auroc": r.get("kappa_auroc"),
                "multi_auroc": r.get("multi_auroc"),
                "auroc_lift": r.get("auroc_lift"),
                "acc_lift": r.get("acc_lift"),
                "kappa_well_lift": r.get("kappa_well_lift"),
                "n": r.get("n"),
                "n_pos": r.get("n_pos"),
            }
        )
    best_lifts.sort(key=lambda x: -(x["auroc_lift"] or -1))

    # Verdict
    max_lift = max((x["auroc_lift"] or 0) for x in best_lifts) if best_lifts else 0
    max_acc_lift = max((x["acc_lift"] or 0) for x in best_lifts) if best_lifts else 0
    cand_lifts = [
        residual[k].get("cand_lift", 0) or 0
        for k in residual
        if "cand_lift" in residual[k]
    ]
    max_cand = max(cand_lifts) if cand_lifts else 0
    gap_win = abs(gap_feat.get("spearman_resid_mean_absJ_gap") or 0) > abs(
        gap_feat.get("spearman_resid_kappa_p") or 0
    ) + 0.05 and abs(gap_feat.get("spearman_resid_mean_absJ_gap") or 0) > 0.15

    partial_ok = independence["auroc_well_resid_kappa_logn"] > 0.55

    if max_lift > 0.02 or max_acc_lift > 0.01 or max_cand > 0.02:
        verdict, strength = "SURVIVOR", "moderate" if max_lift > 0.03 else "weak"
        summary = (
            f"Jump features yield max AUROC lift {max_lift:.4f} and max cand-lift {max_cand:.4f} "
            f"in some regime; not pure noise but limited vs kappa level."
        )
    elif gap_win or (partial_ok and asym["prime"]["valley_fraction"] > 0.9):
        verdict, strength = "SURVIVOR", "descriptive_only"
        summary = (
            "Jump structure is descriptively real (prime valleys) and partially independent of linear kappa, "
            "but does not beat kappa for ranking/classification or gap residual at operational effect size."
        )
    else:
        verdict, strength = "FAILURE", "falsified"
        summary = (
            "J(n) features fail to improve prime classification beyond kappa; gap residual prediction "
            "not improved. Valley geometry is a restatement of local kappa minima from d(n)=2."
        )

    # nuance: if max_lift tiny but valleys strong, report FAILURE for classification claim,
    # with SURVIVOR note for descriptive entry/exit geometry only if valley_fraction separation large
    valley_sep = (asym["prime"]["valley_fraction"] or 0) - (asym["composite"]["valley_fraction"] or 0)

    report = {
        "path": "C",
        "phase": "deep_followup",
        "N": N,
        "verdict": verdict,
        "strength": strength,
        "summary": summary,
        "max_auroc_lift": max_lift,
        "max_acc_lift": max_acc_lift,
        "max_candidate_rerank_lift": max_cand,
        "valley_fraction_sep_prime_minus_composite": valley_sep,
        "best_lifts": best_lifts[:12],
        "regimes": regimes,
        "local_min_stats": local_min_stats,
        "asymmetry": asym,
        "fixed_tau_residuals": residual,
        "gap_prediction": gap_feat,
        "independence": independence,
        "zmap": zmap,
        "prior_art_notes": {
            "divisor_local_structure": (
                "d(n) fluctuates; primes minimize d(n)=2 so kappa local minima at primes are classical "
                "consequences of d-minimality, not a new geometric signal."
            ),
            "adjacent_divisor_jumps": (
                "Differences d(n+1)-d(n) studied indirectly via highly composite neighbors and "
                "smooth numbers; J scales that by ln factors."
            ),
            "PGS_delta": (
                "Sibling PGS studies ordered d-field inside gaps. Path C studies kappa-jump at integers "
                "and windows, not ordered gap-internal structure. Sharp delta: pointwise jump field vs "
                "intra-gap ordered divisor path."
            ),
            "CDL_level": "Parent CDL uses kappa level + adaptive tau; Path C adds discrete derivative.",
        },
        "attacks": {
            "conventional": (
                "J is almost determined by (d(n),d(n+1),n); primes force d=2 so wells are automatic. "
                "Experts: 'local minima of d(n)' already known."
            ),
            "edge_case": (
                "At large n within a narrow band, kappa separates perfectly (AUROC=1) so jump cannot lift. "
                "At mixed small n, scale confounds dominate. Twin primes share neighborhood structure."
            ),
            "so_what": (
                "Even with valley_fraction~1 for primes, adaptive-kappa accuracy already high; "
                "jump adds no prefilter gain if level already ranks."
            ),
            "assessment": None,
        },
        "elapsed_sec": time.time() - t0,
    }

    # Final assessment after attacks
    if max_lift < 0.01 and max_cand < 0.01 and not gap_win:
        report["verdict"] = "FAILURE"
        report["strength"] = "falsified"
        report["summary"] = (
            "FAILURE: asymmetric jump / well structure at primes is real descriptively "
            f"(valley_fraction primes={asym['prime']['valley_fraction']:.3f} vs "
            f"composites={asym['composite']['valley_fraction']:.3f}) but adds negligible "
            f"ranking lift (max AUROC lift={max_lift:.4f}, max cand rerank lift={max_cand:.4f}) "
            "beyond kappa level. Gap residuals not better predicted by jump intensity than kappa. "
            "Hypothesis falsified for operational classification/gap claims."
        )
        report["attacks"]["assessment"] = (
            "All three attacks largely succeed for the operational claim. "
            "Descriptive well geometry survives but is not novel vs d(n) local minima."
        )
        report["strongest_outcome"] = {
            "type": "failure",
            "claim_killed": "Jump variance / asymmetric entry-exit beats or meaningfully lifts kappa for prime class or gaps",
            "descriptive_residue": "Primes sit in kappa wells (high valley_fraction) more than composites",
            "evidence_keys": ["best_lifts", "asymmetry", "gap_prediction", "independence", "local_min_stats"],
        }
    else:
        report["strongest_outcome"] = {
            "type": "survivor",
            "max_auroc_lift": max_lift,
            "evidence_keys": ["best_lifts", "fixed_tau_residuals"],
        }

    outp = OUT / "path_c_deep_results.json"
    with open(outp, "w") as f:
        json.dump(report, f, indent=2, allow_nan=True)
    print(f"Wrote {outp}", flush=True)
    print("VERDICT", report["verdict"], report["strength"], flush=True)
    print("max_auroc_lift", max_lift, "max_cand", max_cand, "valley_sep", valley_sep, flush=True)
    print("top lifts:", best_lifts[:5], flush=True)
    print("independence", independence, flush=True)
    print("gap", {k: gap_feat[k] for k in gap_feat if "resid" in k or k.startswith("hold")}, flush=True)
    print("elapsed", report["elapsed_sec"], flush=True)


if __name__ == "__main__":
    main()
