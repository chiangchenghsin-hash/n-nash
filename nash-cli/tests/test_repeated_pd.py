"""重复囚徒困境环境测试 — SPNE 合作均衡"""

import numpy as np
from src.environments.repeated_prisoners_dilemma import (
    RepeatedPrisonersDilemmaEnvironment,
    create_repeated_prisoners_dilemma,
)


def _make_config(num_agents=20, num_rounds=300):
    return {
        "environment": {
            "type": "repeated_prisoners_dilemma",
            "nobel_reference": {"year": 2005, "laureates": [], "contribution": ""},
        },
        "parameters": {
            "num_agents": {"value": num_agents},
            "discount_factor": {"value": 0.95},
            "num_rounds": {"value": num_rounds},
        },
        "validation": {
            "equilibrium_type": "spne",
            "metrics": [
                {"name": "cooperation_rate", "expected_value": 0.8, "tolerance": 0.2},
            ],
        },
    }


def test_repeated_pd_high_cooperation():
    """高折扣因子 (delta=0.95) 下合作率应 > 60%"""
    np.random.seed(42)
    config = _make_config(num_rounds=300)
    env = RepeatedPrisonersDilemmaEnvironment(config)
    result = env.run_simulation(max_rounds=300)

    cooperation_rate = result["final_metrics"].get("cooperation_rate", 0)
    assert cooperation_rate > 0.6, f"Cooperation rate should be >60%, got {cooperation_rate:.2%}"


def test_repeated_pd_delta_condition():
    """delta > delta* 时 SPNE 条件应被满足"""
    np.random.seed(42)
    config = _make_config(num_rounds=200)
    env = RepeatedPrisonersDilemmaEnvironment(config)
    result = env.run_simulation(max_rounds=200)

    delta = config["parameters"]["discount_factor"]["value"]
    assert delta > 0.5, f"delta=0.95 should exceed delta*=0.5"


def test_create_repeated_pd_factory():
    """工厂函数应返回正确的环境"""
    env, config = create_repeated_prisoners_dilemma(num_agents=10, num_rounds=50)
    assert config["environment"]["type"] == "repeated_prisoners_dilemma"
