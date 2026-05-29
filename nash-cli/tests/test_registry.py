"""环境注册表与 CLI 入口测试"""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from scripts.nash_cli.commands import (
    get_environment_registry,
    list_presets,
    resolve_environment_id,
    get_environment_spec,
    build_run_config,
)


def test_registry_loads_all_environments():
    """注册表应包含全部 8 个环境"""
    registry = get_environment_registry()
    assert len(registry) >= 8, f"Expected >=8 environments, got {len(registry)}"


def test_list_presets_returns_short_ids():
    """list_presets 应返回可用短 ID"""
    presets = list_presets()
    assert len(presets) >= 8
    assert "hawk_dove" in presets or "hawk_dove" in [p for p in presets]


def test_resolve_short_id():
    """短 ID 应能解析为完整环境 ID"""
    resolved = resolve_environment_id("hawk_dove")
    assert resolved is not None
    assert "hawk" in resolved.lower()


def test_get_environment_spec():
    """应能获取环境的完整规格"""
    spec = get_environment_spec("hawk_dove")
    assert spec is not None
    assert spec.env_id == "hawk_dove"
    assert spec.creator is not None
    assert spec.default_config is not None


def test_build_run_config_overrides():
    """build_run_config 应覆盖 agents 和 rounds"""
    spec = get_environment_spec("hawk_dove")
    config = build_run_config(spec, agents=50, rounds=100)
    params = config["parameters"]
    assert params["num_agents"]["value"] == 50
    assert params["num_rounds"]["value"] == 100
