"""鹰鸽博弈环境测试 — ESS 收敛与参数边界"""

import numpy as np
from src.environments.hawk_dove import HawkDoveEnvironment, create_hawk_dove


def _make_config(v=4.0, c=6.0, num_agents=100, num_rounds=300):
    return {
        "environment": {
            "type": "hawk_dove",
            "nobel_reference": {"year": 2005, "laureates": [], "contribution": ""},
        },
        "parameters": {
            "num_agents": {"value": num_agents},
            "resource_value": {"value": v},
            "conflict_cost": {"value": c},
            "num_rounds": {"value": num_rounds},
        },
        "validation": {
            "equilibrium_type": "ess",
            "metrics": [
                {"name": "hawk_ratio", "expected_value": v / c, "tolerance": 0.15},
                {"name": "strategy_stability", "expected_value": 0.8, "tolerance": 0.2},
            ],
        },
    }


def test_hawk_dove_ess_mixed_equilibrium():
    """V < C 时，鹰比例应收敛到 V/C"""
    np.random.seed(42)
    v, c = 4.0, 6.0
    config = _make_config(v=v, c=c, num_rounds=300)
    env = HawkDoveEnvironment(config)
    result = env.run_simulation(max_rounds=300)

    assert result["converged"], f"Should converge: {result['convergence_message']}"
    hawk_ratio = result["final_metrics"]["hawk_ratio"]
    ess_prediction = v / c
    assert abs(hawk_ratio - ess_prediction) < 0.15, (
        f"ESS={ess_prediction:.2f}, got {hawk_ratio:.2f}"
    )


def test_hawk_dove_pure_hawk_equilibrium():
    """V > C 时，鹰是纯 ESS，鹰比例应接近 100%"""
    np.random.seed(42)
    v, c = 8.0, 4.0
    config = _make_config(v=v, c=c, num_rounds=300)
    env = HawkDoveEnvironment(config)
    result = env.run_simulation(max_rounds=300)

    hawk_ratio = result["final_metrics"]["hawk_ratio"]
    assert hawk_ratio > 0.85, f"Pure hawk ESS: expected >85%, got {hawk_ratio:.2%}"


def test_hawk_dove_parameter_boundaries():
    """极端参数：V=C 时鹰比例应接近 100%"""
    np.random.seed(42)
    config = _make_config(v=5.0, c=5.0, num_rounds=200)
    env = HawkDoveEnvironment(config)
    env.ess_hawk_ratio = 1.0
    result = env.run_simulation(max_rounds=200)
    hawk_ratio = result["final_metrics"]["hawk_ratio"]
    assert hawk_ratio > 0.7, f"V=C boundary: expected >70%, got {hawk_ratio:.2%}"


def test_create_hawk_dove_factory():
    """工厂函数应返回正确的环境和配置"""
    env, config = create_hawk_dove(num_agents=50, resource_value=3.0, conflict_cost=9.0)
    assert config["environment"]["type"] == "hawk_dove"
    assert config["parameters"]["num_agents"]["value"] == 50
    assert env.V == 3.0
    assert env.C == 9.0
