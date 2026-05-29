"""StatisticalValidator unit tests."""

import numpy as np
import pytest

from src.statistical_validator import StatisticalValidator
from src.contracts import HypothesisTestData


@pytest.fixture
def validator():
    return StatisticalValidator(alpha=0.05)


def test_t_test_significant(validator):
    """T-test should detect significant difference between distinct groups."""
    data = HypothesisTestData(
        group_a=[10.0, 11.0, 12.0, 10.5, 11.5, 10.8, 11.2, 10.9],
        group_b=[5.0, 6.0, 5.5, 5.8, 6.2, 5.3, 5.7, 5.9],
        test_type="t_test",
    )
    result = validator.validate_hypothesis(data)

    assert result.hypothesis_supported is True
    assert result.p_value < 0.05
    assert abs(result.effect_size) > 1.0


def test_t_test_not_significant(validator):
    """T-test should not detect difference between similar groups."""
    data = HypothesisTestData(
        group_a=[5.0, 5.1, 4.9, 5.0, 5.05, 4.95],
        group_b=[5.0, 5.1, 4.9, 5.0, 5.05, 4.95],
        test_type="t_test",
    )
    result = validator.validate_hypothesis(data)

    assert result.hypothesis_supported is False


def test_mann_whitney(validator):
    """Mann-Whitney should detect non-parametric differences."""
    data = HypothesisTestData(
        group_a=[10, 12, 14, 16, 18, 20, 22, 24],
        group_b=[1, 2, 3, 4, 5, 6, 7, 8],
        test_type="mann_whitney",
    )
    result = validator.validate_hypothesis(data)

    assert result.hypothesis_supported is True
    assert result.p_value < 0.05


def test_ks_test(validator):
    """KS test should detect distributional differences."""
    np.random.seed(42)
    data = HypothesisTestData(
        group_a=np.random.normal(10, 1, 50).tolist(),
        group_b=np.random.normal(15, 1, 50).tolist(),
        test_type="ks_test",
    )
    result = validator.validate_hypothesis(data)

    assert result.hypothesis_supported is True
    assert result.effect_size > 0.5


def test_unknown_test_type_falls_back(validator):
    """Unknown test type should fall back to t-test."""
    data = HypothesisTestData(
        group_a=[10, 11, 12, 13],
        group_b=[1, 2, 3, 4],
        test_type="unknown_test",
    )
    result = validator.validate_hypothesis(data)
    assert "t-test" in result.conclusion


def test_compare_to_baseline(validator):
    """compare_to_baseline should return p-value and effect size."""
    experimental = [0.8, 0.85, 0.78, 0.82, 0.81]
    baseline = [0.3]

    result = validator.compare_to_baseline(experimental, baseline)

    assert "p_value" in result
    assert "effect_size" in result
    assert "significant" in result


def test_compute_gini_perfect_equality(validator):
    """Gini should be ~0 for perfectly equal distribution."""
    gini = validator.compute_gini([10, 10, 10, 10, 10])
    assert gini < 0.05


def test_compute_gini_high_inequality(validator):
    """Gini should be high for unequal distribution."""
    gini = validator.compute_gini([0, 0, 0, 0, 100])
    assert gini > 0.7


def test_compute_gini_empty(validator):
    """Gini should return 0 for empty input."""
    gini = validator.compute_gini([])
    assert gini == 0.0


def test_compute_gini_all_zeros(validator):
    """Gini should return 0 when all values are 0."""
    gini = validator.compute_gini([0, 0, 0, 0])
    assert gini == 0.0


def test_compute_mean_hostility(validator):
    """compute_mean_hostility should average hostility values."""
    beliefs = [
        {"hostility": 0.2},
        {"hostility": 0.4},
        {"hostility": 0.6},
    ]
    result = validator.compute_mean_hostility(beliefs)
    assert abs(result - 0.4) < 0.01


def test_compute_mean_hostility_empty(validator):
    """compute_mean_hostility should return 0 for empty input."""
    assert validator.compute_mean_hostility([]) == 0.0


def test_compute_confidence_interval(validator):
    """Confidence interval should contain the mean."""
    values = [10.0, 11.0, 12.0, 10.5, 11.5, 10.8, 11.2]
    lo, hi = validator.compute_confidence_interval(values, confidence=0.95)

    mean = np.mean(values)
    assert lo < mean < hi


def test_compute_confidence_interval_single(validator):
    """Confidence interval for single value should return (mean, mean)."""
    lo, hi = validator.compute_confidence_interval([5.0])
    assert lo == 5.0
    assert hi == 5.0


def test_compute_significance(validator):
    """compute_significance should return p-value and confidence."""
    group_a = [10, 11, 12, 13, 14, 15]
    group_b = [1, 2, 3, 4, 5, 6]

    p_value, confidence = validator.compute_significance(group_a, group_b)

    assert 0 <= p_value <= 1
    assert 0 <= confidence <= 1
    assert p_value < 0.05
