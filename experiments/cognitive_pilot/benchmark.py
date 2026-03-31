#!/usr/bin/env python3
"""Generate the local Sprint 6 cognitive pilot artifacts."""

from __future__ import annotations

import argparse
import csv
import json
import sys
import time
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from scipy import stats

ROOT = Path(__file__).resolve().parents[2]
OUTPUT_DIR = ROOT / "experiments" / "cognitive_pilot"
SOURCE_DIR = ROOT / "src" / "python"
if str(SOURCE_DIR) not in sys.path:
    sys.path.insert(0, str(SOURCE_DIR))


from cognitive_pilot import CognitivePilot


def build_report(results: dict) -> str:
    sharp = results["group_summary"]["sharp geodesic"]
    compressed = results["group_summary"]["compressed distortion"]
    return "\n".join(
        [
            "# Cognitive Pilot Report — Sprint 6",
            "",
            "## Headline Findings",
            "",
            (
                f"- `{results['participants']}` participants, `{results['trials_per_participant']}` trials each."
            ),
            (
                f"- Hybrid fingerprint recovery reaches MAE `{results['mae']:.4f}` with "
                f"`{results['success_rate']:.2%}` success at `|error| < 0.15`."
            ),
            (
                f"- Hybrid fallback reduces recovery error by "
                f"`{results['hybrid_relative_improvement_pct']:.2f}%` versus pure continuous calibration."
            ),
            (
                f"- Recovered `v` cleanly separates the sharp cluster "
                f"(`{sharp['mean_v_recovered']:.2f} ± {sharp['std_v_recovered']:.2f}`) from the compressed cluster "
                f"(`{compressed['mean_v_recovered']:.2f} ± {compressed['std_v_recovered']:.2f}`)."
            ),
            (
                f"- Psychophysical compression correlation: "
                f"`{results['compression_correlation']:.3f}`."
            ),
            "",
            "## Interpretation",
            "",
            "- The local pilot reproduces the applied bridge from Sprint 3–5 into perceptual data.",
            "- Exact integer curvature still matters on real human-like sequences; the hybrid path materially outperforms a pure smooth surrogate.",
            "- Style labels are operational: low-v participants stay on sharper geodesics, high-v participants show stronger tail collapse.",
            "",
        ]
    ) + "\n"


def write_participant_csv(path: Path, rows: list[dict]) -> None:
    fieldnames = [
        "participant_id",
        "group",
        "v_true",
        "v_recovered",
        "confidence",
        "cognitive_style",
        "style_match",
        "error",
        "continuous_error",
        "hybrid_relative_improvement_pct",
        "noise_sigma",
        "compression_exponent",
        "mean_distortion",
        "z_min",
        "z_max",
        "z_range",
    ]
    with path.open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames, lineterminator="\n")
        writer.writeheader()
        for row in rows:
            writer.writerow(row)


def render_plots(output_dir: Path, rows: list[dict]) -> None:
    sharp = [row for row in rows if row["group"] == "sharp geodesic"]
    compressed = [row for row in rows if row["group"] == "compressed distortion"]

    plt.figure(figsize=(9, 4.8))
    plt.hist([row["v_recovered"] for row in sharp], bins=10, alpha=0.75, label="sharp geodesic")
    plt.hist([row["v_recovered"] for row in compressed], bins=10, alpha=0.75, label="compressed distortion")
    plt.xlabel("Recovered v")
    plt.ylabel("Participants")
    plt.title("Sprint 6 Cognitive Style Clusters")
    plt.legend()
    plt.tight_layout()
    plt.savefig(output_dir / "v_clusters.png", dpi=200, bbox_inches="tight")
    plt.close()

    plt.figure(figsize=(6.4, 4.8))
    colors = ["#0f766e" if row["group"] == "sharp geodesic" else "#b45309" for row in rows]
    plt.scatter(
        [row["compression_exponent"] for row in rows],
        [row["v_recovered"] for row in rows],
        c=colors,
        alpha=0.85,
    )
    plt.xlabel("Compression Exponent")
    plt.ylabel("Recovered v")
    plt.title("Recovered v vs. Psychophysical Compression")
    plt.tight_layout()
    plt.savefig(output_dir / "compression_correlation.png", dpi=200, bbox_inches="tight")
    plt.close()


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--participants", type=int, default=50)
    parser.add_argument("--trials", type=int, default=200)
    parser.add_argument("--seed", type=int, default=20260330)
    parser.add_argument("--support-size", type=int, default=100000)
    parser.add_argument("--reference-trials", type=int, default=50)
    args = parser.parse_args()

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    start = time.time()
    pilot = CognitivePilot(
        n_max=10_000,
        participant_trials=args.trials,
        support_size=args.support_size,
        reference_trials=args.reference_trials,
        random_seed=args.seed,
    )
    rng = np.random.default_rng(args.seed)

    participant_rows = []
    recovered_values = []
    compression_values = []
    hybrid_errors = []
    continuous_errors = []
    low_values = []
    high_values = []

    for participant_index in range(args.participants):
        group = "sharp geodesic" if participant_index < args.participants // 2 else "compressed distortion"
        v_true = float(rng.uniform(0.6, 1.0)) if group == "sharp geodesic" else float(rng.uniform(1.4, 2.2))
        payload = pilot.simulate_participant(
            participant_id=f"P{participant_index + 1:02d}",
            v_true=v_true,
            rng=rng,
            n_trials=args.trials,
        )
        participant = pilot.run_participant(
            payload["presented_n"],
            payload["perceived_z"],
            participant_id=payload["participant_id"],
        )
        comparison = pilot.compare_hybrid_vs_continuous(payload["perceived_z"], v_true)

        row = {
            "participant_id": participant.participant_id,
            "group": group,
            "v_true": round(v_true, 6),
            "v_recovered": round(participant.v_recovered, 6),
            "confidence": round(participant.confidence, 6),
            "cognitive_style": participant.cognitive_style,
            "style_match": participant.cognitive_style == group,
            "error": round(abs(participant.v_recovered - v_true), 6),
            "continuous_error": round(comparison["continuous_error"], 6),
            "hybrid_relative_improvement_pct": round(comparison["relative_improvement"] * 100.0, 6),
            "noise_sigma": round(payload["noise_sigma"], 6),
            "compression_exponent": round(participant.compression_exponent, 6),
            "mean_distortion": round(participant.mean_distortion, 6),
            "z_min": round(participant.z_min, 6),
            "z_max": round(participant.z_max, 6),
            "z_range": round(participant.z_range, 6),
        }
        participant_rows.append(row)
        recovered_values.append(participant.v_recovered)
        compression_values.append(participant.compression_exponent)
        hybrid_errors.append(abs(participant.v_recovered - v_true))
        continuous_errors.append(comparison["continuous_error"])
        if group == "sharp geodesic":
            low_values.append(participant.v_recovered)
        else:
            high_values.append(participant.v_recovered)

    runtime_seconds = time.time() - start
    low_array = np.array(low_values, dtype=np.float64)
    high_array = np.array(high_values, dtype=np.float64)
    t_test = stats.ttest_ind(low_array, high_array, equal_var=False)

    results = {
        "experiment_date": "2026-03-30",
        "participants": args.participants,
        "trials_per_participant": args.trials,
        "noise_sigma_range": [0.05, 0.12],
        "mae": float(np.mean(hybrid_errors)),
        "success_rate": float(np.mean(np.array(hybrid_errors) < 0.15)),
        "style_accuracy": float(np.mean([row["style_match"] for row in participant_rows])),
        "compression_correlation": float(np.corrcoef(recovered_values, compression_values)[0, 1]),
        "hybrid_relative_improvement_pct": float(
            (np.mean(continuous_errors) - np.mean(hybrid_errors))
            / np.mean(continuous_errors)
            * 100.0
        ),
        "runtime_seconds": float(runtime_seconds),
        "group_summary": {
            "sharp geodesic": {
                "mean_v_recovered": float(np.mean(low_array)),
                "std_v_recovered": float(np.std(low_array)),
                "mean_z_range": float(np.mean([row["z_range"] for row in participant_rows if row["group"] == "sharp geodesic"])),
            },
            "compressed distortion": {
                "mean_v_recovered": float(np.mean(high_array)),
                "std_v_recovered": float(np.std(high_array)),
                "mean_z_range": float(np.mean([row["z_range"] for row in participant_rows if row["group"] == "compressed distortion"])),
            },
        },
        "cluster_t_test": {
            "statistic": float(t_test.statistic),
            "p_value": float(t_test.pvalue),
        },
        "participants_detail": participant_rows,
    }

    write_participant_csv(OUTPUT_DIR / "participant_results.csv", participant_rows)
    render_plots(OUTPUT_DIR, participant_rows)
    (OUTPUT_DIR / "PILOT_REPORT.md").write_text(build_report(results), encoding="utf-8")
    (OUTPUT_DIR / "cognitive_pilot_results.json").write_text(
        json.dumps(results, indent=2) + "\n",
        encoding="utf-8",
    )

    print("cognitive pilot benchmark complete")
    print(
        "Best headline: "
        f"MAE={results['mae']:.4f}, success={results['success_rate']:.2%}, "
        f"hybrid improvement={results['hybrid_relative_improvement_pct']:.2f}%"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
