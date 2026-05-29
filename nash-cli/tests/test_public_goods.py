"""公共物品博弈环境测试 — 搭便车均衡"""

import numpy as np
from src.environments.public_goods import PublicGoodsEnvironment, create_public_goods


def _make_config(num_agents=20, endowment=10.0, multiplier=1.6, num_rounds=200):
    return {
        "environment": {
            "type": "public_goods",
            "nobel_reference": {"year": 2009, "laureates": ["Elinor Ostrom"], "contribution": ""},
        },
        "parameters": {
            "num_agents": {"value": num_agents},
            "endowment": {"value": endowment},
            "multiplier": {"value": multiplier},
            "num_rounds": {"value": num_rounds},
        },
        "validation": {
            "equilibrium_type": "free_riding",
            "metrics": [
                {"name": "contribution_rate", "expected_value": 0.0, "tolerance": 0.2},
            ],
        },
    }


def test_public_goods_free_riding():
    """贡献率应趋向降低（搭便车）"""
    np.random.seed(42)
    config = _make_config(num_rounds=200)
    env = PublicGoodsEnvironment(config)
    result = env.run_simulation(max_rounds=200)

    contribution_rate = result["final_metrics"].get("contribution_rate", 1.0)
    assert contribution_rate < 0.4, f"Contribution rate should drop below 40%, got {contribution_rate:.2%}"


def test_public_goods_contribution_declines():
    """后期贡献率应低于前期"""
    np.random.seed(42)
    config = _make_config(num_rounds=200)
    env = PublicGoodsEnvironment(config)
    result = env.run_simulation(max_rounds=200)

    history = result["history"]
    if len(history) > 40:
        early_avg = np.mean([h.get("contribution_rate", 0.5) for h in history[:20]])
        late_avg = np.mean([h.get("contribution_rate", 0.5) for h in history[-20:]])
        assert late_avg <= early_avg + 0.1, (
            f"Contribution should decline: early={early_avg:.2f}, late={late_avg:.2f}"
        )


def test_create_public_goods_factory():
    """工厂函数应正确初始化"""
    env, config = create_public_goods(num_agents=10, endowment=5.0, multiplier=1.5)
    assert config["environment"]["type"] == "public_goods"
