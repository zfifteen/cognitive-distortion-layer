#!/usr/bin/env python3
"""Reproduce the locally materialized Sprint 1–6 artifacts."""

from __future__ import annotations

import csv
import json
import math
import os
import subprocess
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import cdl
from cdl_continuous import (
    ContinuousVRecovery,
    generate_continuous_z_sequence,
    kappa_prime_asymptotic,
    kappa_smooth,
    z_normalize_continuous,
)
from sympy import EulerGamma
from v_recovery import precompute_curvature_table

def write_threshold_map(path: Path) -> list[dict]:
    windows = [(2, 49), (50, 999), (1000, 9999), (10000, 99999)]
    rows = []
    for n_min, n_max in windows:
        numbers = list(range(n_min, n_max + 1))
        items = sorted(
            (cdl.kappa(n), 1 if cdl.is_prime(n) else 0, n)
            for n in numbers
        )
        total = len(items)
        total_primes = sum(label for _, label, _ in items)
        total_composites = total - total_primes
        tp = fp = 0
        best_threshold = items[0][0]
        best_accuracy = -1.0
        best_metrics = {
            "precision": 0.0,
            "recall": 0.0,
        }

        previous_kappa = items[0][0] - 1e-9
        for kappa_value, label, _ in items:
            if label:
                tp += 1
            else:
                fp += 1
            tn = total_composites - fp
            fn = total_primes - tp
            accuracy = (tp + tn) / total
            if accuracy > best_accuracy:
                precision = tp / (tp + fp) if (tp + fp) else 0.0
                recall = tp / (tp + fn) if (tp + fn) else 0.0
                best_threshold = (previous_kappa + kappa_value) / 2.0
                best_accuracy = accuracy
                best_metrics = {
                    "precision": precision,
                    "recall": recall,
                }
            previous_kappa = kappa_value

        false_positives = [
            n for n in numbers
            if not cdl.is_prime(n) and cdl.kappa(n) < best_threshold
        ]
        rows.append(
            {
                "n_min": n_min,
                "n_max": n_max,
                "threshold": best_threshold,
                "accuracy": best_accuracy,
                "precision": best_metrics["precision"],
                "recall": best_metrics["recall"],
                "false_positives": ";".join(str(n) for n in false_positives),
            }
        )

    with path.open("w", newline="") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=[
                "n_min",
                "n_max",
                "threshold",
                "accuracy",
                "precision",
                "recall",
                "false_positives",
            ],
            lineterminator="\n",
        )
        writer.writeheader()
        for row in rows:
            writer.writerow(
                {
                    **row,
                    "threshold": f"{row['threshold']:.6f}",
                    "accuracy": f"{row['accuracy']:.6f}",
                    "precision": f"{row['precision']:.6f}",
                    "recall": f"{row['recall']:.6f}",
                }
            )
    return rows


def build_analytic_artifacts(output_dir: Path) -> dict:
    output_dir.mkdir(parents=True, exist_ok=True)
    gamma = float(EulerGamma)

    table = precompute_curvature_table(500_000)
    numbers = table["numbers"]
    kappas = table["kappas"]
    prime_mask = table["prime_mask"]

    windows = {}
    for x in (100_000, 500_000):
        mask = numbers <= x
        prime_avg = float(np.mean(kappas[mask & prime_mask]))
        composite_avg = float(np.mean(kappas[mask & ~prime_mask]))
        smooth = float(kappa_smooth(x))
        prime_asym = float(kappa_prime_asymptotic(x))
        windows[str(x)] = {
            "prime_kappa_mean": prime_avg,
            "composite_kappa_mean": composite_avg,
            "separation_ratio": composite_avg / prime_avg,
            "kappa_smooth": smooth,
            "prime_asymptotic": prime_asym,
            "composite_relative_error_pct": abs(smooth - composite_avg) / composite_avg * 100.0,
        }

    projection_x = 10_000_000
    analytic_results = {
        "gamma": gamma,
        "asymptotics": {
            "kappa_smooth": "((ln x + 2γ - 1) ln x) / e²",
            "prime_geodesic": "2 ln x / e²",
        },
        "windows": windows,
        "sensitivity_scenarios": {
            "unconditional_floor": 2.8,
            "rh_floor": 3.4,
            "large_x_projection_at_1e7": float(
                kappa_smooth(projection_x) / kappa_prime_asymptotic(projection_x)
            ),
        },
    }

    markdown = "\n".join(
        [
            "# ANALYTIC_CONNECTIONS.md — Theoretical Grounding of κ(n)",
            "",
            "## Derived Asymptotics",
            "",
            "E[κ(n)] ∼ ((ln n + 2γ − 1) ln n) / e²",
            "",
            "E[κ(p)] ≈ 2 ln x / e²",
            "",
            "## Local Empirical Checks",
            "",
            (
                f"- Up to `100000`: prime mean `{windows['100000']['prime_kappa_mean']:.3f}`, "
                f"composite mean `{windows['100000']['composite_kappa_mean']:.3f}`, "
                f"ratio `{windows['100000']['separation_ratio']:.2f}×`, "
                f"κ_smooth error vs composite mean `{windows['100000']['composite_relative_error_pct']:.2f}%`."
            ),
            (
                f"- Up to `500000`: prime mean `{windows['500000']['prime_kappa_mean']:.3f}`, "
                f"composite mean `{windows['500000']['composite_kappa_mean']:.3f}`, "
                f"ratio `{windows['500000']['separation_ratio']:.2f}×`, "
                f"κ_smooth error vs composite mean `{windows['500000']['composite_relative_error_pct']:.2f}%`."
            ),
            "",
            "## Sensitivity Scenarios",
            "",
            (
                f"- Working unconditional floor carried through the local reproduction: "
                f"`{analytic_results['sensitivity_scenarios']['unconditional_floor']:.1f}×`."
            ),
            (
                f"- Working RH-style floor carried through the local reproduction: "
                f"`{analytic_results['sensitivity_scenarios']['rh_floor']:.1f}×`."
            ),
            (
                f"- Smooth large-x projection at `10^7`: "
                f"`{analytic_results['sensitivity_scenarios']['large_x_projection_at_1e7']:.2f}×`."
            ),
            "",
            "## Integration Impact",
            "",
            "- Port 1 can route candidates with range-aware τ from the Sprint 1 threshold map.",
            "- Port 3 can use asymptotic priors when calibrating `v` across wider scales.",
            "- Sprint 5 inherits `κ_smooth(x)` directly from this document.",
            "",
        ]
    ) + "\n"

    (output_dir / "ANALYTIC_CONNECTIONS.md").write_text(markdown, encoding="utf-8")
    (output_dir / "analytic_results.json").write_text(
        json.dumps(analytic_results, indent=2) + "\n",
        encoding="utf-8",
    )
    return analytic_results


def build_continuous_artifacts(output_dir: Path, analytic_results: dict) -> dict:
    output_dir.mkdir(parents=True, exist_ok=True)

    fidelity_100k = analytic_results["windows"]["100000"]["composite_relative_error_pct"]
    fidelity_500k = analytic_results["windows"]["500000"]["composite_relative_error_pct"]
    separation_low = float(kappa_smooth(2_000_000) / kappa_prime_asymptotic(2_000_000))
    separation_high = float(kappa_smooth(5_000_000) / kappa_prime_asymptotic(5_000_000))

    interval = np.linspace(1_000.0, 100_000.0, 5_000)
    variance_reduction = float(
        (1.0 - np.var(z_normalize_continuous(interval, v=0.115)) / np.var(interval)) * 100.0
    )

    rng = np.random.default_rng(123)
    recovery = ContinuousVRecovery(
        x_min=1_000.0,
        x_max=1_000_000.0,
        support_points=15_000,
        sample_size=5_000,
        reference_trials=12,
        random_seed=123,
    )
    v_errors = []
    v_success = []
    for v_true in (0.5, 1.0, 1.5, 2.0, 2.5):
        z_sequence, _ = generate_continuous_z_sequence(
            rng=rng,
            v=v_true,
            sample_size=5_000,
            x_min=1_000.0,
            x_max=1_000_000.0,
            noise_level=0.03,
        )
        result = recovery.infer_v(z_sequence, method="fingerprint")
        v_errors.append(abs(result.v_estimate - v_true))
        v_success.append(abs(result.v_estimate - v_true) < 0.05)

    continuous_results = {
        "fidelity_relative_error_pct": {
            "100000": fidelity_100k,
            "500000": fidelity_500k,
        },
        "continuous_separation_ratio": {
            "2000000": separation_low,
            "5000000": separation_high,
        },
        "variance_reduction_pct": variance_reduction,
        "v_recovery_transfer": {
            "method": "fingerprint",
            "sample_size": 5000,
            "noise_level": 0.03,
            "mae": float(np.mean(v_errors)),
            "success_rate": float(np.mean(v_success)),
        },
    }

    problem_md = "\n".join(
        [
            "# Continuous Geodesic Extension (Sprint 5)",
            "",
            "This experiment extends the CDL from exact integer curvature into a smooth real-valued surrogate.",
            "",
            "Canonical smooth signal:",
            "",
            "```text",
            "κ_smooth(x) = ((ln x + 2γ − 1) ln x) / e²",
            "Z(x) = x / exp(v · κ_smooth(x))",
            "```",
            "",
            "Acceptance targets for the local reproduction:",
            "- κ_smooth tracks large-scale composite curvature with low relative error.",
            "- Continuous normalization preserves large variance collapse.",
            "- `v` recovery transfers to smooth sequences with bounded degradation.",
            "",
        ]
    ) + "\n"

    report_md = "\n".join(
        [
            "# Continuous Extension Experiment Report",
            "",
            "## Headline Findings",
            "",
            (
                f"- κ_smooth matches empirical composite curvature within "
                f"`{fidelity_100k:.2f}%` at `x=100000` and `{fidelity_500k:.2f}%` at `x=500000`."
            ),
            (
                f"- Continuous separation against the prime-geodesic asymptotic runs from "
                f"`{separation_low:.2f}×` at `2e6` to `{separation_high:.2f}×` at `5e6`."
            ),
            f"- Continuous variance reduction benchmark: `{variance_reduction:.2f}%`.",
            (
                f"- Fingerprint-based continuous `v` recovery reaches MAE "
                f"`{continuous_results['v_recovery_transfer']['mae']:.4f}` with "
                f"`{continuous_results['v_recovery_transfer']['success_rate']:.2%}` success "
                f"at `M=5000` and `3%` noise."
            ),
            "",
            "## Interpretation",
            "",
            "- The smooth layer preserves the large-scale distortion geometry while damping local divisor spikes.",
            "- Continuous recovery works best when the calibration support is log-spaced, matching the asymptotic form of κ_smooth.",
            "- The hybrid path keeps exact integer behavior available while enabling real-valued pipelines.",
            "",
        ]
    ) + "\n"

    (output_dir / "PROBLEM.md").write_text(problem_md, encoding="utf-8")
    (output_dir / "EXPERIMENT_REPORT.md").write_text(report_md, encoding="utf-8")
    (output_dir / "continuous_results.json").write_text(
        json.dumps(continuous_results, indent=2) + "\n",
        encoding="utf-8",
    )
    return continuous_results


def run_command(args: list[str]) -> None:
    subprocess.run(args, cwd=ROOT, check=True)


def main() -> int:
    os.chdir(ROOT)
    write_threshold_map(ROOT / "data" / "reference" / "threshold_map.csv")

    run_command(
        [
            sys.executable,
            "experiments/v_inference/benchmark.py",
            "--n-max",
            "10000",
            "--trials",
            "12",
            "--sample-sizes",
            "100",
            "1000",
            "5000",
            "--v-values",
            "0.5",
            "1.0",
            "1.5",
            "2.0",
            "2.5",
            "--methods",
            "moment_match",
            "mle",
            "fingerprint",
            "--sequence-types",
            "random",
            "consecutive",
            "prime_biased",
            "composite_heavy",
            "--noise-level",
            "0.03",
            "--seed",
            "20260330",
        ]
    )

    analytic_results = build_analytic_artifacts(ROOT / "experiments/analytic_connections")
    build_continuous_artifacts(ROOT / "experiments/continuous_extension", analytic_results)

    run_command([sys.executable, "baseline_report.py"])
    run_command([sys.executable, "main.py"])
    run_command([sys.executable, "generate_plots.py"])

    run_command([sys.executable, "experiments/cognitive_pilot/benchmark.py"])

    print("Sprint 1-6 reproduction complete")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
