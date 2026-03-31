#!/usr/bin/env python3
"""
Generate the local figure bundle for the CDL technical note.
"""

from __future__ import annotations

import csv
import json
import shutil
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt


REPO_ROOT = Path(__file__).resolve().parents[1]
NOTE_DIR = Path(__file__).resolve().parent
FIGURES_DIR = NOTE_DIR / "figures"


def copy_static_figures() -> None:
    FIGURES_DIR.mkdir(parents=True, exist_ok=True)
    copies = {
        REPO_ROOT / "artifacts" / "figures" / "cdl_kappa_histograms.png":
            FIGURES_DIR / "figure1_integer_curvature_separation.png",
        REPO_ROOT / "artifacts" / "figures" / "cdl_z_normalized_traces.png":
            FIGURES_DIR / "figure2_z_normalization_traces.png",
    }
    for source, target in copies.items():
        shutil.copy2(source, target)


def generate_threshold_map_figure() -> None:
    rows = []
    with (REPO_ROOT / "data" / "reference" / "threshold_map.csv").open() as handle:
        reader = csv.DictReader(handle)
        for row in reader:
            n_min = int(row["n_min"])
            n_max = int(row["n_max"])
            rows.append(
                {
                    "label": f"{n_min}-{n_max}",
                    "midpoint": (n_min + n_max) / 2.0,
                    "threshold": float(row["threshold"]),
                    "accuracy": float(row["accuracy"]),
                    "precision": float(row["precision"]),
                    "recall": float(row["recall"]),
                }
            )

    labels = [row["label"] for row in rows]
    thresholds = [row["threshold"] for row in rows]
    accuracies = [row["accuracy"] for row in rows]
    precisions = [row["precision"] for row in rows]
    recalls = [row["recall"] for row in rows]

    fig, axes = plt.subplots(1, 2, figsize=(12, 4.8))

    axes[0].plot(labels, thresholds, marker="o", linewidth=2.5, color="#1f77b4")
    axes[0].set_title("Adaptive Threshold by Range Window")
    axes[0].set_xlabel("Range window")
    axes[0].set_ylabel("Threshold tau")
    axes[0].grid(alpha=0.25)

    axes[1].plot(labels, accuracies, marker="o", linewidth=2, label="accuracy", color="#1f77b4")
    axes[1].plot(labels, precisions, marker="s", linewidth=2, label="precision", color="#2ca02c")
    axes[1].plot(labels, recalls, marker="^", linewidth=2, label="recall", color="#d62728")
    axes[1].set_title("Protocol Metrics by Window")
    axes[1].set_xlabel("Range window")
    axes[1].set_ylabel("Score")
    axes[1].set_ylim(0.75, 1.02)
    axes[1].grid(alpha=0.25)
    axes[1].legend()

    fig.tight_layout()
    fig.savefig(FIGURES_DIR / "figure3_adaptive_threshold_protocol.png", dpi=220, bbox_inches="tight")
    plt.close(fig)


def generate_v_inference_figure() -> None:
    with (REPO_ROOT / "experiments" / "v_inference" / "v_inference_results.json").open() as handle:
        payload = json.load(handle)

    table_rows = payload["table_rows"]
    sample_sizes = sorted({row["sample_size"] for row in table_rows})
    sequence_types = ["random", "composite_heavy"]
    method_colors = {
        "moment_match": "#7f7f7f",
        "mle": "#1f77b4",
        "fingerprint": "#d62728",
    }

    fig, axes = plt.subplots(1, 2, figsize=(12, 4.8), sharey=True)
    for axis, sequence_type in zip(axes, sequence_types):
        subset = [row for row in table_rows if row["sequence_type"] == sequence_type]
        for method, color in method_colors.items():
            method_rows = sorted(
                [row for row in subset if row["method"] == method],
                key=lambda row: row["sample_size"],
            )
            axis.plot(
                [row["sample_size"] for row in method_rows],
                [row["mae"] for row in method_rows],
                marker="o",
                linewidth=2.2,
                color=color,
                label=method,
            )
        axis.set_xscale("log")
        axis.set_title(sequence_type.replace("_", " ").title())
        axis.set_xlabel("Sample size M")
        axis.grid(alpha=0.25)
        axis.set_xticks(sample_sizes, [str(value) for value in sample_sizes])

    axes[0].set_ylabel("Mean absolute error")
    axes[0].legend()
    fig.suptitle("v-Inference Recovery Curves", fontsize=14, y=1.02)
    fig.tight_layout()
    fig.savefig(FIGURES_DIR / "figure4_v_inference_recovery_curves.png", dpi=220, bbox_inches="tight")
    plt.close(fig)


def generate_cognitive_pilot_figure() -> None:
    with (REPO_ROOT / "experiments" / "cognitive_pilot" / "cognitive_pilot_results.json").open() as handle:
        payload = json.load(handle)

    participants = payload["participants_detail"]
    groups = {
        "sharp geodesic": {"color": "#1f77b4", "values": [], "points": []},
        "compressed distortion": {"color": "#d62728", "values": [], "points": []},
    }

    for participant in participants:
        group = participant["group"]
        groups[group]["values"].append(participant["v_recovered"])
        groups[group]["points"].append(
            (participant["compression_exponent"], participant["v_recovered"])
        )

    fig, axes = plt.subplots(1, 2, figsize=(12, 4.8))

    bins = 12
    for group, details in groups.items():
        axes[0].hist(
            details["values"],
            bins=bins,
            alpha=0.65,
            color=details["color"],
            label=group,
        )
    axes[0].set_title("Recovered v Clusters")
    axes[0].set_xlabel("Recovered v")
    axes[0].set_ylabel("Participants")
    axes[0].legend()

    for group, details in groups.items():
        xs = [point[0] for point in details["points"]]
        ys = [point[1] for point in details["points"]]
        axes[1].scatter(xs, ys, s=60, alpha=0.8, color=details["color"], label=group)
    axes[1].set_title("Recovered v vs. Compression Exponent")
    axes[1].set_xlabel("Compression exponent")
    axes[1].set_ylabel("Recovered v")
    axes[1].legend()
    axes[1].grid(alpha=0.25)

    fig.tight_layout()
    fig.savefig(FIGURES_DIR / "figure5_cognitive_pilot_bridge.png", dpi=220, bbox_inches="tight")
    plt.close(fig)


def main() -> None:
    copy_static_figures()
    generate_threshold_map_figure()
    generate_v_inference_figure()
    generate_cognitive_pilot_figure()
    print("technical-note figures generated")


if __name__ == "__main__":
    main()
