#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
analyze_swir_metrics.py — Arkhe-Cathedral SwiReasoning Metrics Analyzer

Reads swir_metrics.jsonl and generates:
  1. Entropy time-series plots (per run + aggregated)
  2. Switch count distribution (histogram + boxplot)
  3. Latency scatter vs entropy_std
  4. Calibration heatmap (entropy_ref_x1000 × max_switches)

Usage:
    python analyze_swir_metrics.py swir_metrics.jsonl
    python analyze_swir_metrics.py swir_metrics.jsonl --output-dir ./plots
    python analyze_swir_metrics.py calibration_*.json --mode calibration

Selo: CATHEDRAL-1104.2-ANALYZE-SWIR-v1.1.0-2026-06-13
Arquiteto: ORCID 0009-0005-2697-4668
"""

import argparse
import json
import sys
from pathlib import Path
from typing import List, Dict, Any
from datetime import datetime

import numpy as np
import matplotlib.pyplot as plt
import matplotlib

# ============================================================
# CONFIGURATION
# ============================================================

plt.rcParams.update({
    "figure.figsize": (14, 6),
    "figure.dpi": 150,
    "axes.grid": True,
    "grid.alpha": 0.3,
    "axes.labelsize": 11,
    "axes.titlesize": 13,
    "legend.fontsize": 9,
    "xtick.labelsize": 9,
    "ytick.labelsize": 9,
})

COLORS = {
    "entropy": "#2E5AAC",
    "switch": "#C44E52",
    "latency": "#55A868",
    "confidence": "#DD8452",
    "explicit": "#4C72B0",
    "latent": "#8172B3",
}


# ============================================================
# DATA LOADING
# ============================================================

def load_metrics(filepath: Path) -> List[Dict[str, Any]]:
    """Load metrics from JSONL file."""
    records = []
    with open(filepath, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                records.append(json.loads(line))
            except json.JSONDecodeError as e:
                print(f"[WARN] Skipping malformed line: {e}")
    return records


def load_calibration(filepath: Path) -> Dict[str, Any]:
    """Load calibration JSON report."""
    with open(filepath, "r", encoding="utf-8") as f:
        return json.load(f)


# ============================================================
# PLOT 1: Entropy Time-Series (Individual + Aggregated)
# ============================================================

def plot_entropy_timeseries(records: List[Dict], output_dir: Path, max_runs: int = 10):
    """Plot entropy series for individual runs + aggregated statistics."""

    # Filter records with entropy_series
    valid = [r for r in records if r.get("entropy_series")]
    if not valid:
        print("[WARN] No entropy_series found in metrics.")
        return

    # --- Individual runs (first max_runs) ---
    n = min(max_runs, len(valid))
    fig, axes = plt.subplots(n, 1, figsize=(14, 2.5 * n), sharex=True)
    if n == 1:
        axes = [axes]

    for i, rec in enumerate(valid[:n]):
        ax = axes[i]
        series = rec["entropy_series"]
        tokens = list(range(len(series)))

        ax.plot(tokens, series, color=COLORS["entropy"], linewidth=0.8, alpha=0.9)
        ax.axhline(y=rec.get("entropy_mean", np.mean(series)),
                   color=COLORS["confidence"], linestyle="--", linewidth=1,
                   label=f"mean={rec.get('entropy_mean', 0):.3f}")

        # Mark switch points
        for sp in rec.get("switch_points", []):
            if sp < len(series):
                ax.axvline(x=sp, color=COLORS["switch"], linestyle=":", alpha=0.6, linewidth=0.8)

        ax.set_ylabel("Entropy (nats)")
        ax.set_title(f"Run {rec['run_id'][:8]} | Switches: {rec.get('switch_count', 0)} | "
                     f"Tokens: {rec.get('output_tokens', 0)} | "
                     f"Latency: {rec.get('latency_total_us', 0)/1000:.1f}ms")
        ax.legend(loc="upper right")

    axes[-1].set_xlabel("Token Position")
    plt.tight_layout()
    out = output_dir / "entropy_timeseries_individual.png"
    plt.savefig(out, bbox_inches="tight")
    plt.close()
    print(f"[Plot] Saved: {out}")

    # --- Aggregated statistics ---
    fig, axes = plt.subplots(2, 2, figsize=(14, 10))

    # (a) Mean entropy per position
    max_len = max(len(r["entropy_series"]) for r in valid)
    entropy_matrix = np.full((len(valid), max_len), np.nan)
    for i, rec in enumerate(valid):
        s = rec["entropy_series"]
        entropy_matrix[i, :len(s)] = s

    mean_entropy = np.nanmean(entropy_matrix, axis=0)
    std_entropy = np.nanstd(entropy_matrix, axis=0)
    positions = np.arange(max_len)

    ax = axes[0, 0]
    ax.plot(positions, mean_entropy, color=COLORS["entropy"], linewidth=1.2, label="Mean")
    ax.fill_between(positions, mean_entropy - std_entropy, mean_entropy + std_entropy,
                    alpha=0.2, color=COLORS["entropy"], label="±1σ")
    ax.set_title("Aggregated Entropy (Mean ± Std)")
    ax.set_xlabel("Token Position")
    ax.set_ylabel("Entropy (nats)")
    ax.legend()

    # (b) Entropy distribution histogram
    ax = axes[0, 1]
    all_entropy = [e for r in valid for e in r["entropy_series"]]
    ax.hist(all_entropy, bins=50, color=COLORS["entropy"], alpha=0.7, edgecolor="white")
    ax.axvline(x=np.mean(all_entropy), color=COLORS["switch"], linestyle="--", linewidth=2,
               label=f"μ={np.mean(all_entropy):.3f}")
    ax.set_title("Entropy Distribution (All Tokens)")
    ax.set_xlabel("Entropy (nats)")
    ax.set_ylabel("Frequency")
    ax.legend()

    # (c) Entropy std per run (consistency indicator)
    ax = axes[1, 0]
    run_ids = [r["run_id"][:8] for r in valid]
    entropy_stds = [r.get("entropy_std", 0) for r in valid]
    colors = [COLORS["latency"] if s < 0.15 else COLORS["switch"] for s in entropy_stds]
    ax.bar(run_ids, entropy_stds, color=colors, alpha=0.8, edgecolor="white")
    ax.axhline(y=0.15, color="red", linestyle="--", linewidth=1.5, label="Target < 0.15")
    ax.set_title("Entropy Std per Run (Consistency)")
    ax.set_xlabel("Run ID")
    ax.set_ylabel("Entropy Std")
    ax.tick_params(axis="x", rotation=45)
    ax.legend()

    # (d) Entropy vs token position (all runs overlay)
    ax = axes[1, 1]
    for rec in valid[:min(20, len(valid))]:
        series = rec["entropy_series"]
        tokens = list(range(len(series)))
        ax.plot(tokens, series, alpha=0.15, color=COLORS["entropy"], linewidth=0.5)
    ax.plot(positions, mean_entropy, color="black", linewidth=1.5, label="Mean")
    ax.set_title("Entropy Overlay (All Runs)")
    ax.set_xlabel("Token Position")
    ax.set_ylabel("Entropy (nats)")
    ax.legend()

    plt.tight_layout()
    out = output_dir / "entropy_aggregated.png"
    plt.savefig(out, bbox_inches="tight")
    plt.close()
    print(f"[Plot] Saved: {out}")


# ============================================================
# PLOT 2: Switch Count Distribution
# ============================================================

def plot_switch_distribution(records: List[Dict], output_dir: Path):
    """Plot switch count histogram, boxplot, and correlation with latency."""

    valid = [r for r in records if "switch_count" in r]
    if not valid:
        print("[WARN] No switch_count found in metrics.")
        return

    switch_counts = [r["switch_count"] for r in valid]
    latencies = [r.get("latency_total_us", 0) / 1000 for r in valid]  # ms
    output_tokens = [r.get("output_tokens", 0) for r in valid]

    fig, axes = plt.subplots(2, 2, figsize=(14, 10))

    # (a) Histogram of switch counts
    ax = axes[0, 0]
    bins = np.arange(0, max(switch_counts) + 2) - 0.5
    ax.hist(switch_counts, bins=bins, color=COLORS["switch"], alpha=0.7, edgecolor="white")
    ax.axvline(x=np.mean(switch_counts), color="black", linestyle="--", linewidth=2,
               label=f"μ={np.mean(switch_counts):.2f}")
    ax.set_title("Switch Count Distribution")
    ax.set_xlabel("Number of Switches")
    ax.set_ylabel("Frequency")
    ax.set_xticks(range(max(switch_counts) + 1))
    ax.legend()

    # (b) Boxplot of switch counts by engine (if multiple engines)
    ax = axes[0, 1]
    engines = list(set(r.get("engine", "unknown") for r in valid))
    if len(engines) > 1:
        data_by_engine = [[r["switch_count"] for r in valid if r.get("engine") == e]
                          for e in engines]
        bp = ax.boxplot(data_by_engine, labels=engines, patch_artist=True)
        for patch in bp["boxes"]:
            patch.set_facecolor(COLORS["switch"])
            patch.set_alpha(0.6)
        ax.set_title("Switch Count by Engine")
    else:
        bp = ax.boxplot([switch_counts], labels=[engines[0]], patch_artist=True)
        bp["boxes"][0].set_facecolor(COLORS["switch"])
        bp["boxes"][0].set_alpha(0.6)
        ax.set_title("Switch Count Boxplot")
    ax.set_ylabel("Switches")
    ax.tick_params(axis="x", rotation=30)

    # (c) Switch count vs latency
    ax = axes[1, 0]
    ax.scatter(switch_counts, latencies, alpha=0.6, color=COLORS["latency"], s=50, edgecolors="white")
    z = np.polyfit(switch_counts, latencies, 1)
    p = np.poly1d(z)
    x_line = np.linspace(min(switch_counts), max(switch_counts), 100)
    ax.plot(x_line, p(x_line), "r--", alpha=0.8, linewidth=1.5, label=f"trend (R² pending)")
    ax.set_title("Switch Count vs Total Latency")
    ax.set_xlabel("Switch Count")
    ax.set_ylabel("Latency (ms)")
    ax.legend()

    # (d) Switch efficiency (switches per token)
    ax = axes[1, 1]
    efficiency = [s / max(t, 1) for s, t in zip(switch_counts, output_tokens)]
    ax.hist(efficiency, bins=30, color=COLORS["confidence"], alpha=0.7, edgecolor="white")
    ax.axvline(x=np.mean(efficiency), color="black", linestyle="--", linewidth=2,
               label=f"μ={np.mean(efficiency):.4f}")
    ax.axvline(x=0.05, color="red", linestyle=":", linewidth=1.5, label="Target < 0.05")
    ax.set_title("Switch Efficiency (Switches / Token)")
    ax.set_xlabel("Efficiency Ratio")
    ax.set_ylabel("Frequency")
    ax.legend()

    plt.tight_layout()
    out = output_dir / "switch_distribution.png"
    plt.savefig(out, bbox_inches="tight")
    plt.close()
    print(f"[Plot] Saved: {out}")


# ============================================================
# PLOT 3: Calibration Heatmap (Grid Search Results)
# ============================================================

def plot_calibration_heatmap(calibration: Dict, output_dir: Path):
    """Plot heatmap of calibration grid search results."""

    results = calibration.get("all_results", [])
    if not results:
        print("[WARN] No calibration results found.")
        return

    # Extract grid dimensions
    refs = sorted(set(r["entropy_ref_x1000"] for r in results))
    switches = sorted(set(r["max_switches"] for r in results))

    # Build score matrix
    score_matrix = np.full((len(switches), len(refs)), np.nan)
    for r in results:
        i = switches.index(r["max_switches"])
        j = refs.index(r["entropy_ref_x1000"])
        score_matrix[i, j] = r["score"]

    fig, ax = plt.subplots(figsize=(10, 6))
    im = ax.imshow(score_matrix, cmap="RdYlGn", aspect="auto", interpolation="nearest")

    # Labels
    ax.set_xticks(np.arange(len(refs)))
    ax.set_yticks(np.arange(len(switches)))
    ax.set_xticklabels([str(r) for r in refs])
    ax.set_yticklabels([str(s) for s in switches])
    ax.set_xlabel("entropy_ref_x1000")
    ax.set_ylabel("max_switches")
    ax.set_title("Calibration Score Heatmap (Higher = Better)")

    # Annotate cells
    for i in range(len(switches)):
        for j in range(len(refs)):
            if not np.isnan(score_matrix[i, j]):
                text = ax.text(j, i, f"{score_matrix[i, j]:.2f}",
                               ha="center", va="center", color="black", fontsize=9)

    # Mark best config
    best = calibration.get("best_config", {})
    if best:
        bi = switches.index(best["max_switches"])
        bj = refs.index(best["entropy_ref_x1000"])
        ax.add_patch(plt.Rectangle((bj - 0.5, bi - 0.5), 1, 1,
                                    fill=False, edgecolor="blue", linewidth=3))
        ax.set_title(f"Calibration Score Heatmap | BEST: ref={best['entropy_ref_x1000']}, "
                     f"sw={best['max_switches']} (score={best['score']:.2f})")

    plt.colorbar(im, ax=ax, label="Score")
    plt.tight_layout()
    out = output_dir / "calibration_heatmap.png"
    plt.savefig(out, bbox_inches="tight")
    plt.close()
    print(f"[Plot] Saved: {out}")

    # Secondary: latency heatmap
    latency_matrix = np.full((len(switches), len(refs)), np.nan)
    for r in results:
        i = switches.index(r["max_switches"])
        j = refs.index(r["entropy_ref_x1000"])
        latency_matrix[i, j] = r.get("avg_latency_ms", 0)

    fig, ax = plt.subplots(figsize=(10, 6))
    im = ax.imshow(latency_matrix, cmap="YlOrRd", aspect="auto", interpolation="nearest")
    ax.set_xticks(np.arange(len(refs)))
    ax.set_yticks(np.arange(len(switches)))
    ax.set_xticklabels([str(r) for r in refs])
    ax.set_yticklabels([str(s) for s in switches])
    ax.set_xlabel("entropy_ref_x1000")
    ax.set_ylabel("max_switches")
    ax.set_title("Calibration Latency Heatmap (ms, Lower = Better)")
    plt.colorbar(im, ax=ax, label="Latency (ms)")
    plt.tight_layout()
    out = output_dir / "calibration_latency.png"
    plt.savefig(out, bbox_inches="tight")
    plt.close()
    print(f"[Plot] Saved: {out}")


# ============================================================
# MAIN
# ============================================================

def main():
    parser = argparse.ArgumentParser(
        description="Arkhe-Cathedral SwiReasoning Metrics Analyzer"
    )
    parser.add_argument("input", type=str, help="Input file (metrics JSONL or calibration JSON)")
    parser.add_argument("--output-dir", type=str, default="./plots",
                        help="Output directory for plots")
    parser.add_argument("--mode", choices=["metrics", "calibration"], default="metrics",
                        help="Analysis mode")
    parser.add_argument("--max-runs", type=int, default=10,
                        help="Max individual runs to plot in entropy timeseries")

    args = parser.parse_args()

    input_path = Path(args.input)
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    print("=" * 60)
    print("ARKHE-CATHEDRAL SWIREASONING METRICS ANALYZER")
    print(f"Input: {input_path}")
    print(f"Output: {output_dir}")
    print("=" * 60)

    if args.mode == "calibration":
        calibration = load_calibration(input_path)
        plot_calibration_heatmap(calibration, output_dir)
    else:
        records = load_metrics(input_path)
        print(f"Loaded {len(records)} metric records")

        if not records:
            print("[ERROR] No records found.")
            sys.exit(1)

        plot_entropy_timeseries(records, output_dir, max_runs=args.max_runs)
        plot_switch_distribution(records, output_dir)

    print(f"\n[Done] All plots saved to {output_dir}")


if __name__ == "__main__":
    main()
