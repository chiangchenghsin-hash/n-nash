#!/usr/bin/env python3
"""nash sweep — Parameter sweeping across environment presets."""

import json
import sys
import copy
import random

import numpy as np

from scripts.nash_cli.commands import get_environment_spec, list_presets


def cmd_sweep(args) -> dict:
    with open(args.config, "r", encoding="utf-8") as f:
        base_config = json.load(f)

    range_parts = args.range.split(",")
    if len(range_parts) != 2:
        return {"error": "Range format: MIN,MAX (e.g. 50,200)"}
    p_min, p_max = float(range_parts[0]), float(range_parts[1])
    p_step = args.step

    num_steps = int((p_max - p_min) / p_step) + 1
    if num_steps <= 0:
        return {"error": f"Empty range: min={p_min}, max={p_max}, step={p_step}"}
    if num_steps > 100:
        return {"error": f"Too many configs ({num_steps}). Limit sweep to 100 steps max."}

    param_values = [p_min + i * p_step for i in range(num_steps)]

    env_type = base_config.get("environment", {}).get("type", "")
    spec = get_environment_spec(env_type) if env_type else None
    if not spec:
        return {
            "error": f"Unknown environment type in config: {env_type}",
            "available_presets": list_presets(),
        }

    print(f"[nash sweep] {len(param_values)} configs for '{args.param}' in {env_type}: "
          f"{param_values[0]:.2f} -> {param_values[-1]:.2f} (step={p_step})", file=sys.stderr)

    if args.seed is not None:
        random.seed(args.seed)
        np.random.seed(args.seed)

    results = []
    errors = []

    for i, value in enumerate(param_values):
        cfg = copy.deepcopy(base_config)
        _set_nested(cfg, args.param, value)

        print(f"  [{i+1}/{len(param_values)}] {args.param}={value}", file=sys.stderr)

        try:
            run_result = _run_environment_config(spec, cfg, args.rounds)
            final_metrics = run_result.get("final_metrics", {})
            results.append({
                "index": i,
                "param_value": value,
                "final_metrics": final_metrics,
                "converged": run_result.get("converged", False),
                "total_rounds": run_result.get("total_rounds", 0),
            })
        except Exception as e:
            errors.append({"index": i, "param_value": value, "error": str(e)})
            print(f"    ERROR: {e}", file=sys.stderr)

    summary = {
        "parameter": args.param,
        "range": [p_min, p_max],
        "step": p_step,
        "total": len(param_values),
        "completed": len(results),
        "errors": len(errors),
    }

    return {
        "status": "completed" if not errors else "partial",
        "summary": summary,
        "results": results,
        "errors": errors,
    }


def _set_nested(d: dict, key: str, value):
    parts = key.split(".")
    for part in parts[:-1]:
        d = d.setdefault(part, {})
    d[parts[-1]] = value


def _run_environment_config(spec, config: dict, rounds: int) -> dict:
    env = spec.env_class(config)
    return env.run_simulation(max_rounds=rounds)
