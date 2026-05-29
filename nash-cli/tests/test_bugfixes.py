"""Tests for bug fixes found during audit."""

import numpy as np
import pytest
from argparse import Namespace

from src.environments.two_sided_matching import TwoSidedMatchingEnvironment
from src.environments.auction_common_value import AuctionCommonValueEnvironment
from src.validators.nobel_validator import NobelValidator
from src.statistical_validator import StatisticalValidator


class TestGaleShapleyUnequalSides:
    """CR-01: Gale-Shapley should handle num_men > num_women without crashing."""

    def _make_config(self, num_men, num_women):
        return {
            "environment": {"type": "two_sided_matching",
                           "nobel_reference": {"year": 2012, "laureates": [], "contribution": ""}},
            "parameters": {
                "num_men": {"value": num_men},
                "num_women": {"value": num_women},
                "num_rounds": {"value": 10},
            },
            "validation": {"equilibrium_type": "stable_matching", "metrics": []},
        }

    def test_more_men_than_women(self):
        """3 men, 2 women should not crash."""
        np.random.seed(42)
        config = self._make_config(num_men=3, num_women=2)
        env = TwoSidedMatchingEnvironment(config)
        matches = env.gale_shapley()
        assert len(matches) == 2

    def test_more_women_than_men(self):
        """2 men, 4 women should produce 2 matches."""
        np.random.seed(42)
        config = self._make_config(num_men=2, num_women=4)
        env = TwoSidedMatchingEnvironment(config)
        matches = env.gale_shapley()
        assert len(matches) == 2

    def test_equal_sides(self):
        """5 men, 5 women should produce 5 matches."""
        np.random.seed(42)
        config = self._make_config(num_men=5, num_women=5)
        env = TwoSidedMatchingEnvironment(config)
        matches = env.gale_shapley()
        assert len(matches) == 5

    def test_single_man_many_women(self):
        """1 man, 3 women should produce 1 match."""
        np.random.seed(42)
        config = self._make_config(num_men=1, num_women=3)
        env = TwoSidedMatchingEnvironment(config)
        matches = env.gale_shapley()
        assert len(matches) == 1


class TestWinnerCurseMetric:
    """CR-02: Winner's curse should measure overpayment, not overestimation."""

    def _make_config(self):
        return {
            "environment": {"type": "auction_common_value",
                           "nobel_reference": {"year": 2020, "laureates": [], "contribution": ""}},
            "parameters": {
                "num_bidders": {"value": 5},
                "true_value": {"value": 100.0},
                "noise_std": {"value": 30.0},
                "num_rounds": {"value": 200},
            },
            "validation": {"equilibrium_type": "winner_curse", "metrics": []},
        }

    def test_winner_curse_is_overpayment(self):
        """winner_curse should be True when second_price > true_value."""
        np.random.seed(42)
        config = self._make_config()
        env = AuctionCommonValueEnvironment(config)
        result = env.run_simulation(max_rounds=100)

        for entry in result["history"]:
            if entry["second_price"] > env.true_value:
                assert bool(entry["winner_curse"]) is True
            else:
                assert bool(entry["winner_curse"]) is False

    def test_overestimated_tracked_separately(self):
        """overestimated should track estimate > true_value independently."""
        np.random.seed(42)
        config = self._make_config()
        env = AuctionCommonValueEnvironment(config)
        env.initialize_agents()
        entry = env.run_step()

        assert "overestimated" in entry
        assert "winner_curse" in entry

    def test_single_bidder_pays_zero(self):
        """M-02: Single bidder should pay 0 (second-price with no competition)."""
        config = self._make_config()
        config["parameters"]["num_bidders"] = {"value": 1}
        np.random.seed(42)
        env = AuctionCommonValueEnvironment(config)
        env.initialize_agents()
        entry = env.run_step()

        assert entry["second_price"] == 0.0
        assert entry["winner_payoff"] == env.true_value


class TestNobelValidatorEdgeCases:
    """M-01: Nobel validator should handle missing/empty config gracefully."""

    def test_hawk_dove_empty_config(self):
        """Should not crash with empty config dict."""
        validator = NobelValidator()
        result = validator.validate(
            "hawk_dove",
            {"hawk_ratio": 0.66, "ess_deviation": 0.01, "strategy_stability": 0.95},
            {},
        )
        assert result.hypothesis_supported is True
        assert "ess_deviation" in str(result.metrics) or result.confidence > 0

    def test_hawk_dove_no_parameters(self):
        """Should not crash when config has no 'parameters' key."""
        validator = NobelValidator()
        result = validator.validate(
            "hawk_dove",
            {"hawk_ratio": 0.5, "ess_deviation": 0.2, "strategy_stability": 0.5},
            {"some_other_key": "value"},
        )
        assert isinstance(result.confidence, float)

    def test_hawk_dove_flat_params(self):
        """Should handle flat parameter values (not nested dicts)."""
        validator = NobelValidator()
        result = validator.validate(
            "hawk_dove",
            {"hawk_ratio": 0.66, "ess_deviation": 0.05},
            {"parameters": {"resource_value": 4.0, "conflict_cost": 6.0}},
        )
        assert isinstance(result.conclusion, str)


class TestStatisticalValidatorEdgeCases:
    """M-06 + L-05: Statistical validator edge cases."""

    def test_cohens_d_single_sample(self):
        """M-06: Cohen's d with single-sample groups should return 0."""
        import numpy as np
        validator = StatisticalValidator(alpha=0.05)
        group_a = np.array([5.0])
        group_b = np.array([10.0])
        d = validator._compute_cohens_d(group_a, group_b)
        assert d == 0.0

    def test_cohens_d_identical_groups(self):
        """Cohen's d with identical groups should return 0."""
        import numpy as np
        validator = StatisticalValidator(alpha=0.05)
        group_a = np.array([5.0, 5.0, 5.0])
        group_b = np.array([5.0, 5.0, 5.0])
        d = validator._compute_cohens_d(group_a, group_b)
        assert d == 0.0

    def test_gini_negative_values(self):
        """L-05: Gini with negative values should return 0."""
        validator = StatisticalValidator(alpha=0.05)
        gini = validator.compute_gini([-1, 2, 3, 4])
        assert gini == 0.0

    def test_gini_empty(self):
        """Gini with empty input should return 0."""
        validator = StatisticalValidator(alpha=0.05)
        assert validator.compute_gini([]) == 0.0

    def test_gini_all_negative(self):
        """Gini with all negative values should return 0."""
        validator = StatisticalValidator(alpha=0.05)
        gini = validator.compute_gini([-5, -3, -1])
        assert gini == 0.0
