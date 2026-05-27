#!/usr/bin/env python3
"""nash sweep — Parameter sweeping across environment presets."""

import json
import sys
import os
import copy
import importlib
import inspect
import random

import numpy as np


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
            run_result = _run_environment_config(cfg, args.rounds)
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


def _run_environment_config(config: dict, rounds: int) -> dict:
    _CREATOR_MODULES = {
        "hawk_dove": "src.environments.hawk_dove",
        "prisoners_dilemma": "src.environments.repeated_prisoners_dilemma",
        "public_goods": "src.environments.public_goods",
        "common_pool": "src.environments.common_pool_resource",
        "vickrey": "src.environments.vickrey_auction",
        "spence": "src.environments.spence_signaling",
        "matching": "src.environments.two_sided_matching",
        "auction_common_value": "src.environments.auction_common_value",
    }

    _CREATOR_FUNCTIONS = {
        "hawk_dove": "create_hawk_dove",
        "prisoners_dilemma": "create_repeated_prisoners_dilemma",
        "public_goods": "create_public_goods",
        "common_pool": "create_common_pool_resource",
        "vickrey": "create_vickrey_auction",
        "spence": "create_spence_signaling",
        "matching": "create_two_sided_matching",
        "auction_common_value": "create_auction_common_value",
    }

    env_type = config.get("environment", {}).get("type", "")
    module_name = _CREATOR_MODULES.get(env_type)
    func_name = _CREATOR_FUNCTIONS.get(env_type)

    if not module_name or not func_name:
        raise ValueError(f"Unknown environment type: {env_type}")

    mod = importlib.import_module(module_name)
    creator = getattr(mod, func_name)

    sig = inspect.signature(creator)
    creator_kwargs = {}
    for param_name in sig.parameters:
        if param_name in ("num_agents", "num_bidders"):
            val = config.get("parameters", {}).get("num_agents", {})
            creator_kwargs[param_name] = val.get("value", 100) if isinstance(val, dict) else val
        elif param_name == "num_men":
            val = config.get("parameters", {}).get("num_agents", {})
            n = val.get("value", 50) if isinstance(val, dict) else val
            creator_kwargs[param_name] = max(1, n // 2)
        elif param_name == "num_women":
            val = config.get("parameters", {}).get("num_agents", {})
            n = val.get("value", 50) if isinstance(val, dict) else val
            creator_kwargs[param_name] = max(1, n // 2)
        elif param_name == "num_rounds":
            creator_kwargs[param_name] = rounds
        elif param_name in ("resource_value", "conflict_cost", "learning_rate",
                           "discount_factor", "exploration_rate", "multiplier",
                           "regeneration_rate", "initial_resource"):
            param_val = config.get("parameters", {}).get(param_name, {})
            creator_kwargs[param_name] = param_val.get("value", 1.0) if isinstance(param_val, dict) else param_val

    env, _ = creator(**creator_kwargs)
    result = env.run_simulation(max_rounds=rounds)
    return result