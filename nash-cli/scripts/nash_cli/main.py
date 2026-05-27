#!/usr/bin/env python3
"""
NASH CLI — Game theory simulation toolkit powered by Nobel prize-winning models.

Usage:
  uv run nash run --preset hawk_dove --rounds 200
  uv run nash env list
  uv run nash validate --data results.json
  uv run nash sweep --config env_config.json --param resource_value --range 1,10 --step 1
  uv run nash viz --data results.json --type all
  uv run nash config template --preset hawk_dove -o config.json

All commands output JSON to stdout, human-readable progress to stderr.
"""

import argparse
import json
import sys
import os

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")

_project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if _project_root not in sys.path:
    sys.path.insert(0, _project_root)


def main():
    parser = argparse.ArgumentParser(
        prog="nash",
        description="NASH CLI — Game theory simulation & validation toolkit"
    )
    sub = parser.add_subparsers(dest="command", required=True)

    # -- run --
    p_run = sub.add_parser("run", help="Run a game theory simulation")
    p_run.add_argument("--preset", type=str, required=True,
                       choices=["hawk_dove", "prisoners_dilemma", "public_goods",
                                "common_pool", "vickrey", "spence", "matching",
                                "auction_common_value"],
                       help="Game environment preset")
    p_run.add_argument("--agents", type=int, default=100, help="Number of agents")
    p_run.add_argument("--rounds", type=int, default=100, help="Simulation rounds")
    p_run.add_argument("--output", "-o", type=str, help="Output JSON file path")
    p_run.add_argument("--seed", type=int, help="Random seed for reproducibility")

    # -- env --
    p_env = sub.add_parser("env", help="Game environment management")
    p_env_sub = p_env.add_subparsers(dest="env_action", required=True)
    p_env_list = p_env_sub.add_parser("list", help="List available environments")
    p_env_list.add_argument("--format", type=str, choices=["json", "table"], default="json")
    p_env_info = p_env_sub.add_parser("info", help="Show environment details")
    p_env_info.add_argument("name", type=str, help="Environment name")
    p_env_info.add_argument("--format", type=str, choices=["json", "text"], default="json")

    # -- validate --
    p_val = sub.add_parser("validate", help="Statistical & Nobel validation")
    p_val.add_argument("--data", type=str, required=True, help="Path to simulation results JSON")
    p_val.add_argument("--type", type=str, choices=["statistical", "nobel", "both"], default="both")
    p_val.add_argument("--baseline-gini", type=float, default=0.3)
    p_val.add_argument("--baseline-hostility", type=float, default=0.4)
    p_val.add_argument("--output", "-o", type=str, help="Output JSON file path")

    # -- sweep --
    p_sweep = sub.add_parser("sweep", help="Parameter sweep across an environment")
    p_sweep.add_argument("--config", type=str, required=True, help="Environment config JSON (from 'nash config template')")
    p_sweep.add_argument("--param", type=str, required=True, help="Parameter path to sweep (e.g. resource_value or parameters.resource_value)")
    p_sweep.add_argument("--range", type=str, required=True, help="Range: MIN,MAX")
    p_sweep.add_argument("--step", type=float, required=True, help="Step size")
    p_sweep.add_argument("--rounds", type=int, default=100, help="Rounds per config")
    p_sweep.add_argument("--seed", type=int, help="Random seed")
    p_sweep.add_argument("--output", "-o", type=str, help="Output JSON file path")

    # -- viz --
    p_viz = sub.add_parser("viz", help="Generate matplotlib charts")
    p_viz.add_argument("--data", type=str, required=True, help="Path to simulation results JSON")
    p_viz.add_argument("--type", type=str, choices=["gini", "hostility", "energy", "beliefs", "all"],
                       default="all")
    p_viz.add_argument("--output", "-o", type=str, help="Output image path (PNG)")

    # -- config --
    p_cfg = sub.add_parser("config", help="Environment config helpers")
    p_cfg_sub = p_cfg.add_subparsers(dest="config_action", required=True)
    p_cfg_template = p_cfg_sub.add_parser("template", help="Generate environment config template")
    p_cfg_template.add_argument("--preset", type=str, required=True,
                                help="Environment preset name (hawk_dove, prisoners_dilemma, etc.)")
    p_cfg_template.add_argument("--output", "-o", type=str, help="Output file path")
    p_cfg_validate = p_cfg_sub.add_parser("validate", help="Validate an environment config file")
    p_cfg_validate.add_argument("file", type=str, help="Config JSON file to validate")

    try:
        args = parser.parse_args()
    except SystemExit:
        _error("invalid arguments: use --help for usage")
        return

    try:
        result = _dispatch(args)
        _output(result, args)
    except Exception as e:
        _error(str(e))


def _dispatch(args) -> dict:
    cmd = args.command

    if cmd == "run":
        from scripts.nash_cli.commands.run import cmd_run
        return cmd_run(args)
    elif cmd == "env":
        from scripts.nash_cli.commands.env_cmd import cmd_env
        return cmd_env(args)
    elif cmd == "validate":
        from scripts.nash_cli.commands.validate import cmd_validate
        return cmd_validate(args)
    elif cmd == "sweep":
        from scripts.nash_cli.commands.sweep import cmd_sweep
        return cmd_sweep(args)
    elif cmd == "viz":
        from scripts.nash_cli.commands.viz import cmd_viz
        return cmd_viz(args)
    elif cmd == "config":
        from scripts.nash_cli.commands.config_cmd import cmd_config
        return cmd_config(args)

    return {"error": f"Unknown command: {cmd}"}


def _output(result: dict, args):
    if args.command == "viz":
        if result and "error" not in result:
            print(json.dumps(result))
        else:
            print(json.dumps(result), file=sys.stderr)
        return

    out_path = getattr(args, "output", None)

    if out_path:
        with open(out_path, "w", encoding="utf-8") as f:
            json.dump(result, f, indent=2, ensure_ascii=False, default=str)
        print(json.dumps({"status": "ok", "output": os.path.abspath(out_path)}))
    else:
        print(json.dumps(result, indent=2, ensure_ascii=False, default=str))


def _error(msg: str):
    err = {"error": msg, "status": "failed"}
    print(json.dumps(err, indent=2), file=sys.stderr)
    sys.exit(1)


if __name__ == "__main__":
    main()