#!/usr/bin/env python3
"""nash run — Execute game theory simulations via preset environments."""

import json
import random
import sys

import numpy as np

from scripts.nash_cli.commands import (
    build_run_config,
    get_environment_spec,
    list_presets,
    validate_params,
)


def cmd_run(args) -> dict:
    extra_params = _parse_extra_params(args)

    spec = get_environment_spec(args.preset)
    if not spec:
        return {
            "error": f"Unknown preset: {args.preset}",
            "available_presets": list_presets(),
        }

    seeds = _parse_seeds(args)
    if seeds:
        return _run_multi_seed(spec, args, extra_params, seeds)
    return _run_single(spec, args, extra_params)


# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------

def _parse_extra_params(args):
    raw = getattr(args, "params", None)
    if not raw:
        return {}
    try:
        params = json.loads(raw)
    except json.JSONDecodeError as exc:
        print(f"[nash] Invalid --params JSON: {exc}", file=sys.stderr)
        sys.exit(1)
    try:
        return validate_params(args.preset, params)
    except ValueError as exc:
        print(f"[nash] {exc}", file=sys.stderr)
        sys.exit(1)


def _parse_seeds(args):
    raw = getattr(args, "seeds", None)
    if not raw:
        return []
    try:
        return [int(s.strip()) for s in raw.split(",") if s.strip()]
    except ValueError as exc:
        print(f"[nash] Invalid --seeds value: {exc}", file=sys.stderr)
        sys.exit(1)


def _make_input_params(extra_params: dict, args) -> dict:
    """Build the input_params echo block (requirement 4)."""
    ip = dict(extra_params)
    if args.seed is not None:
        ip["seed"] = args.seed
    ip["rounds"] = args.rounds
    return ip


def _run_single(spec, args, extra_params: dict) -> dict:
    if args.seed is not None:
        random.seed(args.seed)
        np.random.seed(args.seed)

    print(f"[nash] Creating environment: {spec.short_id} ({spec.env_id})", file=sys.stderr)
    run_config = build_run_config(spec, agents=args.agents, rounds=args.rounds,
                                  extra_params=extra_params)
    env = spec.env_class(run_config)

    print(f"[nash] Running {args.rounds} rounds...", file=sys.stderr)
    result = env.run_simulation(max_rounds=args.rounds)
    print(f"[nash] Converged: {result['converged']}", file=sys.stderr)

    return {
        "status": "completed",
        "preset": spec.short_id,
        "environment": spec.short_id,
        "environment_type": spec.env_id,
        "input_params": _make_input_params(extra_params, args),
        "total_rounds": result["total_rounds"],
        "converged": result["converged"],
        "convergence_message": result["convergence_message"],
        "final_metrics": result["final_metrics"],
        "history": result["history"],
        "config": run_config,
    }


def _run_multi_seed(spec, args, extra_params: dict, seeds: list) -> dict:
    per_seed_results = []

    for seed in seeds:
        random.seed(seed)
        np.random.seed(seed)

        run_config = build_run_config(spec, agents=args.agents, rounds=args.rounds,
                                      extra_params=extra_params)
        env = spec.env_class(run_config)
        result = env.run_simulation(max_rounds=args.rounds)

        per_seed_results.append({
            "seed": seed,
            "converged": result["converged"],
            "total_rounds": result["total_rounds"],
            "final_metrics": result["final_metrics"],
        })

    aggregated_metrics = _aggregate_metrics(per_seed_results)

    return {
        "status": "completed",
        "preset": spec.short_id,
        "environment": spec.short_id,
        "environment_type": spec.env_id,
        "seeds": seeds,
        "input_params": {**extra_params, "seeds": seeds, "rounds": args.rounds},
        "aggregated_metrics": aggregated_metrics,
        "per_seed_results": per_seed_results,
        "config": build_run_config(spec, agents=args.agents, rounds=args.rounds,
                                   extra_params=extra_params),
    }


def _aggregate_metrics(per_seed_results: list) -> dict:
    if not per_seed_results:
        return {}

    all_metric_keys: set = set()
    for r in per_seed_results:
        all_metric_keys.update(r["final_metrics"].keys())

    aggregated = {}
    for key in sorted(all_metric_keys):
        values = [
            r["final_metrics"][key]
            for r in per_seed_results
            if key in r["final_metrics"]
        ]
        if not values:
            continue
        arr = np.array(values, dtype=float)
        aggregated[key] = {
            "mean": float(np.mean(arr)),
            "std": float(np.std(arr)),
            "min": float(np.min(arr)),
            "max": float(np.max(arr)),
        }
    return aggregated
