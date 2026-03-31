#!/usr/bin/env python3
"""
Sprint 6 cognitive pilot pipeline for human-like magnitude estimation data.
"""

from __future__ import annotations

import csv
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Iterable

import numpy as np
from scipy import stats

from . import core as cdl
from .continuous import ContinuousVRecovery
from .inference import VRecovery


DEFAULT_STYLE_THRESHOLD = 1.2


@dataclass(frozen=True)
class ParticipantResult:
    participant_id: str
    v_recovered: float
    confidence: float
    cognitive_style: str
    mean_distortion: float
    compression_exponent: float
    z_min: float
    z_max: float
    z_range: float
    method: str

    def as_dict(self) -> dict:
        return asdict(self)


class CognitivePilot:
    """Ingest and analyze perceptual magnitude-estimation data."""

    def __init__(
        self,
        n_max: int = 10_000,
        participant_trials: int = 200,
        support_size: int = 100_000,
        reference_trials: int = 50,
        random_seed: int = 20260330,
    ) -> None:
        self.n_max = n_max
        self.participant_trials = participant_trials
        self.random_seed = random_seed

        support_rng = np.random.default_rng(random_seed + 1)
        support_values = self.sample_presented_numbers(
            support_rng,
            n_trials=support_size,
            n_max=n_max,
        ).astype(np.float64)
        support_kappas = np.array([cdl.kappa(int(value)) for value in support_values], dtype=np.float64)
        support_prime_mask = np.array([cdl.is_prime(int(value)) for value in support_values], dtype=bool)

        self.recovery = VRecovery(
            sample_size=participant_trials,
            sequence_type="random",
            reference_trials=reference_trials,
            random_seed=random_seed,
            support_values=support_values,
            support_kappas=support_kappas,
            support_prime_mask=support_prime_mask,
        )
        self.continuous_recovery = ContinuousVRecovery(
            x_min=2.0,
            x_max=float(n_max),
            support_points=10_000,
            sample_size=participant_trials,
            reference_trials=max(12, reference_trials // 2),
            random_seed=random_seed,
        )

    @staticmethod
    def sample_presented_numbers(
        rng: np.random.Generator,
        n_trials: int,
        n_max: int = 10_000,
    ) -> np.ndarray:
        """Mix uniform and log-biased integer sampling."""
        if n_trials < 1:
            raise ValueError("n_trials must be >= 1")

        uniform_count = n_trials // 2
        log_count = n_trials - uniform_count
        uniform = rng.integers(2, n_max + 1, size=uniform_count)
        log_uniform = np.exp(rng.uniform(np.log(2), np.log(n_max), size=log_count))
        log_uniform = np.clip(np.round(log_uniform).astype(int), 2, n_max)
        numbers = np.concatenate([uniform, log_uniform]).astype(np.int64)
        rng.shuffle(numbers)
        return numbers

    @staticmethod
    def infer_style(v_estimate: float, threshold: float = DEFAULT_STYLE_THRESHOLD) -> str:
        return "sharp geodesic" if v_estimate < threshold else "compressed distortion"

    @staticmethod
    def magnitude_estimation_exponent(
        presented_n: Iterable[float],
        perceived_z: Iterable[float],
    ) -> float:
        presented = np.asarray(list(presented_n), dtype=np.float64)
        perceived = np.clip(np.asarray(list(perceived_z), dtype=np.float64), 1e-12, None)
        slope, _, _, _, _ = stats.linregress(np.log(presented), np.log(perceived))
        return float(1.0 - slope)

    def simulate_participant(
        self,
        participant_id: str,
        v_true: float,
        rng: np.random.Generator,
        n_trials: int | None = None,
        noise_sigma: float | None = None,
    ) -> dict:
        """Generate synthetic human-like magnitude-estimation data."""
        trial_count = n_trials or self.participant_trials
        sigma = noise_sigma if noise_sigma is not None else float(rng.uniform(0.05, 0.12))
        presented = self.sample_presented_numbers(rng, n_trials=trial_count, n_max=self.n_max)
        perceived = np.array([cdl.z_normalize(int(n), v=v_true) for n in presented], dtype=np.float64)
        perceived *= 1.0 + rng.normal(0.0, sigma, size=perceived.shape)
        perceived = np.clip(perceived, 1e-12, None)
        return {
            "participant_id": participant_id,
            "presented_n": presented,
            "perceived_z": perceived,
            "v_true": float(v_true),
            "noise_sigma": float(sigma),
        }

    def run_participant(
        self,
        presented_n: Iterable[float],
        perceived_z: Iterable[float],
        participant_id: str = "participant",
        method: str = "fingerprint",
    ) -> ParticipantResult:
        """Recover v from human perceptual data and summarize the participant profile."""
        presented = np.asarray(list(presented_n), dtype=np.float64)
        perceived = np.clip(np.asarray(list(perceived_z), dtype=np.float64), 1e-12, None)
        inference = self.recovery.infer_v(perceived, method=method)
        return ParticipantResult(
            participant_id=participant_id,
            v_recovered=float(inference.v_estimate),
            confidence=float(inference.confidence_half_width),
            cognitive_style=self.infer_style(float(inference.v_estimate)),
            mean_distortion=float(np.mean(perceived / presented)),
            compression_exponent=self.magnitude_estimation_exponent(presented, perceived),
            z_min=float(np.min(perceived)),
            z_max=float(np.max(perceived)),
            z_range=float(np.max(perceived) - np.min(perceived)),
            method=method,
        )

    def compare_hybrid_vs_continuous(
        self,
        perceived_z: Iterable[float],
        v_true: float,
        method: str = "fingerprint",
    ) -> dict:
        """Compare the mixed exact/smooth pipeline against pure continuous calibration."""
        perceived = np.clip(np.asarray(list(perceived_z), dtype=np.float64), 1e-12, None)
        hybrid = self.recovery.infer_v(perceived, method=method)
        continuous = self.continuous_recovery.infer_v(perceived, method=method)
        hybrid_error = abs(float(hybrid.v_estimate) - v_true)
        continuous_error = abs(float(continuous.v_estimate) - v_true)
        improvement = 0.0
        if continuous_error > 1e-12:
            improvement = (continuous_error - hybrid_error) / continuous_error
        return {
            "hybrid_v": float(hybrid.v_estimate),
            "continuous_v": float(continuous.v_estimate),
            "hybrid_error": float(hybrid_error),
            "continuous_error": float(continuous_error),
            "relative_improvement": float(improvement),
        }

    def run_csv(
        self,
        csv_path: str | Path,
        participant_column: str = "participant_id",
        stimulus_column: str = "presented_n",
        response_column: str = "perceived_z",
        method: str = "fingerprint",
    ) -> list[ParticipantResult]:
        """Load a study CSV and recover v for each participant."""
        participant_rows: dict[str, dict[str, list[float]]] = {}
        with Path(csv_path).open() as handle:
            reader = csv.DictReader(handle)
            for row in reader:
                participant_id = row[participant_column]
                bucket = participant_rows.setdefault(
                    participant_id,
                    {"presented_n": [], "perceived_z": []},
                )
                bucket["presented_n"].append(float(row[stimulus_column]))
                bucket["perceived_z"].append(float(row[response_column]))

        return [
            self.run_participant(
                payload["presented_n"],
                payload["perceived_z"],
                participant_id=participant_id,
                method=method,
            )
            for participant_id, payload in sorted(participant_rows.items())
        ]


__all__ = [
    "CognitivePilot",
    "DEFAULT_STYLE_THRESHOLD",
    "ParticipantResult",
]
