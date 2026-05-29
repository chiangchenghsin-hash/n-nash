"""Viz command tests — chart generation from simulation results."""

import json
import os
import pytest
from argparse import Namespace

from scripts.nash_cli.commands.viz import cmd_viz, _extract_time_series


def _write_run_results(tmp_path, env_type="hawk_dove"):
    """Write simulation results file and return path."""
    data = {
        "status": "completed",
        "environment": env_type,
        "environment_type": env_type,
        "total_rounds": 100,
        "converged": True,
        "final_metrics": {"hawk_ratio": 0.66, "ess_deviation": 0.01},
        "history": [
            {
                "round": i,
                "hawk_ratio": 0.5 + i * 0.002,
                "avg_payoff_hawk": 1.5,
                "avg_payoff_dove": 0.8,
                "ess_deviation": abs(0.5 + i * 0.002 - 0.667),
            }
            for i in range(100)
        ],
    }
    path = tmp_path / "run_results.json"
    path.write_text(json.dumps(data), encoding="utf-8")
    return str(path)


def test_viz_all_generates_chart(tmp_path):
    """Viz --type all should generate a PNG file."""
    data_path = _write_run_results(tmp_path)
    out_path = str(tmp_path / "chart.png")

    args = Namespace(data=data_path, type="all", output=out_path)
    result = cmd_viz(args)

    assert result["status"] == "ok"
    assert os.path.exists(out_path)


def test_viz_output_path_default(tmp_path):
    """Viz should use default output path when none specified."""
    data_path = _write_run_results(tmp_path)

    args = Namespace(data=data_path, type="all", output=None)
    result = cmd_viz(args)

    assert result["status"] == "ok"
    assert os.path.exists("nash_viz_output.png")
    os.remove("nash_viz_output.png")


def test_viz_with_gini_data(tmp_path):
    """Viz should handle gini_history data."""
    data = {
        "gini_history": [0.3 + i * 0.001 for i in range(100)],
        "hostility_history": [0.4 - i * 0.001 for i in range(100)],
    }
    path = tmp_path / "gini_data.json"
    path.write_text(json.dumps(data), encoding="utf-8")
    out_path = str(tmp_path / "gini_chart.png")

    args = Namespace(data=str(path), type="all", output=out_path)
    result = cmd_viz(args)

    assert result["status"] == "ok"
    assert os.path.exists(out_path)


def test_viz_gini_type(tmp_path):
    """Viz --type gini should plot gini history."""
    data = {"gini_history": [0.3 + i * 0.001 for i in range(50)]}
    path = tmp_path / "gini_only.json"
    path.write_text(json.dumps(data), encoding="utf-8")
    out_path = str(tmp_path / "gini.png")

    args = Namespace(data=str(path), type="gini", output=out_path)
    result = cmd_viz(args)

    assert result["status"] == "ok"
    assert result["type"] == "gini"


def test_viz_no_gini_data(tmp_path):
    """Viz --type gini without gini data should return error."""
    data = {"history": [{"round": 1}]}
    path = tmp_path / "no_gini.json"
    path.write_text(json.dumps(data), encoding="utf-8")

    args = Namespace(data=str(path), type="gini", output=str(tmp_path / "out.png"))
    result = cmd_viz(args)

    assert "error" in result


def test_viz_missing_file():
    """Viz with nonexistent file should raise."""
    args = Namespace(data="/nonexistent.json", type="all", output=None)
    with pytest.raises(FileNotFoundError):
        cmd_viz(args)


def test_extract_time_series_hawk_dove():
    """_extract_time_series should extract numeric series from history."""
    history = [
        {"round": 1, "hawk_ratio": 0.5, "avg_payoff_hawk": 1.5},
        {"round": 2, "hawk_ratio": 0.55, "avg_payoff_hawk": 1.4},
    ]
    series = _extract_time_series(history, "hawk_dove")

    assert "hawk_ratio" in series
    assert "avg_payoff_hawk" in series
    assert series["hawk_ratio"] == [0.5, 0.55]


def test_extract_time_series_dedup():
    """_extract_time_series should skip duplicate rounds."""
    history = [
        {"round": 1, "hawk_ratio": 0.5},
        {"round": 1, "hawk_ratio": 0.51},
        {"round": 2, "hawk_ratio": 0.6},
    ]
    series = _extract_time_series(history, "hawk_dove")

    assert series["hawk_ratio"] == [0.5, 0.6]


def test_extract_time_series_empty():
    """_extract_time_series should handle empty history."""
    series = _extract_time_series([], "hawk_dove")
    assert series == {}
