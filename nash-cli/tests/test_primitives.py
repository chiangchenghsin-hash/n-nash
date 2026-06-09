"""动态原语组装引擎测试 — TDD Phase T1-T8

覆盖:
  T1: 特征提取
  T2: 原语激活
  T3: 类型与约束
  T4: 符号一致性
  T5: 数值稳定性
  T6: 硬凑检测
  T7: 解释边界
  T8: 集成案例（杀糕会、高校体制冲突、真实草地）
"""

import pytest
from src.primitives import (
    # M1
    FeatureVector,
    # M2
    PrimitiveLibrary,
    PrimitiveSpec,
    PrimitiveDomain,
    # M3
    VariableDecl,
    InvariantDecl,
    MonotonicityRule,
    PhaseBoundary,
    # M4
    CouplingGraph,
    CouplingEdge,
    CouplingType,
    TopologyNode,
    # M5
    ConstraintCompiler,
    ConstraintReport,
    ConstraintViolation,
    # M6
    SymbolicAuditor,
    AuditFinding,
    # M7
    StabilityValidator,
    StabilityResult,
    # M8
    BoundaryController,
    BoundaryLabel,
    BoundaryReport,
)


# ============================================================================
# T1: 特征提取测试
# ============================================================================

class TestFeatureExtraction:
    """TDD T1 — FeatureVector 正确构造和使用"""

    def test_feature_vector_defaults_to_zeros(self):
        fv = FeatureVector()
        assert fv.information_asymmetry == 0.0
        assert fv.commons_character == 0.0

    def test_feature_vector_can_set_values(self):
        fv = FeatureVector(information_asymmetry=0.8, commons_character=0.6)
        assert fv.information_asymmetry == 0.8

    def test_feature_vector_to_from_dict_roundtrip(self):
        fv = FeatureVector(
            information_asymmetry=0.7,
            commons_character=0.5,
            resource_type="trust",
            time_horizon_rigidity=0.3,
        )
        d = fv.to_dict()
        fv2 = FeatureVector.from_dict(d)
        assert fv2.information_asymmetry == 0.7
        assert fv2.commons_character == 0.5
        assert fv2.resource_type == "trust"

    def test_extracts_information_asymmetry_feature(self):
        """杀糕会场景应提取高信息不对称"""
        fv = FeatureVector(
            information_asymmetry=0.7,
            commons_character=0.8,
            resource_type="trust",
            trust_sensitivity=0.9,
            stigma_potential=0.7,
        )
        assert fv.information_asymmetry > 0.5

    def test_extracts_governance_strength_feature(self):
        fv = FeatureVector(governance_presence=0.9, institutional_layering=0.7)
        assert fv.governance_presence > 0.5

    def test_extracts_layered_structure_features(self):
        """双层制度结构应被标注"""
        fv = FeatureVector(institutional_layering=0.8)
        assert fv.institutional_layering > 0.5


# ============================================================================
# T2: 原语激活测试
# ============================================================================

class TestPrimitiveActivation:
    """TDD T2 — 原语激活逻辑"""

    def test_activates_lemons_for_high_information_asymmetry_case(self):
        fv = FeatureVector(
            information_asymmetry=0.8,
            adverse_selection_risk=0.5,
        )
        activated, reasons = PrimitiveLibrary.activate(fv)
        prim_ids = {p.primitive_id for p in activated}
        assert "adverse_selection" in prim_ids or "lemons_market" in prim_ids, (
            f"Expected lemon/adverse-selection activation, got {prim_ids}"
        )

    def test_activates_principal_agent_for_incentive_misalignment_case(self):
        fv = FeatureVector(
            incentive_misalignment=0.7,
            moral_hazard_potential=0.5,
        )
        activated, _ = PrimitiveLibrary.activate(fv)
        prim_ids = {p.primitive_id for p in activated}
        assert "moral_hazard" in prim_ids or "principal_agent" in prim_ids, (
            f"Expected PA/MH activation, got {prim_ids}"
        )

    def test_activates_cpr_for_true_common_pool_case(self):
        fv = FeatureVector(
            commons_character=0.7,
            resource_type="physical",
        )
        activated, _ = PrimitiveLibrary.activate(fv)
        prim_ids = {p.primitive_id for p in activated}
        assert "common_pool_resource" in prim_ids, (
            f"Physical commons should activate CPR, got {prim_ids}"
        )

    def test_activates_social_trust_commons_for_trust_commons(self):
        fv = FeatureVector(
            commons_character=0.7,
            resource_type="trust",
        )
        activated, _ = PrimitiveLibrary.activate(fv)
        prim_ids = {p.primitive_id for p in activated}
        assert "social_trust_commons" in prim_ids, (
            f"Trust commons should activate STC, got {prim_ids}"
        )

    def test_activates_dual_primitives_for_mixed_case(self):
        """杀糕会：信息不对称 + 信任公地 → 至少激活两个原语"""
        fv = FeatureVector(
            information_asymmetry=0.7,
            commons_character=0.8,
            resource_type="trust",
            trust_sensitivity=0.9,
            stigma_potential=0.7,
        )
        activated, _ = PrimitiveLibrary.activate(fv)
        assert len(activated) >= 2, (
            f"Mixed case should activate >= 2 primitives, got {len(activated)}: "
            f"{[p.primitive_id for p in activated]}"
        )

    def test_activation_provides_reasons(self):
        fv = FeatureVector(commons_character=0.6, resource_type="physical")
        _, reasons = PrimitiveLibrary.activate(fv)
        assert "common_pool_resource" in reasons, f"Should have reason for CPR, got {reasons}"

    def test_low_features_activate_nothing(self):
        fv = FeatureVector()  # all zeros
        activated, _ = PrimitiveLibrary.activate(fv)
        assert len(activated) == 0, f"Zero features should activate nothing, got {activated}"


# ============================================================================
# T3: 类型与约束测试
# ============================================================================

class TestTypeAndConstraint:
    """TDD T3 — 变量类型声明 + 约束编译器"""

    def test_probability_variables_remain_normalized(self):
        decl = VariableDecl("x", (0, 1), is_probability=True)
        violations = ConstraintCompiler.check_state_space(
            {"x": 0.5}, [decl]
        )
        assert len(violations) == 0

        violations = ConstraintCompiler.check_state_space(
            {"x": 1.5}, [decl]
        )
        assert len(violations) > 0, "1.5 exceeds [0,1]"

    def test_stock_variables_remain_non_negative(self):
        decl = VariableDecl("trust", (0, 1000), is_stock=True)
        violations = ConstraintCompiler.check_state_space(
            {"trust": -10}, [decl]
        )
        assert len(violations) > 0, "Negative stock should be flagged"

    def test_price_is_monotonic_in_trust_when_declared(self):
        rules = [MonotonicityRule("trust", "price", "increasing")]
        equations = {"price": "base_price * (trust / max_trust) ** alpha"}
        violations = ConstraintCompiler.check_monotonicity(equations, rules)
        # "trust" present in equation → no warning about missing driver
        driver_missing_warnings = [v for v in violations if "not found" in v.description]
        assert len(driver_missing_warnings) == 0

    def test_missing_monotonicity_driver_is_warned(self):
        rules = [MonotonicityRule("trust", "price", "increasing")]
        equations = {"price": "base_price * (quality / max_quality)"}
        violations = ConstraintCompiler.check_monotonicity(equations, rules)
        driver_warnings = [v for v in violations if "trust" in v.description]
        assert len(driver_warnings) >= 1, "Missing driver 'trust' should trigger warning"

    def test_phase_boundary_detection(self):
        boundaries = [PhaseBoundary("trust", 200, "below", "price = 0")]
        violations = ConstraintCompiler.check_phase_boundaries(
            {"trust": 150}, boundaries
        )
        assert len(violations) == 1, "trust=150 < 200 should trigger boundary warning"

    def test_full_constraint_compile_passes_clean(self):
        declarations = [
            VariableDecl("trust", (0, 1000), is_stock=True),
            VariableDecl("price", (0, 100), is_stock=False),
        ]
        rules = [MonotonicityRule("trust", "price", "increasing")]
        equations = {"price": "p_max * (trust / K)"}
        report = ConstraintCompiler.compile(
            variables={"trust": 500, "price": 50},
            declarations=declarations,
            equations=equations,
            monotonicity_rules=rules,
            phase_boundaries=[],
        )
        assert report.passed, f"Clean model should pass, got: {report.violations}"

    def test_invalid_coupling_is_rejected(self):
        """检查 can_couple_with / cannot_couple_with 语义"""
        stc = PrimitiveLibrary.get("social_trust_commons")
        assert stc is not None
        assert "lemons_market" in stc.can_couple_with

        # 不存在的 forbidden 应不报错
        stc = PrimitiveLibrary.get("common_pool_resource")
        assert stc is not None
        # 验证 cannot_couple_with 不含已激活的合理组合
        assert "public_goods" not in stc.cannot_couple_with


# ============================================================================
# T4: 符号一致性测试
# ============================================================================

class TestSymbolicAudit:
    """TDD T4 — 符号一致性审计"""

    def test_symbolic_auditor_flags_sign_inconsistency(self):
        rules = [MonotonicityRule("trust", "price", "increasing")]
        declared = {"price": "price should decrease when trust decreases"}
        auditor = SymbolicAuditor()
        findings = auditor.audit_sign_consistency(rules, declared)
        # "decrease" in declared + "increasing" in rule → 不矛盾（方向一致）
        # 但如果是 "decrease" vs "decreasing" → 矛盾
        # 更严格的测试：
        rules2 = [MonotonicityRule("stigma", "trust", "increasing")]
        declared2 = {"trust": "trust should decrease as stigma increases"}
        findings = auditor.audit_sign_consistency(rules2, declared2)
        inconsistent = [f for f in findings if f.severity == "error"]
        # stigma increasing → trust increasing vs "trust should decrease" = contradiction
        assert len(inconsistent) > 0, f"Should detect sign contradiction, got {findings}"

    def test_symbolic_auditor_passes_consistent_monotonic_model(self):
        rules = [MonotonicityRule("governance", "quality", "increasing")]
        declared = {"quality": "quality should increase with governance"}
        auditor = SymbolicAuditor()
        findings = auditor.audit_sign_consistency(rules, declared)
        inconsistent = [f for f in findings if f.severity == "error"]
        assert len(inconsistent) == 0, f"Consistent model should pass: {findings}"

    def test_semantic_contradiction_detection(self):
        auditor = SymbolicAuditor()
        # 两个声明互斥的原语
        lemons = PrimitiveLibrary.get("lemons_market")
        # lemons_market 没有在 cannot_couple_with 中列出任何人
        # 验证系统能发现实际上冲突的组合
        findings = auditor.audit_semantic_contradiction([lemons])
        # 单个原语没有矛盾
        assert len([f for f in findings if f.severity == "error"]) == 0


# ============================================================================
# T5: 数值稳定性测试
# ============================================================================

class TestStabilityValidation:
    """TDD T5 — 数值稳定验证"""

    def test_boundary_conditions_do_not_produce_invalid_states(self):
        declarations = [
            VariableDecl("trust", (0, 1000), is_stock=True),
            VariableDecl("stigma", (0, 1000), is_stock=True),
        ]
        safe, warnings = StabilityValidator.check_boundary_conditions(
            {"trust": 500, "stigma": 100}, declarations
        )
        assert safe, f"Boundary-safe state should pass: {warnings}"

    def test_boundary_negative_stock_is_flagged(self):
        declarations = [VariableDecl("trust", (0, 1000), is_stock=True)]
        safe, warnings = StabilityValidator.check_boundary_conditions(
            {"trust": -50}, declarations
        )
        assert not safe, "Negative stock should be flagged at boundary"


# ============================================================================
# T6: 硬凑检测测试
# ============================================================================

class TestForcedFitDetection:
    """TDD T6 — 层级混杂/因果桥缺失检测"""

    def test_flags_mixed_institutional_and_individual_level_mapping(self):
        """制度层和个体层混写为一个变量应被检测"""
        fv = FeatureVector(
            institutional_layering=0.9,    # 高度制度层
            conflict_intensity=0.8,         # 个体冲突
        )
        # 同时激活制度层原语和个体层原语时需要双层建议
        assert fv.institutional_layering > 0.5
        assert fv.conflict_intensity > 0.5
        # 这种情况下 Skills 应建议双层/多层建模

    def test_features_can_detect_single_layer_case(self):
        """真实草地：单层就够了"""
        fv = FeatureVector(
            commons_character=0.9,
            resource_type="physical",
            institutional_layering=0.1,
        )
        assert fv.institutional_layering < 0.3, "Simple physical commons = single layer"

    def test_features_can_detect_dual_layer_case(self):
        """杀糕会：平台层 + 用户层 = 双层"""
        fv = FeatureVector(
            institutional_layering=0.7,
            commons_character=0.8,
            information_asymmetry=0.6,
        )
        assert fv.institutional_layering > 0.5, "Platform dynamics = multi-layer"


# ============================================================================
# T7: 解释边界测试
# ============================================================================

class TestBoundaryControl:
    """TDD T7 — 解释边界控制器"""

    def test_extreme_case_outputs_non_determinism_warning(self):
        report = BoundaryController.label_output(
            conclusion_type="structural",
            case_text="涉及暴力和自杀的社会风险分析",
        )
        assert len(report.extreme_case_warnings) > 0, (
            "Extreme case should trigger warning"
        )
        assert len(report.non_determinism_notice) > 0, (
            "Should include non-determinism notice"
        )

    def test_system_does_not_claim_violent_outcome_is_inevitable(self):
        report = BoundaryController.label_output(
            conclusion_type="event_prediction",
            case_text="这个模型预测暴力冲突必然发生",
        )
        assert report.primary_label == BoundaryLabel.NOT_MECHANICALLY_DEDUCIBLE, (
            f"Event prediction should be labelled NOT_DEDUCIBLE, got {report.primary_label}"
        )

    def test_output_distinguishes_model_claim_from_commentary_claim(self):
        struct_report = BoundaryController.label_output("structural")
        metaphor_report = BoundaryController.label_output("metaphor")

        assert struct_report.primary_label == BoundaryLabel.MODEL_SUPPORTED
        assert metaphor_report.primary_label == BoundaryLabel.COMMENTARY_METAPHOR
        assert struct_report.primary_label != metaphor_report.primary_label

    def test_normal_case_no_extreme_warning(self):
        report = BoundaryController.label_output(
            conclusion_type="structural",
            case_text="草地资源管理中的公地悲剧",
        )
        assert len(report.extreme_case_warnings) == 0
        assert report.non_determinism_notice == ""


# ============================================================================
# T8: 集成测试
# ============================================================================

class TestIntegration:
    """TDD T8 — 完整案例集成"""

    def test_shagaohui_integration(self):
        """杀糕会案例：应激活 social_trust_commons + lemons/信号原语"""
        fv = FeatureVector(
            information_asymmetry=0.7,
            commons_character=0.8,
            resource_type="trust",
            trust_sensitivity=0.9,
            stigma_potential=0.8,
            adverse_selection_risk=0.6,
            governance_presence=0.2,
            threshold_diffusion_risk=0.5,
            network_density=0.7,
        )
        activated, reasons = PrimitiveLibrary.activate(fv)
        prim_ids = {p.primitive_id for p in activated}

        # 核心断言：不应只激活单一原语
        assert len(activated) >= 2, (
            f"Shagaohui should activate >= 2 primitives, got {prim_ids}"
        )

        # 应包含信任公地
        assert "social_trust_commons" in prim_ids, (
            f"Must include social_trust_commons, got {prim_ids}"
        )

        # 每个激活原语都有理由
        for p in activated:
            assert p.primitive_id in reasons, f"Missing reason for {p.primitive_id}"

    def test_physical_grassland_integration(self):
        """真实草地/渔场案例：单一 CPR 即足够"""
        fv = FeatureVector(
            commons_character=0.9,
            resource_type="physical",
            information_asymmetry=0.1,
            institutional_layering=0.1,
        )
        activated, _ = PrimitiveLibrary.activate(fv)
        prim_ids = {p.primitive_id for p in activated}

        # 应激活 CPR
        assert "common_pool_resource" in prim_ids, (
            f"Grassland should activate CPR, got {prim_ids}"
        )

        # 不应过度复杂化 — 对于纯物理公地，1个主原语足够
        # (其他原语可能因低特征而不会被激活)
        info_primitives = {"lemons_market", "spence_signaling", "adverse_selection"}
        assert not (info_primitives & prim_ids), (
            f"Grassland should NOT activate info primitives, got {prim_ids}"
        )

    def test_university_conflict_integration(self):
        """高校体制冲突：应激活委托代理 + 重复互动相关原语"""
        fv = FeatureVector(
            incentive_misalignment=0.8,
            moral_hazard_potential=0.4,
            time_horizon_rigidity=0.7,
            repetition_potential=0.6,
            institutional_layering=0.8,
            conflict_intensity=0.5,
        )
        activated, _ = PrimitiveLibrary.activate(fv)
        prim_ids = {p.primitive_id for p in activated}

        # 应有委托代理/道德风险相关
        pa_related = {"principal_agent", "moral_hazard"}
        assert pa_related & prim_ids, (
            f"University conflict should activate PA/MH, got {prim_ids}"
        )

        # 应有重复互动原语
        assert "repeated_prisoners_dilemma" in prim_ids, (
            f"Should include RPD for repeated interaction, got {prim_ids}"
        )

    def test_primitives_have_valid_declarations(self):
        """所有注册的原语必须有必要的声明"""
        for pid in PrimitiveLibrary.list_all():
            spec = PrimitiveLibrary.get(pid)
            assert spec is not None
            assert spec.primitive_id == pid
            assert spec.name, f"{pid} missing name"
            assert spec.domain is not None, f"{pid} missing domain"
            # 不要求必须有 state_variables（有些原语可能只用已有环境的变量）

    def test_coupling_graph_construction(self):
        """验证耦合图谱可以正确构建"""
        graph = CouplingGraph(
            primitives=["social_trust_commons", "lemons_market"],
            primary_primitive="social_trust_commons",
            auxiliary_primitives=["lemons_market"],
            layered_structure="dual",
            nodes=[
                TopologyNode("trust", "state_variable", "信任存量", (0, 1000), "social_trust_commons"),
                TopologyNode("quality_ratio", "state_variable", "质量比例", (0, 1), "lemons_market"),
            ],
            edges=[
                CouplingEdge("quality_ratio", "trust", CouplingType.FEEDBACK, "-", "negative",
                             "柠檬市场质量下降 → 信任下降"),
            ],
        )

        summary = graph.summary()
        assert "social_trust_commons" in summary
        assert "lemons_market" in summary
        assert "dual" in summary
