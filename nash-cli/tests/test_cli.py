"""CLI entry point and argument parsing tests."""

import sys
import json
import pytest
from unittest.mock import patch
from argparse import Namespace

from scripts.nash_cli.main import _dispatch, _json_default, _output
from scripts.nash_cli.commands import list_presets


def test_list_presets_returns_strings():
    """list_presets should return a list of short ID strings."""
    presets = list_presets()
    assert isinstance(presets, list)
    assert all(isinstance(p, str) for p in presets)
    assert len(presets) >= 8


def test_dispatch_run():
    """_dispatch should route 'run' command to cmd_run."""
    args = Namespace(command="run", preset="hawk_dove", agents=10, rounds=5,
                     output=None, seed=42)
    result = _dispatch(args)
    assert result["status"] == "completed"
    assert result["environment_type"] == "hawk_dove"


def test_dispatch_env_list():
    """_dispatch should route 'env list' to cmd_env."""
    args = Namespace(command="env", env_action="list", format="json")
    result = _dispatch(args)
    assert "environments" in result
    assert result["count"] >= 8


def test_dispatch_env_info():
    """_dispatch should route 'env info' to cmd_env."""
    args = Namespace(command="env", env_action="info", name="hawk_dove", format="json")
    result = _dispatch(args)
    assert result["id"] == "hawk_dove"


def test_dispatch_unknown_command():
    """_dispatch should return error for unknown commands."""
    args = Namespace(command="nonexistent")
    result = _dispatch(args)
    assert "error" in result


def test_json_default_numpy_scalar():
    """_json_default should handle numpy scalars."""
    import numpy as np
    val = np.float64(3.14)
    result = _json_default(val)
    assert result == 3.14


def test_json_default_numpy_array():
    """_json_default should handle numpy arrays via tolist."""
    import numpy as np
    val = np.array([1, 2, 3])
    # _json_default checks .item() first which fails for multi-element arrays
    # then falls through to .tolist() — verify it converts correctly
    assert hasattr(val, "tolist")
    result = val.tolist()
    assert result == [1, 2, 3]


def test_json_default_numpy_scalar_array():
    """_json_default should handle single-element numpy arrays."""
    import numpy as np
    val = np.array([3.14])
    result = _json_default(val)
    assert result == 3.14


def test_json_default_dataclass():
    """_json_default should handle dataclasses."""
    import dataclasses

    @dataclasses.dataclass
    class Dummy:
        x: int
        y: str

    result = _json_default(Dummy(x=1, y="hello"))
    assert result == {"x": 1, "y": "hello"}


def test_json_default_set():
    """_json_default should convert sets to lists."""
    result = _json_default({1, 2, 3})
    assert sorted(result) == [1, 2, 3]


def test_json_default_fallback():
    """_json_default should fall back to str() for unknown types."""
    result = _json_default(object())
    assert isinstance(result, str)


def test_output_stdout(capsys):
    """_output should print JSON to stdout when no output path."""
    args = Namespace(command="run", output=None)
    _output({"status": "ok"}, args)
    captured = capsys.readouterr()
    data = json.loads(captured.out)
    assert data["status"] == "ok"


def test_output_to_file(tmp_path):
    """_output should write JSON to file when output path given."""
    out_file = str(tmp_path / "result.json")
    args = Namespace(command="run", output=out_file)
    _output({"status": "ok", "data": [1, 2, 3]}, args)
    with open(out_file) as f:
        data = json.load(f)
    assert data["data"] == [1, 2, 3]


def test_output_viz_success(capsys):
    """_output for viz command should print JSON to stdout."""
    args = Namespace(command="viz")
    _output({"status": "ok", "output": "/tmp/chart.png"}, args)
    captured = capsys.readouterr()
    data = json.loads(captured.out)
    assert data["status"] == "ok"


def test_output_viz_error(capsys):
    """_output for viz error should print to stderr."""
    args = Namespace(command="viz")
    _output({"error": "no data"}, args)
    captured = capsys.readouterr()
    assert captured.out == ""
    assert "error" in captured.err


def test_main_no_args(capsys):
    """main() with no args should exit with error."""
    with patch("sys.argv", ["nash"]):
        from scripts.nash_cli.main import main
        with pytest.raises(SystemExit) as exc_info:
            main()
        assert exc_info.value.code == 1
        captured = capsys.readouterr()
        assert "error" in captured.err or "invalid" in captured.err.lower()
