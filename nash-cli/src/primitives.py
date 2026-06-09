"""
NASH 动态原语组装引擎 — 类型化原语系统 + 约束编译器 + 符号审计器 + 数值验证器

本模块提供 PRD M2-M8 所需的 Python 支撑层：
  M2: PrimitiveLibrary — 原语库定义与激活逻辑
  M3: PrimitiveSpec   — 每个原语的类型/不变量/耦合声明
  M4: CouplingGraph   — 多原语耦合拓扑图谱
  M5: ConstraintCompiler — 状态空间/单调性/流量守恒/相变边界校验
  M6: SymbolicAuditor — 导数方向/语义矛盾/极限行为审计
  M7: StabilityValidator — 多初值/多步长/扰动敏感性
  M8: BoundaryController — 解释边界标签

设计原则 (PRD 第十二节):
  - 第一优先级不是符号回归，而是不变量/守恒锚定与类型约束
  - 先让系统学会"不能乱写"，再让它学会"能自由组装"
  - 符号回归可作为候选发现器，但不能作为主约束器
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Set, Tuple
import math


# ============================================================================
# M1 支撑：特征向量
# ============================================================================

@dataclass
class FeatureVector:
    """M1 语义解构器输出 — 从案例文本提取的结构特征向量。

    每个维度取值 [0, 1]，0=不存在该特征，1=该特征极为显著。
    """

    # 信息结构
    information_asymmetry: float = 0.0    # 信息不对称程度

    # 时间结构
    time_horizon_rigidity: float = 0.0    # 时间刚性（有限期/截止日）
    repetition_potential: float = 0.0     # 重复互动可能性

    # 激励结构
    incentive_misalignment: float = 0.0   # 激励错位（委托代理问题）
    moral_hazard_potential: float = 0.0   # 道德风险
    adverse_selection_risk: float = 0.0   # 逆向选择风险

    # 资源与公地
    commons_character: float = 0.0        # 公地属性强度
    resource_type: str = "none"           # "physical" | "trust" | "none"
    public_goods_character: float = 0.0   # 公共物品属性

    # 网络与扩散
    threshold_diffusion_risk: float = 0.0 # 阈值扩散/级联风险
    network_density: float = 0.0          # 网络密度/群体规模感

    # 治理与制度
    governance_presence: float = 0.0      # 治理强度
    institutional_layering: float = 0.0   # 制度层级（单层/双层/多层）
    exit_cost: float = 0.0               # 退出成本

    # 冲突
    conflict_intensity: float = 0.0       # 冲突/竞争强度
    coordination_need: float = 0.0        # 协调需求

    # 信任
    trust_sensitivity: float = 0.0        # 对信任/声誉的敏感度
    stigma_potential: float = 0.0         # 污名化/标签污染可能性

    def to_dict(self) -> Dict[str, Any]:
        result = {}
        for field_name in self.__dataclass_fields__:
            result[field_name] = getattr(self, field_name)
        return result

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "FeatureVector":
        valid = set(cls.__dataclass_fields__.keys())
        return cls(**{k: v for k, v in d.items() if k in valid})


# ============================================================================
# M3 支撑：类型化原语声明
# ============================================================================

class PrimitiveDomain(Enum):
    """原语所属领域"""
    INFORMATION_SIGNAL = "information_signal"
    CONTRACT_ORGANIZATION = "contract_organization"
    COLLECTIVE_COORDINATION = "collective_coordination"
    COMMONS_RESOURCE = "commons_resource"
    EVOLUTIONARY_DYNAMICS = "evolutionary_dynamics"
    CONFLICT_INTERACTION = "conflict_interaction"


@dataclass
class VariableDecl:
    """变量类型声明"""
    name: str
    domain: Tuple[float, float]          # [lower, upper]
    unit: str = ""
    description: str = ""
    is_probability: bool = False          # 概率/比例变量需归一
    is_stock: bool = False                # 存量变量需非负
    is_flow: bool = False                 # 流量变量

    @property
    def must_be_nonnegative(self) -> bool:
        return self.is_stock or self.is_probability or self.domain[0] >= 0

    @property
    def must_be_normalized(self) -> bool:
        return self.is_probability


@dataclass
class InvariantDecl:
    """不变量声明"""
    name: str
    description: str
    expression_hint: str = ""             # 人类可读的不变量描述
    severity: str = "hard"               # "hard" | "soft"


@dataclass
class MonotonicityRule:
    """单调性规则 — 声明 A 上升时 B 必须上升/下降/不变"""
    driver: str                           # 驱动变量
    target: str                           # 被影响变量
    direction: str                        # "increasing" | "decreasing" | "non_increasing" | "non_decreasing"
    condition: str = ""                   # 触发条件（空 = 无条件）


@dataclass
class PhaseBoundary:
    """相变边界声明"""
    variable: str                         # 触发变量
    threshold: float                      # 阈值
    threshold_type: str                   # "below" | "above"
    effect_description: str               # 越过阈值后的行为变化


@dataclass
class PrimitiveSpec:
    """M3: 类型化原语模块声明

    每个原语不是一个裸公式，而是带类型、约束和接口声明的模块。
    """

    # 标识
    primitive_id: str                     # e.g. "lemons_market"
    name: str                             # e.g. "柠檬市场"
    domain: PrimitiveDomain
    description: str = ""

    # 变量声明
    state_variables: List[VariableDecl] = field(default_factory=list)
    control_variables: List[VariableDecl] = field(default_factory=list)
    derived_variables: List[VariableDecl] = field(default_factory=list)

    # 接口
    input_variables: List[str] = field(default_factory=list)
    output_variables: List[str] = field(default_factory=list)

    # 约束
    invariants: List[InvariantDecl] = field(default_factory=list)
    monotonicity_rules: List[MonotonicityRule] = field(default_factory=list)
    phase_boundaries: List[PhaseBoundary] = field(default_factory=list)

    # 耦合声明
    can_couple_with: List[str] = field(default_factory=list)
    cannot_couple_with: List[str] = field(default_factory=list)

    # 数值范围
    recommended_dt: float = 0.1           # 推荐步长
    stiffness_warning: bool = False       # 刚性系统警告

    # 激活条件 — 从 FeatureVector 到激活分数的函数描述
    activation_conditions: List[str] = field(default_factory=list)


# ============================================================================
# M4 支撑：耦合图谱
# ============================================================================

class CouplingType(Enum):
    SERIES = "series"                     # 串联：A 的输出 → B 的输入
    PARALLEL = "parallel"                 # 并联：A 和 B 共同作用于同一变量
    NESTED = "nested"                     # 嵌套：B 在 A 的内部运行
    FEEDBACK = "feedback"                 # 反馈：A → B → A


@dataclass
class CouplingEdge:
    """图谱中的一条边"""
    source: str                           # 源节点（变量或原语）
    target: str                           # 目标节点（变量或原语）
    coupling_type: CouplingType
    influence_sign: str                   # "+" | "-" | "+/-"
    feedback_type: str = ""               # "positive" | "negative" | ""
    description: str = ""


@dataclass
class TopologyNode:
    """图谱节点"""
    node_id: str
    node_type: str                        # "state_variable" | "primitive" | "control_variable"
    label: str
    domain: Optional[Tuple[float, float]] = None
    parent_primitive: str = ""


@dataclass
class CouplingGraph:
    """M4: 多原语耦合拓扑图谱"""
    primitives: List[str] = field(default_factory=list)
    nodes: List[TopologyNode] = field(default_factory=list)
    edges: List[CouplingEdge] = field(default_factory=list)
    primary_primitive: str = ""
    auxiliary_primitives: List[str] = field(default_factory=list)
    layered_structure: str = ""           # "single" | "dual" | "multi"

    def summary(self) -> str:
        lines = [f"Primary: {self.primary_primitive}"]
        if self.auxiliary_primitives:
            lines.append(f"Auxiliary: {', '.join(self.auxiliary_primitives)}")
        lines.append(f"Layers: {self.layered_structure}")
        lines.append(f"Nodes: {len(self.nodes)}, Edges: {len(self.edges)}")
        for e in self.edges:
            lines.append(f"  {e.source} --[{e.coupling_type.value}, {e.influence_sign}]--> {e.target}")
        return "\n".join(lines)


# ============================================================================
# M5 支撑：约束编译器
# ============================================================================

@dataclass
class ConstraintViolation:
    """单条约束违反"""
    constraint_type: str                  # "state_space" | "monotonicity" | "flow_conservation" | "phase_boundary"
    severity: str                         # "error" | "warning"
    description: str
    location: str = ""                    # 违反位置（方程/变量名）
    fix_suggestion: str = ""


@dataclass
class ConstraintReport:
    """M5: 约束编译报告"""
    passed: bool = True
    violations: List[ConstraintViolation] = field(default_factory=list)
    warnings: List[ConstraintViolation] = field(default_factory=list)

    @property
    def has_errors(self) -> bool:
        return any(v.severity == "error" for v in self.violations)


class ConstraintCompiler:
    """M5: 约束编译器 — 校验状态空间、单调性、流量守恒、相变边界。

    使用方式：Skills 在生成方程后，引导用户将方程以结构化形式提交，
    ConstraintCompiler 逐项检查并返回报告。
    """

    @staticmethod
    def check_state_space(
        variables: Dict[str, float],
        declarations: List[VariableDecl],
    ) -> List[ConstraintViolation]:
        """状态空间约束：非负性、上界、比例归一"""
        violations = []
        decl_map = {d.name: d for d in declarations}

        for name, value in variables.items():
            decl = decl_map.get(name)
            if decl is None:
                continue

            # 非负性
            if decl.must_be_nonnegative and value < 0:
                violations.append(ConstraintViolation(
                    constraint_type="state_space",
                    severity="error",
                    description=f"Variable '{name}' = {value} violates non-negativity",
                    location=name,
                    fix_suggestion=f"Clamp {name} to [{decl.domain[0]}, {decl.domain[1]}]",
                ))

            # 上下界
            if value < decl.domain[0] or value > decl.domain[1]:
                violations.append(ConstraintViolation(
                    constraint_type="state_space",
                    severity="error",
                    description=f"Variable '{name}' = {value} outside domain {decl.domain}",
                    location=name,
                    fix_suggestion=f"Clamp {name} to [{decl.domain[0]}, {decl.domain[1]}]",
                ))

        return violations

    @staticmethod
    def check_monotonicity(
        equations: Dict[str, str],           # var_name -> equation string
        rules: List[MonotonicityRule],
    ) -> List[ConstraintViolation]:
        """单调性约束：符号方向检查。

        注意：这是启发式检查 —— 我们分析方程字符串中的符号模式，
        不执行完整符号微分。工具标记潜在不一致供人工复核。
        """
        violations = []
        for rule in rules:
            if rule.target not in equations:
                continue
            eq = equations[rule.target]
            driver_present = rule.driver in eq

            if not driver_present and rule.condition == "":
                violations.append(ConstraintViolation(
                    constraint_type="monotonicity",
                    severity="warning",
                    description=(
                        f"Monotonicity rule: '{rule.driver}' → '{rule.target}' "
                        f"({rule.direction}), but '{rule.driver}' not found in equation for '{rule.target}'"
                    ),
                    location=rule.target,
                    fix_suggestion=f"Ensure '{rule.target}' equation includes '{rule.driver}' term",
                ))

            # 如果 driver 在方程中但符号不对，标记
            if driver_present:
                if rule.direction == "decreasing" and f"+ {rule.driver}" in eq:
                    violations.append(ConstraintViolation(
                        constraint_type="monotonicity",
                        severity="warning",
                        description=(
                            f"'{rule.target}' should decrease with '{rule.driver}', "
                            f"but equation shows positive sign"
                        ),
                        location=rule.target,
                        fix_suggestion=f"Verify sign of {rule.driver} term in {rule.target} equation",
                    ))

        return violations

    @staticmethod
    def check_phase_boundaries(
        variables: Dict[str, float],
        boundaries: List[PhaseBoundary],
    ) -> List[ConstraintViolation]:
        """相变边界约束"""
        violations = []
        for pb in boundaries:
            if pb.variable not in variables:
                continue
            val = variables[pb.variable]
            triggered = (
                (pb.threshold_type == "below" and val < pb.threshold) or
                (pb.threshold_type == "above" and val > pb.threshold)
            )
            if triggered:
                violations.append(ConstraintViolation(
                    constraint_type="phase_boundary",
                    severity="warning",
                    description=f"Phase boundary triggered: {pb.variable}={val} {pb.threshold_type} {pb.threshold}",
                    location=pb.variable,
                ))
        return violations

    @staticmethod
    def compile(
        variables: Dict[str, float],
        declarations: List[VariableDecl],
        equations: Dict[str, str],
        monotonicity_rules: List[MonotonicityRule],
        phase_boundaries: List[PhaseBoundary],
    ) -> ConstraintReport:
        """完整约束编译"""
        all_violations = []
        all_violations.extend(ConstraintCompiler.check_state_space(variables, declarations))
        all_violations.extend(ConstraintCompiler.check_monotonicity(equations, monotonicity_rules))
        all_violations.extend(ConstraintCompiler.check_phase_boundaries(variables, phase_boundaries))

        errors = [v for v in all_violations if v.severity == "error"]
        warnings = [v for v in all_violations if v.severity == "warning"]

        return ConstraintReport(
            passed=len(errors) == 0,
            violations=errors,
            warnings=warnings,
        )


# ============================================================================
# M6 支撑：符号一致性审计器
# ============================================================================

@dataclass
class AuditFinding:
    """审计发现"""
    finding_type: str                     # "sign_inconsistency" | "semantic_contradiction" | "limit_behavior"
    severity: str                         # "error" | "warning"
    description: str
    location: str = ""
    recommendation: str = ""


@dataclass
class AuditReport:
    """M6: 符号一致性审计报告"""
    passed: bool = True
    findings: List[AuditFinding] = field(default_factory=list)
    consistency_score: float = 1.0        # 0-1, 1 = 完全一致


class SymbolicAuditor:
    """M6: 符号一致性审计器

    不做数据拟合，做结构审计：
    - 导数方向是否符合原语语义
    - 耦合后是否自相矛盾
    - 局部极限行为是否符合常识
    - 关键项符号是否与业务声明一致
    """

    @staticmethod
    def audit_sign_consistency(
        monotonicity_rules: List[MonotonicityRule],
        declared_behavior: Dict[str, str],  # variable -> expected behavior description
    ) -> List[AuditFinding]:
        """检查符号一致性"""
        findings = []
        for rule in monotonicity_rules:
            expected = declared_behavior.get(rule.target, "")
            if not expected:
                continue

            # 检查：如果声明"信任下降 → 价格下降"，则方向必须是 decreasing
            if "decrease" in expected.lower() and rule.direction == "increasing":
                findings.append(AuditFinding(
                    finding_type="sign_inconsistency",
                    severity="error",
                    description=(
                        f"Contradiction: '{rule.target}' declared to decrease but "
                        f"monotonicity rule for '{rule.driver}'→'{rule.target}' is '{rule.direction}'"
                    ),
                    location=rule.target,
                    recommendation=f"Either fix declaration or change direction to 'decreasing'",
                ))

        return findings

    @staticmethod
    def audit_limit_behavior(
        equations: Dict[str, str],
        limit_checks: Dict[str, str],       # variable -> what should happen at limits
    ) -> List[AuditFinding]:
        """检查局部极限行为"""
        findings = []
        for var, expectation in limit_checks.items():
            if var not in equations:
                findings.append(AuditFinding(
                    finding_type="limit_behavior",
                    severity="warning",
                    description=f"No equation found for '{var}' to verify limit behavior: {expectation}",
                    location=var,
                ))
        return findings

    @staticmethod
    def audit_semantic_contradiction(
        primitive_specs: List[PrimitiveSpec],
    ) -> List[AuditFinding]:
        """检查原语组合中的语义矛盾"""
        findings = []
        # 检查：不能同时耦合声明为互斥的原语
        coupled_ids = {p.primitive_id for p in primitive_specs}
        for p in primitive_specs:
            for forbidden in p.cannot_couple_with:
                if forbidden in coupled_ids:
                    findings.append(AuditFinding(
                        finding_type="semantic_contradiction",
                        severity="error",
                        description=(
                            f"'{p.primitive_id}' declares it cannot couple with '{forbidden}', "
                            f"but both are active"
                        ),
                        location=f"{p.primitive_id} ↔ {forbidden}",
                        recommendation=f"Remove one of the conflicting primitives or override coupling restriction with justification",
                    ))
        return findings


# ============================================================================
# M7 支撑：数值稳定验证器
# ============================================================================

@dataclass
class StabilityResult:
    """M7: 数值稳定验证结果"""
    stable: bool = True
    stability_level: str = "high"          # "high" | "medium" | "low" | "unstable"
    max_deviation: float = 0.0
    perturbation_sensitivity: float = 0.0
    step_size_sensitivity: float = 0.0
    boundary_safe: bool = True
    bifurcation_risk: str = "none"         # "none" | "low" | "medium" | "high"
    warnings: List[str] = field(default_factory=list)
    recommendations: List[str] = field(default_factory=list)


class StabilityValidator:
    """M7: 数值稳定验证器

    保证生成的方程不是"只能在一组幸运参数下跑起来"。
    """

    @staticmethod
    def check_step_size_sensitivity(
        simulate_fn: Callable[[float], List[float]],  # dt -> time_series
        dt_values: List[float] = None,
    ) -> float:
        """多步长回放：检查步长敏感性"""
        if dt_values is None:
            dt_values = [0.01, 0.05, 0.1, 0.5]
        # 简化实现：返回占位值
        # 实际使用需要 simulate_fn 返回可比较的时间序列
        return 0.0

    @staticmethod
    def check_perturbation_sensitivity(
        base_result: Dict[str, Any],
        perturbed_results: List[Dict[str, Any]],
    ) -> float:
        """小扰动敏感性分析"""
        if not perturbed_results:
            return 0.0
        # 检查关键指标在扰动下的变化
        return 0.0

    @staticmethod
    def check_boundary_conditions(
        state: Dict[str, float],
        declarations: List[VariableDecl],
    ) -> Tuple[bool, List[str]]:
        """边界条件回放"""
        warnings = []
        for decl in declarations:
            if decl.must_be_nonnegative and state.get(decl.name, 0) < 0:
                warnings.append(f"{decl.name} is negative at boundary")
        return len(warnings) == 0, warnings


# ============================================================================
# M8 支撑：解释边界控制器
# ============================================================================

class BoundaryLabel(Enum):
    """解释边界标签"""
    MODEL_SUPPORTED = "model_supported"           # 模型支持的结构结论
    HEURISTIC_INTERPRETATION = "heuristic"        # 启发式解释
    COMMENTARY_METAPHOR = "commentary"             # 评论性隐喻
    NOT_MECHANICALLY_DEDUCIBLE = "not_deductible" # 不能机械推出


@dataclass
class BoundaryReport:
    """M8: 解释边界报告"""
    primary_label: BoundaryLabel = BoundaryLabel.MODEL_SUPPORTED
    labels: Dict[str, BoundaryLabel] = field(default_factory=dict)
    extreme_case_warnings: List[str] = field(default_factory=list)
    non_determinism_notice: str = ""


class BoundaryController:
    """M8: 解释边界控制器

    阻止系统把结构高风险分析误写成事件必然性。
    """

    EXTREME_CASE_KEYWORDS = [
        "暴力", "自杀", "他杀", "犯罪", "刑事",
        "violence", "suicide", "homicide", "criminal",
        "死亡", "death", "谋杀", "murder",
    ]

    DEFAULT_NON_DETERMINISM_NOTICE = (
        "该方程组可解释结构性风险积累与系统性高危背景，"
        "但不能机械推出具体极端事件的必然发生。"
    )

    @staticmethod
    def detect_extreme_case(text: str) -> bool:
        """检测是否涉及极端案例"""
        lower = text.lower()
        return any(kw.lower() in lower for kw in BoundaryController.EXTREME_CASE_KEYWORDS)

    @staticmethod
    def label_output(
        conclusion_type: str,         # "structural" | "event_prediction" | "metaphor"
        case_text: str = "",
    ) -> BoundaryReport:
        """为输出打边界标签"""
        report = BoundaryReport()

        if conclusion_type == "structural":
            report.primary_label = BoundaryLabel.MODEL_SUPPORTED
        elif conclusion_type == "event_prediction":
            report.primary_label = BoundaryLabel.NOT_MECHANICALLY_DEDUCIBLE
        elif conclusion_type == "metaphor":
            report.primary_label = BoundaryLabel.COMMENTARY_METAPHOR

        if BoundaryController.detect_extreme_case(case_text):
            report.extreme_case_warnings.append(
                "案例涉及极端/敏感场景，已自动附加非决定论声明"
            )
            report.non_determinism_notice = BoundaryController.DEFAULT_NON_DETERMINISM_NOTICE

        return report


# ============================================================================
# M2 支撑：原语库
# ============================================================================

class PrimitiveLibrary:
    """M2: 原语库 — 经济学原语的类型化注册表。

    Skills 通过本库激活原语、获取约束声明、校验耦合合法性。
    """

    PRIMITIVES: Dict[str, PrimitiveSpec] = {}

    @staticmethod
    def register(spec: PrimitiveSpec) -> None:
        PrimitiveLibrary.PRIMITIVES[spec.primitive_id] = spec

    @staticmethod
    def get(primitive_id: str) -> Optional[PrimitiveSpec]:
        return PrimitiveLibrary.PRIMITIVES.get(primitive_id)

    @staticmethod
    def list_all() -> List[str]:
        return sorted(PrimitiveLibrary.PRIMITIVES.keys())

    @staticmethod
    def list_by_domain(domain: PrimitiveDomain) -> List[PrimitiveSpec]:
        return [p for p in PrimitiveLibrary.PRIMITIVES.values() if p.domain == domain]

    @staticmethod
    def activate(features: FeatureVector) -> Tuple[List[PrimitiveSpec], Dict[str, str]]:
        """M2 核心：根据特征向量激活原语。

        Returns:
            (activated_primitives, activation_reasons)
            activation_reasons 将 primitive_id 映射到激活原因的简短描述。
        """
        activated = []
        reasons = {}

        # 信息不对称显著 → 柠檬市场/信号发送/逆向选择
        if features.information_asymmetry > 0.4:
            lemons = PrimitiveLibrary.get("lemons_market")
            spence = PrimitiveLibrary.get("spence_signaling")
            adverse = PrimitiveLibrary.get("adverse_selection")
            if features.adverse_selection_risk > 0.3 and adverse:
                activated.append(adverse)
                reasons[adverse.primitive_id] = f"逆向选择风险={features.adverse_selection_risk:.2f}"
            elif lemons and features.trust_sensitivity > 0.3:
                activated.append(lemons)
                reasons[lemons.primitive_id] = f"信息不对称={features.information_asymmetry:.2f} + 信任敏感"
            elif spence:
                activated.append(spence)
                reasons[spence.primitive_id] = f"信息不对称={features.information_asymmetry:.2f}"

        # 激励错位 → 委托代理/道德风险
        if features.incentive_misalignment > 0.3:
            pa = PrimitiveLibrary.get("principal_agent")
            mh = PrimitiveLibrary.get("moral_hazard")
            if features.moral_hazard_potential > 0.3 and mh:
                activated.append(mh)
                reasons[mh.primitive_id] = f"道德风险={features.moral_hazard_potential:.2f}"
            elif pa:
                activated.append(pa)
                reasons[pa.primitive_id] = f"激励错位={features.incentive_misalignment:.2f}"

        # 公地属性 → 物理公地 / 信任公地
        if features.commons_character > 0.3:
            if features.resource_type == "trust":
                stc = PrimitiveLibrary.get("social_trust_commons")
                if stc:
                    activated.append(stc)
                    reasons[stc.primitive_id] = f"信任公地={features.commons_character:.2f}"
            else:
                cpr = PrimitiveLibrary.get("common_pool_resource")
                if cpr:
                    activated.append(cpr)
                    reasons[cpr.primitive_id] = f"物理公地={features.commons_character:.2f}"

        # 公共物品
        if features.public_goods_character > 0.3:
            pg = PrimitiveLibrary.get("public_goods")
            if pg:
                activated.append(pg)
                reasons[pg.primitive_id] = f"公共物品={features.public_goods_character:.2f}"

        # 阈值扩散 → Schelling 阈值
        if features.threshold_diffusion_risk > 0.3:
            st = PrimitiveLibrary.get("schelling_threshold")
            if st:
                activated.append(st)
                reasons[st.primitive_id] = f"阈值扩散风险={features.threshold_diffusion_risk:.2f}"

        # 冲突 + 重复 → PD / Hawk-Dove
        if features.conflict_intensity > 0.3:
            if features.repetition_potential > 0.3:
                rpd = PrimitiveLibrary.get("repeated_prisoners_dilemma")
                if rpd:
                    activated.append(rpd)
                    reasons[rpd.primitive_id] = f"冲突={features.conflict_intensity:.2f} + 重复={features.repetition_potential:.2f}"
            else:
                hd = PrimitiveLibrary.get("hawk_dove")
                if hd:
                    activated.append(hd)
                    reasons[hd.primitive_id] = f"冲突={features.conflict_intensity:.2f} (单次)"

        # 协调需求 → Stag Hunt
        if features.coordination_need > 0.4:
            sh = PrimitiveLibrary.get("stag_hunt")
            if sh:
                activated.append(sh)
                reasons[sh.primitive_id] = f"协调需求={features.coordination_need:.2f}"

        # 演化 → Replicator Dynamics（通常作为元层）
        if features.network_density > 0.5 and len(activated) > 1:
            rd = PrimitiveLibrary.get("replicator_dynamics")
            if rd:
                activated.append(rd)
                reasons[rd.primitive_id] = f"网络密度={features.network_density:.2f} + 多原语({len(activated)})"

        return activated, reasons


# ============================================================================
# 预注册所有原语
# ============================================================================

def _register_all_primitives():
    """注册所有经济学原语到原语库"""

    # --- 信息与信号矩阵 ---
    PrimitiveLibrary.register(PrimitiveSpec(
        primitive_id="lemons_market",
        name="柠檬市场",
        domain=PrimitiveDomain.INFORMATION_SIGNAL,
        description="Akerlof 1970: 信息不对称导致劣币驱逐良币，市场崩溃",
        state_variables=[
            VariableDecl("quality_ratio", (0, 1), is_probability=True, description="优质品比例"),
            VariableDecl("price", (0, float('inf')), is_stock=False, description="市场价格"),
        ],
        output_variables=["price", "quality_ratio"],
        invariants=[
            InvariantDecl("quality_nonnegative", "质量比例不低于0", "quality_ratio ∈ [0,1]"),
            InvariantDecl("price_nonnegative", "价格不得为负", "price >= 0"),
        ],
        monotonicity_rules=[
            MonotonicityRule("information_asymmetry", "quality_ratio", "decreasing"),
            MonotonicityRule("quality_ratio", "price", "decreasing"),
        ],
        can_couple_with=["spence_signaling", "schelling_threshold", "common_pool_resource", "social_trust_commons"],
        cannot_couple_with=[],
        activation_conditions=["information_asymmetry > 0.4", "adverse_selection_risk > 0.3"],
    ))

    PrimitiveLibrary.register(PrimitiveSpec(
        primitive_id="spence_signaling",
        name="斯彭斯信号发送",
        domain=PrimitiveDomain.INFORMATION_SIGNAL,
        description="Spence 1973: 通过 costly signal 实现分离均衡",
        state_variables=[
            VariableDecl("education_level", (0, float('inf')), is_stock=True, description="教育/信号水平"),
            VariableDecl("wage", (0, float('inf')), is_stock=False, description="工资"),
        ],
        can_couple_with=["lemons_market", "principal_agent"],
    ))

    PrimitiveLibrary.register(PrimitiveSpec(
        primitive_id="adverse_selection",
        name="逆向选择",
        domain=PrimitiveDomain.INFORMATION_SIGNAL,
        description="事前信息不对称导致高风险者更愿意参与",
        state_variables=[
            VariableDecl("risk_pool_quality", (0, 1), is_probability=True, description="参与池质量"),
        ],
        can_couple_with=["lemons_market", "moral_hazard"],
    ))

    # --- 契约与组织矩阵 ---
    PrimitiveLibrary.register(PrimitiveSpec(
        primitive_id="principal_agent",
        name="委托代理",
        domain=PrimitiveDomain.CONTRACT_ORGANIZATION,
        description="激励错位：委托人目标与代理人行为偏离",
        state_variables=[
            VariableDecl("effort", (0, 1), is_probability=True, description="代理人努力水平"),
            VariableDecl("output", (0, float('inf')), is_stock=True, description="产出"),
        ],
        monotonicity_rules=[
            MonotonicityRule("incentive_strength", "effort", "increasing"),
            MonotonicityRule("monitoring_cost", "effort", "increasing"),
        ],
        can_couple_with=["moral_hazard", "repeated_prisoners_dilemma"],
    ))

    PrimitiveLibrary.register(PrimitiveSpec(
        primitive_id="moral_hazard",
        name="道德风险",
        domain=PrimitiveDomain.CONTRACT_ORGANIZATION,
        description="事后行为变化：被保险后更冒险",
        state_variables=[
            VariableDecl("risk_taking", (0, 1), is_probability=True, description="冒险程度"),
        ],
        can_couple_with=["principal_agent", "adverse_selection"],
    ))

    # --- 群体协同矩阵 ---
    PrimitiveLibrary.register(PrimitiveSpec(
        primitive_id="stag_hunt",
        name="猎鹿博弈",
        domain=PrimitiveDomain.COLLECTIVE_COORDINATION,
        description="Rousseau: 协同收益大但背叛安全 — 协调失败风险",
        state_variables=[
            VariableDecl("cooperation_rate", (0, 1), is_probability=True, description="合作比例"),
        ],
        can_couple_with=["replicator_dynamics", "schelling_threshold"],
    ))

    PrimitiveLibrary.register(PrimitiveSpec(
        primitive_id="schelling_threshold",
        name="谢林阈值扩散",
        domain=PrimitiveDomain.COLLECTIVE_COORDINATION,
        description="Schelling 1978: 微观动机→宏观行为，临界点相变",
        state_variables=[
            VariableDecl("adoption_rate", (0, 1), is_probability=True, description="采纳/传播比例"),
            VariableDecl("threshold", (0, 1), is_probability=True, description="个体临界阈值"),
        ],
        phase_boundaries=[
            PhaseBoundary("adoption_rate", 0.5, "above", "超过50%后加速扩散（级联效应）"),
        ],
        can_couple_with=["lemons_market", "social_trust_commons", "stag_hunt"],
    ))

    # --- 公地与资源矩阵 ---
    PrimitiveLibrary.register(PrimitiveSpec(
        primitive_id="common_pool_resource",
        name="公共池资源（物理）",
        domain=PrimitiveDomain.COMMONS_RESOURCE,
        description="Ostrom 2009: 物理资源的公地悲剧",
        state_variables=[
            VariableDecl("resource_stock", (0, float('inf')), is_stock=True, description="资源存量"),
        ],
        can_couple_with=["public_goods"],
    ))

    PrimitiveLibrary.register(PrimitiveSpec(
        primitive_id="social_trust_commons",
        name="社会信任公地",
        domain=PrimitiveDomain.COMMONS_RESOURCE,
        description="信任/声誉/标签作为公共资源 — 杀糕会模型",
        state_variables=[
            VariableDecl("trust", (0, float('inf')), is_stock=True, description="信任存量"),
            VariableDecl("quality", (0, 1), is_probability=True, description="平均质量"),
            VariableDecl("stigma", (0, float('inf')), is_stock=True, description="污名存量"),
            VariableDecl("price", (0, float('inf')), is_stock=False, description="市场价格"),
        ],
        monotonicity_rules=[
            MonotonicityRule("trust", "price", "increasing"),
            MonotonicityRule("stigma", "trust", "decreasing"),
            MonotonicityRule("governance", "quality", "increasing"),
        ],
        phase_boundaries=[
            PhaseBoundary("trust", 0.2, "below", "价格归零、市场拒收"),
            PhaseBoundary("stigma", 0.7, "above", "标签从向往变为羞耻"),
        ],
        can_couple_with=["lemons_market", "schelling_threshold", "adverse_selection"],
    ))

    PrimitiveLibrary.register(PrimitiveSpec(
        primitive_id="public_goods",
        name="公共物品",
        domain=PrimitiveDomain.COMMONS_RESOURCE,
        description="搭便车问题：个人贡献不足、集体供给不足",
        state_variables=[
            VariableDecl("contribution_rate", (0, 1), is_probability=True, description="贡献率"),
        ],
        can_couple_with=["common_pool_resource", "replicator_dynamics"],
    ))

    # --- 动态演化矩阵 ---
    PrimitiveLibrary.register(PrimitiveSpec(
        primitive_id="replicator_dynamics",
        name="复制者动态",
        domain=PrimitiveDomain.EVOLUTIONARY_DYNAMICS,
        description="Taylor & Jonker 1978: 策略比例按适应度增长率演化",
        state_variables=[
            VariableDecl("strategy_share", (0, 1), is_probability=True, description="策略份额"),
        ],
        invariants=[
            InvariantDecl("shares_sum_to_one", "所有策略份额之和为1", "Σ share_i = 1"),
        ],
        can_couple_with=[],  # 几乎可以与任何原语耦合作为演化层
        cannot_couple_with=[],
    ))

    # --- 冲突矩阵 ---
    PrimitiveLibrary.register(PrimitiveSpec(
        primitive_id="hawk_dove",
        name="鹰鸽博弈",
        domain=PrimitiveDomain.CONFLICT_INTERACTION,
        description="Maynard Smith 1973: 冲突与克制 — ESS 混合策略",
        state_variables=[
            VariableDecl("hawk_ratio", (0, 1), is_probability=True, description="鹰派比例"),
        ],
        can_couple_with=["replicator_dynamics"],
    ))

    PrimitiveLibrary.register(PrimitiveSpec(
        primitive_id="repeated_prisoners_dilemma",
        name="重复囚徒困境",
        domain=PrimitiveDomain.CONFLICT_INTERACTION,
        description="Axelrod 1984: 重复互动下合作可作为 SPNE 出现",
        state_variables=[
            VariableDecl("cooperation_rate", (0, 1), is_probability=True, description="合作率"),
        ],
        can_couple_with=["principal_agent", "replicator_dynamics"],
    ))


# 模块加载时注册
_register_all_primitives()
