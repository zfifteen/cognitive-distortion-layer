#!/usr/bin/env python3
"""
Continuous-domain CDL extensions derived from the Sprint 4 asymptotic model.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Iterable

import numpy as np
import sympy as sp

import cdl
from v_recovery import InferenceResult, VRecovery, generate_z_sequence


gamma = float(sp.EulerGamma)


def kappa_prime_asymptotic(x: float | np.ndarray) -> float | np.ndarray:
    """Prime-geodesic asymptotic curvature at scale x."""
    values = np.asarray(x, dtype=np.float64)
    values = np.clip(values, 1e-12, None)
    result = 2.0 * np.log(values) / (math.e ** 2)
    if np.isscalar(x):
        return float(result)
    return result


def kappa_smooth(x: float | np.ndarray) -> float | np.ndarray:
    """Continuous curvature using the average-order asymptotic of d(n)."""
    values = np.asarray(x, dtype=np.float64)
    clipped = np.clip(values, 1e-12, None)
    log_x = np.log(clipped)
    result = (log_x + 2.0 * gamma - 1.0) * log_x / (math.e ** 2)
    result = np.where(values > 0, result, 0.0)
    if np.isscalar(x):
        return float(result)
    return result


def z_normalize_continuous(x: float | np.ndarray, v: float = 1.0) -> float | np.ndarray:
    """Continuous analog of the canonical Z-normalization."""
    values = np.asarray(x, dtype=np.float64)
    result = values / np.exp(v * kappa_smooth(values))
    if np.isscalar(x):
        return float(result)
    return result


def hybrid_kappa(x: float) -> float:
    """Use exact κ on integers and κ_smooth elsewhere."""
    if float(x).is_integer() and x >= 2:
        return cdl.kappa(int(x))
    return float(kappa_smooth(x))


def hybrid_classify(
    x: float,
    tau: float = 1.5,
    adaptive: bool = False,
) -> str:
    """Classify integers exactly and real-valued inputs by smooth curvature."""
    if float(x).is_integer() and x >= 2:
        return cdl.classify(int(x), threshold=tau, adaptive=adaptive)
    threshold = tau
    if adaptive and x >= 2:
        threshold = cdl.lookup_adaptive_threshold(max(2, int(round(x))))
    return "prime-like geodesic" if hybrid_kappa(x) < threshold else "composite distortion"


def generate_continuous_z_sequence(
    rng: np.random.Generator,
    v: float,
    sample_size: int,
    x_min: float = 2.0,
    x_max: float = 5_000_000.0,
    noise_level: float = 0.0,
    sequence_type: str = "random",
) -> tuple[np.ndarray, np.ndarray]:
    """Generate synthetic continuous-domain Z sequences."""
    if sample_size < 1:
        raise ValueError("sample_size must be >= 1")
    if x_min <= 0 or x_max <= x_min:
        raise ValueError("Continuous support must satisfy 0 < x_min < x_max")

    if sequence_type == "consecutive":
        start = float(rng.uniform(x_min, x_max - sample_size))
        x = np.linspace(start, start + sample_size, sample_size, dtype=np.float64)
    else:
        x = np.exp(rng.uniform(np.log(x_min), np.log(x_max), size=sample_size))

    z = z_normalize_continuous(x, v=v)
    if noise_level > 0:
        z = z * (1.0 + rng.normal(0.0, noise_level, size=z.shape))
        z = np.clip(z, 1e-12, None)
    return z.astype(np.float64), x.astype(np.float64)


class ContinuousVRecovery:
    """Continuous-domain v recovery calibrated on κ_smooth support."""

    def __init__(
        self,
        x_min: float = 2.0,
        x_max: float = 5_000_000.0,
        support_points: int = 20_000,
        sample_size: int = 5_000,
        reference_trials: int = 20,
        random_seed: int = 0,
    ) -> None:
        if support_points < 100:
            raise ValueError("support_points must be >= 100")

        self.x_min = x_min
        self.x_max = x_max
        self.support = np.exp(np.linspace(np.log(x_min), np.log(x_max), support_points))
        self.support_kappas = np.asarray(kappa_smooth(self.support), dtype=np.float64)
        self.recovery = VRecovery(
            sample_size=sample_size,
            sequence_type="random",
            reference_trials=reference_trials,
            random_seed=random_seed,
            support_values=self.support,
            support_kappas=self.support_kappas,
        )

    def infer_v(
        self,
        z_sequence: Iterable[float],
        method: str = "mle",
    ) -> InferenceResult:
        return self.recovery.infer_v(z_sequence, method=method)


__all__ = [
    "ContinuousVRecovery",
    "gamma",
    "generate_continuous_z_sequence",
    "hybrid_classify",
    "hybrid_kappa",
    "kappa_prime_asymptotic",
    "kappa_smooth",
    "z_normalize_continuous",
]
