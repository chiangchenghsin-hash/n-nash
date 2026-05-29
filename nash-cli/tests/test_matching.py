"""双边匹配环境测试 — Gale-Shapley 稳定匹配"""

import numpy as np
from src.environments.two_sided_matching import (
    TwoSidedMatchingEnvironment,
    create_two_sided_matching,
)


def _make_config(num_men=10, num_women=10, num_rounds=100):
    return {
        "environment": {
            "type": "two_sided_matching",
            "nobel_reference": {"year": 2012, "laureates": [], "contribution": ""},
        },
        "parameters": {
            "num_men": {"value": num_men},
            "num_women": {"value": num_women},
            "num_rounds": {"value": num_rounds},
        },
        "validation": {
            "equilibrium_type": "stable_matching",
            "metrics": [
                {"name": "stability_index", "expected_value": 1.0, "tolerance": 0.05},
            ],
        },
    }


def test_matching_stability():
    """Gale-Shapley 算法应产生稳定匹配（稳定性 > 95%）"""
    np.random.seed(42)
    config = _make_config(num_rounds=100)
    env = TwoSidedMatchingEnvironment(config)
    result = env.run_simulation(max_rounds=100)

    stability = result["final_metrics"].get("stability_index", 0)
    assert stability > 0.95, f"Stability should be >95%, got {stability:.2%}"


def test_create_matching_factory():
    """工厂函数应正确初始化"""
    env, config = create_two_sided_matching(num_men=5, num_women=5)
    assert config["environment"]["type"] == "two_sided_matching"
