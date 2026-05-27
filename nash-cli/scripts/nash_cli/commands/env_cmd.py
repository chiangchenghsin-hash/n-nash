#!/usr/bin/env python3
"""nash env — List and inspect game theory environments."""

import json
import os
import sys


# Short ID → long key aliases, matching CLI --preset choices
_ALIASES = {
    "prisoners_dilemma": "repeated_prisoners_dilemma",
    "common_pool": "common_pool_resource",
    "vickrey": "vickrey_auction",
    "spence": "spence_signaling",
    "matching": "two_sided_matching",
}

# Reverse mapping for short_id display
_SHORT_IDS = {v: k for k, v in _ALIASES.items()}


def cmd_env(args) -> dict:
    if args.env_action == "list":
        return _list_environments(args)
    elif args.env_action == "info":
        return _info_environment(args)
    return {"error": f"Unknown env action: {args.env_action}"}


ENVIRONMENTS = {
    "hawk_dove": {
        "name": "Hawk-Dove Game",
        "nobel": {"year": 2005, "laureates": ["Robert Aumann", "Thomas Schelling"]},
        "equilibrium": "Evolutionarily Stable Strategy (ESS)",
        "description": "Agents choose hawk (fight) or dove (display). ESS ratio = V/C when V < C.",
        "parameters": ["num_agents", "resource_value", "conflict_cost", "num_rounds"],
        "key_metric": "hawk_ratio",
    },
    "repeated_prisoners_dilemma": {
        "name": "Repeated Prisoner's Dilemma",
        "nobel": {"year": 2005, "laureates": ["Robert Aumann", "Thomas Schelling"]},
        "equilibrium": "Subgame Perfect Nash Equilibrium (SPNE)",
        "description": "Iterated PD with tit-for-tat strategies. Cooperation emerges through repeated interaction.",
        "parameters": ["num_agents", "temptation", "reward", "punishment", "sucker", "num_rounds"],
        "key_metric": "cooperation_rate",
    },
    "public_goods": {
        "name": "Public Goods Game",
        "nobel": {"year": 2009, "laureates": ["Elinor Ostrom"]},
        "equilibrium": "Free-rider equilibrium (Nash = 0 contribution)",
        "description": "Agents contribute to a public good. Nash predicts zero contribution, but experiments show ~50%.",
        "parameters": ["num_agents", "endowment", "multiplier", "num_rounds"],
        "key_metric": "contribution_rate",
    },
    "common_pool_resource": {
        "name": "Common Pool Resource",
        "nobel": {"year": 2009, "laureates": ["Elinor Ostrom"]},
        "equilibrium": "Tragedy of the Commons (Nash = over-extraction)",
        "description": "Agents extract from a shared resource. Ostrom showed communities can self-govern.",
        "parameters": ["num_agents", "resource_size", "regeneration_rate", "num_rounds"],
        "key_metric": "sustainability_index",
    },
    "vickrey_auction": {
        "name": "Vickrey Auction",
        "nobel": {"year": 1996, "laureates": ["William Vickrey"]},
        "equilibrium": "Truthful bidding (dominant strategy)",
        "description": "Second-price sealed-bid auction. Dominant strategy is to bid true value.",
        "parameters": ["num_agents", "num_rounds"],
        "key_metric": "truthful_bidding_rate",
    },
    "spence_signaling": {
        "name": "Spence Signaling Game",
        "nobel": {"year": 2001, "laureates": ["George Akerlof", "Michael Spence", "Joseph Stiglitz"]},
        "equilibrium": "Separating equilibrium",
        "description": "High-type agents signal through costly education. Pooling vs separating equilibria.",
        "parameters": ["num_agents", "signal_cost_high", "signal_cost_low", "num_rounds"],
        "key_metric": "separation_index",
    },
    "two_sided_matching": {
        "name": "Two-Sided Matching",
        "nobel": {"year": 2012, "laureates": ["Alvin Roth", "Lloyd Shapley"]},
        "equilibrium": "Stable matching (deferred acceptance)",
        "description": "Gale-Shapley deferred acceptance algorithm for stable matching.",
        "parameters": ["num_agents", "num_rounds"],
        "key_metric": "stability_index",
    },
    "auction_common_value": {
        "name": "Common Value Auction",
        "nobel": {"year": 2020, "laureates": ["Paul Milgrom", "Robert Wilson"]},
        "equilibrium": "Winner's curse avoidance",
        "description": "Bidders face common but uncertain value. Winner's curse when overbidding.",
        "parameters": ["num_agents", "num_rounds"],
        "key_metric": "winners_curse_rate",
    },
}


def _list_environments(args) -> dict:
    envs = []
    for key, info in ENVIRONMENTS.items():
        envs.append({
            "id": key,
            "short_id": _SHORT_IDS.get(key, key),
            "name": info["name"],
            "nobel_year": info["nobel"]["year"],
            "equilibrium": info["equilibrium"],
        })
    return {"environments": envs, "count": len(envs)}


def _info_environment(args) -> dict:
    name = _ALIASES.get(args.name, args.name)
    info = ENVIRONMENTS.get(name)
    if not info:
        return {"error": f"Unknown environment: {args.name}", "available": list(ENVIRONMENTS.keys())}
    return {"id": name, "short_id": _SHORT_IDS.get(name, name), **info}
