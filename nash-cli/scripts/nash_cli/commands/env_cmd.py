#!/usr/bin/env python3
"""nash env — List and inspect game theory environments."""

from scripts.nash_cli.commands import get_environment_registry, get_environment_spec, list_presets


def cmd_env(args) -> dict:
    if args.env_action == "list":
        return _list_environments(args)
    elif args.env_action == "info":
        return _info_environment(args)
    return {"error": f"Unknown env action: {args.env_action}"}

def _list_environments(args) -> dict:
    registry = get_environment_registry()
    envs = []
    for env_id, spec in sorted(registry.items(), key=lambda kv: kv[0]):
        cfg = spec.default_config
        nobel = cfg.get("environment", {}).get("nobel_reference", {})
        validation = cfg.get("validation", {})
        envs.append(
            {
                "id": env_id,
                "short_id": spec.short_id,
                "module": spec.module_name,
                "creator": spec.creator_name,
                "nobel_year": nobel.get("year"),
                "equilibrium": validation.get("equilibrium_type"),
            }
        )
    return {"environments": envs, "count": len(envs)}


def _info_environment(args) -> dict:
    spec = get_environment_spec(args.name)
    if not spec:
        return {"error": f"Unknown environment: {args.name}", "available_presets": list_presets()}

    cfg = spec.default_config
    env_meta = cfg.get("environment", {})
    validation = cfg.get("validation", {})
    params = cfg.get("parameters", {})

    return {
        "id": spec.env_id,
        "short_id": spec.short_id,
        "module": spec.module_name,
        "creator": spec.creator_name,
        "nobel_reference": env_meta.get("nobel_reference", {}),
        "equilibrium_type": validation.get("equilibrium_type"),
        "metrics": validation.get("metrics", []),
        "parameters": sorted(params.keys()) if isinstance(params, dict) else [],
        "config_template": cfg,
    }
