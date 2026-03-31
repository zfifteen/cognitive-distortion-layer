#!/usr/bin/env python3
"""Reproducible Sprint 3 benchmark for v inference."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Dict, Iterable, List

import numpy as np

ROOT = Path(__file__).resolve().parents[2]
SOURCE_DIR = ROOT / "src" / "python"
if str(SOURCE_DIR) not in sys.path:
    sys.path.insert(0, str(SOURCE_DIR))

from v_recovery import VRecovery, generate_z_sequence


DEFAULT_V_VALUES = [0.5, 1.0, 1.5, 2.0, 2.5]
DEFAULT_SAMPLE_SIZES = [100, 1_000, 3_000, 5_000]
DEFAULT_SEQUENCE_TYPES = ["random", "consecutive", "prime_biased", "composite_heavy"]
DEFAULT_METHODS = ["moment_match", "mle", "fingerprint"]


def summarize_errors(errors: List[float]) -> Dict[str, float]:
    array = np.asarray(errors, dtype=np.float64)
    return {
        "mae": float(np.mean(np.abs(array))),
        "rmse": float(np.sqrt(np.mean(array ** 2))),
        "bias": float(np.mean(array)),
        "max_abs_error": float(np.max(np.abs(array))),
        "success_rate": float(np.mean(np.abs(array) < 0.05)),
    }


def build_report_markdown(results: Dict) -> str:
    lines = [
        "# v-Inference Benchmark Experiment Report",
        "",
        f"Date: {results['experiment_date']}",
        "",
        "This report is generated from a local benchmark run in this repository.",
        "",
        "## Configuration",
        "",
        f"- `n_max_precomputed`: {results['n_max_precomputed']}",
        f"- `trials_per_cell`: {results['trials_per_cell']}",
        f"- `sample_sizes`: {results['sample_sizes']}",
        f"- `sequence_types`: {results['sequence_types']}",
        f"- `methods`: {results['methods']}",
        f"- `noise_level`: {results['noise_level']}",
        f"- `v_values`: {results['v_values']}",
        "",
        "## Headline Findings",
        "",
    ]

    summary = results["headline_summary"]
    for item in summary:
        lines.append(f"- {item}")

    lines.extend(
        [
            "",
            "## Metrics by Cell",
            "",
            "| Sample Size | Sequence Type | Method | MAE | RMSE | Bias | Success Rate |",
            "|---|---|---|---:|---:|---:|---:|",
        ]
    )

    for row in results["table_rows"]:
        lines.append(
            "| "
            f"{row['sample_size']} | "
            f"{row['sequence_type']} | "
            f"{row['method']} | "
            f"{row['mae']:.4f} | "
            f"{row['rmse']:.4f} | "
            f"{row['bias']:.4f} | "
            f"{row['success_rate']:.2%} |"
        )

    lines.extend(
        [
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
    )
    return "\n".join(lines) + "\n"


def run_benchmark(
    output_dir: Path,
    n_max: int,
    trials: int,
    sample_sizes: Iterable[int],
    v_values: Iterable[float],
    methods: Iterable[str],
    sequence_types: Iterable[str],
    noise_level: float,
    seed: int,
) -> Dict:
    rng = np.random.default_rng(seed)
    sample_sizes = [int(size) for size in sample_sizes]
    v_values = [float(v) for v in v_values]
    methods = [str(method) for method in methods]
    sequence_types = [str(seq) for seq in sequence_types]

    calibrators = {}
    for sample_size in sample_sizes:
        for sequence_type in sequence_types:
            calibrators[(sample_size, sequence_type)] = VRecovery(
                calibration_n_max=n_max,
                v_grid=np.round(np.arange(0.3, 3.01, 0.1), 2),
                sample_size=sample_size,
                sequence_type=sequence_type,
                reference_trials=max(12, min(40, trials)),
                random_seed=seed,
            )

    records = []
    for sample_size in sample_sizes:
        for sequence_type in sequence_types:
            calibrator = calibrators[(sample_size, sequence_type)]
            for method in methods:
                for v_true in v_values:
                    errors = []
                    confidence_values = []
                    for _ in range(trials):
                        z_sequence, _ = generate_z_sequence(
                            numbers=calibrator.numbers,
                            kappas=calibrator.kappas,
                            rng=rng,
                            v=v_true,
                            sample_size=sample_size,
                            sequence_type=sequence_type,
                            noise_level=noise_level,
                            prime_mask=calibrator.prime_mask,
                        )
                        inference = calibrator.infer_v(z_sequence, method=method)
                        errors.append(inference.v_estimate - v_true)
                        confidence_values.append(inference.confidence_half_width)

                    summary = summarize_errors(errors)
                    summary.update(
                        {
                            "sample_size": sample_size,
                            "sequence_type": sequence_type,
                            "method": method,
                            "v_true": v_true,
                            "mean_confidence_half_width": float(np.mean(confidence_values)),
                        }
                    )
                    records.append(summary)

    def aggregate(method: str, sequence_type: str, sample_size: int) -> Dict[str, float]:
        matching = [
            row
            for row in records
            if row["method"] == method
            and row["sequence_type"] == sequence_type
            and row["sample_size"] == sample_size
        ]
        if not matching:
            raise ValueError("No matching rows for aggregation")
        mae = float(np.mean([row["mae"] for row in matching]))
        rmse = float(np.mean([row["rmse"] for row in matching]))
        bias = float(np.mean([row["bias"] for row in matching]))
        success_rate = float(np.mean([row["success_rate"] for row in matching]))
        return {
            "sample_size": sample_size,
            "sequence_type": sequence_type,
            "method": method,
            "mae": mae,
            "rmse": rmse,
            "bias": bias,
            "success_rate": success_rate,
        }

    table_rows = []
    for sample_size in sample_sizes:
        for sequence_type in sequence_types:
            for method in methods:
                table_rows.append(aggregate(method, sequence_type, sample_size))

    best_row = min(table_rows, key=lambda row: row["mae"])
    fingerprint_rows = [row for row in table_rows if row["method"] == "fingerprint"]
    mle_rows = [row for row in table_rows if row["method"] == "mle"]
    moment_rows = [row for row in table_rows if row["method"] == "moment_match"]
    composite_rows = [row for row in table_rows if row["sequence_type"] == "composite_heavy"]
    strong_rows = [row for row in table_rows if row["success_rate"] >= 0.90]
    headline_summary = [
        f"Best aggregate cell: `{best_row['method']}` on `{best_row['sequence_type']}` "
        f"at `M={best_row['sample_size']}` with MAE `{best_row['mae']:.4f}`.",
    ]
    if fingerprint_rows:
        best_fingerprint = min(fingerprint_rows, key=lambda row: row["mae"])
        headline_summary.append(
            "Fingerprint recovery reaches "
            f"MAE `{best_fingerprint['mae']:.4f}` on `{best_fingerprint['sequence_type']}` "
            f"at `M={best_fingerprint['sample_size']}`."
        )
    if mle_rows:
        best_mle = min(mle_rows, key=lambda row: row["mae"])
        headline_summary.append(
            "MLE reaches "
            f"MAE `{best_mle['mae']:.4f}` on `{best_mle['sequence_type']}` "
            f"at `M={best_mle['sample_size']}`."
        )
    if moment_rows:
        best_moment = min(moment_rows, key=lambda row: row["mae"])
        headline_summary.append(
            "Moment matching is prior-sensitive but usable in its best calibrated regime, reaching "
            f"MAE `{best_moment['mae']:.4f}` on `{best_moment['sequence_type']}` "
            f"at `M={best_moment['sample_size']}`."
        )
    if composite_rows:
        best_composite = min(composite_rows, key=lambda row: row["mae"])
        headline_summary.append(
            "Composite-heavy sequences shift the ranking: the best method there is "
            f"`{best_composite['method']}` with MAE `{best_composite['mae']:.4f}` "
            f"at `M={best_composite['sample_size']}`."
        )
    headline_summary.append(
        f"`{len(strong_rows)}` aggregate cells clear a 90% success rate threshold in this run."
    )

    results = {
        "experiment_date": str(np.datetime64("today")),
        "n_max_precomputed": n_max,
        "trials_per_cell": trials,
        "sample_sizes": sample_sizes,
        "v_values": v_values,
        "sequence_types": sequence_types,
        "methods": methods,
        "noise_level": noise_level,
        "seed": seed,
        "raw_records": records,
        "table_rows": table_rows,
        "headline_summary": headline_summary,
        "reproduction_command": (
            "python3 experiments/v_inference/benchmark.py "
            f"--n-max {n_max} --trials {trials} "
            f"--sample-sizes {' '.join(str(x) for x in sample_sizes)} "
            f"--v-values {' '.join(str(x) for x in v_values)} "
            f"--methods {' '.join(methods)} "
            f"--sequence-types {' '.join(sequence_types)} "
            f"--noise-level {noise_level} --seed {seed}"
        ),
    }

    output_dir.mkdir(parents=True, exist_ok=True)
    json_path = output_dir / "v_inference_results.json"
    report_path = output_dir / "EXPERIMENT_REPORT.md"
    json_path.write_text(json.dumps(results, indent=2) + "\n", encoding="utf-8")
    report_path.write_text(build_report_markdown(results), encoding="utf-8")
    return results


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", default="experiments/v_inference")
    parser.add_argument("--n-max", type=int, default=15_000)
    parser.add_argument("--trials", type=int, default=16)
    parser.add_argument("--sample-sizes", nargs="+", type=int, default=DEFAULT_SAMPLE_SIZES)
    parser.add_argument("--v-values", nargs="+", type=float, default=DEFAULT_V_VALUES)
    parser.add_argument("--methods", nargs="+", default=DEFAULT_METHODS)
    parser.add_argument("--sequence-types", nargs="+", default=DEFAULT_SEQUENCE_TYPES)
    parser.add_argument("--noise-level", type=float, default=0.03)
    parser.add_argument("--seed", type=int, default=20260330)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    results = run_benchmark(
        output_dir=Path(args.output_dir),
        n_max=args.n_max,
        trials=args.trials,
        sample_sizes=args.sample_sizes,
        v_values=args.v_values,
        methods=args.methods,
        sequence_types=args.sequence_types,
        noise_level=args.noise_level,
        seed=args.seed,
    )
    best_row = min(results["table_rows"], key=lambda row: row["mae"])
    print("v-inference benchmark complete")
    print(
        f"Best cell: method={best_row['method']} sequence_type={best_row['sequence_type']} "
        f"M={best_row['sample_size']} MAE={best_row['mae']:.4f}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
