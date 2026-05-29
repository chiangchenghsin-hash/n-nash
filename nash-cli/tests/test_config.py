"""Config command tests — template generation and config validation."""

import json
import pytest
from argparse import Namespace

from scripts.nash_cli.commands.config_cmd import cmd_config


def test_config_template_hawk_dove():
    """Config template for hawk_dove should return valid config."""
    args = Namespace(config_action="template", preset="hawk_dove", output=None)
    result = cmd_config(args)

    assert result["environment"]["type"] == "hawk_dove"
    assert "parameters" in result
    assert "num_agents" in result["parameters"]
    assert "resource_value" in result["parameters"]


def test_config_template_all_presets():
    """Config template should work for all presets."""
    from scripts.nash_cli.commands import list_presets
    for preset in list_presets():
        args = Namespace(config_action="template", preset=preset, output=None)
        result = cmd_config(args)
        assert "environment" in result
        assert "parameters" in result


def test_config_template_unknown_preset():
    """Config template with unknown preset should return error."""
    args = Namespace(config_action="template", preset="nonexistent", output=None)
    result = cmd_config(args)
    assert "error" in result


def test_config_validate_valid(tmp_path):
    """Config validate should accept valid config files."""
    config = {
        "environment": {"type": "hawk_dove"},
        "parameters": {"num_agents": {"value": 50}},
    }
    path = tmp_path / "valid_config.json"
    path.write_text(json.dumps(config), encoding="utf-8")

    args = Namespace(config_action="validate", file=str(path))
    result = cmd_config(args)

    assert result["valid"] is True
    assert result["environment"] == "hawk_dove"


def test_config_validate_unknown_env(tmp_path):
    """Config validate should reject unknown environment types."""
    config = {
        "environment": {"type": "nonexistent_game"},
        "parameters": {},
    }
    path = tmp_path / "bad_env.json"
    path.write_text(json.dumps(config), encoding="utf-8")

    args = Namespace(config_action="validate", file=str(path))
    result = cmd_config(args)

    assert result["valid"] is False
    assert "nonexistent_game" in result["error"]


def test_config_validate_missing_env_type(tmp_path):
    """Config validate should reject configs without environment.type."""
    config = {"parameters": {"num_agents": {"value": 50}}}
    path = tmp_path / "no_type.json"
    path.write_text(json.dumps(config), encoding="utf-8")

    args = Namespace(config_action="validate", file=str(path))
    result = cmd_config(args)

    assert result["valid"] is False


def test_config_validate_missing_file():
    """Config validate should handle missing files gracefully."""
    args = Namespace(config_action="validate", file="/nonexistent/file.json")
    result = cmd_config(args)

    assert result["valid"] is False
    assert "error" in result


def test_config_validate_invalid_json(tmp_path):
    """Config validate should handle malformed JSON gracefully."""
    path = tmp_path / "invalid.json"
    path.write_text("{not valid json", encoding="utf-8")

    args = Namespace(config_action="validate", file=str(path))
    result = cmd_config(args)

    assert result["valid"] is False


def test_config_validate_params_not_dict(tmp_path):
    """Config validate should reject non-dict parameters."""
    config = {
        "environment": {"type": "hawk_dove"},
        "parameters": "not a dict",
    }
    path = tmp_path / "bad_params.json"
    path.write_text(json.dumps(config), encoding="utf-8")

    args = Namespace(config_action="validate", file=str(path))
    result = cmd_config(args)

    assert result["valid"] is False
