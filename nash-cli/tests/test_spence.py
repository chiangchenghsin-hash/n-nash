"""Spence 信号传递环境测试 — 分离均衡"""

import numpy as np
from src.environments.spence_signaling import SpenceSignalingEnvironment, create_spence_signaling


def _make_config(num_workers=20, num_firms=5, num_rounds=200):
    return {
        "environment": {
            "type": "spence_signaling",
            "nobel_reference": {"year": 2001, "laureates": [], "contribution": ""},
        },
        "parameters": {
            "num_workers": {"value": num_workers},
            "num_firms": {"value": num_firms},
            "num_rounds": {"value": num_rounds},
        },
        "validation": {
            "equilibrium_type": "separating",
            "metrics": [
                {"name": "separation_index", "expected_value": 1.0, "tolerance": 0.1},
            ],
        },
    }


def test_spence_separation():
    """分离指数应 > 0.7（高能力者选择高教育信号）"""
    np.random.seed(42)
    config = _make_config(num_rounds=300)
    env = SpenceSignalingEnvironment(config)
    result = env.run_simulation(max_rounds=300)

    separation = result["final_metrics"].get("separation_index", 0)
    assert separation > 0.7, f"Separation index should be >0.7, got {separation:.2f}"


def test_create_spence_factory():
    """工厂函数应正确初始化"""
    env, config = create_spence_signaling(num_workers=10, num_firms=3, num_rounds=50)
    assert config["environment"]["type"] == "spence_signaling"
