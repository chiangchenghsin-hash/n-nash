"""M7 数值稳定验证器测试 — 完整覆盖三步法 + CLI 命令。

覆盖:
  - check_step_size_sensitivity: 多 dt 回放
  - check_perturbation_sensitivity: base vs perturbed
  - check_perturbation_sensitivity_from_seeds: 多种子 CV
  - check_boundary_conditions: 边界检查
  - StabilityValidator.validate_from_seeds: 完整流水线
  - StabilityValidator.from_sweep_results: sweep 敏感性
  - stability CLI command: 三种模式
"""

import json
import sys
from argparse import Namespace
from pathlib import Path

import numpy as np
import pytest

from src.primitives import VariableDecl
from src.stability_validator import (
    StabilityValidator,
    StabilityResult,
    _sensitivity_from_seeds,
    DOMAIN_RATIO_LOW,
    DOMAIN_RATIO_MEDIUM,
    DOMAIN_RATIO_HIGH,
    CV_MAD_LOW,
    CV_MAD_MEDIUM,
    CV_MAD_HIGH,
    DEFAULT_DT_VALUES,
    MIN_SEEDS_FOR_SENSITIVITY,
)

# Make scripts importable
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))


# ============================================================================
# Fixtures
# ============================================================================

@pytest.fixture
def validator():
    return StabilityValidator()


@pytest.fixture
def stock_decls():
    return [
        VariableDecl("trust", (0, 1000), is_stock=True, description="信任存量"),
        VariableDecl("stigma", (0, 1000), is_stock=True, description="污名存量"),
        VariableDecl("quality", (0, 1), is_probability=True, description="平均质量"),
    ]


@pytest.fixture
def sample_per_seed_results():
    """Simulate 5 seeds of hawk_dove at ESS."""
    return [
        {"seed": 42,  "final_metrics": {"hawk_ratio": 0.660, "ess_deviation": 0.010}},
        {"seed": 123, "final_metrics": {"hawk_ratio": 0.670, "ess_deviation": 0.005}},
        {"seed": 456, "final_metrics": {"hawk_ratio": 0.655, "ess_deviation": 0.012}},
        {"seed": 789, "final_metrics": {"hawk_ratio": 0.668, "ess_deviation": 0.008}},
        {"seed": 1024,"final_metrics": {"hawk_ratio": 0.662, "ess_deviation": 0.009}},
    ]


@pytest.fixture
def unstable_per_seed_results():
    """Simulate 5 seeds with high variance — should trigger low stability."""
    return [
        {"seed": 1, "final_metrics": {"sustainability_index": 0.8}},
        {"seed": 2, "final_metrics": {"sustainability_index": 0.1}},
        {"seed": 3, "final_metrics": {"sustainability_index": 0.9}},
        {"seed": 4, "final_metrics": {"sustainability_index": 0.05}},
        {"seed": 5, "final_metrics": {"sustainability_index": 0.6}},
    ]


# ============================================================================
# check_boundary_conditions
# ============================================================================

class TestBoundaryConditions:
    def test_safe_state_passes(self, stock_decls):
        safe, warnings = StabilityValidator.check_boundary_conditions(
            {"trust": 500, "stigma": 100, "quality": 0.6}, stock_decls
        )
        assert safe
        assert len(warnings) == 0

    def test_negative_stock_flagged(self, stock_decls):
        safe, warnings = StabilityValidator.check_boundary_conditions(
            {"trust": -50, "stigma": 100, "quality": 0.6}, stock_decls
        )
        assert not safe
        assert any("trust" in w for w in warnings)

    def test_probability_out_of_bounds_flagged(self, stock_decls):
        safe, warnings = StabilityValidator.check_boundary_conditions(
            {"trust": 500, "stigma": 100, "quality": 1.5}, stock_decls
        )
        assert not safe, "quality=1.5 > [0,1] should be flagged"
        assert any("quality" in w for w in warnings)

    def test_stock_below_domain_flagged(self, stock_decls):
        safe, warnings = StabilityValidator.check_boundary_conditions(
            {"trust": 500, "stigma": -10, "quality": 0.6}, stock_decls
        )
        assert not safe
        assert any("stigma" in w for w in warnings)

    def test_missing_variable_not_flagged(self, stock_decls):
        """Variables not in state dict should not cause errors."""
        safe, warnings = StabilityValidator.check_boundary_conditions(
            {"trust": 500}, stock_decls
        )
        assert safe, "Missing variables should be skipped, not flagged"


# ============================================================================
# check_step_size_sensitivity
# ============================================================================

class TestStepSizeSensitivity:
    def test_identical_results_zero_sensitivity(self, validator):
        def fn(dt: float) -> dict:
            return {"hawk_ratio": 0.667, "ess_deviation": 0.005}

        score = validator.check_step_size_sensitivity(fn)
        assert score == 0.0, f"Identical results should have 0 sensitivity, got {score}"

    def test_divergent_results_high_sensitivity(self, validator):
        def fn(dt: float) -> dict:
            return {"hawk_ratio": 0.6 + dt * 0.5}  # dt changes outcome significantly

        score = validator.check_step_size_sensitivity(fn)
        assert score > 0.05, f"Divergent results should have >5% sensitivity, got {score:.4f}"

    def test_simulate_fn_error_is_handled_gracefully(self, validator):
        call_count = [0]

        def fn(dt: float) -> dict:
            call_count[0] += 1
            if dt == 0.05:
                raise ValueError("simulation exploded")
            return {"x": 1.0}

        score = validator.check_step_size_sensitivity(fn)
        # Should not crash; should compute from surviving dt values
        assert score >= 0.0

    def test_single_dt_value_returns_zero(self, validator):
        """Need >= 2 dt values to compute sensitivity."""
        v = StabilityValidator(dt_values=[0.1])

        def fn(dt: float) -> dict:
            return {"x": dt}

        score = v.check_step_size_sensitivity(fn)
        assert score == 0.0

    def test_nan_values_are_skipped(self, validator):
        def fn(dt: float) -> dict:
            return {"x": float('nan') if dt == 0.2 else 1.0}

        score = validator.check_step_size_sensitivity(fn)
        assert score == 0.0, "NaN-only metric should be skipped"


# ============================================================================
# check_perturbation_sensitivity (base vs perturbed)
# ============================================================================

class TestPerturbationSensitivity:
    def test_empty_perturbed_returns_zero(self, validator):
        score = validator.check_perturbation_sensitivity(
            {"x": 0.5}, []
        )
        assert score == 0.0

    def test_identical_perturbed_returns_zero(self, validator):
        score = validator.check_perturbation_sensitivity(
            {"x": 0.5, "y": 1.0},
            [{"x": 0.5, "y": 1.0}, {"x": 0.5, "y": 1.0}],
        )
        assert score == 0.0

    def test_large_deviation_returns_high_score(self, validator):
        # Need >= MIN_PERTURBED_FOR_STAT (2) perturbed samples
        score = validator.check_perturbation_sensitivity(
            {"x": 0.5},
            [{"x": 0.9}, {"x": 0.1}, {"x": 0.3}],
        )
        assert score > 0.2, f"Large spread within [0,1] should be >0.2, got {score:.4f}"

    def test_mixed_keys_handled(self, validator):
        """Perturbed results may have different keys than base."""
        score = validator.check_perturbation_sensitivity(
            {"x": 0.5, "y": 1.0},
            [{"x": 0.5, "z": 2.0}, {"y": 1.0}],
        )
        assert 0.0 <= score <= 1.0

    def test_base_near_zero_handled(self, validator):
        """When base is near zero, use absolute deviation relative to max."""
        score = validator.check_perturbation_sensitivity(
            {"x": 0.0},
            [{"x": 0.1}, {"x": 0.2}],
        )
        assert 0.0 <= score <= 1.0


# ============================================================================
# check_perturbation_sensitivity_from_seeds
# ============================================================================

class TestPerturbationFromSeeds:
    def test_stable_seeds_low_sensitivity(self, validator, sample_per_seed_results):
        # Give domain decls for hawk_ratio + ess_deviation so the domain-based
        # normalisation applies (both are [0,1] probabilities)
        decls = {
            "hawk_ratio": VariableDecl("hawk_ratio", (0, 1), is_probability=True),
            "ess_deviation": VariableDecl("ess_deviation", (0, 1), is_probability=True),
        }
        score = _sensitivity_from_seeds(sample_per_seed_results, decls, validator)
        # hawk seeds are tightly clustered → std/domain ≈ 0.006 → very low
        assert score < DOMAIN_RATIO_MEDIUM, (
            f"Stable seeds should have score < {DOMAIN_RATIO_MEDIUM}, got {score:.4f}"
        )

    def test_unstable_seeds_high_sensitivity(self, validator, unstable_per_seed_results):
        score = _sensitivity_from_seeds(unstable_per_seed_results, {}, validator)
        assert score > DOMAIN_RATIO_MEDIUM, (
            f"Unstable seeds should have score > {DOMAIN_RATIO_MEDIUM}, got {score:.4f}"
        )

    def test_single_seed_returns_zero(self, validator):
        score = _sensitivity_from_seeds([
            {"seed": 42, "final_metrics": {"x": 0.5}}
        ], {}, validator)
        assert score == 0.0, "Single seed has no variance"

    def test_empty_returns_zero(self, validator):
        score = _sensitivity_from_seeds([], {}, validator)
        assert score == 0.0

    def test_missing_metrics_handled(self, validator):
        """Some seeds may lack certain metrics."""
        results = [
            {"seed": 1, "final_metrics": {"a": 1.0, "b": 2.0}},
            {"seed": 2, "final_metrics": {"a": 1.1}},  # missing b
            {"seed": 3, "final_metrics": {"a": 0.9, "b": 1.8}},
        ]
        score = _sensitivity_from_seeds(results, {}, validator)
        assert 0.0 <= score <= 1.0


# ============================================================================
# validate_from_seeds (complete pipeline)
# ============================================================================

class TestValidateFromSeeds:
    def test_stable_result_is_high(self, validator, sample_per_seed_results, stock_decls):
        # 用 haw_dove 的 domain decl 而非 trust/stigma decl
        hd_decls = [
            VariableDecl("hawk_ratio", (0, 1), is_probability=True, description="鹰派比例"),
            VariableDecl("ess_deviation", (0, 1), is_probability=True, description="ESS 偏差"),
        ]
        result = validator.validate_from_seeds(sample_per_seed_results, hd_decls)
        assert result.stable
        assert result.stability_level == "high", (
            f"Got {result.stability_level}, score={result.perturbation_sensitivity:.4f}"
        )
        assert result.bifurcation_risk == "none"

    def test_unstable_result_is_low_or_unstable(self, validator, unstable_per_seed_results):
        result = validator.validate_from_seeds(unstable_per_seed_results)
        assert not result.stable
        assert result.stability_level in ("low", "unstable")

    def test_result_is_serializable(self, validator, sample_per_seed_results):
        result = validator.validate_from_seeds(sample_per_seed_results)
        d = result.to_dict()
        assert isinstance(d, dict)
        assert "stability_level" in d

    def test_unstable_generates_warnings_and_recommendations(self, validator, unstable_per_seed_results):
        result = validator.validate_from_seeds(unstable_per_seed_results)
        assert len(result.warnings) > 0, "Unstable should produce warnings"
        assert len(result.recommendations) > 0, "Unstable should produce recommendations"


# ============================================================================
# from_sweep_results
# ============================================================================

class TestFromSweepResults:
    def test_flat_sweep_zero_sensitivity(self):
        """All configs produce same metrics → 0 sensitivity."""
        sweep = [
            {"param_value": 1.0, "final_metrics": {"x": 0.5}},
            {"param_value": 2.0, "final_metrics": {"x": 0.5}},
            {"param_value": 3.0, "final_metrics": {"x": 0.5}},
        ]
        score = StabilityValidator.from_sweep_results(sweep)
        assert score == 0.0

    def test_divergent_sweep_high_sensitivity(self):
        sweep = [
            {"param_value": 1.0, "final_metrics": {"x": 0.1}},
            {"param_value": 2.0, "final_metrics": {"x": 0.9}},
        ]
        score = StabilityValidator.from_sweep_results(sweep)
        assert score > 0.3, f"Divergent sweep should have high sensitivity, got {score:.4f}"

    def test_empty_sweep_zero(self):
        score = StabilityValidator.from_sweep_results([])
        assert score == 0.0

    def test_single_config_zero(self):
        score = StabilityValidator.from_sweep_results([
            {"param_value": 1.0, "final_metrics": {"x": 0.5}}
        ])
        assert score == 0.0


# ============================================================================
# CLI Command tests
# ============================================================================

class TestStabilityCLI:
    def test_cli_multi_seed_mode(self, tmp_path, sample_per_seed_results):
        """stability --data multi_seed.json should work."""
        data = {
            "status": "completed",
            "preset": "hawk_dove",
            "seeds": [42, 123, 456, 789, 1024],
            "per_seed_results": sample_per_seed_results,
            "aggregated_metrics": {
                "hawk_ratio": {"mean": 0.663, "std": 0.006},
            },
        }
        path = tmp_path / "multi_seed.json"
        path.write_text(json.dumps(data), encoding="utf-8")

        from scripts.nash_cli.commands.stability import cmd_stability
        args = Namespace(data=str(path), sweep=None, preset="hawk_dove")
        result = cmd_stability(args)

        assert result["status"] == "completed"
        assert result["meta"]["mode"] == "multi_seed"
        assert result["meta"]["num_seeds"] == 5
        assert "stability_level" in result
        # stable seeds — may be "high" or "medium" depending on domain decl

    def test_cli_single_seed_mode(self, tmp_path):
        """stability --data single.json --preset hawk_dove for boundary check."""
        data = {
            "status": "completed",
            "preset": "hawk_dove",
            "environment_type": "hawk_dove",
            "converged": True,
            "final_metrics": {"hawk_ratio": 0.66, "ess_deviation": 0.01},
        }
        path = tmp_path / "single.json"
        path.write_text(json.dumps(data), encoding="utf-8")

        from scripts.nash_cli.commands.stability import cmd_stability
        args = Namespace(data=str(path), sweep=None, preset="hawk_dove")
        result = cmd_stability(args)

        assert result["status"] == "completed"
        assert result["meta"]["mode"] == "single_seed"
        assert result["boundary_safe"] is True

    def test_cli_sweep_mode(self, tmp_path):
        """stability --sweep sweep.json should work."""
        sweep_data = {
            "status": "completed",
            "summary": {"parameter": "resource_value", "range": [1, 5], "step": 1},
            "results": [
                {"param_value": 1.0, "final_metrics": {"hawk_ratio": 0.5}, "converged": True, "total_rounds": 50},
                {"param_value": 2.0, "final_metrics": {"hawk_ratio": 0.6}, "converged": True, "total_rounds": 50},
                {"param_value": 3.0, "final_metrics": {"hawk_ratio": 0.7}, "converged": True, "total_rounds": 50},
            ],
        }
        path = tmp_path / "sweep.json"
        path.write_text(json.dumps(sweep_data), encoding="utf-8")

        from scripts.nash_cli.commands.stability import cmd_stability
        args = Namespace(data=None, sweep=str(path), preset=None)
        result = cmd_stability(args)

        assert result["status"] == "completed"
        assert result["meta"]["mode"] == "sweep"
        assert result["meta"]["num_configs"] == 3
        assert "perturbation_sensitivity" in result

    def test_cli_missing_both_data_and_sweep(self):
        """stability without --data or --sweep should error."""
        from scripts.nash_cli.commands.stability import cmd_stability
        args = Namespace(data=None, sweep=None, preset=None)
        result = cmd_stability(args)
        assert "error" in result

    def test_cli_file_not_found(self):
        """stability --data nonexistent.json should sys.exit."""
        from scripts.nash_cli.commands.stability import cmd_stability
        args = Namespace(data="/nonexistent/path.json", sweep=None, preset=None)
        with pytest.raises(SystemExit):
            cmd_stability(args)


# ============================================================================
# Threshold & edge cases
# ============================================================================

class TestThresholds:
    def test_domain_thresholds_are_monotonic(self):
        assert DOMAIN_RATIO_LOW < DOMAIN_RATIO_MEDIUM < DOMAIN_RATIO_HIGH

    def test_mad_thresholds_are_monotonic(self):
        assert CV_MAD_LOW < CV_MAD_MEDIUM < CV_MAD_HIGH

    def test_default_dt_values_nonempty(self):
        assert len(DEFAULT_DT_VALUES) >= 2

    def test_min_samples_for_sensitivity(self):
        assert MIN_SEEDS_FOR_SENSITIVITY == 3

    def test_custom_thresholds_accepted(self):
        v = StabilityValidator(domain_low=0.01, domain_medium=0.03, domain_high=0.10)
        assert v.domain_low == 0.01
        assert v.domain_medium == 0.03
        assert v.domain_high == 0.10

    def test_result_to_dict_all_fields_present(self):
        r = StabilityResult()
        d = r.to_dict()
        required = [
            "stable", "stability_level", "max_deviation",
            "perturbation_sensitivity", "step_size_sensitivity",
            "boundary_safe", "bifurcation_risk", "warnings", "recommendations",
        ]
        for key in required:
            assert key in d, f"Missing field {key}"


# ============================================================================
# Compatibility: old primitives.StabilityValidator API still works
# ============================================================================

class TestPrimitivesCompatibility:
    def test_old_api_still_works(self, stock_decls):
        """The StabilityValidator in primitives.py delegates to the new impl."""
        from src.primitives import StabilityValidator as OldAPI

        # check_boundary_conditions still works
        safe, warnings = OldAPI.check_boundary_conditions(
            {"trust": 500, "stigma": 0}, stock_decls
        )
        assert safe

        # check_perturbation_sensitivity still works with old signature
        score = OldAPI.check_perturbation_sensitivity(
            {"x": 0.5}, [{"x": 0.5}, {"x": 0.5}]
        )
        assert score == 0.0

        # check_step_size_sensitivity still works with old signature
        def fn(dt):
            return [1.0, 1.0, 1.0]  # returns list per old API

        score = OldAPI.check_step_size_sensitivity(fn)
        assert 0.0 <= score <= 1.0
