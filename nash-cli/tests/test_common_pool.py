"""公共池资源环境测试 — 公地悲剧"""

import numpy as np
from src.environments.common_pool_resource import (
    CommonPoolResourceEnvironment,
    create_common_pool_resource,
)


def _make_config(num_agents=10, num_rounds=200):
    return {
        "environment": {
            "type": "common_pool_resource",
            "nobel_reference": {"year": 2009, "laureates": ["Elinor Ostrom"], "contribution": ""},
        },
        "parameters": {
            "num_agents": {"value": num_agents},
            "num_rounds": {"value": num_rounds},
        },
        "validation": {
            "equilibrium_type": "tragedy_of_commons",
            "metrics": [
                {"name": "resource_depletion_rate", "expected_value": 1.0, "tolerance": 0.5},
            ],
        },
    }


def test_common_pool_resource_depletion():
    """无制度约束时资源应被过度消耗"""
    np.random.seed(42)
    config = _make_config(num_rounds=200)
    env = CommonPoolResourceEnvironment(config)
    result = env.run_simulation(max_rounds=200)

    depletion_rate = result["final_metrics"].get("resource_depletion_rate", 0)
    assert depletion_rate > 0.2, f"Resource should be depleted: rate={depletion_rate:.2%}"


def test_create_common_pool_factory():
    """工厂函数应正确初始化"""
    env, config = create_common_pool_resource(num_agents=5, num_rounds=50)
    assert config["environment"]["type"] == "common_pool_resource"
