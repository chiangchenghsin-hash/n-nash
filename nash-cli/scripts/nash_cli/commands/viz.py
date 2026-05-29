#!/usr/bin/env python3
"""nash viz — Generate matplotlib visualizations from simulation results."""

import json
import sys
import os
from itertools import cycle
from typing import Any


def cmd_viz(args: Any) -> dict:
    with open(args.data, "r", encoding="utf-8") as f:
        data = json.load(f)

    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
    except ImportError:
        return {"error": "matplotlib not installed. Run: pip install matplotlib"}

    output_path = args.output or "nash_viz_output.png"
    viz_type = args.type

    if viz_type == "all":
        return _viz_all(data, output_path, plt)
    elif viz_type == "gini":
        return _viz_single(data, "gini", output_path, plt, "Gini Coefficient Over Time", "red")
    elif viz_type == "hostility":
        return _viz_single(data, "hostility", output_path, plt, "Mean Hostility Over Time", "orange")
    elif viz_type == "energy":
        return _viz_energy(data, output_path, plt)
    elif viz_type == "beliefs":
        return _viz_beliefs(data, output_path, plt)

    return {"error": f"Unknown viz type: {viz_type}"}


def _viz_all(data, output_path, plt):
    has_gini = "gini_history" in data
    has_hostility = "hostility_history" in data
    has_metrics = "final_metrics" in data

    if has_gini and has_hostility:
        fig, axes = plt.subplots(1, 2, figsize=(12, 5))

        axes[0].plot(data["gini_history"], color="#e74c3c", linewidth=1.5)
        axes[0].set_title("Gini Coefficient")
        axes[0].set_xlabel("Step")
        axes[0].set_ylabel("Gini")
        axes[0].grid(True, alpha=0.3)

        axes[1].plot(data["hostility_history"], color="#e67e22", linewidth=1.5)
        axes[1].set_title("Mean Hostility")
        axes[1].set_xlabel("Step")
        axes[1].set_ylabel("Hostility")
        axes[1].grid(True, alpha=0.3)

        plt.tight_layout()
        plt.savefig(output_path, dpi=80, bbox_inches="tight")
        plt.close(fig)
        return {"status": "ok", "output": os.path.abspath(output_path), "type": "all"}

    if has_metrics and "history" in data:
        return _viz_environment(data, output_path, plt)

    fig, ax = plt.subplots(figsize=(8, 4))
    ax.text(0.5, 0.5, "No plot data available", ha="center", va="center",
            transform=ax.transAxes, fontsize=14)
    plt.tight_layout()
    plt.savefig(output_path, dpi=80, bbox_inches="tight")
    plt.close(fig)
    return {"status": "ok", "output": os.path.abspath(output_path), "type": "all"}


def _viz_environment(data, output_path, plt):
    """Plot time-series from environment history entries."""
    history = data["history"]
    metrics = data.get("final_metrics", {})
    env_type = data.get("environment", "unknown")

    series = _extract_time_series(history, env_type)
    if not series:
        fig, ax = plt.subplots(figsize=(8, 4))
        ax.text(0.5, 0.5, "No plot data available", ha="center", va="center",
                transform=ax.transAxes, fontsize=14)
        plt.tight_layout()
        plt.savefig(output_path, dpi=80, bbox_inches="tight")
        plt.close(fig)
        return {"status": "ok", "output": os.path.abspath(output_path), "type": "all"}

    n = len(series)
    base_colors = ["#e74c3c", "#2ecc71", "#3498db", "#e67e22", "#9b59b6", "#1abc9c"]
    color_cycle = cycle(base_colors)
    fig, axes = plt.subplots(1, n, figsize=(5 * n, 4))
    if n == 1:
        axes = [axes]

    for ax, (name, values) in zip(axes, series.items()):
        color = next(color_cycle)
        ax.plot(values, color=color, linewidth=1.5, marker=".", markersize=2)
        ax.set_title(name.replace("_", " ").title())
        ax.set_xlabel("Round")
        ax.set_ylabel(name.replace("_", " ").title())
        ax.grid(True, alpha=0.3)

        # Add final value annotation
        if values:
            final = values[-1]
            ax.axhline(y=final, color=color, linestyle="--", alpha=0.25)
            ax.text(len(values) - 1, final, f" {final:.3f}", va="center", fontsize=8)

    plt.suptitle(f"Environment: {env_type.replace('_', ' ').title()}", fontsize=12, y=1.01)
    plt.tight_layout()
    plt.savefig(output_path, dpi=80, bbox_inches="tight")
    plt.close(fig)
    return {"status": "ok", "output": os.path.abspath(output_path), "type": "all", "metrics_plotted": list(series.keys())}


def _extract_time_series(history, env_type):
    """Extract numeric time series from history list, deduplicating rounds."""
    if not history:
        return {}

    seen_rounds = set()
    numeric_keys = set()

    # First pass: discover all numeric keys
    for entry in history:
        for k, v in entry.items():
            if k not in ("round", "winner_id") and isinstance(v, (int, float)):
                numeric_keys.add(k)

    # For vickrey auctions, add aggregate bid stats
    if env_type == "vickrey":
        numeric_keys.discard("bids")
        numeric_keys.update(["winning_bid", "price_paid", "winner_payoff"])

    series = {k: [] for k in sorted(numeric_keys)}
    if not series:
        return {}

    # Second pass: collect values, skip duplicate rounds
    for entry in history:
        r = entry.get("round", 0)
        if r in seen_rounds:
            continue
        seen_rounds.add(r)
        for k in series:
            series[k].append(entry.get(k, None))

    # Remove any series that are all None
    return {k: [v for v in vals if v is not None]
            for k, vals in series.items()
            if any(x is not None for x in vals)}


def _viz_single(data, key, output_path, plt, title, color):
    values = data.get(f"{key}_history", [])
    if not values:
        return {"error": f"No '{key}_history' found in data"}

    plt.figure(figsize=(10, 4))
    plt.plot(values, color=color, linewidth=1.5)
    plt.title(title)
    plt.xlabel("Step" if "step" not in key else "Round")
    plt.ylabel(key.replace("_", " ").title())
    plt.grid(True, alpha=0.3)

    final = values[-1]
    plt.axhline(y=final, color=color, linestyle="--", alpha=0.3)
    plt.text(len(values) - 1, final, f" {final:.3f}", va="center", fontsize=9)

    plt.tight_layout()
    fig = plt.gcf()
    plt.savefig(output_path, dpi=80, bbox_inches="tight")
    plt.close(fig)

    return {"status": "ok", "output": os.path.abspath(output_path), "type": key, "final_value": final}


def _viz_energy(data, output_path, plt):
    if "agents" in data:
        energies = [a.get("energy", 0) for a in data["agents"]]
        fig = plt.figure(figsize=(8, 4))
        plt.hist(energies, bins=20, edgecolor="black", alpha=0.7)
        plt.title("Agent Energy Distribution")
        plt.xlabel("Energy")
        plt.ylabel("Count")
        plt.grid(True, alpha=0.3, axis="y")
        plt.tight_layout()
        plt.savefig(output_path, dpi=80, bbox_inches="tight")
        plt.close(fig)
        return {"status": "ok", "output": os.path.abspath(output_path), "type": "energy"}
    return {"error": "No agent-level data available (use --type gini or hostility)"}


def _viz_beliefs(data, output_path, plt):
    if "agents" in data and data["agents"] and "beliefs" in data["agents"][0]:
        beliefs = {}
        for agent in data["agents"]:
            for k, v in agent.get("beliefs", {}).items():
                beliefs.setdefault(k, []).append(v)

        if beliefs:
            n = len(beliefs)
            fig, axes = plt.subplots(1, n, figsize=(4 * n, 4))
            if n == 1:
                axes = [axes]
            for ax, (name, values) in zip(axes, beliefs.items()):
                ax.hist(values, bins=15, edgecolor="black", alpha=0.7)
                ax.set_title(name.replace("_", " ").title())
                ax.set_xlabel("Value")
                ax.set_ylabel("Count")
            plt.tight_layout()
            plt.savefig(output_path, dpi=80, bbox_inches="tight")
            plt.close(fig)
            return {"status": "ok", "output": os.path.abspath(output_path), "type": "beliefs"}
    return {"error": "No belief data available"}
