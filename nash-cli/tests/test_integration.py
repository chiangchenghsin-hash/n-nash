"""End-to-end integration tests — full workflows from CLI to validation."""

import json
import os
import pytest
import numpy as np
from argparse import Namespace

from scripts.nash_cli.commands.run import cmd_run
from scripts.nash_cli.commands.validate import cmd_validate
from scripts.nash_cli.commands.sweep import cmd_sweep
from scripts.nash_cli.commands.config_cmd import cmd_config
from scripts.nash_cli.commands.env_cmd import cmd_env


def _run_environment(preset, agents=20, rounds=50, seed=42):
    """Run an environment and return results dict."""
    args = Namespace(command="run", preset=preset, agents=agents,
                     rounds=rounds, output=None, seed=seed)
    return cmd_run(args)


class TestRunValidateWorkflow:
    """Full run -> validate -> output workflow."""

    @pytest.mark.parametrize("preset", [
        "hawk_dove", "prisoners_dilemma", "public_goods",
        "common_pool", "spence", "matching",
        "vickrey", "auction_common_value",
    ])
    def test_run_produces_valid_result(self, preset):
        """Each environment should produce a completed result with metrics."""
        result = _run_environment(preset, rounds=50)

        assert result["status"] == "completed"
        assert "final_metrics" in result
        assert "environment_type" in result
        assert isinstance(result["final_metrics"], dict)

    def test_run_and_save_to_file(self, tmp_path):
        """Run results should be serializable to JSON file."""
        result = _run_environment("hawk_dove")

        out_path = str(tmp_path / "hawk_dove.json")
        with open(out_path, "w") as f:
            json.dump(result, f, default=str)

        with open(out_path) as f:
            loaded = json.load(f)

        assert loaded["status"] == "completed"
        assert loaded["environment_type"] == "hawk_dove"

    def test_run_then_validate(self, tmp_path):
        """Run hawk_dove, save results, then validate with Nobel validator."""
        result = _run_environment("hawk_dove", rounds=200)

        data_path = str(tmp_path / "results.json")
        with open(data_path, "w") as f:
            json.dump(result, f, default=str)

        args = Namespace(data=data_path, type="nobel",
                         baseline_gini=0.3, baseline_hostility=0.4, output=None)
        validation = cmd_validate(args)

        assert "nobel" in validation
        nobel = validation["nobel"]
        assert "hypothesis_supported" in nobel
        assert "confidence" in nobel


class TestConfigTemplateToRunWorkflow:
    """config template -> run with config workflow."""

    def test_template_then_run(self, tmp_path):
        """Generate config template, then run with it."""
        args = Namespace(config_action="template", preset="hawk_dove", output=None)
        config = cmd_config(args)

        config_path = str(tmp_path / "config.json")
        with open(config_path, "w") as f:
            json.dump(config, f)

        args = Namespace(config_action="validate", file=config_path)
        validation = cmd_config(args)
        assert validation["valid"] is True

    def test_template_then_sweep(self, tmp_path):
        """Generate config template, then sweep a parameter."""
        args = Namespace(config_action="template", preset="hawk_dove", output=None)
        config = cmd_config(args)

        config_path = str(tmp_path / "config.json")
        with open(config_path, "w") as f:
            json.dump(config, f)

        args = Namespace(config=config_path, param="resource_value",
                         range="2,8", step=2.0, rounds=20, seed=42, output=None)
        result = cmd_sweep(args)

        assert result["status"] == "completed"
        assert result["summary"]["total"] == 4
        assert result["summary"]["completed"] == 4


class TestMultiEnvironmentComparison:
    """Run multiple environments and compare results."""

    def test_all_environments_converge(self):
        """All 8 environments should produce completed results."""
        presets = [
            "hawk_dove", "prisoners_dilemma", "public_goods",
            "common_pool", "spence", "matching",
            "vickrey", "auction_common_value",
        ]
        results = {}
        for preset in presets:
            results[preset] = _run_environment(preset, rounds=50)

        for preset, result in results.items():
            assert result["status"] == "completed", f"{preset} failed"
            assert "final_metrics" in result

    def test_env_list_matches_runnable_presets(self):
        """env list should return all presets that can be run."""
        env_args = Namespace(env_action="list", format="json")
        env_result = cmd_env(env_args)
        env_ids = {e["id"] for e in env_result["environments"]}

        from scripts.nash_cli.commands import list_presets
        presets = list_presets()

        for preset in presets:
            run_args = Namespace(command="run", preset=preset, agents=10,
                                 rounds=5, output=None, seed=42)
            result = cmd_run(run_args)
            assert result["status"] == "completed", f"Preset {preset} not runnable"
            assert result["environment_type"] in env_ids


class TestNobelValidatorIntegration:
    """Test NobelValidator with real simulation results."""

    def test_hawk_dove_nobel_validation(self):
        """Hawk-dove ESS should pass Nobel validation."""
        from src.validators.nobel_validator import NobelValidator
        validator = NobelValidator()

        result = validator.validate(
            "hawk_dove",
            {"hawk_ratio": 0.66, "ess_deviation": 0.01, "strategy_stability": 0.95},
            {
                "parameters": {
                    "resource_value": {"value": 4.0},
                    "conflict_cost": {"value": 6.0},
                }
            },
        )

        assert result.hypothesis_supported is True
        assert result.confidence > 0.8

    def test_vickrey_nobel_validation(self):
        """Vickrey truthful bidding should pass Nobel validation."""
        from src.validators.nobel_validator import NobelValidator
        validator = NobelValidator()

        result = validator.validate(
            "vickrey",
            {"truthful_bidding_rate": 0.98, "allocative_efficiency": 1.0},
            {"parameters": {}},
        )

        assert result.hypothesis_supported is True
        assert result.confidence > 0.9

    def test_unknown_env_nobel_validation(self):
        """Unknown environment should fail validation gracefully."""
        from src.validators.nobel_validator import NobelValidator
        validator = NobelValidator()

        result = validator.validate("unknown_game", {}, {})

        assert result.hypothesis_supported is False
        assert result.confidence == 0.0
