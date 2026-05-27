#!/usr/bin/env python3
"""nash run — Execute game theory simulations via preset environments."""

import json
import random
import sys
import importlib
import inspect

import numpy as np


def cmd_run(args) -> dict:
    if args.seed is not None:
        random.seed(args.seed)
        np.random.seed(args.seed)

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

    module_name = _CREATOR_MODULES.get(args.preset)
    func_name = _CREATOR_FUNCTIONS.get(args.preset)

    if not module_name or not func_name:
        return {"error": f"Unknown preset: {args.preset}",
                "available": list(_CREATOR_MODULES.keys())}

    try:
        mod = importlib.import_module(module_name)
        creator = getattr(mod, func_name)
    except (ImportError, AttributeError) as e:
        return {"error": f"Failed to load preset '{args.preset}': {e}"}

    # Adapt CLI args to creator's actual parameters
    sig = inspect.signature(creator)
    creator_kwargs = {}
    for param_name in sig.parameters:
        if param_name in ("num_agents", "num_bidders"):
            creator_kwargs[param_name] = args.agents
        elif param_name == "num_men":
            creator_kwargs[param_name] = max(1, args.agents // 2)
        elif param_name == "num_women":
            creator_kwargs[param_name] = max(1, args.agents // 2)
        elif param_name == "num_rounds":
            creator_kwargs[param_name] = args.rounds

    print(f"[nash] Creating environment: {args.preset}", file=sys.stderr)
    env, config = creator(**creator_kwargs)

    print(f"[nash] Running {args.rounds} rounds...", file=sys.stderr)
    result = env.run_simulation(max_rounds=args.rounds)

    print(f"[nash] Converged: {result['converged']}", file=sys.stderr)

    return {
        "status": "completed",
        "environment": args.preset,
        "total_rounds": result["total_rounds"],
        "converged": result["converged"],
        "convergence_message": result["convergence_message"],
        "final_metrics": result["final_metrics"],
        "history": result["history"],
        "config": config,
    }