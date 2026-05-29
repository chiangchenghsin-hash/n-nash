#!/usr/bin/env python3
"""nash run — Execute game theory simulations via preset environments."""

import random
import sys

import numpy as np

from scripts.nash_cli.commands import build_run_config, get_environment_spec, list_presets


def cmd_run(args) -> dict:
    if args.seed is not None:
        random.seed(args.seed)
        np.random.seed(args.seed)

    spec = get_environment_spec(args.preset)
    if not spec:
        registry_presets = list_presets()
        return {
            "error": f"Unknown preset: {args.preset}",
            "available_presets": registry_presets,
        }

    print(f"[nash] Creating environment: {spec.short_id} ({spec.env_id})", file=sys.stderr)
    run_config = build_run_config(spec, agents=args.agents, rounds=args.rounds)
    env = spec.env_class(run_config)

    print(f"[nash] Running {args.rounds} rounds...", file=sys.stderr)
    result = env.run_simulation(max_rounds=args.rounds)

    print(f"[nash] Converged: {result['converged']}", file=sys.stderr)

    return {
        "status": "completed",
        "environment": spec.short_id,
        "environment_type": spec.env_id,
        "total_rounds": result["total_rounds"],
        "converged": result["converged"],
        "convergence_message": result["convergence_message"],
        "final_metrics": result["final_metrics"],
        "history": result["history"],
        "config": run_config,
    }
