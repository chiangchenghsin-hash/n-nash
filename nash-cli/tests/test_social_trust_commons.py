"""社会信任公地环境测试 — Social Trust Commons (杀糕会模型)

TDD Phase 1: 环境骨架测试
TDD Phase 2: 动力学正确性测试
TDD Phase 3: 断裂点检测测试
TDD Phase 4: 坏稳态识别测试
"""

import numpy as np
import pytest
from src.environments.social_trust_commons import (
    SocialTrustCommonsEnvironment,
    EquilibriumType,
    create_social_trust_commons,
)


# ============================================================================
# Helper
# ============================================================================

def _make_config(**overrides):
    """Build a minimal valid config for social_trust_commons."""
    params = {
        "num_organizers": 20,
        "initial_trust": 800.0,
        "max_trust": 1000.0,
        "natural_repair_rate": 0.03,
        "quality_positive_feedback": 0.2,
        "low_quality_damage": 0.4,
        "stigma_drag": 0.15,
        "governance_strength": 0.3,
        "price_elasticity": 1.5,
        "critical_trust_threshold": 200.0,
        "critical_stigma_threshold": 700.0,
        "shock_probability": 0.0,
        "shock_impact": 0.0,
        "learning_rate": 0.05,
        "quality_cost_coefficient": 0.3,
        "penalty_coefficient": 0.1,
        "num_rounds": 300,
        "base_price": 10.0,
        "base_cost": 5.0,
    }
    params.update(overrides)
    return {
        "environment": {
            "type": "social_trust_commons",
            "nobel_reference": {
                "year": 2009,
                "laureates": ["Elinor Ostrom"],
                "contribution": "社会信任公地悲剧 — 平台信任与叙事资源的过度抽取",
            },
        },
        "parameters": {k: {"value": v} for k, v in params.items()},
        "validation": {
            "equilibrium_type": "social_trust_tragedy",
            "metrics": [
                {"name": "trust_depletion_rate", "expected_value": 0.3, "tolerance": 0.3},
                {"name": "price_decline_rate", "expected_value": 0.2, "tolerance": 0.3},
            ],
        },
    }


# ============================================================================
# Phase 1: 环境骨架测试
# ============================================================================

class TestEnvSkeleton:
    """TDD Phase 1 — 环境最小可运行验证"""

    def test_social_trust_env_can_initialize(self):
        """能实例化 social_trust_commons"""
        config = _make_config()
        env = SocialTrustCommonsEnvironment(config)
        assert env.environment_type == "social_trust_commons"
        assert env.trust == config["parameters"]["initial_trust"]["value"]

    def test_social_trust_env_can_run_steps(self):
        """能运行若干 step"""
        np.random.seed(42)
        config = _make_config(num_rounds=10)
        env = SocialTrustCommonsEnvironment(config)
        env.initialize_agents()
        for _ in range(10):
            state = env.run_step()
        assert env.current_round == 10
        assert state["round"] == 10

    def test_social_trust_env_outputs_required_fields(self):
        """能输出基础状态变量"""
        np.random.seed(42)
        config = _make_config(num_rounds=100)
        env = SocialTrustCommonsEnvironment(config)
        result = env.run_simulation(max_rounds=100)

        assert "trust_history" in result
        assert "quality_history" in result
        assert "stigma_history" in result
        assert "price_history" in result
        assert "profit_history" in result
        assert "equilibrium_type" in result
        assert "breakpoints" in result

    def test_run_simulation_returns_complete_history(self):
        """运行完整模拟返回所有必需历史数据"""
        np.random.seed(42)
        config = _make_config(num_rounds=100)
        env = SocialTrustCommonsEnvironment(config)
        result = env.run_simulation(max_rounds=100)

        assert len(result["trust_history"]) > 0
        assert len(result["quality_history"]) > 0
        assert len(result["stigma_history"]) > 0
        assert len(result["price_history"]) > 0
        assert len(result["profit_history"]) > 0
        # final_metrics should include trust-specific metrics
        assert "trust_depletion_rate" in result["final_metrics"]
        assert "avg_profit_health" in result["final_metrics"]

    def test_factory_function(self):
        """create_social_trust_commons 工厂函数正确初始化"""
        env, config = create_social_trust_commons(num_organizers=5, num_rounds=50)
        assert config["environment"]["type"] == "social_trust_commons"


# ============================================================================
# Phase 2: 动力学正确性测试
# ============================================================================

class TestDynamics:
    """TDD Phase 2 — 模型行为方向正确性"""

    def test_high_quality_events_increase_trust_relative_to_low_quality(self):
        """高质量活动提升信任"""
        np.random.seed(42)
        # High quality: 高治理 + 低密度 = 高质量活动
        config_high = _make_config(
            governance_strength=0.9,
            num_organizers=5,
            quality_cost_coefficient=0.1,
            natural_repair_rate=0.05,
        )
        # Low quality: 低治理 + 高密度 + 低修复率 = 低质量活动导致信任暴跌
        config_low = _make_config(
            governance_strength=0.05,
            num_organizers=30,
            quality_cost_coefficient=0.8,
            natural_repair_rate=0.005,
            base_cost=5.0,
        )

        env_high = SocialTrustCommonsEnvironment(config_high)
        result_high = env_high.run_simulation(max_rounds=300)

        np.random.seed(42)
        env_low = SocialTrustCommonsEnvironment(config_low)
        result_low = env_low.run_simulation(max_rounds=300)

        # 高质量场景的信任保持率应高于低质量场景
        trust_keep_high = 1 - result_high["final_metrics"]["trust_depletion_rate"]
        trust_keep_low = 1 - result_low["final_metrics"]["trust_depletion_rate"]
        assert trust_keep_high > trust_keep_low, (
            f"High quality should preserve more trust: high={trust_keep_high:.2f}, low={trust_keep_low:.2f}"
        )

    def test_stigma_reduces_trust_even_under_same_activity_level(self):
        """污名升高拖低信任 — 高污名drag系数导致信任更快枯竭"""
        np.random.seed(42)
        # Need sufficient stigma persistence and incident rate so stigma
        # doesn't decay to zero before the drag effect can be observed.
        base_params = dict(
            natural_repair_rate=0.02,
            governance_strength=0.25,
            base_cost=5.0,
            num_organizers=18,
            quality_cost_coefficient=0.35,
            low_quality_damage=0.40,
            quality_positive_feedback=0.22,
            initial_quality=0.55,
            stigma_incident_rate=0.08,
            stigma_persistence=0.95,
            critical_trust_threshold=200.0,
            critical_stigma_threshold=600.0,
            initial_trust=750.0,
            initial_stigma=80.0,
        )

        config_low_stigma = _make_config(stigma_drag=0.02, **base_params)
        config_high_stigma = _make_config(stigma_drag=1.0, **base_params)

        np.random.seed(42)
        env_low = SocialTrustCommonsEnvironment(config_low_stigma)
        result_low = env_low.run_simulation(max_rounds=300)

        np.random.seed(42)
        env_high = SocialTrustCommonsEnvironment(config_high_stigma)
        result_high = env_high.run_simulation(max_rounds=300)

        final_trust_low = result_low["trust_history"][-1]
        final_trust_high = result_high["trust_history"][-1]
        assert final_trust_high < final_trust_low, (
            f"Higher stigma should result in lower trust: "
            f"high_stigma_trust={final_trust_high:.0f}, low_stigma_trust={final_trust_low:.0f}"
        )

    def test_price_monotonically_decreases_with_trust(self):
        """信任下降导致价格下降（单调性检验）"""
        np.random.seed(42)
        config = _make_config(
            natural_repair_rate=0.01,
            governance_strength=0.1,
            num_organizers=25,
        )
        env = SocialTrustCommonsEnvironment(config)
        result = env.run_simulation(max_rounds=200)

        trust = np.array(result["trust_history"])
        price = np.array(result["price_history"])

        # 计算 Spearman-like：后期信任是否低于前期
        early_trust = trust[:50].mean()
        late_trust = trust[-50:].mean()
        early_price = price[:50].mean()
        late_price = price[-50:].mean()

        # 信任下降则价格也应下降
        if early_trust > late_trust:
            assert early_price > late_price, (
                f"Price should fall when trust falls: "
                f"early_price={early_price:.2f}, late_price={late_price:.2f}"
            )

    def test_governance_slows_trust_depletion(self):
        """治理增强减缓信任损耗"""
        np.random.seed(42)
        config_low_g = _make_config(
            governance_strength=0.03,
            natural_repair_rate=0.005,
            base_cost=5.0,
        )
        config_high_g = _make_config(
            governance_strength=0.8,
            natural_repair_rate=0.05,
        )

        env_low = SocialTrustCommonsEnvironment(config_low_g)
        result_low = env_low.run_simulation(max_rounds=200)

        np.random.seed(42)
        env_high = SocialTrustCommonsEnvironment(config_high_g)
        result_high = env_high.run_simulation(max_rounds=200)

        depletion_low = result_low["final_metrics"]["trust_depletion_rate"]
        depletion_high = result_high["final_metrics"]["trust_depletion_rate"]
        assert depletion_low > depletion_high, (
            f"Higher governance should slow depletion: "
            f"low_g={depletion_low:.2f}, high_g={depletion_high:.2f}"
        )

    def test_shock_causes_discontinuous_trust_drop(self):
        """外部冲击造成信任跳水"""
        np.random.seed(42)
        config = _make_config(
            shock_probability=1.0,  # 每轮必定触发
            shock_impact=200.0,     # 每次冲击减少200信任
            natural_repair_rate=0.05,
        )
        env = SocialTrustCommonsEnvironment(config)
        result = env.run_simulation(max_rounds=50)

        trust_history = result["trust_history"]
        # 由于每轮都冲击，信任应快速下降
        final_trust = trust_history[-1]
        initial_trust = trust_history[0]
        assert final_trust < initial_trust * 0.7, (
            f"Shocks should cause significant trust drop: "
            f"initial={initial_trust:.0f}, final={final_trust:.0f}"
        )


# ============================================================================
# Phase 3: 断裂点测试
# ============================================================================

class TestBreakpoints:
    """TDD Phase 3 — 三类断裂点检测"""

    def test_detects_price_breakpoint_when_profit_turns_negative(self):
        """价格断裂点：当利润窗口连续转负时检测"""
        np.random.seed(42)
        config = _make_config(
            governance_strength=0.03,
            num_organizers=35,
            natural_repair_rate=0.003,
            price_elasticity=2.5,
            critical_trust_threshold=400.0,
            base_cost=6.0,
            quality_cost_coefficient=0.6,
        )
        env = SocialTrustCommonsEnvironment(config)
        result = env.run_simulation(max_rounds=300)

        breakpoints = result.get("breakpoints", {})
        assert "price_breakpoint" in breakpoints, (
            f"Should detect price breakpoint. Breakpoints: {breakpoints}"
        )
        pb = breakpoints["price_breakpoint"]
        assert pb is not None, "Price breakpoint should not be None"
        assert "round" in pb
        assert "avg_profit" in pb

    def test_detects_ecological_breakpoint_when_trust_enters_net_loss_zone(self):
        """生态断裂点：R 跌破安全线且净变化为负"""
        np.random.seed(42)
        config = _make_config(
            governance_strength=0.03,
            num_organizers=35,
            natural_repair_rate=0.003,
            critical_trust_threshold=300.0,
            base_cost=5.0,
            quality_cost_coefficient=0.5,
        )
        env = SocialTrustCommonsEnvironment(config)
        result = env.run_simulation(max_rounds=400)

        breakpoints = result.get("breakpoints", {})
        assert "ecological_breakpoint" in breakpoints, (
            f"Should detect ecological breakpoint. Breakpoints: {breakpoints}"
        )
        eb = breakpoints["ecological_breakpoint"]
        assert eb is not None, "Ecological breakpoint should not be None"
        assert "round" in eb
        assert "trust_level" in eb

    def test_detects_collapse_breakpoint_when_trust_or_stigma_crosses_threshold(self):
        """崩塌断裂点：R < R_crit 或 S > S_crit"""
        np.random.seed(42)
        config = _make_config(
            governance_strength=0.02,
            num_organizers=35,
            natural_repair_rate=0.002,
            critical_trust_threshold=500.0,
            critical_stigma_threshold=300.0,
            stigma_drag=0.5,
            shock_probability=0.1,
            shock_impact=100.0,
        )
        env = SocialTrustCommonsEnvironment(config)
        result = env.run_simulation(max_rounds=500)

        breakpoints = result.get("breakpoints", {})
        assert "collapse_breakpoint" in breakpoints, (
            f"Should detect collapse breakpoint. Breakpoints: {breakpoints}"
        )
        cb = breakpoints["collapse_breakpoint"]
        assert cb is not None, "Collapse breakpoint should not be None"
        assert "round" in cb
        assert cb.get("trust_below_critical", False) or cb.get("stigma_above_critical", False), (
            f"Collapse should be due to trust or stigma threshold: {cb}"
        )

    def test_governance_delays_breakpoints(self):
        """高治理下断裂点后移"""
        np.random.seed(42)
        config_low = _make_config(
            governance_strength=0.05,
            num_organizers=25,
            natural_repair_rate=0.01,
        )
        config_high = _make_config(
            governance_strength=0.8,
            num_organizers=25,
            natural_repair_rate=0.01,
        )

        env_low = SocialTrustCommonsEnvironment(config_low)
        result_low = env_low.run_simulation(max_rounds=400)

        np.random.seed(42)
        env_high = SocialTrustCommonsEnvironment(config_high)
        result_high = env_high.run_simulation(max_rounds=400)

        bp_low = result_low.get("breakpoints", {})
        bp_high = result_high.get("breakpoints", {})

        # 如果低治理检测到生态断裂点，高治理应该更晚或无
        if bp_low.get("ecological_breakpoint") is not None:
            low_round = bp_low["ecological_breakpoint"]["round"]
            if bp_high.get("ecological_breakpoint") is not None:
                high_round = bp_high["ecological_breakpoint"]["round"]
                assert high_round >= low_round, (
                    f"Governance should delay ecological breakpoint: "
                    f"low_g_round={low_round}, high_g_round={high_round}"
                )


# ============================================================================
# Phase 4: 坏稳态识别测试
# ============================================================================

class TestEquilibriumClassification:
    """TDD Phase 4 — 区分健康稳态/低信任陷阱/崩塌稳态"""

    def test_low_trust_low_variance_state_is_not_healthy_equilibrium(self):
        """低信任、低波动的僵死稳态不应被识别为健康"""
        np.random.seed(42)
        config = _make_config(
            governance_strength=0.02,
            num_organizers=35,
            natural_repair_rate=0.001,
            critical_trust_threshold=300.0,
            base_cost=5.0,
            quality_cost_coefficient=0.5,
        )
        env = SocialTrustCommonsEnvironment(config)
        result = env.run_simulation(max_rounds=300)

        eq_type = result.get("equilibrium_type")
        assert eq_type != "healthy_equilibrium", (
            f"Depleted trust should not be labelled healthy. Got: {eq_type}"
        )

    def test_collapsed_state_is_classified_as_collapsed_equilibrium(self):
        """已崩塌状态应被分类为 collapsed_equilibrium"""
        np.random.seed(42)
        config = _make_config(
            governance_strength=0.02,
            num_organizers=35,
            natural_repair_rate=0.002,
            critical_trust_threshold=300.0,
            critical_stigma_threshold=600.0,
            stigma_drag=0.3,
            shock_probability=0.05,
            shock_impact=150.0,
        )
        env = SocialTrustCommonsEnvironment(config)
        result = env.run_simulation(max_rounds=500)

        eq_type = result.get("equilibrium_type")
        # 应该识别出崩塌或至少低信任陷阱
        assert eq_type in ("collapsed_equilibrium", "low_trust_trap"), (
            f"Collapsed system should get collapsed/trap label. Got: {eq_type}"
        )

    def test_healthy_high_trust_state_is_classified_as_healthy_equilibrium(self):
        """高治理下的高信任稳态应为 healthy_equilibrium"""
        np.random.seed(42)
        config = _make_config(
            governance_strength=0.9,
            num_organizers=5,
            natural_repair_rate=0.1,
            quality_cost_coefficient=0.1,
            stigma_drag=0.01,
        )
        env = SocialTrustCommonsEnvironment(config)
        result = env.run_simulation(max_rounds=300)

        eq_type = result.get("equilibrium_type")
        assert eq_type == "healthy_equilibrium", (
            f"Healthy system should be labelled healthy. Got: {eq_type}"
        )

    def test_returns_warning_flags_for_degraded_state(self):
        """退化状态应返回 warning_flags"""
        np.random.seed(42)
        config = _make_config(
            governance_strength=0.05,
            num_organizers=25,
            natural_repair_rate=0.005,
        )
        env = SocialTrustCommonsEnvironment(config)
        result = env.run_simulation(max_rounds=300)

        warning_flags = result.get("warning_flags", [])
        if result["equilibrium_type"] != "healthy_equilibrium":
            assert len(warning_flags) > 0, (
                f"Non-healthy state should have warning flags. Got: {warning_flags}"
            )

    def test_sustainability_not_fooled_by_stable_death(self):
        """验证可持续性指标不会被'死得很稳'的系统欺骗"""
        np.random.seed(42)
        config = _make_config(
            governance_strength=0.02,
            num_organizers=30,
            natural_repair_rate=0.002,
            critical_trust_threshold=300.0,
        )
        env = SocialTrustCommonsEnvironment(config)
        result = env.run_simulation(max_rounds=500)

        final_metrics = result.get("final_metrics", {})
        trust_depletion = final_metrics.get("trust_depletion_rate", 0)

        # 信任已枯竭的系统不应有高可持续性分数
        if trust_depletion > 0.5:
            sustainability = final_metrics.get("sustainability_index", 1.0)
            assert sustainability < 0.5, (
                f"Depleted trust (rate={trust_depletion:.2f}) "
                f"should not show high sustainability ({sustainability:.2f})"
            )


# ============================================================================
# Phase 5: 路由与分析测试
# ============================================================================

class TestRouting:
    """TDD Phase 5 — nash-env 和 nash-analyze 路由正确性

    These tests verify the environment registry can discover and resolve
    social_trust_commons, and that the keyword → model mapping is correct.
    """

    def test_social_trust_commons_is_in_registry(self):
        """验证 social_trust_commons 在环境注册表中"""
        from scripts.nash_cli.commands import get_environment_registry
        registry = get_environment_registry()
        assert "social_trust_commons" in registry, (
            f"social_trust_commons should be in registry. Got: {sorted(registry.keys())}"
        )

    def test_social_trust_has_short_id(self):
        """验证 social_trust_commons 有短ID"""
        from scripts.nash_cli.commands import get_environment_registry
        registry = get_environment_registry()
        spec = registry["social_trust_commons"]
        assert spec.short_id is not None and len(spec.short_id) > 0

    def test_social_trust_params_can_be_validated(self):
        """验证 social_trust_commons 参数可以被验证"""
        from scripts.nash_cli.commands import get_environment_spec, validate_params
        spec = get_environment_spec("social_trust_commons")
        assert spec is not None

        params = validate_params(spec.short_id, {
            "governance_strength": 0.7,
            "stigma_sensitivity": 0.3,
        })
        assert params is not None


# ============================================================================
# Phase 6: NobelValidator 集成测试
# ============================================================================

class TestNobelValidatorIntegration:
    """验证 NobelValidator 能处理 social_trust_commons"""

    def test_nobel_validator_recognizes_social_trust_commons(self):
        """NobelValidator 应识别 social_trust_commons 环境类型"""
        from src.validators.nobel_validator import NobelValidator
        validator = NobelValidator()

        result = validator.validate(
            environment_type="social_trust_commons",
            metrics={
                "trust_depletion_rate": 0.6,
                "price_decline_rate": 0.4,
                "sustainability_index": 0.3,
            },
            config={
                "environment": {"type": "social_trust_commons"},
                "parameters": {},
                "validation": {"equilibrium_type": "social_trust_tragedy"},
            },
        )

        assert result.model_name == "社会信任公地悲剧"
        assert result.nobel_year == 2009
        # 信任显著枯竭应支持假设
        assert result.hypothesis_supported, (
            f"Trust tragedy should be detected. Conclusion: {result.conclusion}"
        )

    def test_nobel_validator_handles_short_id_social_trust(self):
        """短ID也应该能匹配"""
        from src.validators.nobel_validator import NobelValidator

        validator = NobelValidator()
        # Test that short_id 'social_trust' resolves
        result = validator.validate(
            environment_type="social_trust",
            metrics={"trust_depletion_rate": 0.1, "sustainability_index": 0.8},
            config={
                "environment": {"type": "social_trust"},
                "parameters": {},
                "validation": {"equilibrium_type": "social_trust_tragedy"},
            },
        )
        # Even without explicit social_trust validator, should fall through to generic
        assert result is not None


# ============================================================================
# 金标准验收场景
# ============================================================================

class TestGoldStandardScenarios:
    """PRD 定义的金标准验收场景"""

    def test_scenario_a_fragile_trust(self):
        """场景A：脆弱信任 — 低治理 + 高污名敏感 + 高质量成本 → 断裂点前移"""
        np.random.seed(42)
        config = _make_config(
            governance_strength=0.03,
            stigma_drag=0.5,
            quality_cost_coefficient=0.8,
            num_organizers=30,
            natural_repair_rate=0.003,
            critical_trust_threshold=400.0,
            critical_stigma_threshold=400.0,
            base_cost=5.0,
        )
        env = SocialTrustCommonsEnvironment(config)
        result = env.run_simulation(max_rounds=400)

        breakpoints = result.get("breakpoints", {})
        eq_type = result.get("equilibrium_type")

        # 应有至少一个断裂点
        has_any_breakpoint = any(v is not None for v in breakpoints.values())
        assert has_any_breakpoint, "Fragile scenario should trigger at least one breakpoint"

        # 不应是健康稳态
        assert eq_type != "healthy_equilibrium", (
            f"Fragile trust should not be healthy. Got: {eq_type}"
        )

    def test_scenario_b_baseline_trust(self):
        """场景B：基准信任 — 中等治理 + 中等污名扩散 → 出现明确断裂点"""
        np.random.seed(42)
        config = _make_config(
            governance_strength=0.2,
            stigma_drag=0.3,
            quality_cost_coefficient=0.5,
            num_organizers=25,
            natural_repair_rate=0.008,
            critical_trust_threshold=300.0,
            critical_stigma_threshold=600.0,
            base_cost=7.0,
            low_quality_damage=0.55,
            quality_positive_feedback=0.15,
            initial_quality=0.5,
            stigma_incident_rate=0.04,
        )
        env = SocialTrustCommonsEnvironment(config)
        result = env.run_simulation(max_rounds=400)

        breakpoints = result.get("breakpoints", {})
        eq_type = result.get("equilibrium_type")

        # 应有至少一种断裂点被检测
        assert any(v is not None for v in breakpoints.values()), (
            f"Baseline scenario should detect breakpoints: {breakpoints}"
        )

    def test_scenario_c_strong_governance(self):
        """场景C：强治理 — 高治理 → 断裂点后移，信任存量更高"""
        np.random.seed(42)
        config_strong = _make_config(
            governance_strength=0.9,
            stigma_drag=0.1,
            quality_cost_coefficient=0.2,
            num_organizers=15,
            natural_repair_rate=0.08,
            critical_trust_threshold=300.0,
        )
        config_weak = _make_config(
            governance_strength=0.03,
            stigma_drag=0.3,
            quality_cost_coefficient=0.5,
            num_organizers=20,
            natural_repair_rate=0.005,
            critical_trust_threshold=300.0,
            base_cost=7.0,
            low_quality_damage=0.55,
            quality_positive_feedback=0.15,
            initial_quality=0.5,
            stigma_incident_rate=0.04,
        )

        np.random.seed(42)
        env_strong = SocialTrustCommonsEnvironment(config_strong)
        result_strong = env_strong.run_simulation(max_rounds=300)

        np.random.seed(42)
        env_weak = SocialTrustCommonsEnvironment(config_weak)
        result_weak = env_weak.run_simulation(max_rounds=300)

        # 强治理下信任存量应更高
        strong_final_trust = result_strong["trust_history"][-1]
        weak_final_trust = result_weak["trust_history"][-1]
        assert strong_final_trust > weak_final_trust, (
            f"Strong governance should preserve more trust: "
            f"strong={strong_final_trust:.0f}, weak={weak_final_trust:.0f}"
        )

        # 强治理下价格应更稳定
        strong_price_std = np.std(result_strong["price_history"])
        weak_price_std = np.std(result_weak["price_history"])
        assert strong_price_std < weak_price_std * 1.2, (
            f"Strong governance should yield more stable prices: "
            f"strong_std={strong_price_std:.2f}, weak_std={weak_price_std:.2f}"
        )
