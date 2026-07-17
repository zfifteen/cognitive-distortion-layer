#!/usr/bin/env python3
"""
Path B probe: Dual of v-recovery.

Recover support mixture weights π from Z at FIXED known v (esp. v=e²/2),
rather than recovering v from a known support prior.

Hypothesis: At the prime fixed-point speed v*=e²/2, Z parks primes at 1 and
contracts composites, so low-d family mass is more identifiable from Z samples
than from raw magnitude samples of equal size (higher Fisher info / lower MAE
sample complexity).

Fair comparison (no labels / no factoring at inference time):
  - Observer A sees unlabeled Z samples only
  - Observer B sees unlabeled n magnitude samples only
  - Both know family generators and fixed v when computing theoretical densities
    for Z; Observer B uses only magnitude-based features (log n histogram/moments)

Also attack:
  - Wrong fixed v (not e²/2)
  - Multi-family (d=2,3,4,6+) recovery
  - Natural-density baseline (π_nat ≈ 1/ln N) as non-informative magnitude prior
"""

from __future__ import annotations

import json
import math
import sys
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Sequence, Tuple

import numpy as np
from scipy import optimize, stats

ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / "src" / "python"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from v_recovery import precompute_curvature_table, validate_precomputed_kappas  # noqa: E402

ARTIFACT_DIR = Path(__file__).resolve().parent
V_STAR = (math.e ** 2) / 2.0


@dataclass
class FamilySpec:
    name: str
    mask: np.ndarray  # boolean over support indices


def build_families(divisor_counts: np.ndarray) -> List[FamilySpec]:
    """Partition support into exact-d families plus residual high-d bucket."""
    families = [
        FamilySpec("d2_primes", divisor_counts == 2),
        FamilySpec("d3_p2", divisor_counts == 3),
        FamilySpec("d4", divisor_counts == 4),
        FamilySpec("d_ge_5", divisor_counts >= 5),
    ]
    # ensure full cover
    covered = np.zeros_like(divisor_counts, dtype=bool)
    for f in families:
        covered |= f.mask
    if not np.all(covered):
        raise RuntimeError("family partition incomplete")
    return families


def family_index_map(families: Sequence[FamilySpec]) -> np.ndarray:
    idx = np.full(len(families[0].mask), -1, dtype=np.int32)
    for k, fam in enumerate(families):
        idx[fam.mask] = k
    if np.any(idx < 0):
        raise RuntimeError("unassigned support points")
    return idx


def z_from_n(numbers: np.ndarray, kappas: np.ndarray, v: float) -> np.ndarray:
    return numbers / np.exp(v * kappas)


def sample_mixture(
    rng: np.random.Generator,
    family_indices: List[np.ndarray],
    pi: np.ndarray,
    m: int,
) -> Tuple[np.ndarray, np.ndarray]:
    """Sample m indices: first draw family ~ pi, then uniform within family."""
    pi = np.asarray(pi, dtype=np.float64)
    pi = pi / pi.sum()
    fam_draws = rng.choice(len(pi), size=m, p=pi)
    out = np.empty(m, dtype=np.int64)
    labels = fam_draws.copy()
    for k in range(len(pi)):
        where = np.where(fam_draws == k)[0]
        if len(where) == 0:
            continue
        pool = family_indices[k]
        out[where] = rng.choice(pool, size=len(where), replace=True)
    return out, labels


def features_z(z: np.ndarray) -> np.ndarray:
    z = np.clip(np.asarray(z, dtype=np.float64), 1e-300, None)
    log_z = np.log(z)
    # Prime parking fraction: mass near Z=1
    park = float(np.mean(np.abs(z - 1.0) < 1e-9))
    soft_park = float(np.mean(np.abs(log_z) < 0.05))
    hist, _ = np.histogram(log_z, bins=12, range=(-20.0, 2.0), density=True)
    hist = hist / max(hist.sum(), 1e-12)
    quant = np.quantile(log_z, [0.1, 0.25, 0.5, 0.75, 0.9])
    return np.concatenate(
        [
            np.array(
                [
                    park,
                    soft_park,
                    float(np.mean(log_z)),
                    float(np.var(log_z)),
                    float(stats.skew(log_z, bias=False)) if len(z) > 2 else 0.0,
                    float(stats.kurtosis(log_z, fisher=True, bias=False)) if len(z) > 3 else 0.0,
                    float(np.mean(z)),
                    float(np.median(z)),
                    float(np.std(z) / max(abs(np.mean(z)), 1e-12)),
                ],
                dtype=np.float64,
            ),
            quant.astype(np.float64),
            hist.astype(np.float64),
        ]
    )


def features_raw_n(numbers: np.ndarray) -> np.ndarray:
    n = np.asarray(numbers, dtype=np.float64)
    log_n = np.log(n)
    hist, _ = np.histogram(log_n, bins=12, range=(math.log(2.0), math.log(float(n.max()) + 1.0)), density=True)
    hist = hist / max(hist.sum(), 1e-12)
    quant = np.quantile(log_n, [0.1, 0.25, 0.5, 0.75, 0.9])
    # modular / parity-ish features without factoring
    frac_even = float(np.mean((n % 2) == 0))
    frac_mod3 = float(np.mean((n % 3) == 0))
    frac_mod5 = float(np.mean((n % 5) == 0))
    return np.concatenate(
        [
            np.array(
                [
                    float(np.mean(log_n)),
                    float(np.var(log_n)),
                    float(stats.skew(log_n, bias=False)) if len(n) > 2 else 0.0,
                    float(stats.kurtosis(log_n, fisher=True, bias=False)) if len(n) > 3 else 0.0,
                    float(np.mean(n)),
                    float(np.median(n)),
                    float(np.std(n) / max(abs(np.mean(n)), 1e-12)),
                    frac_even,
                    frac_mod3,
                    frac_mod5,
                ],
                dtype=np.float64,
            ),
            quant.astype(np.float64),
            hist.astype(np.float64),
        ]
    )


def build_reference_fingerprints(
    rng: np.random.Generator,
    numbers: np.ndarray,
    kappas: np.ndarray,
    family_indices: List[np.ndarray],
    pi_grid: np.ndarray,
    v: float,
    m_ref: int,
    trials: int,
    feature_fn: str,
) -> Tuple[np.ndarray, np.ndarray]:
    """Mean fingerprint per pi on grid for nearest-neighbor / interpolation recovery."""
    fps = []
    for pi in pi_grid:
        rows = []
        for _ in range(trials):
            idxs, _ = sample_mixture(rng, family_indices, pi, m_ref)
            if feature_fn == "z":
                z = z_from_n(numbers[idxs], kappas[idxs], v)
                rows.append(features_z(z))
            else:
                rows.append(features_raw_n(numbers[idxs]))
        fps.append(np.mean(np.vstack(rows), axis=0))
    stack = np.vstack(fps)
    scale = np.std(stack, axis=0)
    scale[scale < 1e-8] = 1.0
    return stack, scale


def recover_pi_fingerprint(
    obs_fp: np.ndarray,
    ref_fps: np.ndarray,
    ref_scale: np.ndarray,
    pi_grid: np.ndarray,
) -> np.ndarray:
    """Nearest grid pi by scaled L2; 1D refine via local parabola when applicable."""
    dists = np.linalg.norm((ref_fps - obs_fp) / ref_scale, axis=1)
    best = int(np.argmin(dists))
    # For multi-dim pi_grid (rows), return the grid row; for 1D simplex param use interp
    if pi_grid.ndim == 1:
        estimate = float(pi_grid[best])
        if 0 < best < len(pi_grid) - 1:
            x1, x2, x3 = pi_grid[best - 1 : best + 2]
            y1, y2, y3 = dists[best - 1 : best + 2]
            denom = (x1 - x2) * (x1 - x3) * (x2 - x3)
            if abs(denom) > 1e-12:
                a = (x3 * (y2 - y1) + x2 * (y1 - y3) + x1 * (y3 - y2)) / denom
                b = (x3 * x3 * (y1 - y2) + x2 * x2 * (y3 - y1) + x1 * x1 * (y2 - y3)) / denom
                if abs(a) > 1e-12:
                    refined = -b / (2 * a)
                    if pi_grid[0] <= refined <= pi_grid[-1]:
                        estimate = float(refined)
        return np.array([estimate, 1.0 - estimate], dtype=np.float64)
    return pi_grid[best].astype(np.float64).copy()


def recover_pi_z_park(z: np.ndarray, eps: float = 1e-9) -> float:
    """Direct prime-mass estimator from parking mass at Z=1 (v=v*)."""
    return float(np.mean(np.abs(z - 1.0) < eps))


def recover_pi_mle_binary(
    values: np.ndarray,
    fam_values: List[np.ndarray],
    n_bins: int = 64,
) -> float:
    """
    1D histogram MLE for binary mixture on a scalar observation (log Z or log n).
    fam_values[0], fam_values[1] are population samples of the scalar feature per family.
    """
    lo = min(float(np.min(values)), min(float(np.min(fv)) for fv in fam_values))
    hi = max(float(np.max(values)), max(float(np.max(fv)) for fv in fam_values))
    edges = np.linspace(lo - 1e-9, hi + 1e-9, n_bins + 1)
    dens = []
    for fv in fam_values:
        h, _ = np.histogram(fv, bins=edges, density=True)
        h = h.astype(np.float64) + 1e-12
        h /= h.sum()
        dens.append(h)
    dens0, dens1 = dens[0], dens[1]
    bin_idx = np.clip(np.searchsorted(edges, values, side="right") - 1, 0, n_bins - 1)

    def nll(p):
        p = float(np.clip(p[0], 1e-6, 1 - 1e-6))
        mix = p * dens0[bin_idx] + (1.0 - p) * dens1[bin_idx]
        return -float(np.sum(np.log(mix + 1e-300)))

    res = optimize.minimize(nll, x0=np.array([0.3]), bounds=[(1e-6, 1 - 1e-6)], method="L-BFGS-B")
    return float(res.x[0])


def recover_pi_mle_multi(
    values: np.ndarray,
    fam_values: List[np.ndarray],
    n_bins: int = 48,
) -> np.ndarray:
    """Histogram MLE over K-family simplex for scalar feature."""
    k = len(fam_values)
    lo = min(float(np.min(values)), min(float(np.min(fv)) for fv in fam_values))
    hi = max(float(np.max(values)), max(float(np.max(fv)) for fv in fam_values))
    edges = np.linspace(lo - 1e-9, hi + 1e-9, n_bins + 1)
    dens = []
    for fv in fam_values:
        h, _ = np.histogram(fv, bins=edges, density=True)
        h = h.astype(np.float64) + 1e-12
        h /= h.sum()
        dens.append(h)
    dens_m = np.vstack(dens)  # K x bins
    bin_idx = np.clip(np.searchsorted(edges, values, side="right") - 1, 0, n_bins - 1)

    def nll(theta):
        # softmax parametrization
        e = np.exp(theta - np.max(theta))
        p = e / e.sum()
        mix = dens_m.T[bin_idx] @ p
        return -float(np.sum(np.log(mix + 1e-300)))

    res = optimize.minimize(nll, x0=np.zeros(k), method="BFGS")
    e = np.exp(res.x - np.max(res.x))
    return (e / e.sum()).astype(np.float64)


def numerical_fisher_binary(
    rng: np.random.Generator,
    numbers: np.ndarray,
    kappas: np.ndarray,
    family_indices: List[np.ndarray],
    pi_true: float,
    v: float,
    m: int,
    trials: int,
    channel: str,
) -> float:
    """
    Approximate Fisher information for π via Monte Carlo score variance of
    histogram likelihood on log-Z or log-n.
    I(π) = E[(d log f / dπ)^2]
    """
    # Build fixed population densities
    n0 = numbers[family_indices[0]]
    n1 = numbers[family_indices[1]]
    if channel == "z":
        pop0 = np.log(np.clip(z_from_n(n0, kappas[family_indices[0]], v), 1e-300, None))
        pop1 = np.log(np.clip(z_from_n(n1, kappas[family_indices[1]], v), 1e-300, None))
    else:
        pop0 = np.log(n0.astype(np.float64))
        pop1 = np.log(n1.astype(np.float64))

    edges = np.linspace(
        min(float(pop0.min()), float(pop1.min())) - 1e-9,
        max(float(pop0.max()), float(pop1.max())) + 1e-9,
        65,
    )
    d0, _ = np.histogram(pop0, bins=edges, density=True)
    d1, _ = np.histogram(pop1, bins=edges, density=True)
    d0 = d0 + 1e-12
    d1 = d1 + 1e-12
    d0 /= d0.sum()
    d1 /= d1.sum()

    scores = []
    pi = float(np.clip(pi_true, 1e-4, 1 - 1e-4))
    for _ in range(trials):
        idxs, _ = sample_mixture(rng, family_indices, np.array([pi, 1 - pi]), m)
        if channel == "z":
            vals = np.log(np.clip(z_from_n(numbers[idxs], kappas[idxs], v), 1e-300, None))
        else:
            vals = np.log(numbers[idxs].astype(np.float64))
        b = np.clip(np.searchsorted(edges, vals, side="right") - 1, 0, len(d0) - 1)
        f = pi * d0[b] + (1 - pi) * d1[b]
        # score for full sample (sum of iid scores)
        s = np.sum((d0[b] - d1[b]) / f)
        scores.append(s)
    scores = np.asarray(scores, dtype=np.float64)
    # Fisher for the sample of size m; report per-sample Fisher = Var(score_sum)/m^2 * m = Var(sum)/m
    var_sum = float(np.var(scores, ddof=1))
    return var_sum / m  # per-observation Fisher approx


def mae_rows(errors: Sequence[float]) -> Dict[str, float]:
    arr = np.asarray(errors, dtype=np.float64)
    return {
        "mae": float(np.mean(np.abs(arr))),
        "rmse": float(np.sqrt(np.mean(arr ** 2))),
        "bias": float(np.mean(arr)),
        "p90_abs": float(np.quantile(np.abs(arr), 0.90)),
        "success_rate_0p05": float(np.mean(np.abs(arr) < 0.05)),
        "success_rate_0p10": float(np.mean(np.abs(arr) < 0.10)),
    }


def run_binary_experiment(
    numbers: np.ndarray,
    kappas: np.ndarray,
    families: List[FamilySpec],
    rng: np.random.Generator,
    sample_sizes: List[int],
    pi_values: List[float],
    trials: int,
    v_fixed: float,
) -> Dict:
    # Binary: primes vs non-primes
    prime_idx = np.where(families[0].mask)[0]
    comp_idx = np.where(~families[0].mask)[0]
    fam_idx_list = [prime_idx, comp_idx]

    # Population scalars for MLE
    z_pop_prime = z_from_n(numbers[prime_idx], kappas[prime_idx], v_fixed)
    z_pop_comp = z_from_n(numbers[comp_idx], kappas[comp_idx], v_fixed)
    logz_pop = [np.log(np.clip(z_pop_prime, 1e-300, None)), np.log(np.clip(z_pop_comp, 1e-300, None))]
    logn_pop = [np.log(numbers[prime_idx].astype(np.float64)), np.log(numbers[comp_idx].astype(np.float64))]

    # Fingerprint grids (1D π_prime)
    pi_grid = np.linspace(0.05, 0.95, 19)
    pi_grid_vec = pi_grid  # 1D path in recover_pi_fingerprint

    results_cells = []
    for m in sample_sizes:
        # Build references at this m
        ref_z, scale_z = build_reference_fingerprints(
            rng, numbers, kappas, fam_idx_list,
            np.array([[p, 1 - p] for p in pi_grid]),
            v_fixed, m_ref=m, trials=max(6, trials // 2), feature_fn="z",
        )
        # For 1D recovery path we need matching API: use multi-row grid
        # We'll recover via argmin over multi pi vectors
        ref_n, scale_n = build_reference_fingerprints(
            rng, numbers, kappas, fam_idx_list,
            np.array([[p, 1 - p] for p in pi_grid]),
            v_fixed, m_ref=m, trials=max(6, trials // 2), feature_fn="n",
        )
        pi_grid_rows = np.array([[p, 1 - p] for p in pi_grid], dtype=np.float64)

        for method in ["z_park", "z_mle", "z_fingerprint", "n_mle", "n_fingerprint", "natural_density"]:
            for pi_true in pi_values:
                errs = []
                for t in range(trials):
                    idxs, _ = sample_mixture(
                        rng, fam_idx_list, np.array([pi_true, 1 - pi_true]), m
                    )
                    sampled_n = numbers[idxs]
                    sampled_z = z_from_n(sampled_n, kappas[idxs], v_fixed)

                    if method == "z_park":
                        pi_hat = recover_pi_z_park(sampled_z)
                    elif method == "z_mle":
                        pi_hat = recover_pi_mle_binary(
                            np.log(np.clip(sampled_z, 1e-300, None)), logz_pop
                        )
                    elif method == "z_fingerprint":
                        fp = features_z(sampled_z)
                        pi_hat_vec = recover_pi_fingerprint(fp, ref_z, scale_z, pi_grid_rows)
                        pi_hat = float(pi_hat_vec[0])
                    elif method == "n_mle":
                        pi_hat = recover_pi_mle_binary(np.log(sampled_n.astype(np.float64)), logn_pop)
                    elif method == "n_fingerprint":
                        fp = features_raw_n(sampled_n)
                        pi_hat_vec = recover_pi_fingerprint(fp, ref_n, scale_n, pi_grid_rows)
                        pi_hat = float(pi_hat_vec[0])
                    elif method == "natural_density":
                        # Classical baseline: ignore sample structure, use 1/ln N
                        pi_hat = 1.0 / math.log(float(numbers[-1]))
                    else:
                        raise ValueError(method)
                    errs.append(pi_hat - pi_true)

                cell = {
                    "sample_size": m,
                    "method": method,
                    "pi_true": pi_true,
                    "v_fixed": v_fixed,
                    "channel": "z" if method.startswith("z") else ("baseline" if method == "natural_density" else "n"),
                    **mae_rows(errs),
                }
                results_cells.append(cell)

    # Fisher info at representative π
    fisher = {}
    for m in sample_sizes:
        for channel in ["z", "n"]:
            fi = numerical_fisher_binary(
                rng, numbers, kappas, fam_idx_list, pi_true=0.25, v=v_fixed, m=m, trials=80, channel=channel
            )
            fisher[f"{channel}_m{m}"] = fi

    return {"cells": results_cells, "fisher_per_obs_approx": fisher, "v_fixed": v_fixed}


def run_multifamily_experiment(
    numbers: np.ndarray,
    kappas: np.ndarray,
    families: List[FamilySpec],
    rng: np.random.Generator,
    sample_sizes: List[int],
    trials: int,
    v_fixed: float,
) -> Dict:
    fam_idx_list = [np.where(f.mask)[0] for f in families]
    # ensure nonempty
    for i, ix in enumerate(fam_idx_list):
        if len(ix) == 0:
            raise RuntimeError(f"empty family {families[i].name}")

    true_pis = [
        np.array([0.35, 0.05, 0.25, 0.35], dtype=np.float64),
        np.array([0.15, 0.10, 0.35, 0.40], dtype=np.float64),
        np.array([0.50, 0.05, 0.20, 0.25], dtype=np.float64),
    ]
    for p in true_pis:
        p /= p.sum()

    logz_pops = []
    logn_pops = []
    for ix in fam_idx_list:
        z = z_from_n(numbers[ix], kappas[ix], v_fixed)
        logz_pops.append(np.log(np.clip(z, 1e-300, None)))
        logn_pops.append(np.log(numbers[ix].astype(np.float64)))

    cells = []
    for m in sample_sizes:
        for pi_true in true_pis:
            errs_z = []
            errs_n = []
            l1_z = []
            l1_n = []
            for _ in range(trials):
                idxs, _ = sample_mixture(rng, fam_idx_list, pi_true, m)
                sampled_n = numbers[idxs]
                sampled_z = z_from_n(sampled_n, kappas[idxs], v_fixed)
                pi_z = recover_pi_mle_multi(np.log(np.clip(sampled_z, 1e-300, None)), logz_pops)
                pi_n = recover_pi_mle_multi(np.log(sampled_n.astype(np.float64)), logn_pops)
                errs_z.append(float(pi_z[0] - pi_true[0]))  # prime mass error
                errs_n.append(float(pi_n[0] - pi_true[0]))
                l1_z.append(float(np.sum(np.abs(pi_z - pi_true))))
                l1_n.append(float(np.sum(np.abs(pi_n - pi_true))))
            cells.append(
                {
                    "sample_size": m,
                    "pi_true": pi_true.tolist(),
                    "v_fixed": v_fixed,
                    "z_mle_prime_mae": mae_rows(errs_z)["mae"],
                    "n_mle_prime_mae": mae_rows(errs_n)["mae"],
                    "z_mle_l1_mean": float(np.mean(l1_z)),
                    "n_mle_l1_mean": float(np.mean(l1_n)),
                    "l1_ratio_n_over_z": float(np.mean(l1_n) / max(np.mean(l1_z), 1e-12)),
                    "prime_mae_ratio_n_over_z": float(
                        mae_rows(errs_n)["mae"] / max(mae_rows(errs_z)["mae"], 1e-12)
                    ),
                }
            )
    return {"cells": cells, "family_names": [f.name for f in families], "v_fixed": v_fixed}


def run_v_sensitivity(
    numbers: np.ndarray,
    kappas: np.ndarray,
    families: List[FamilySpec],
    rng: np.random.Generator,
    m: int,
    trials: int,
    pi_true: float,
    v_values: List[float],
) -> Dict:
    prime_idx = np.where(families[0].mask)[0]
    comp_idx = np.where(~families[0].mask)[0]
    fam_idx_list = [prime_idx, comp_idx]
    rows = []
    for v in v_values:
        logz_pop = [
            np.log(np.clip(z_from_n(numbers[prime_idx], kappas[prime_idx], v), 1e-300, None)),
            np.log(np.clip(z_from_n(numbers[comp_idx], kappas[comp_idx], v), 1e-300, None)),
        ]
        # separation diagnostics
        z_p = z_from_n(numbers[prime_idx], kappas[prime_idx], v)
        z_c = z_from_n(numbers[comp_idx], kappas[comp_idx], v)
        sep = float(abs(np.mean(np.log(np.clip(z_p, 1e-300, None))) - np.mean(np.log(np.clip(z_c, 1e-300, None)))))
        park_mass_mean = float(np.mean(np.abs(z_p - 1.0) < 1e-9))

        errs_park = []
        errs_mle = []
        for _ in range(trials):
            idxs, _ = sample_mixture(rng, fam_idx_list, np.array([pi_true, 1 - pi_true]), m)
            z = z_from_n(numbers[idxs], kappas[idxs], v)
            errs_park.append(recover_pi_z_park(z) - pi_true)
            errs_mle.append(
                recover_pi_mle_binary(np.log(np.clip(z, 1e-300, None)), logz_pop) - pi_true
            )
        rows.append(
            {
                "v": v,
                "is_v_star": abs(v - V_STAR) < 1e-12,
                "logz_mean_separation": sep,
                "prime_exact_park_fraction": park_mass_mean,
                "z_park_mae": mae_rows(errs_park)["mae"],
                "z_mle_mae": mae_rows(errs_mle)["mae"],
            }
        )
    return {"m": m, "pi_true": pi_true, "rows": rows}


def z_map_summary(numbers: np.ndarray, kappas: np.ndarray, families: List[FamilySpec], v: float) -> Dict:
    out = {"v": v, "v_star": V_STAR, "families": []}
    for fam in families:
        ix = np.where(fam.mask)[0]
        z = z_from_n(numbers[ix], kappas[ix], v)
        out["families"].append(
            {
                "name": fam.name,
                "count": int(len(ix)),
                "mean_z": float(np.mean(z)),
                "median_z": float(np.median(z)),
                "std_z": float(np.std(z)),
                "mean_log_z": float(np.mean(np.log(np.clip(z, 1e-300, None)))),
                "frac_exact_1": float(np.mean(np.abs(z - 1.0) < 1e-9)),
                "p05_z": float(np.quantile(z, 0.05)),
                "p95_z": float(np.quantile(z, 0.95)),
            }
        )
    return out


def main() -> None:
    n_max = 20_000
    seed = 20260716
    trials = 40
    sample_sizes = [50, 100, 250, 500, 1000, 2000]
    pi_values = [0.10, 0.25, 0.40, 0.55]

    rng = np.random.default_rng(seed)
    table = precompute_curvature_table(n_max)
    validate_precomputed_kappas(table["kappas"], limit=100)
    numbers = table["numbers"].astype(np.float64)
    kappas = table["kappas"].astype(np.float64)
    dcounts = table["divisor_counts"]
    families = build_families(dcounts)

    print(f"Support [2,{n_max}] size={len(numbers)}")
    for f in families:
        print(f"  {f.name}: {int(f.mask.sum())}")

    zmap_star = z_map_summary(numbers, kappas, families, V_STAR)
    zmap_one = z_map_summary(numbers, kappas, families, 1.0)

    print("Running binary mixture recovery at v* ...")
    binary_star = run_binary_experiment(
        numbers, kappas, families, rng, sample_sizes, pi_values, trials, V_STAR
    )
    print("Running binary mixture recovery at v=1.0 ...")
    binary_v1 = run_binary_experiment(
        numbers, kappas, families, rng, sample_sizes, pi_values, trials, 1.0
    )
    print("Running multi-family MLE ...")
    multi_star = run_multifamily_experiment(
        numbers, kappas, families, rng, sample_sizes=[100, 500, 2000], trials=trials, v_fixed=V_STAR
    )
    multi_v1 = run_multifamily_experiment(
        numbers, kappas, families, rng, sample_sizes=[100, 500, 2000], trials=trials, v_fixed=1.0
    )
    print("Running v-sensitivity sweep ...")
    vsens = run_v_sensitivity(
        numbers,
        kappas,
        families,
        rng,
        m=500,
        trials=trials,
        pi_true=0.25,
        v_values=[0.5, 1.0, 1.5, V_STAR, 2.5, 3.0, (math.e ** 2) / 3.0, (math.e ** 2) / 4.0],
    )

    # Aggregate headline comparisons at each m: mean MAE over pi_true
    def aggregate_method(cells, method, m):
        subset = [c for c in cells if c["method"] == method and c["sample_size"] == m]
        if not subset:
            return None
        return {
            "mae_mean": float(np.mean([c["mae"] for c in subset])),
            "success_0p05_mean": float(np.mean([c["success_rate_0p05"] for c in subset])),
        }

    headlines = []
    comparison_table = []
    for m in sample_sizes:
        z_park = aggregate_method(binary_star["cells"], "z_park", m)
        z_mle = aggregate_method(binary_star["cells"], "z_mle", m)
        n_mle = aggregate_method(binary_star["cells"], "n_mle", m)
        n_fp = aggregate_method(binary_star["cells"], "n_fingerprint", m)
        z_fp = aggregate_method(binary_star["cells"], "z_fingerprint", m)
        nat = aggregate_method(binary_star["cells"], "natural_density", m)
        row = {
            "m": m,
            "z_park_mae": z_park["mae_mean"] if z_park else None,
            "z_mle_mae": z_mle["mae_mean"] if z_mle else None,
            "z_fingerprint_mae": z_fp["mae_mean"] if z_fp else None,
            "n_mle_mae": n_mle["mae_mean"] if n_mle else None,
            "n_fingerprint_mae": n_fp["mae_mean"] if n_fp else None,
            "natural_density_mae": nat["mae_mean"] if nat else None,
        }
        if z_mle and n_mle and z_mle["mae_mean"] > 0:
            row["mae_ratio_n_mle_over_z_mle"] = n_mle["mae_mean"] / z_mle["mae_mean"]
        if z_park and n_mle and z_park["mae_mean"] > 0:
            row["mae_ratio_n_mle_over_z_park"] = n_mle["mae_mean"] / max(z_park["mae_mean"], 1e-12)
        comparison_table.append(row)

    # Fisher ratios
    fisher_ratios = {}
    for m in sample_sizes:
        zfi = binary_star["fisher_per_obs_approx"].get(f"z_m{m}")
        nfi = binary_star["fisher_per_obs_approx"].get(f"n_m{m}")
        if zfi is not None and nfi is not None and nfi > 0:
            fisher_ratios[str(m)] = {
                "I_z": zfi,
                "I_n": nfi,
                "ratio_Iz_over_In": zfi / nfi if nfi > 0 else None,
            }

    # Verdict logic
    # Strong survivor if: (1) z methods beat n methods by ratio >= 2 at m>=250
    # (2) advantage peaks near v*
    # (3) multi-family L1 also favors Z
    ratios = [r.get("mae_ratio_n_mle_over_z_mle") for r in comparison_table if r.get("mae_ratio_n_mle_over_z_mle")]
    median_ratio = float(np.median(ratios)) if ratios else 0.0
    large_m_ratios = [
        r["mae_ratio_n_mle_over_z_mle"]
        for r in comparison_table
        if r["m"] >= 250 and r.get("mae_ratio_n_mle_over_z_mle")
    ]
    mean_large_ratio = float(np.mean(large_m_ratios)) if large_m_ratios else 0.0

    v_rows = vsens["rows"]
    best_v_row = min(v_rows, key=lambda r: r["z_mle_mae"])
    vstar_row = next(r for r in v_rows if r["is_v_star"])
    v_advantage = best_v_row["v"]  # is best near v*?

    multi_ratios = [c["l1_ratio_n_over_z"] for c in multi_star["cells"]]
    multi_mean_ratio = float(np.mean(multi_ratios)) if multi_ratios else 0.0

    survivor = (
        mean_large_ratio >= 2.0
        and multi_mean_ratio >= 1.5
        and vstar_row["z_mle_mae"] <= min(r["z_mle_mae"] for r in v_rows) * 1.25
        and vstar_row["prime_exact_park_fraction"] > 0.99
    )
    partial = (mean_large_ratio >= 1.3) or (multi_mean_ratio >= 1.3)

    if survivor:
        verdict = "SURVIVOR"
        verdict_detail = (
            "At fixed v*=e^2/2, mixture weights of low-d families are substantially more "
            "identifiable from Z samples than from raw magnitude samples of equal size."
        )
    elif partial:
        verdict = "PARTIAL_SURVIVOR"
        verdict_detail = (
            "Z channel improves mixture recovery relative to raw n, but the advantage is "
            "weaker than hypothesized or not cleanly peaked only at v*."
        )
    else:
        verdict = "FAILURE"
        verdict_detail = (
            "Hypothesis not supported: Z at fixed v does not reliably reduce sample complexity "
            "for mixture weight recovery versus raw magnitude features."
        )

    payload = {
        "experiment": "path_b_dual_v_recovery_mixture_weights",
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "config": {
            "n_max": n_max,
            "seed": seed,
            "trials_per_cell": trials,
            "sample_sizes": sample_sizes,
            "pi_values_binary": pi_values,
            "v_star": V_STAR,
            "families": [f.name for f in families],
            "family_counts": {f.name: int(f.mask.sum()) for f in families},
        },
        "z_map": {"v_star": zmap_star, "v_1": zmap_one},
        "binary_at_v_star": binary_star,
        "binary_at_v_1": binary_v1,
        "multifamily_at_v_star": multi_star,
        "multifamily_at_v_1": multi_v1,
        "v_sensitivity": vsens,
        "comparison_table": comparison_table,
        "fisher_ratios": fisher_ratios,
        "headline_metrics": {
            "median_mae_ratio_n_mle_over_z_mle": median_ratio,
            "mean_mae_ratio_m_ge_250": mean_large_ratio,
            "mean_multifamily_l1_ratio_n_over_z": multi_mean_ratio,
            "best_v_for_z_mle": best_v_row["v"],
            "v_star_z_mle_mae": vstar_row["z_mle_mae"],
            "v_star_park_mae": vstar_row["z_park_mae"],
            "v_star_prime_exact_park_fraction": vstar_row["prime_exact_park_fraction"],
        },
        "verdict": verdict,
        "verdict_detail": verdict_detail,
        "prior_art_notes": [
            {
                "idea": "v_recovery (CDL Sprint 3)",
                "overlap": "Distributional recovery from Z fingerprints/MLE/moments",
                "delta": "Inverts the dual: recovers π at fixed v, not v at fixed support prior",
            },
            {
                "idea": "z-process-fingerprint joint (regime, v)",
                "overlap": "Process channel view of Z; regime sensitivity",
                "delta": "Path B freezes v (esp. v*) and targets mixture weights as the parameter of interest",
            },
            {
                "idea": "divisor-family-resonance v_d=e^2/d fixed points",
                "overlap": "Uses family fixed-point geometry (primes at Z=1)",
                "delta": "Uses parking as a statistical sufficient structure for π recovery, not band flatness catalog",
            },
            {
                "idea": "Finite mixture models / EM / Fisher for mixing proportions",
                "overlap": "Standard mixture-weight MLE and Fisher information",
                "delta": "Claims a CDL-specific channel advantage: fixed-point transform induces near-separable components",
            },
            {
                "idea": "Prime number theorem density 1/ln x",
                "overlap": "Baseline for natural prime mass",
                "delta": "Arbitrary mixture π is not natural density; Z parking recovers arbitrary generator mass",
            },
        ],
        "attacks": [
            {
                "name": "just_p_vs_np_with_labels",
                "argument": "If you already have d(n) or primality labels, π is the empirical frequency; Z is unnecessary.",
                "response": "Path B assumes unlabeled observations of the process output (Z or n). Labels are not available to either observer.",
            },
            {
                "name": "computing_Z_needs_d_n",
                "argument": "Z requires d(n), so any advantage is circular for cryptographic scales.",
                "response": "Claim is about sample complexity of π given already-observed Z vs observed n magnitudes, not computational primality.",
            },
            {
                "name": "wrong_v_destroys_parking",
                "argument": "Advantage is knife-edge at v* only.",
                "response": "v-sensitivity table measures this; survivor requires peak near v*.",
            },
            {
                "name": "raw_n_with_modular_features_enough",
                "argument": "Parity and small-modulus features recover composite mass without Z.",
                "response": "n_fingerprint includes mod 2/3/5; still compared head-to-head in MAE ratios.",
            },
        ],
    }

    out_json = ARTIFACT_DIR / "path_b_results.json"
    with out_json.open("w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2)

    # Human-readable report
    lines = [
        "# Path B Probe Report — Dual of v-recovery",
        "",
        f"Date (UTC): {payload['timestamp_utc']}",
        f"Verdict: **{verdict}**",
        "",
        verdict_detail,
        "",
        "## Setup",
        "",
        f"- Support: integers `n ∈ [2, {n_max}]`",
        f"- Fixed traversal rates: `v* = e²/2 ≈ {V_STAR:.6f}` and attack `v = 1.0`",
        f"- Families: {', '.join(f.name for f in families)}",
        f"- Trials/cell: {trials}; sample sizes: {sample_sizes}",
        f"- Binary π_prime grid: {pi_values}",
        "",
        "## Z-map at v*",
        "",
        "| Family | Count | mean Z | median Z | frac Z=1 | mean log Z |",
        "|---|---:|---:|---:|---:|---:|",
    ]
    for fam in zmap_star["families"]:
        lines.append(
            f"| {fam['name']} | {fam['count']} | {fam['mean_z']:.4g} | {fam['median_z']:.4g} | "
            f"{fam['frac_exact_1']:.3f} | {fam['mean_log_z']:.4g} |"
        )

    lines.extend(
        [
            "",
            "## Binary recovery MAE (mean over π_true) at v*",
            "",
            "| M | z_park | z_mle | z_fp | n_mle | n_fp | natural | n_mle/z_mle |",
            "|---:|---:|---:|---:|---:|---:|---:|---:|",
        ]
    )
    for r in comparison_table:
        lines.append(
            f"| {r['m']} | {r['z_park_mae']:.4f} | {r['z_mle_mae']:.4f} | {r['z_fingerprint_mae']:.4f} | "
            f"{r['n_mle_mae']:.4f} | {r['n_fingerprint_mae']:.4f} | {r['natural_density_mae']:.4f} | "
            f"{r.get('mae_ratio_n_mle_over_z_mle', float('nan')):.2f} |"
        )

    lines.extend(
        [
            "",
            "## Fisher (approx per-observation) at π=0.25, v*",
            "",
            "| M | I_Z | I_n | I_Z / I_n |",
            "|---:|---:|---:|---:|",
        ]
    )
    for m in sample_sizes:
        fr = fisher_ratios.get(str(m))
        if fr:
            lines.append(
                f"| {m} | {fr['I_z']:.4g} | {fr['I_n']:.4g} | {fr['ratio_Iz_over_In']:.2f} |"
            )

    lines.extend(
        [
            "",
            "## v-sensitivity (binary MLE / park, M=500, π=0.25)",
            "",
            "| v | park_frac primes | logZ sep | park MAE | MLE MAE |",
            "|---:|---:|---:|---:|---:|",
        ]
    )
    for r in v_rows:
        mark = " ← v*" if r["is_v_star"] else ""
        lines.append(
            f"| {r['v']:.6f}{mark} | {r['prime_exact_park_fraction']:.3f} | {r['logz_mean_separation']:.4g} | "
            f"{r['z_park_mae']:.4f} | {r['z_mle_mae']:.4f} |"
        )

    lines.extend(
        [
            "",
            "## Multi-family L1 (mean ratios n/z) at v*",
            "",
        ]
    )
    for c in multi_star["cells"]:
        lines.append(
            f"- M={c['sample_size']}, π={np.round(c['pi_true'], 3).tolist()}: "
            f"L1_z={c['z_mle_l1_mean']:.4f}, L1_n={c['n_mle_l1_mean']:.4f}, "
            f"ratio={c['l1_ratio_n_over_z']:.2f}"
        )

    lines.extend(
        [
            "",
            "## Headline metrics",
            "",
            f"- median n_mle/z_mle MAE ratio: {median_ratio:.3f}",
            f"- mean n_mle/z_mle MAE ratio (M≥250): {mean_large_ratio:.3f}",
            f"- mean multi-family L1 ratio n/z: {multi_mean_ratio:.3f}",
            f"- best v for z_mle (M=500): {best_v_row['v']:.6f}",
            f"- v* z_mle MAE: {vstar_row['z_mle_mae']:.4f}",
            f"- v* park MAE: {vstar_row['z_park_mae']:.4f}",
            "",
            "## Novelty delta (not restating dfr/cst/dpt/hidden_tuning)",
            "",
            "The dual channel claim: with v fixed at the prime fixed-point speed, the **mixture weights**",
            "of known support families become the recoverable parameter from Z alone, with measurable",
            "sample-complexity advantage over raw magnitude. This is the reverse of v_recovery",
            "(recover v under known support prior) and a frozen-v special case distinct from zpf joint (regime,v).",
            "",
            "## Falsifier",
            "",
            "If at M≥250, mean MAE of best Z estimator is not ≤ 1/2 the mean MAE of best raw-n estimator",
            "across π_true ∈ {0.1,0.25,0.4,0.55}, or if multi-family L1 ratio < 1.5, reject the strong claim.",
            "",
            f"JSON: `{out_json.name}`",
            "",
        ]
    )

    report_path = ARTIFACT_DIR / "PATH_B_REPORT.md"
    report_path.write_text("\n".join(lines), encoding="utf-8")
    print(f"Wrote {out_json}")
    print(f"Wrote {report_path}")
    print(f"VERDICT: {verdict}")
    print(f"mean_large_ratio={mean_large_ratio:.3f} multi_l1_ratio={multi_mean_ratio:.3f}")


if __name__ == "__main__":
    main()
