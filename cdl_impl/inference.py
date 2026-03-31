#!/usr/bin/env python3
"""
Recover the traversal rate parameter v from observed Z sequences.

This module keeps the canonical CDL forward model untouched:

    κ(n) = d(n) · ln(n) / e²
    Z(n) = n / exp(v · κ(n))

The recovery path is calibrated from those primitives and operates on observed
Z values alone under an explicit sequence prior.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Dict, Iterable, Literal, Tuple

import numpy as np
from scipy import stats

from . import core as cdl

SequenceType = Literal["random", "consecutive", "prime_biased", "composite_heavy"]
RecoveryMethod = Literal["moment_match", "mle", "fingerprint"]


def divisor_count_sieve(n_max: int) -> np.ndarray:
    """Compute d(n) for 0..n_max with a vectorized divisor sieve."""
    if n_max < 1:
        raise ValueError("n_max must be >= 1")

    counts = np.zeros(n_max + 1, dtype=np.int32)
    for step in range(1, n_max + 1):
        counts[step::step] += 1
    return counts


def precompute_curvature_table(n_max: int) -> Dict[str, np.ndarray]:
    """Precompute the integer support, divisor counts, and κ(n) table."""
    if n_max < 2:
        raise ValueError("n_max must be >= 2")

    numbers = np.arange(2, n_max + 1, dtype=np.int64)
    divisor_counts = divisor_count_sieve(n_max)[2:]
    kappas = divisor_counts * np.log(numbers) / (math.e ** 2)
    return {
        "numbers": numbers,
        "divisor_counts": divisor_counts,
        "kappas": kappas,
        "prime_mask": divisor_counts == 2,
    }


def validate_precomputed_kappas(kappas: np.ndarray, limit: int = 100) -> None:
    """Check the sieve table against the canonical cdl.kappa primitive."""
    max_n = min(limit, len(kappas) + 1)
    for n in range(2, max_n + 1):
        expected = cdl.kappa(n)
        actual = float(kappas[n - 2])
        if not math.isclose(actual, expected, rel_tol=1e-12, abs_tol=1e-12):
            raise ValueError(f"kappa table mismatch at n={n}: {actual} != {expected}")


def _weights_from_sequence_type(
    sequence_type: SequenceType,
    kappas: np.ndarray,
    prime_mask: np.ndarray,
) -> np.ndarray | None:
    if sequence_type == "random":
        return None
    if sequence_type == "prime_biased":
        weights = np.exp(-(kappas - kappas.min()) / max(float(kappas.std()), 1e-8))
        weights = weights * 0.5 + prime_mask.astype(np.float64)
        return weights / weights.sum()
    if sequence_type == "composite_heavy":
        weights = np.where(prime_mask, 0.05, np.maximum(kappas, 1e-6) ** 1.5)
        return weights / weights.sum()
    return None


def sample_indices(
    rng: np.random.Generator,
    sequence_type: SequenceType,
    sample_size: int,
    support_size: int,
    kappas: np.ndarray,
    prime_mask: np.ndarray,
) -> np.ndarray:
    """Sample integer indices for a synthetic Z sequence."""
    if sample_size < 1:
        raise ValueError("sample_size must be >= 1")

    if sequence_type == "consecutive":
        if sample_size > support_size:
            raise ValueError("sample_size exceeds calibrated support")
        start = int(rng.integers(0, support_size - sample_size + 1))
        return np.arange(start, start + sample_size, dtype=np.int64)

    weights = _weights_from_sequence_type(sequence_type, kappas, prime_mask)
    return rng.choice(support_size, size=sample_size, replace=True, p=weights)


def generate_z_sequence(
    numbers: np.ndarray,
    kappas: np.ndarray,
    rng: np.random.Generator,
    v: float,
    sample_size: int,
    sequence_type: SequenceType = "random",
    noise_level: float = 0.0,
    prime_mask: np.ndarray | None = None,
) -> Tuple[np.ndarray, np.ndarray]:
    """Generate a synthetic Z sequence and the sampled source integers."""
    if prime_mask is None:
        prime_mask = np.zeros_like(kappas, dtype=bool)

    indices = sample_indices(
        rng=rng,
        sequence_type=sequence_type,
        sample_size=sample_size,
        support_size=len(numbers),
        kappas=kappas,
        prime_mask=prime_mask,
    )
    sampled_numbers = numbers[indices]
    sampled_kappas = kappas[indices]
    z = sampled_numbers / np.exp(v * sampled_kappas)

    if noise_level > 0:
        z = z * (1.0 + rng.normal(0.0, noise_level, size=z.shape))
        z = np.clip(z, 1e-12, None)

    return z.astype(np.float64), sampled_numbers


def _safe_skew(values: np.ndarray) -> float:
    if len(values) < 3:
        return 0.0
    skew = float(stats.skew(values, bias=False))
    return 0.0 if math.isnan(skew) else skew


def _safe_kurtosis(values: np.ndarray) -> float:
    if len(values) < 4:
        return 0.0
    kurt = float(stats.kurtosis(values, fisher=True, bias=False))
    return 0.0 if math.isnan(kurt) else kurt


@dataclass(frozen=True)
class InferenceResult:
    v_estimate: float
    confidence_half_width: float
    method: RecoveryMethod
    score: float


class VRecovery:
    """Infer v from observed Z sequences under an explicit calibrated prior."""

    def __init__(
        self,
        calibration_n_max: int = 15_000,
        v_grid: Iterable[float] | None = None,
        sample_size: int = 5_000,
        sequence_type: SequenceType = "random",
        reference_trials: int = 24,
        histogram_bins: int = 7,
        random_seed: int = 0,
        support_values: np.ndarray | None = None,
        support_kappas: np.ndarray | None = None,
        support_prime_mask: np.ndarray | None = None,
    ) -> None:
        self.n_max = calibration_n_max
        self.sample_size = sample_size
        self.sequence_type = sequence_type
        self.reference_trials = reference_trials
        self.random_seed = random_seed

        if support_values is None or support_kappas is None:
            table = precompute_curvature_table(calibration_n_max)
            validate_precomputed_kappas(table["kappas"], limit=100)
            self.numbers = table["numbers"].astype(np.float64)
            self.kappas = table["kappas"].astype(np.float64)
            self.prime_mask = table["prime_mask"]
            self.divisor_counts = table["divisor_counts"]
        else:
            self.numbers = np.asarray(support_values, dtype=np.float64)
            self.kappas = np.asarray(support_kappas, dtype=np.float64)
            if self.numbers.shape != self.kappas.shape:
                raise ValueError("support_values and support_kappas must have the same shape")
            if support_prime_mask is None:
                self.prime_mask = np.zeros_like(self.kappas, dtype=bool)
            else:
                self.prime_mask = np.asarray(support_prime_mask, dtype=bool)
            self.divisor_counts = np.zeros_like(self.kappas, dtype=np.int32)

        self.log_numbers = np.log(self.numbers)
        self.sequence_weights = _weights_from_sequence_type(sequence_type, self.kappas, self.prime_mask)
        if self.sequence_weights is None:
            self.sequence_weights = np.full_like(self.kappas, 1.0 / len(self.kappas), dtype=np.float64)

        if v_grid is None:
            v_grid = np.round(np.arange(0.3, 3.01, 0.1), 2)
        self.v_grid = np.array(list(v_grid), dtype=np.float64)
        if self.v_grid.ndim != 1 or len(self.v_grid) < 3:
            raise ValueError("v_grid must contain at least three points")

        max_log_z = float(np.max(self.log_numbers - self.v_grid.min() * self.kappas))
        min_log_z = float(np.min(self.log_numbers - self.v_grid.max() * self.kappas))
        self.histogram_edges = np.linspace(min_log_z, max_log_z, histogram_bins + 1)
        self.density_edges = np.linspace(min_log_z, max_log_z, 129)

        self._moment_lookup = self._build_moment_lookup()
        self._density_lookup = self._build_density_lookup()
        self._fingerprint_lookup, self._fingerprint_scale = self._build_fingerprint_lookup()

    def _build_moment_lookup(self) -> Dict[str, np.ndarray]:
        mean_log_z = []
        std_log_z = []
        mean_z = []
        std_z = []
        weights = self.sequence_weights
        for v in self.v_grid:
            log_z = self.log_numbers - v * self.kappas
            z = np.exp(log_z)
            mean_log = float(np.sum(weights * log_z))
            var_log = float(np.sum(weights * (log_z - mean_log) ** 2))
            mean_raw = float(np.sum(weights * z))
            var_raw = float(np.sum(weights * (z - mean_raw) ** 2))
            mean_log_z.append(mean_log)
            std_log_z.append(math.sqrt(max(var_log, 0.0)))
            mean_z.append(mean_raw)
            std_z.append(math.sqrt(max(var_raw, 0.0)))
        return {
            "mean_log_z": np.array(mean_log_z, dtype=np.float64),
            "std_log_z": np.array(std_log_z, dtype=np.float64),
            "mean_z": np.array(mean_z, dtype=np.float64),
            "std_z": np.array(std_z, dtype=np.float64),
        }

    def _build_density_lookup(self) -> Dict[float, np.ndarray]:
        lookup: Dict[float, np.ndarray] = {}
        for v in self.v_grid:
            log_z = self.log_numbers - v * self.kappas
            density, _ = np.histogram(log_z, bins=self.density_edges, weights=self.sequence_weights)
            density = density.astype(np.float64) + 1e-12
            density /= density.sum()
            lookup[float(v)] = density
        return lookup

    def _build_fingerprint_lookup(self) -> Tuple[Dict[float, np.ndarray], np.ndarray]:
        rng = np.random.default_rng(self.random_seed)
        lookup: Dict[float, np.ndarray] = {}
        all_features = []

        for v in self.v_grid:
            feature_rows = []
            for _ in range(self.reference_trials):
                z, _ = generate_z_sequence(
                    numbers=self.numbers,
                    kappas=self.kappas,
                    rng=rng,
                    v=float(v),
                    sample_size=self.sample_size,
                    sequence_type=self.sequence_type,
                    noise_level=0.0,
                    prime_mask=self.prime_mask,
                )
                fingerprint = self.extract_fingerprint(z)
                feature_rows.append(fingerprint)
                all_features.append(fingerprint)
            lookup[float(v)] = np.mean(np.vstack(feature_rows), axis=0)

        feature_stack = np.vstack(all_features)
        scale = np.std(feature_stack, axis=0)
        scale[scale < 1e-8] = 1.0
        return lookup, scale

    def extract_fingerprint(self, z_sequence: np.ndarray) -> np.ndarray:
        """Compute a 20-dimensional distributional fingerprint from Z alone."""
        z = np.asarray(z_sequence, dtype=np.float64)
        z = np.clip(z, 1e-12, None)
        log_z = np.log(z)
        quantiles = np.quantile(log_z, [0.10, 0.25, 0.50, 0.75, 0.90])
        histogram, _ = np.histogram(log_z, bins=self.histogram_edges, density=True)
        histogram = histogram.astype(np.float64)
        histogram /= max(histogram.sum(), 1e-8)
        cv = float(np.std(z) / max(abs(np.mean(z)), 1e-8))

        return np.concatenate(
            [
                np.array(
                    [
                        np.mean(log_z),
                        np.var(log_z),
                        _safe_skew(log_z),
                        _safe_kurtosis(log_z),
                    ],
                    dtype=np.float64,
                ),
                quantiles.astype(np.float64),
                np.array(
                    [
                        np.min(log_z),
                        np.max(log_z),
                        np.ptp(log_z),
                        cv,
                    ],
                    dtype=np.float64,
                ),
                histogram,
            ]
        )

    def _interpolate(self, values: np.ndarray, v: float) -> float:
        clipped_v = float(np.clip(v, self.v_grid[0], self.v_grid[-1]))
        return float(np.interp(clipped_v, self.v_grid, values))

    def infer_v(
        self,
        z_sequence: Iterable[float],
        method: RecoveryMethod = "fingerprint",
        v_bounds: Tuple[float, float] = (0.3, 3.0),
    ) -> InferenceResult:
        """Infer v from observed Z values alone."""
        z = np.asarray(list(z_sequence), dtype=np.float64)
        if z.ndim != 1 or len(z) == 0:
            raise ValueError("z_sequence must be a non-empty 1D sequence")
        z = np.clip(z, 1e-12, None)
        log_z = np.log(z)

        lower = max(v_bounds[0], float(self.v_grid[0]))
        upper = min(v_bounds[1], float(self.v_grid[-1]))
        if lower >= upper:
            raise ValueError("v_bounds do not overlap the calibrated v_grid")

        if method == "moment_match":
            observed_mean = float(np.mean(log_z))
            estimate = float(
                np.interp(
                    observed_mean,
                    self._moment_lookup["mean_log_z"][::-1],
                    self.v_grid[::-1],
                )
            )
            estimate = float(np.clip(estimate, lower, upper))
            residual = abs(
                observed_mean - self._interpolate(self._moment_lookup["mean_log_z"], estimate)
            )
            return InferenceResult(estimate, 0.05, method, residual)

        if method == "mle":
            bin_indices = np.searchsorted(self.density_edges, log_z, side="right") - 1
            bin_indices = np.clip(bin_indices, 0, len(self.density_edges) - 2)
            grid_values = np.array([float(v) for v in self.v_grid if lower <= v <= upper], dtype=np.float64)
            grid_scores = []
            for v in grid_values:
                density = self._density_lookup[float(v)]
                grid_scores.append(float(-np.sum(np.log(density[bin_indices]))))
            grid_scores = np.array(grid_scores, dtype=np.float64)
            best_index = int(np.argmin(grid_scores))
            estimate = float(grid_values[best_index])

            if 0 < best_index < len(grid_values) - 1:
                x1, x2, x3 = grid_values[best_index - 1 : best_index + 2]
                y1, y2, y3 = grid_scores[best_index - 1 : best_index + 2]
                denom = (x1 - x2) * (x1 - x3) * (x2 - x3)
                if abs(denom) > 1e-12:
                    a = (x3 * (y2 - y1) + x2 * (y1 - y3) + x1 * (y3 - y2)) / denom
                    b = (x3 * x3 * (y1 - y2) + x2 * x2 * (y3 - y1) + x1 * x1 * (y2 - y3)) / denom
                    if abs(a) > 1e-12:
                        refined = -b / (2 * a)
                        if lower <= refined <= upper:
                            estimate = float(refined)

            best = float(np.min(grid_scores))
            mask = grid_scores <= best + 1.92
            if np.any(mask):
                confidence = float(max(abs(estimate - grid_values[mask][0]), abs(estimate - grid_values[mask][-1])))
            else:
                confidence = 0.05
            return InferenceResult(estimate, max(confidence, 0.01), method, best)

        if method == "fingerprint":
            fingerprint = self.extract_fingerprint(z)
            distances = []
            grid_values = []
            for v in self.v_grid:
                if not lower <= float(v) <= upper:
                    continue
                reference = self._fingerprint_lookup[float(v)]
                distance = np.linalg.norm((fingerprint - reference) / self._fingerprint_scale)
                distances.append(float(distance))
                grid_values.append(float(v))
            distance_array = np.array(distances, dtype=np.float64)
            grid_array = np.array(grid_values, dtype=np.float64)
            best_index = int(np.argmin(distance_array))
            estimate = float(grid_array[best_index])

            if 0 < best_index < len(grid_array) - 1:
                x1, x2, x3 = grid_array[best_index - 1 : best_index + 2]
                y1, y2, y3 = distance_array[best_index - 1 : best_index + 2]
                denom = (x1 - x2) * (x1 - x3) * (x2 - x3)
                if abs(denom) > 1e-12:
                    a = (x3 * (y2 - y1) + x2 * (y1 - y3) + x1 * (y3 - y2)) / denom
                    b = (x3 * x3 * (y1 - y2) + x2 * x2 * (y3 - y1) + x1 * x1 * (y2 - y3)) / denom
                    if abs(a) > 1e-12:
                        refined = -b / (2 * a)
                        if lower <= refined <= upper:
                            estimate = float(refined)

            sorted_distances = np.sort(distance_array)
            confidence = 0.05
            if len(sorted_distances) >= 2:
                confidence = float(
                    np.clip(0.05 / max(sorted_distances[1] - sorted_distances[0], 1e-6), 0.01, 0.50)
                )
            return InferenceResult(estimate, confidence, method, float(np.min(distance_array)))

        raise ValueError(f"Unknown method: {method}")


__all__ = [
    "InferenceResult",
    "RecoveryMethod",
    "SequenceType",
    "VRecovery",
    "divisor_count_sieve",
    "generate_z_sequence",
    "precompute_curvature_table",
    "validate_precomputed_kappas",
]
