"""Vickrey analytical verification tests — dominant strategy proof."""

import numpy as np
import pytest

from src.environments.vickrey_auction import (
    VickreyAuctionEnvironment,
    create_vickrey_auction,
)


def _make_config(value_range=None):
    if value_range is None:
        value_range = [0, 200]
    return {
        "environment": {
            "type": "vickrey_auction",
            "nobel_reference": {"year": 1996, "laureates": ["William Vickrey"], "contribution": ""},
        },
        "parameters": {
            "num_bidders": {"value": 5},
            "value_range": {"value": value_range},
            "learning_rate": {"value": 0.1},
            "exploration_rate": {"value": 0.01},
            "num_rounds": {"value": 100},
        },
        "validation": {
            "equilibrium_type": "truthful_bidding_dominant_strategy",
            "metrics": [],
        },
    }


def test_analytical_dominant_strategy_holds():
    """verify_dominant_strategy should prove truthful bidding is weakly dominant."""
    config = _make_config()
    env = VickreyAuctionEnvironment(config)

    result = env.verify_dominant_strategy()

    assert result["dominant_strategy_holds"] is True
    assert result["verification_type"] == "analytical_weak_dominance"
    assert result["num_values_tested"] > 0
    assert result["num_alternative_bids_tested"] > 0
    assert result["num_prices_tested"] > 0
    assert result["average_max_utility_loss_from_deviating"] == 0.0
    assert "PASS" in result["conclusion"]


def test_analytical_narrow_value_range():
    """Dominant strategy should hold for any value range."""
    for value_range in [[0, 100], [50, 150], [10, 1000]]:
        config = _make_config(value_range=value_range)
        env = VickreyAuctionEnvironment(config)
        result = env.verify_dominant_strategy()
        assert result["dominant_strategy_holds"] is True, (
            f"Failed for value_range={value_range}"
        )


def test_analytical_no_utility_loss():
    """Deviating from truthful bidding should never increase utility."""
    config = _make_config()
    env = VickreyAuctionEnvironment(config)
    result = env.verify_dominant_strategy()

    assert result["average_max_utility_loss_from_deviating"] == 0.0


def test_analytical_result_independent_of_simulation():
    """verify_dominant_strategy should work without running simulation."""
    config = _make_config()
    env = VickreyAuctionEnvironment(config)
    env.initialize_agents()

    result = env.verify_dominant_strategy()
    assert result["dominant_strategy_holds"] is True


def test_analytical_theorem_reference():
    """Result should reference Vickrey (1961)."""
    config = _make_config()
    env = VickreyAuctionEnvironment(config)
    result = env.verify_dominant_strategy()

    assert "Vickrey" in result["theorem"]
    assert "1961" in result["theorem"]
