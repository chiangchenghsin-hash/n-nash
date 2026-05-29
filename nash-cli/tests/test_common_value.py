"""共同价值拍卖环境测试 — 赢家诅咒"""

import numpy as np
from src.environments.auction_common_value import (
    AuctionCommonValueEnvironment,
    create_auction_common_value,
)


def _make_config(num_bidders=5, true_value=100.0, noise_std=15.0, num_rounds=300):
    return {
        "environment": {
            "type": "auction_common_value",
            "nobel_reference": {"year": 2020, "laureates": [], "contribution": ""},
        },
        "parameters": {
            "num_bidders": {"value": num_bidders},
            "true_value": {"value": true_value},
            "noise_std": {"value": noise_std},
            "num_rounds": {"value": num_rounds},
        },
        "validation": {
            "equilibrium_type": "winner_curse",
            "metrics": [
                {"name": "winner_curse_rate", "expected_value": 0.5, "tolerance": 0.3},
            ],
        },
    }


def test_common_value_winner_curse():
    """赢家诅咒应存在（赢家经常支付超过真实价值）"""
    np.random.seed(42)
    config = _make_config(num_rounds=300)
    env = AuctionCommonValueEnvironment(config)
    result = env.run_simulation(max_rounds=300)

    curse_rate = result["final_metrics"].get("winner_curse_rate", 0)
    assert curse_rate > 0.2, f"Winner's curse rate should be >20%, got {curse_rate:.2%}"


def test_create_common_value_factory():
    """工厂函数应正确初始化"""
    env, config = create_auction_common_value(num_bidders=3, true_value=100.0, noise_std=10.0)
    assert config["environment"]["type"] == "auction_common_value"
