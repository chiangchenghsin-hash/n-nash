#!/usr/bin/env python3
"""nash config — Generate environment preset config templates."""

import json
import sys

ENV_PARAMETERS = {
    "hawk_dove": {
        "num_agents": {"value": 100, "description": "Number of agents"},
        "resource_value": {"value": 4.0, "description": "Resource value V"},
        "conflict_cost": {"value": 6.0, "description": "Conflict cost C"},
        "num_rounds": {"value": 200, "description": "Simulation rounds"},
    },
    "prisoners_dilemma": {
        "num_agents": {"value": 100, "description": "Number of agents"},
        "learning_rate": {"value": 0.1, "description": "Strategy learning rate"},
        "discount_factor": {"value": 0.95, "description": "Future reward discount"},
        "exploration_rate": {"value": 0.1, "description": "Random exploration probability"},
        "num_rounds": {"value": 200, "description": "Simulation rounds"},
    },
    "public_goods": {
        "num_agents": {"value": 100, "description": "Number of agents"},
        "multiplier": {"value": 1.6, "description": "Public goods multiplier"},
        "initial_resource": {"value": 100.0, "description": "Initial resource per agent"},
        "num_rounds": {"value": 200, "description": "Simulation rounds"},
    },
    "common_pool": {
        "num_agents": {"value": 100, "description": "Number of agents"},
        "initial_resource": {"value": 1000.0, "description": "Initial common pool size"},
        "regeneration_rate": {"value": 0.05, "description": "Resource regeneration rate"},
        "num_rounds": {"value": 200, "description": "Simulation rounds"},
    },
    "vickrey": {
        "num_bidders": {"value": 20, "description": "Number of bidders"},
        "num_rounds": {"value": 100, "description": "Auction rounds"},
    },
    "spence": {
        "num_agents": {"value": 50, "description": "Number of agents"},
        "num_rounds": {"value": 100, "description": "Simulation rounds"},
    },
    "matching": {
        "num_men": {"value": 25, "description": "Number of men"},
        "num_women": {"value": 25, "description": "Number of women"},
        "num_rounds": {"value": 100, "description": "Simulation rounds"},
    },
    "auction_common_value": {
        "num_bidders": {"value": 20, "description": "Number of bidders"},
        "num_rounds": {"value": 100, "description": "Auction rounds"},
    },
}

NOBEL_REFS = {
    "hawk_dove": {"year": 2005, "laureates": ["Robert Aumann", "Thomas Schelling"]},
    "prisoners_dilemma": {"year": 2005, "laureates": ["Robert Aumann", "Thomas Schelling"]},
    "public_goods": {"year": 2009, "laureates": ["Elinor Ostrom"]},
    "common_pool": {"year": 2009, "laureates": ["Elinor Ostrom"]},
    "vickrey": {"year": 1996, "laureates": ["William Vickrey"]},
    "spence": {"year": 2001, "laureates": ["George Akerlof", "Michael Spence", "Joseph Stiglitz"]},
    "matching": {"year": 2012, "laureates": ["Alvin Roth", "Lloyd Shapley"]},
    "auction_common_value": {"year": 2020, "laureates": ["Paul Milgrom", "Robert Wilson"]},
}


def cmd_config(args) -> dict:
    if args.config_action == "template":
        return _cmd_template(args)
    elif args.config_action == "validate":
        return _cmd_validate(args)
    return {"error": f"Unknown config action: {args.config_action}"}


def _cmd_template(args) -> dict:
    preset_name = args.preset or "hawk_dove"

    if preset_name not in ENV_PARAMETERS:
        return {"error": f"Unknown preset: {preset_name}",
                "available": list(ENV_PARAMETERS.keys())}

    nobel = NOBEL_REFS.get(preset_name, {})
    template = {
        "environment": {
            "type": preset_name,
            "nobel_reference": nobel,
        },
        "parameters": ENV_PARAMETERS[preset_name],
    }

    if not args.output:
        print(f"[nash config] Preset: {preset_name}", file=sys.stderr)

    return template


def _cmd_validate(args) -> dict:
    filepath = args.file
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            data = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError) as e:
        return {"valid": False, "error": str(e), "file": filepath}

    env_type = data.get("environment", {}).get("type", "")
    params = data.get("parameters", {})

    if not env_type:
        return {"valid": False, "error": "Missing environment.type in config", "file": filepath}
    if env_type not in ENV_PARAMETERS:
        return {"valid": False, "error": f"Unknown environment type: {env_type}",
                "file": filepath, "available": list(ENV_PARAMETERS.keys())}
    if not isinstance(params, dict):
        return {"valid": False, "error": "parameters must be a dict", "file": filepath}

    return {"valid": True, "file": filepath, "environment": env_type,
            "params_count": len(params)}