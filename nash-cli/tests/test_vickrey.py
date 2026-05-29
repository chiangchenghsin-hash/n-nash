"""Vickrey 拍卖环境测试 — 真实出价占优策略收敛"""

import numpy as np
from src.environments.vickrey_auction import VickreyAuctionEnvironment, create_vickrey_auction


def _make_config(num_bidders=5, true_value=100.0, num_rounds=500, exploration_rate=0.01):
    return {
        "environment": {
            "type": "vickrey_auction",
            "nobel_reference": {"year": 1996, "laureates": ["William Vickrey"], "contribution": ""},
        },
        "parameters": {
            "num_bidders": {"value": num_bidders},
            "value_range": {"value": [0, 200]},
            "learning_rate": {"value": 0.1},
            "exploration_rate": {"value": exploration_rate},
            "num_rounds": {"value": num_rounds},
        },
        "validation": {
            "equilibrium_type": "truthful_bidding_dominant_strategy",
            "metrics": [
                {"name": "truthful_bidding_rate", "expected_value": 1.0, "tolerance": 0.05},
                {"name": "allocative_efficiency", "expected_value": 1.0, "tolerance": 0.1},
            ],
        },
    }


def test_vickrey_truthful_bidding_converges():
    """说真话比率应 > 75%（考虑 1% 探索率上限为 ~99%）"""
    np.random.seed(42)
    config = _make_config(num_rounds=1000)
    env = VickreyAuctionEnvironment(config)
    result = env.run_simulation(max_rounds=1000)

    truthful_rate = result["final_metrics"].get("truthful_bidding_rate", 0)
    assert truthful_rate > 0.75, f"Truthful rate should be >75%, got {truthful_rate:.2%}"


def test_vickrey_allocative_efficiency():
    """配置效率：最高价值者应经常赢得拍卖"""
    np.random.seed(42)
    config = _make_config(num_rounds=500)
    env = VickreyAuctionEnvironment(config)
    result = env.run_simulation(max_rounds=500)

    efficiency = result["final_metrics"].get("allocative_efficiency", 0)
    assert efficiency > 0.7, f"Allocative efficiency should be >70%, got {efficiency:.2%}"


def test_create_vickrey_factory():
    """工厂函数应正确初始化"""
    env, config = create_vickrey_auction(num_bidders=3, num_rounds=100)
    assert config["environment"]["type"] == "vickrey_auction"
    assert config["parameters"]["num_bidders"]["value"] == 3
