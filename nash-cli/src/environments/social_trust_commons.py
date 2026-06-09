"""
社会信任公地环境 (Social Trust Commons / Platform Trust Commons)

基于 Ostrom (2009) 公地悲剧框架扩展 — 针对平台信任、陌生人社交、
公信力市场和标签生态的互联网公地悲剧建模。

核心区别 vs common_pool_resource:
  - 资源是"信任与叙事"，不是物理库存
  - 包含价格函数 p(R)："信任越高越赚钱"
  - 包含质量变量 Q："先降质保利润，再退出"
  - 包含污名变量 S："标签从向往到羞耻的相变"
  - 区分三类断裂点：价格断裂、生态断裂、崩塌断裂
  - 区分三种稳态：healthy_equilibrium / low_trust_trap / collapsed_equilibrium

动力学方程 (PRD F2-F6):
  R(t+1) = R(t) + γ*R*(1-R/K) + β*Q*A - δ*(1-Q)*A - ξ*S + θ(t)
  Q(t+1) = Q(t) + ρ*G - ν*A - κ*low_margin
  S(t+1) = σ*S(t) + φ*incident + ψ*1(R < R_crit)
  p(R)    = p_max * (R/K)^α
  π_i     = p(R)*a_i - c0 - λ*q_i - ω*penalty_i
"""

import numpy as np
from typing import Dict, Any, List, Optional, Tuple
from dataclasses import dataclass, field
from src.environments.base import BaseEnvironment, ConvergenceResult


# ============================================================================
# Equilibrium type enum
# ============================================================================

class EquilibriumType:
    """稳态分类"""
    HEALTHY = "healthy_equilibrium"
    LOW_TRUST_TRAP = "low_trust_trap"
    COLLAPSED = "collapsed_equilibrium"
    TRANSITIONING = "transitioning"


# ============================================================================
# Breakpoint containers
# ============================================================================

@dataclass
class BreakpointInfo:
    detected: bool = False
    round: int = 0
    details: Dict[str, Any] = field(default_factory=dict)


@dataclass
class Organizer:
    """信任/组局者代理"""
    agent_id: int
    activity_level: float       # 每个组织者抽取的信任量（物理单位，非比例）
    quality_choice: float       # 活动质量 (0-1)
    learning_rate: float = 0.05

    def choose_activity(self, price: float, governance: float,
                        num_organizers: int) -> float:
        """根据价格信号决定组局量（抽取的信任量）

        价格越高越活跃；治理越严越收敛。
        活动量以信任单位计 — 与信任存量的再生/损耗方程直接对接。
        """
        # 基础活动幅度：价格驱动的抽取量
        incentive = price * 1.5          # 价格高则多办局
        deterrence = governance * 8.0    # 治理严格则收敛
        base = 5.0                       # 基础最小活跃度（信任单位）

        noise = np.random.normal(0, 1.0)
        desired = np.clip(incentive - deterrence + noise + base, 0.5, 40.0)
        self.activity_level = 0.7 * self.activity_level + 0.3 * desired
        return self.activity_level

    def choose_quality(self, margin: float, governance: float) -> float:
        """根据利润空间选择活动质量

        margin < 0: 亏损 → 降质保命
        margin < 3: 薄利 → 轻微降质
        margin >= 3: 高利润 → 提升质量
        """
        if margin <= -3:
            target = max(0.05, self.quality_choice - 0.20)
        elif margin <= 0:
            target = max(0.10, self.quality_choice - 0.10)
        elif margin < 5.0:
            target = max(0.15, self.quality_choice - 0.02)
        else:
            target = min(0.95, self.quality_choice + 0.06)

        # 治理推动质量提升
        target = min(0.95, target + governance * 0.12)

        self.quality_choice = 0.65 * self.quality_choice + 0.35 * target
        return self.quality_choice


# ============================================================================
# Main Environment
# ============================================================================

class SocialTrustCommonsEnvironment(BaseEnvironment):
    """
    社会信任公地环境 (杀糕会模型)

    状态变量:
      R_t : 信任存量 Trust Stock
      A_t : 活跃组局者数量 Active Organizers
      Q_t : 平均活动质量 Average Quality
      S_t : 污名/标签污染 Stigma Stock

    派生量:
      p(R)    : 价格函数
      π_i     : 单个组织者利润
      D_t     : 信任损耗量
      G_t     : 治理强度 Governance
    """

    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)

        # ---- 信任资源参数 ----
        self.trust = self._p("initial_trust", 800.0)
        self.max_trust = self._p("max_trust", 1000.0)
        self.natural_repair_rate = self._p("natural_repair_rate", 0.03)      # γ
        self.quality_positive_feedback = self._p("quality_positive_feedback", 0.2)  # β
        self.low_quality_damage = self._p("low_quality_damage", 0.4)         # δ
        self.stigma_drag = self._p("stigma_drag", 0.15)                      # ξ

        # ---- 治理参数 ----
        self.governance_strength = self._p("governance_strength", 0.3)       # G

        # ---- 价格函数参数 ----
        self.price_elasticity = self._p("price_elasticity", 1.5)             # α
        self.base_price = self._p("base_price", 10.0)                        # p_max

        # ---- 临界阈值 ----
        self.critical_trust_threshold = self._p("critical_trust_threshold", 200.0)   # R_crit
        self.critical_stigma_threshold = self._p("critical_stigma_threshold", 700.0) # S_crit

        # ---- 冲击参数 ----
        self.shock_probability = self._p("shock_probability", 0.0)
        self.shock_impact = self._p("shock_impact", 0.0)

        # ---- 代理参数 ----
        self.num_organizers = self._p("num_organizers", 20)
        self.learning_rate = self._p("learning_rate", 0.05)
        self.quality_cost_coeff = self._p("quality_cost_coefficient", 0.3)   # λ
        self.penalty_coefficient = self._p("penalty_coefficient", 0.1)       # ω
        self.base_cost = self._p("base_cost", 5.0)                           # c0 — per-unit cost

        # ---- 初始质量与污名 ----
        self.quality = self._p("initial_quality", 0.6)
        self.stigma = self._p("initial_stigma", 0.0)

        # ---- 质量演化参数 ----
        self.quality_governance_effect = 0.15                                # ρ
        self.quality_density_penalty = 0.003                                 # ν (per unit of activity density)
        self.quality_margin_penalty = 0.05                                   # κ

        # ---- 污名演化参数 ----
        self.stigma_persistence = self._p("stigma_persistence", 0.85)        # σ
        self.stigma_incident_rate = self._p("stigma_incident_rate", 0.02)    # φ
        self.stigma_critical_multiplier = 1.5                                # ψ

        # ---- 代理 ----
        self.organizers: List[Organizer] = []

        # ---- 历史记录 ----
        self._round_history: List[Dict[str, Any]] = []
        self._trust_history: List[float] = []
        self._quality_history: List[float] = []
        self._stigma_history: List[float] = []
        self._price_history: List[float] = []
        self._profit_history: List[float] = []

        # ---- 断裂点追踪 ----
        self._price_breakpoint: Optional[BreakpointInfo] = None
        self._ecological_breakpoint: Optional[BreakpointInfo] = None
        self._collapse_breakpoint: Optional[BreakpointInfo] = None
        self._profit_negative_streak: int = 0
        self._trust_net_loss_streak: int = 0

        # ---- 稳态分类(每次check_convergence时更新) ----
        self._equilibrium_type: str = EquilibriumType.TRANSITIONING

    # ========================================================================
    # Public API (BaseEnvironment interface)
    # ========================================================================

    def initialize_agents(self) -> None:
        """初始化组织者代理"""
        self.organizers = []
        for i in range(self.num_organizers):
            organizer = Organizer(
                agent_id=i,
                activity_level=np.random.uniform(5, 15),
                quality_choice=np.random.uniform(0.3, 0.7),
                learning_rate=self.learning_rate,
            )
            self.organizers.append(organizer)

        # Reset all state
        self.trust = self._p("initial_trust", 800.0)
        self.quality = self._p("initial_quality", 0.6)
        self.stigma = self._p("initial_stigma", 0.0)
        self.current_round = 0
        self._round_history = []
        self._trust_history = []
        self._quality_history = []
        self._stigma_history = []
        self._price_history = []
        self._profit_history = []
        self._price_breakpoint = None
        self._ecological_breakpoint = None
        self._collapse_breakpoint = None
        self._profit_negative_streak = 0
        self._trust_net_loss_streak = 0
        self._equilibrium_type = EquilibriumType.TRANSITIONING

    def run_step(self) -> Dict[str, Any]:
        """运行一步模拟 —— 完整动力学方程"""
        self.current_round += 1

        # ---- Step 1: 计算价格 ----
        price = self._calculate_price()

        # ---- Step 2: 代理决策 ----
        total_activity = 0.0
        total_quality = 0.0
        profits = []

        for org in self.organizers:
            # 2a: 决定组局量（信任抽取量）
            activity = org.choose_activity(
                price, self.governance_strength, self.num_organizers
            )
            total_activity += activity

            # 2b: 先用上轮质量计算本轮利润，再根据利润更新质量（时序正确）
            revenue = price * activity
            # 成本随活动量线性增长：base_cost=每单位活动的固定成本
            base_cost_total = self.base_cost * activity
            quality_cost = self.quality_cost_coeff * org.quality_choice * activity * 2
            penalty_cost = (self.penalty_coefficient
                           * (1 - org.quality_choice)
                           * self.governance_strength
                           * activity * 2)
            total_cost = base_cost_total + quality_cost + penalty_cost
            margin = revenue - total_cost
            profit = margin

            # 基于本轮利润更新质量（影响下轮）
            quality = org.choose_quality(margin, self.governance_strength)
            total_quality += quality

            profits.append(profit)

        avg_quality = total_quality / max(1, self.num_organizers)
        avg_profit = np.mean(profits) if profits else 0.0

        # ---- Step 3: 信任演化 (F2 方程) ----
        old_trust = self.trust

        # 逻辑斯蒂再生
        regeneration = self.natural_repair_rate * self.trust * (1 - self.trust / self.max_trust)

        # 使用上轮平均质量计算本轮的信任效应
        # 本轮的 quality 是 *新* 质量（将用于下轮），上轮质量 = self.quality
        prev_quality = self.quality
        quality_boost = self.quality_positive_feedback * prev_quality * total_activity
        quality_damage = self.low_quality_damage * (1 - prev_quality) * total_activity
        stigma_loss = self.stigma_drag * self.stigma

        shock = 0.0
        if self.shock_probability > 0 and np.random.random() < self.shock_probability:
            shock = self.shock_impact

        delta_trust = regeneration + quality_boost - quality_damage - stigma_loss - shock
        self.trust = np.clip(old_trust + delta_trust, 0.0, self.max_trust)

        # ---- Step 4: 质量演化 (F4 方程) ----
        density = total_activity / max(1, self.num_organizers)
        margin_pressure = 0.0
        if avg_profit < 2.0:
            margin_pressure = self.quality_margin_penalty * (1.0 - np.clip(avg_profit / 2.0, -2, 1))
        delta_quality = (
            self.quality_governance_effect * self.governance_strength
            - self.quality_density_penalty * density
            - margin_pressure
        )
        self.quality = np.clip(avg_quality + delta_quality, 0.05, 0.95)

        # ---- Step 5: 污名演化 (F5 方程) ----
        # S(t+1) = σ*S(t) + φ*incident + ψ*1(R < R_crit)
        incident = self.stigma_incident_rate * (1 - prev_quality) * total_activity
        trust_critical = 1.0 if self.trust < self.critical_trust_threshold else 0.0
        new_stigma = (
            self.stigma_persistence * self.stigma
            + incident
            + self.stigma_critical_multiplier * trust_critical
        )
        self.stigma = np.clip(new_stigma, 0.0, self.max_trust)

        # ---- Step 6: 记录历史 ----
        round_data = {
            "round": self.current_round,
            "trust_before": old_trust,
            "trust_after": self.trust,
            "delta_trust": delta_trust,
            "regeneration": regeneration,
            "quality_boost": quality_boost,
            "quality_damage": quality_damage,
            "stigma_loss": stigma_loss,
            "shock": shock,
            "avg_quality": prev_quality,
            "stigma": self.stigma,
            "price": price,
            "avg_profit": avg_profit,
            "total_activity": total_activity,
            "profits": profits,
        }
        self._round_history.append(round_data)
        self._trust_history.append(self.trust)
        self._quality_history.append(prev_quality)
        self._stigma_history.append(self.stigma)
        self._price_history.append(price)
        self._profit_history.append(avg_profit)

        # ---- Step 7: 检测断裂点 ----
        self._detect_breakpoints(avg_profit, delta_trust)

        return {
            "round": self.current_round,
            "trust": self.trust,
            "price": price,
            "quality": prev_quality,
            "stigma": self.stigma,
            "avg_profit": avg_profit,
        }

    def check_convergence(self) -> ConvergenceResult:
        """检查系统稳态 —— 区分三种健康状态 (F8)

        不得再把 "低资源 + 低价格 + 低波动" 直接视为正向收敛。
        要求至少运行 100 轮才开始检查收敛。
        """
        if len(self._round_history) < 50:
            return ConvergenceResult(
                converged=False,
                metric_name="social_trust_health",
                current_value=0.0,
                expected_value=0.5,
                tolerance=0.2,
                message="数据不足，需要至少 50 轮互动",
            )

        # 要求最少 100 轮才允许收敛 — 但鼓励运行更久以观察长期趋势
        min_rounds_before_convergence = 100
        if self.current_round < min_rounds_before_convergence:
            return ConvergenceResult(
                converged=False,
                metric_name="social_trust_health",
                current_value=self.trust / self.max_trust,
                expected_value=0.5,
                tolerance=0.2,
                message=f"运行中... ({self.current_round} < {min_rounds_before_convergence} 轮)",
            )

        recent = self._round_history[-50:]
        recent_trust = [h["trust_after"] for h in recent]
        trust_std = np.std(recent_trust)
        avg_trust = np.mean(recent_trust)
        avg_price = np.mean([h["price"] for h in recent])
        avg_profit_recent = np.mean([h["avg_profit"] for h in recent])
        avg_stigma = np.mean([h["stigma"] for h in recent])

        # 稳定性判定 — 更严格的阈值
        trust_stability_threshold = self.max_trust * 0.02
        is_stable = trust_std < trust_stability_threshold

        # 状态分类
        trust_ratio = avg_trust / self.max_trust
        stigma_ratio = avg_stigma / self.max_trust

        # 必须检查信任和价格水平，不能只看波动
        if trust_ratio < 0.03 or (trust_ratio < 0.05 and avg_price < 0.1):
            # 信任几乎枯竭 + 价格几乎归零 → 崩溃
            self._equilibrium_type = EquilibriumType.COLLAPSED
        elif trust_ratio < 0.2:
            if is_stable:
                self._equilibrium_type = EquilibriumType.LOW_TRUST_TRAP
            else:
                self._equilibrium_type = EquilibriumType.TRANSITIONING
        elif trust_ratio > 0.5 and avg_profit_recent > 2.0 and is_stable:
            self._equilibrium_type = EquilibriumType.HEALTHY
        elif trust_ratio > 0.3 and avg_profit_recent > 0 and is_stable:
            self._equilibrium_type = EquilibriumType.HEALTHY
        elif is_stable:
            self._equilibrium_type = EquilibriumType.LOW_TRUST_TRAP
        else:
            self._equilibrium_type = EquilibriumType.TRANSITIONING

        converged = is_stable

        # 构建消息
        emoji = {
            EquilibriumType.HEALTHY: "✅",
            EquilibriumType.LOW_TRUST_TRAP: "⚠️",
            EquilibriumType.COLLAPSED: "❌",
            EquilibriumType.TRANSITIONING: "⏳",
        }

        message = (
            f"{emoji.get(self._equilibrium_type, '?')} "
            f"{self._equilibrium_type} | "
            f"信任: {avg_trust:.0f}/{self.max_trust:.0f} | "
            f"价格: {avg_price:.2f} | "
            f"利润: {avg_profit_recent:.2f} | "
            f"污名: {avg_stigma:.0f}"
        )

        return ConvergenceResult(
            converged=converged,
            metric_name="social_trust_health",
            current_value=trust_ratio,
            expected_value=0.5,
            tolerance=0.2,
            message=message,
        )

    def get_validation_metrics(self) -> Dict[str, float]:
        """获取验证指标 (F7 组合式可持续性)"""
        if not self._round_history:
            return {
                "trust_depletion_rate": 0.0,
                "sustainability_index": 0.5,
                "price_decline_rate": 0.0,
                "avg_quality": 0.5,
                "avg_stigma": 0.0,
                "avg_profit_health": 0.5,
            }

        recent = self._round_history[-50:] if len(self._round_history) >= 50 else self._round_history
        initial_trust = self._round_history[0]["trust_after"]
        current_trust = self._round_history[-1]["trust_after"]

        # 信任枯竭率
        trust_depletion_rate = max(0, (initial_trust - current_trust) / max(1, initial_trust))

        # 组合式可持续性指数 (F7)
        trust_level_ratio = current_trust / self.max_trust
        recent_deltas = [h["delta_trust"] for h in recent]
        net_direction = np.mean(recent_deltas)
        avg_price = np.mean(self._price_history[-50:]) if self._price_history else 0

        # 不能只比较本轮抽取与再生，必须综合多因素
        sustainability = (
            0.30 * np.clip(trust_level_ratio, 0, 1)
            + 0.20 * np.clip(net_direction / max(1.0, self.max_trust * 0.05), -1, 1)
            + 0.15 * np.clip(avg_price / max(0.1, self.base_price), 0, 1)
            + 0.20 * np.clip(self.quality, 0, 1)
            + 0.15 * (1 - np.clip(self.stigma / max(1.0, self.max_trust * 0.5), 0, 1))
        )
        sustainability = np.clip(sustainability, 0.0, 1.0)

        # 价格下降率
        price_history_recent = self._price_history[-50:] if self._price_history else [0]
        if price_history_recent[0] > 0.01:
            price_decline_rate = (price_history_recent[0] - price_history_recent[-1]) / price_history_recent[0]
        else:
            price_decline_rate = 0.0
        price_decline_rate = max(0, price_decline_rate)

        # 利润健康度
        avg_profit_recent = np.mean([h["avg_profit"] for h in recent])
        profit_health = np.clip(avg_profit_recent / max(0.1, self.base_price), 0, 2)
        profit_health = np.clip(profit_health, 0, 1)

        return {
            "trust_depletion_rate": trust_depletion_rate,
            "sustainability_index": sustainability,
            "price_decline_rate": price_decline_rate,
            "avg_quality": self.quality,
            "avg_stigma": self.stigma,
            "avg_profit_health": profit_health,
        }

    # ========================================================================
    # Internal helpers
    # ========================================================================

    def _calculate_price(self) -> float:
        """F3: 价格函数 p(R) = p_max * (R/K)^α

        信任越高越赚钱；信任低于临界值价格归零。
        """
        if self.trust < self.critical_trust_threshold:
            return 0.0
        return self.base_price * (self.trust / self.max_trust) ** self.price_elasticity

    def _detect_breakpoints(self, avg_profit: float, delta_trust: float) -> None:
        """F9: 检测三类断裂点"""
        # ---- 价格断裂点：利润连续转负 ----
        if self._price_breakpoint is None:
            if avg_profit < 0:
                self._profit_negative_streak += 1
            else:
                self._profit_negative_streak = max(0, self._profit_negative_streak - 1)

            if self._profit_negative_streak >= 10:
                self._price_breakpoint = BreakpointInfo(
                    detected=True,
                    round=self.current_round,
                    details={
                        "type": "price",
                        "avg_profit": float(avg_profit),
                        "negative_streak": self._profit_negative_streak,
                        "trust": float(self.trust),
                        "price": float(self._calculate_price()),
                    },
                )

        # ---- 生态断裂点：R 跌破安全线 + 长期净损耗 ----
        if self._ecological_breakpoint is None:
            if delta_trust < 0 and self.trust < self.max_trust * 0.5:
                self._trust_net_loss_streak += 1
            else:
                self._trust_net_loss_streak = max(0, self._trust_net_loss_streak - 1)

            if self._trust_net_loss_streak >= 20:
                self._ecological_breakpoint = BreakpointInfo(
                    detected=True,
                    round=self.current_round,
                    details={
                        "type": "ecological",
                        "trust_level": float(self.trust),
                        "trust_ratio": float(self.trust / self.max_trust),
                        "net_loss_streak": self._trust_net_loss_streak,
                        "delta_trust": float(delta_trust),
                    },
                )

        # ---- 崩塌断裂点：R < R_crit 或 S > S_crit ----
        if self._collapse_breakpoint is None:
            trust_collapsed = self.trust < self.critical_trust_threshold
            stigma_collapsed = self.stigma > self.critical_stigma_threshold
            if trust_collapsed or stigma_collapsed:
                self._collapse_breakpoint = BreakpointInfo(
                    detected=True,
                    round=self.current_round,
                    details={
                        "type": "collapse",
                        "trust_below_critical": trust_collapsed,
                        "stigma_above_critical": stigma_collapsed,
                        "trust": float(self.trust),
                        "R_crit": float(self.critical_trust_threshold),
                        "stigma": float(self.stigma),
                        "S_crit": float(self.critical_stigma_threshold),
                    },
                )

    def _get_warning_flags(self) -> List[str]:
        """生成警告标志"""
        flags = []
        et = getattr(self, '_equilibrium_type', None)
        if et == EquilibriumType.LOW_TRUST_TRAP:
            flags.append("trust_stuck_at_low_level")
            flags.append("profit_margin_thin")
        if et == EquilibriumType.COLLAPSED:
            flags.append("trust_collapsed")
            flags.append("market_refuses_to_pay")
            flags.append("price_at_zero")
        if self.stigma > 500:
            flags.append("stigma_label_pollution_high")
        if self.quality < 0.3:
            flags.append("quality_degradation_severe")
        if self._price_breakpoint and self._price_breakpoint.detected:
            flags.append("price_breakpoint_crossed")
        if self._ecological_breakpoint and self._ecological_breakpoint.detected:
            flags.append("ecological_breakpoint_crossed")
        if self._collapse_breakpoint and self._collapse_breakpoint.detected:
            flags.append("collapse_breakpoint_crossed")
        return flags

    def _breakpoints_to_dict(self) -> Dict[str, Optional[Dict[str, Any]]]:
        """序列化断裂点为字典"""
        result = {}
        for name, bp in [
            ("price_breakpoint", self._price_breakpoint),
            ("ecological_breakpoint", self._ecological_breakpoint),
            ("collapse_breakpoint", self._collapse_breakpoint),
        ]:
            if bp is not None and bp.detected:
                result[name] = {
                    "detected": True,
                    "round": bp.round,
                    **bp.details,
                }
            else:
                result[name] = None
        return result

    # ========================================================================
    # Override _generate_result
    # ========================================================================

    def _generate_result(self) -> Dict[str, Any]:
        """生成模拟结果 —— 扩展基类输出"""
        final_metrics = self.get_validation_metrics()
        convergence = self.check_convergence()

        # 确保 equilibrium_type 已设置
        eq_type = getattr(self, '_equilibrium_type', None)
        if eq_type is None:
            _ = self.check_convergence()
            eq_type = getattr(self, '_equilibrium_type', EquilibriumType.TRANSITIONING)

        return {
            "environment_type": self.environment_type,
            "total_rounds": self.current_round,
            "converged": bool(convergence.converged),
            "convergence_message": convergence.message,
            "final_metrics": final_metrics,
            "metrics_history": self.metrics_history,
            "history": self.history,
            # 扩展字段 (PRD 数据与接口要求)
            "trust_history": self._trust_history,
            "quality_history": self._quality_history,
            "stigma_history": self._stigma_history,
            "price_history": self._price_history,
            "profit_history": self._profit_history,
            "equilibrium_type": eq_type,
            "health_status": "uncertain" if eq_type == EquilibriumType.TRANSITIONING else eq_type,
            "warning_flags": self._get_warning_flags(),
            "breakpoints": self._breakpoints_to_dict(),
        }


# ============================================================================
# Factory
# ============================================================================

def create_social_trust_commons(
    num_organizers: int = 20,
    initial_trust: float = 800.0,
    max_trust: float = 1000.0,
    natural_repair_rate: float = 0.03,
    quality_positive_feedback: float = 0.2,
    low_quality_damage: float = 0.4,
    stigma_drag: float = 0.15,
    governance_strength: float = 0.3,
    price_elasticity: float = 1.5,
    critical_trust_threshold: float = 200.0,
    critical_stigma_threshold: float = 700.0,
    learning_rate: float = 0.05,
    num_rounds: int = 300,
) -> tuple:
    """创建社会信任公地环境

    Args:
        num_organizers: 组局者数量
        initial_trust: 初始信任存量
        max_trust: 最大信任容量
        natural_repair_rate: 自然修复率 γ
        quality_positive_feedback: 高质量正反馈 β
        low_quality_damage: 低质量伤害 δ
        stigma_drag: 污名拖累系数 ξ
        governance_strength: 治理强度 G
        price_elasticity: 价格弹性 α
        critical_trust_threshold: 信任临界阈值 R_crit
        critical_stigma_threshold: 污名临界阈值 S_crit
        learning_rate: 学习率
        num_rounds: 模拟轮数

    Returns:
        (environment, standard_config)
    """
    standard_config = {
        "environment": {
            "type": "social_trust_commons",
            "nobel_reference": {
                "year": 2009,
                "laureates": ["Elinor Ostrom"],
                "contribution": "社会信任公地悲剧 — 对平台信任与叙事资源的治理分析",
            },
        },
        "parameters": {
            "num_organizers": {"value": num_organizers, "description": "组局者/活动组织者数量"},
            "initial_trust": {"value": initial_trust, "description": "初始社会信任存量"},
            "max_trust": {"value": max_trust, "description": "最大信任容量 K"},
            "natural_repair_rate": {"value": natural_repair_rate, "description": "自然修复率 γ"},
            "quality_positive_feedback": {"value": quality_positive_feedback, "description": "高质量正反馈系数 β"},
            "low_quality_damage": {"value": low_quality_damage, "description": "低质量活动信任伤害系数 δ"},
            "stigma_drag": {"value": stigma_drag, "description": "污名对信任的拖累系数 ξ"},
            "governance_strength": {"value": governance_strength, "description": "平台治理强度 G"},
            "price_elasticity": {"value": price_elasticity, "description": "价格弹性系数 α"},
            "critical_trust_threshold": {"value": critical_trust_threshold, "description": "信任临界阈值 R_crit"},
            "critical_stigma_threshold": {"value": critical_stigma_threshold, "description": "污名临界阈值 S_crit"},
            "learning_rate": {"value": learning_rate, "description": "策略学习率"},
            "num_rounds": {"value": num_rounds, "description": "模拟轮数"},
            "base_price": {"value": 10.0, "description": "最大价格 p_max"},
            "base_cost": {"value": 2.0, "description": "基础成本 c0"},
            "quality_cost_coefficient": {"value": 0.3, "description": "质量成本系数 λ"},
            "penalty_coefficient": {"value": 0.1, "description": "惩罚成本系数 ω"},
            "shock_probability": {"value": 0.0, "description": "外部冲击概率"},
            "shock_impact": {"value": 0.0, "description": "外部冲击力度"},
            "stigma_persistence": {"value": 0.85, "description": "污名持久性 σ"},
            "stigma_incident_rate": {"value": 0.02, "description": "事件污名率 φ"},
            "initial_quality": {"value": 0.6, "description": "初始平均质量"},
            "initial_stigma": {"value": 0.0, "description": "初始污名存量"},
        },
        "validation": {
            "equilibrium_type": "social_trust_tragedy",
            "metrics": [
                {
                    "name": "trust_depletion_rate",
                    "expected_value": 0.3,
                    "tolerance": 0.3,
                    "description": "信任资源枯竭率",
                },
                {
                    "name": "sustainability_index",
                    "expected_value": 0.4,
                    "tolerance": 0.4,
                    "description": "组合式可持续性指数",
                },
                {
                    "name": "price_decline_rate",
                    "expected_value": 0.2,
                    "tolerance": 0.3,
                    "description": "价格下降率",
                },
                {
                    "name": "avg_profit_health",
                    "expected_value": 0.3,
                    "tolerance": 0.3,
                    "description": "利润健康度",
                },
            ],
        },
    }

    env = SocialTrustCommonsEnvironment(standard_config)
    return env, standard_config
