"""Error handling and edge case tests."""

import json
import pytest
import numpy as np
from argparse import Namespace

from scripts.nash_cli.commands.run import cmd_run
from scripts.nash_cli.commands.env_cmd import cmd_env
from scripts.nash_cli.commands.sweep import cmd_sweep
from scripts.nash_cli.commands.config_cmd import cmd_config


def test_run_unknown_preset():
    """Run with unknown preset should return error, not crash."""
    args = Namespace(command="run", preset="nonexistent", agents=10,
                     rounds=5, output=None, seed=42)
    result = cmd_run(args)

    assert "error" in result
    assert "nonexistent" in result["error"]
    assert "available_presets" in result


def test_env_info_unknown():
    """Env info with unknown name should return error."""
    args = Namespace(env_action="info", name="nonexistent", format="json")
    result = cmd_env(args)

    assert "error" in result
    assert "available_presets" in result


def test_env_unknown_action():
    """Env with unknown action should return error."""
    args = Namespace(env_action="delete", format="json")
    result = cmd_env(args)

    assert "error" in result


def test_run_reproducibility():
    """Same seed should produce identical results."""
    args1 = Namespace(command="run", preset="hawk_dove", agents=20,
                      rounds=50, output=None, seed=12345)
    args2 = Namespace(command="run", preset="hawk_dove", agents=20,
                      rounds=50, output=None, seed=12345)

    result1 = cmd_run(args1)
    result2 = cmd_run(args2)

    assert result1["final_metrics"] == result2["final_metrics"]
    assert result1["total_rounds"] == result2["total_rounds"]


def test_run_different_seeds_differ():
    """Different seeds should produce different results."""
    args1 = Namespace(command="run", preset="hawk_dove", agents=50,
                      rounds=50, output=None, seed=1)
    args2 = Namespace(command="run", preset="hawk_dove", agents=50,
                      rounds=50, output=None, seed=999)

    result1 = cmd_run(args1)
    result2 = cmd_run(args2)

    metrics1 = result1["final_metrics"]
    metrics2 = result2["final_metrics"]
    assert metrics1 != metrics2


def test_run_no_seed_works():
    """Run without seed should still work."""
    args = Namespace(command="run", preset="hawk_dove", agents=20,
                     rounds=10, output=None, seed=None)
    result = cmd_run(args)
    assert result["status"] == "completed"


def test_config_validate_empty_json(tmp_path):
    """Config validate with empty JSON object."""
    path = tmp_path / "empty.json"
    path.write_text("{}", encoding="utf-8")

    args = Namespace(config_action="validate", file=str(path))
    result = cmd_config(args)
    assert result["valid"] is False


def test_config_validate_all_known_envs(tmp_path):
    """Config validate should accept all known environment types."""
    from scripts.nash_cli.commands import get_environment_registry
    registry = get_environment_registry()

    for env_id in registry:
        config = {
            "environment": {"type": env_id},
            "parameters": {},
        }
        path = tmp_path / f"config_{env_id}.json"
        path.write_text(json.dumps(config), encoding="utf-8")

        args = Namespace(config_action="validate", file=str(path))
        result = cmd_config(args)
        assert result["valid"] is True, f"Failed for {env_id}: {result}"


def test_sweep_with_seed(tmp_path):
    """Sweep with seed should be reproducible."""
    config = {
        "environment": {"type": "hawk_dove"},
        "parameters": {
            "num_agents": {"value": 20},
            "resource_value": {"value": 4.0},
            "conflict_cost": {"value": 6.0},
            "num_rounds": {"value": 20},
        },
        "validation": {"equilibrium_type": "ess", "metrics": []},
    }
    path = tmp_path / "config.json"
    path.write_text(json.dumps(config), encoding="utf-8")

    args1 = Namespace(config=str(path), param="resource_value",
                      range="2,6", step=2.0, rounds=20, seed=42, output=None)
    args2 = Namespace(config=str(path), param="resource_value",
                      range="2,6", step=2.0, rounds=20, seed=42, output=None)

    r1 = cmd_sweep(args1)
    r2 = cmd_sweep(args2)

    m1 = [x["final_metrics"] for x in r1["results"]]
    m2 = [x["final_metrics"] for x in r2["results"]]
    assert m1 == m2


def test_environment_small_agent_count():
    """Environments should handle very small agent counts."""
    args = Namespace(command="run", preset="hawk_dove", agents=2,
                     rounds=10, output=None, seed=42)
    result = cmd_run(args)
    assert result["status"] == "completed"


def test_environment_single_round():
    """Environments should handle single-round simulations."""
    args = Namespace(command="run", preset="hawk_dove", agents=20,
                     rounds=1, output=None, seed=42)
    result = cmd_run(args)
    assert result["status"] == "completed"
    assert result["total_rounds"] >= 1
