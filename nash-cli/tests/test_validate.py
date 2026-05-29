"""Validate command tests — statistical and Nobel validation."""

import json
import pytest
from argparse import Namespace

from scripts.nash_cli.commands.validate import cmd_validate


def _write_hawk_dove_results(tmp_path):
    """Write hawk_dove simulation results for validation."""
    data = {
        "status": "completed",
        "environment": "hawk_dove",
        "environment_type": "hawk_dove",
        "total_rounds": 200,
        "converged": True,
        "final_metrics": {
            "hawk_ratio": 0.66,
            "ess_deviation": 0.01,
            "strategy_stability": 0.95,
        },
        "history": [
            {"round": i, "hawk_ratio": 0.5 + i * 0.001}
            for i in range(200)
        ],
        "config": {
            "environment": {"type": "hawk_dove"},
            "parameters": {
                "resource_value": {"value": 4.0},
                "conflict_cost": {"value": 6.0},
            },
        },
    }
    path = tmp_path / "hawk_dove_results.json"
    path.write_text(json.dumps(data), encoding="utf-8")
    return str(path)


def test_validate_nobel(tmp_path):
    """Nobel validation should validate hawk_dove ESS convergence."""
    data_path = _write_hawk_dove_results(tmp_path)
    args = Namespace(data=data_path, type="nobel",
                     baseline_gini=0.3, baseline_hostility=0.4, output=None)
    result = cmd_validate(args)

    assert "nobel" in result
    nobel = result["nobel"]
    assert "model_name" in nobel
    assert "hypothesis_supported" in nobel
    assert nobel["model_name"] == "鹰鸽博弈"
    assert nobel["hypothesis_supported"] is True


def test_validate_statistical(tmp_path):
    """Statistical validation should return gini analysis."""
    data_path = _write_hawk_dove_results(tmp_path)
    args = Namespace(data=data_path, type="statistical",
                     baseline_gini=0.3, baseline_hostility=0.4, output=None)
    result = cmd_validate(args)

    assert "statistical" in result
    stat = result["statistical"]
    assert "message" in stat or "gini" in stat


def test_validate_both(tmp_path):
    """Both validation should return statistical and nobel results."""
    data_path = _write_hawk_dove_results(tmp_path)
    args = Namespace(data=data_path, type="both",
                     baseline_gini=0.3, baseline_hostility=0.4, output=None)
    result = cmd_validate(args)

    assert "statistical" in result
    assert "nobel" in result


def test_validate_vickrey_results(tmp_path):
    """Nobel validation should handle vickrey auction results."""
    data = {
        "status": "completed",
        "environment": "vickrey",
        "environment_type": "vickrey_auction",
        "total_rounds": 500,
        "converged": True,
        "final_metrics": {
            "truthful_bidding_rate": 0.98,
            "allocative_efficiency": 1.0,
        },
        "history": [],
        "config": {
            "environment": {"type": "vickrey_auction"},
            "parameters": {"num_bidders": {"value": 5}},
        },
    }
    path = tmp_path / "vickrey_results.json"
    path.write_text(json.dumps(data), encoding="utf-8")

    args = Namespace(data=str(path), type="nobel",
                     baseline_gini=0.3, baseline_hostility=0.4, output=None)
    result = cmd_validate(args)

    nobel = result["nobel"]
    assert nobel["hypothesis_supported"] is True
    assert nobel["confidence"] > 0.9


def test_validate_no_data():
    """Validate without data file should return capabilities info."""
    args = Namespace(data=None, type="both",
                     baseline_gini=0.3, baseline_hostility=0.4, output=None)
    result = cmd_validate(args)

    assert "statistical" in result
    stat = result["statistical"]
    assert "capabilities" in stat or "message" in stat


def test_validate_missing_file():
    """Validate with nonexistent file should raise."""
    args = Namespace(data="/nonexistent/file.json", type="nobel",
                     baseline_gini=0.3, baseline_hostility=0.4, output=None)
    with pytest.raises(FileNotFoundError):
        cmd_validate(args)


def test_validate_repeated_pd(tmp_path):
    """Nobel validation should handle repeated PD results."""
    data = {
        "status": "completed",
        "environment": "prisoners_dilemma",
        "environment_type": "repeated_prisoners_dilemma",
        "total_rounds": 300,
        "converged": True,
        "final_metrics": {
            "cooperation_rate": 0.85,
            "spne_supported": 0.8,
        },
        "history": [],
        "config": {
            "environment": {"type": "repeated_prisoners_dilemma"},
            "parameters": {"discount_factor": {"value": 0.95}},
        },
    }
    path = tmp_path / "pd_results.json"
    path.write_text(json.dumps(data), encoding="utf-8")

    args = Namespace(data=str(path), type="nobel",
                     baseline_gini=0.3, baseline_hostility=0.4, output=None)
    result = cmd_validate(args)

    nobel = result["nobel"]
    assert nobel["hypothesis_supported"] is True
