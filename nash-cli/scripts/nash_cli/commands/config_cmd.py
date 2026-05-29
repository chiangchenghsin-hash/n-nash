#!/usr/bin/env python3
"""nash config — Generate environment preset config templates."""

import json
import sys

from scripts.nash_cli.commands import get_environment_spec, list_presets, resolve_environment_id


def cmd_config(args) -> dict:
    if args.config_action == "template":
        return _cmd_template(args)
    elif args.config_action == "validate":
        return _cmd_validate(args)
    return {"error": f"Unknown config action: {args.config_action}"}


def _cmd_template(args) -> dict:
    preset_name = args.preset or "hawk_dove"
    spec = get_environment_spec(preset_name)
    if not spec:
        return {"error": f"Unknown preset: {preset_name}", "available_presets": list_presets()}

    if not args.output:
        print(f"[nash config] Preset: {spec.short_id} ({spec.env_id})", file=sys.stderr)

    return spec.default_config


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

    resolved = resolve_environment_id(env_type)
    if not resolved:
        return {
            "valid": False,
            "error": f"Unknown environment type: {env_type}",
            "file": filepath,
            "available_presets": list_presets(),
        }
    if not isinstance(params, dict):
        return {"valid": False, "error": "parameters must be a dict", "file": filepath}

    return {
        "valid": True,
        "file": filepath,
        "environment": env_type,
        "resolved_environment_type": resolved,
        "params_count": len(params),
    }
