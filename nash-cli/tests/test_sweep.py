"""Sweep command tests — parameter scanning and error handling."""

import json
import pytest
from argparse import Namespace
from unittest.mock import patch

from scripts.nash_cli.commands.sweep import cmd_sweep, _set_nested


def _write_hawk_dove_config(tmp_path):
    """Write a hawk_dove config file and return its path."""
    config = {
        "environment": {
            "type": "hawk_dove",
            "nobel_reference": {"year": 2005, "laureates": [], "contribution": ""},
        },
        "parameters": {
            "num_agents": {"value": 20},
            "resource_value": {"value": 4.0},
            "conflict_cost": {"value": 6.0},
            "num_rounds": {"value": 50},
        },
        "validation": {
            "equilibrium_type": "ess",
            "metrics": [],
        },
    }
    path = tmp_path / "hawk_dove_config.json"
    path.write_text(json.dumps(config), encoding="utf-8")
    return str(path)


def test_sweep_basic(tmp_path):
    """Sweep should run multiple configs and return results."""
    config_path = _write_hawk_dove_config(tmp_path)
    args = Namespace(config=config_path, param="resource_value",
                     range="2,6", step=2.0, rounds=10, seed=42, output=None)
    result = cmd_sweep(args)

    assert result["status"] == "completed"
    assert result["summary"]["total"] == 3
    assert result["summary"]["completed"] == 3
    assert len(result["results"]) == 3


def test_sweep_param_name_in_results(tmp_path):
    """Each sweep result should include the parameter name."""
    config_path = _write_hawk_dove_config(tmp_path)
    args = Namespace(config=config_path, param="resource_value",
                     range="2,6", step=2.0, rounds=10, seed=42, output=None)
    result = cmd_sweep(args)

    for item in result["results"]:
        assert item["parameter"] == "resource_value"
        assert "param_value" in item
        assert "final_metrics" in item


def test_sweep_param_values(tmp_path):
    """Sweep should produce correct parameter values."""
    config_path = _write_hawk_dove_config(tmp_path)
    args = Namespace(config=config_path, param="resource_value",
                     range="1,5", step=1.0, rounds=10, seed=42, output=None)
    result = cmd_sweep(args)

    values = [r["param_value"] for r in result["results"]]
    assert values == [1.0, 2.0, 3.0, 4.0, 5.0]


def test_sweep_convergence_info(tmp_path):
    """Each sweep result should include convergence info."""
    config_path = _write_hawk_dove_config(tmp_path)
    args = Namespace(config=config_path, param="resource_value",
                     range="4,8", step=2.0, rounds=50, seed=42, output=None)
    result = cmd_sweep(args)

    for item in result["results"]:
        assert "converged" in item
        assert "total_rounds" in item
        assert isinstance(item["converged"], bool)


def test_sweep_invalid_range_format(tmp_path):
    """Sweep with bad range format should return error."""
    config_path = _write_hawk_dove_config(tmp_path)
    args = Namespace(config=config_path, param="resource_value",
                     range="bad", step=1.0, rounds=10, seed=42, output=None)
    result = cmd_sweep(args)
    assert "error" in result


def test_sweep_empty_range(tmp_path):
    """Sweep where min > max should return error."""
    config_path = _write_hawk_dove_config(tmp_path)
    args = Namespace(config=config_path, param="resource_value",
                     range="10,1", step=1.0, rounds=10, seed=42, output=None)
    result = cmd_sweep(args)
    assert "error" in result


def test_sweep_too_many_steps(tmp_path):
    """Sweep exceeding 100 steps should return error."""
    config_path = _write_hawk_dove_config(tmp_path)
    args = Namespace(config=config_path, param="resource_value",
                     range="1,1000", step=0.01, rounds=10, seed=42, output=None)
    result = cmd_sweep(args)
    assert "error" in result
    assert "Too many" in result["error"]


def test_sweep_unknown_env_type(tmp_path):
    """Sweep with unknown environment type should return error."""
    config = {"environment": {"type": "nonexistent_game"}, "parameters": {}}
    path = tmp_path / "bad_config.json"
    path.write_text(json.dumps(config), encoding="utf-8")

    args = Namespace(config=str(path), param="x",
                     range="1,5", step=1.0, rounds=10, seed=42, output=None)
    result = cmd_sweep(args)
    assert "error" in result
    assert "nonexistent_game" in result["error"]


def test_sweep_missing_config_file():
    """Sweep with nonexistent config file should raise."""
    args = Namespace(config="/nonexistent/path.json", param="x",
                     range="1,5", step=1.0, rounds=10, seed=42, output=None)
    with pytest.raises(FileNotFoundError):
        cmd_sweep(args)


def test_set_nested_simple():
    """_set_nested should set top-level keys."""
    d = {}
    _set_nested(d, "key", 42)
    assert d["key"] == 42


def test_set_nested_dotted():
    """_set_nested should handle dotted paths."""
    d = {"parameters": {"resource_value": {"value": 4.0}}}
    _set_nested(d, "parameters.resource_value.value", 8.0)
    assert d["parameters"]["resource_value"]["value"] == 8.0


def test_set_nested_creates_intermediate():
    """_set_nested should create intermediate dicts."""
    d = {}
    _set_nested(d, "a.b.c", 99)
    assert d["a"]["b"]["c"] == 99
