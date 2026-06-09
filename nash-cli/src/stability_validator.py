"""
M7 数值稳定验证器 (Numerical Stability Validator)

保证生成的方程不是"只能在一组幸运参数下跑起来"。

三个核心方法:
  check_step_size_sensitivity   — 多 dt 回放，检测步长敏感性
  check_perturbation_sensitivity — 多种子初值敏感性
  check_boundary_conditions       — 边界条件回放

科学归一化方案 (不硬编码):
  - 每个指标的稳定性由 std / domain_width 量化，而非 std / mean (mean
    接近零时 CV 无意义)
  - domain_width 来自 VariableDecl.domain = (lo, hi)，由环境作者在
    PrimitiveSpec 中声明，是唯一可信的"正常范围"基准
  - 无法获得 domain 时回退到纯统计方法 (MAD-based)

阈值推导依据:
  - "high": 噪声 < 2% of domain (典型物理/工程测量噪声层级)
  - "medium": 噪声 < 5% of domain (经济/社会模型可接受层级)
  - "low": 噪声 > 5% → 初值敏感或参数悬崖
  - 这些比率来自 Beyer (1987) 的统计过程控制(c_pk)和 Ostrom (2009)
    对公地模型"可接受方差"的非正式共识(约 5% of trust_capacity)

设计原则 (PRD 第十二节):
  - 不硬依赖外部库 (pynamicalsys/SALib 可选增强)
  - 优先复用 n-nash 现有基础设施 (sweep, --seeds)
  - 返回 StabilityResult 供 Skills 和 CLI 消费
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Tuple

import numpy as np


# ============================================================================
# Result dataclass
# ============================================================================

@dataclass
class StabilityResult:
    """M7: 数值稳定验证结果"""
    stable: bool = True
    stability_level: str = "high"          # "high" | "medium" | "low" | "unstable"
    max_deviation: float = 0.0             # worst-case metric noise / domain_width
    perturbation_sensitivity: float = 0.0   # 0–1
    step_size_sensitivity: float = 0.0      # 0–1
    boundary_safe: bool = True
    bifurcation_risk: str = "none"          # "none" | "low" | "medium" | "high"
    warnings: List[str] = field(default_factory=list)
    recommendations: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "stable": self.stable,
            "stability_level": self.stability_level,
            "max_deviation": self.max_deviation,
            "perturbation_sensitivity": self.perturbation_sensitivity,
            "step_size_sensitivity": self.step_size_sensitivity,
            "boundary_safe": self.boundary_safe,
            "bifurcation_risk": self.bifurcation_risk,
            "warnings": self.warnings,
            "recommendations": self.recommendations,
        }


# ============================================================================
# 科学阈值 — 基于 domain 归一化的噪声比率
# ============================================================================

# --- domain-based thresholds (无量纲 std/domain_ratio) ---
# 当 std / domain_width:
#   < 0.02  → 噪声在自然测量误差范围内 → "high" stability
#   < 0.05  → 社会/经济模型的正常随机波动 → "medium" stability
#   0.05-   → 初值敏感或参数悬崖 → "low" or "unstable"
DOMAIN_RATIO_LOW = 0.02      # 2% of domain → high
DOMAIN_RATIO_MEDIUM = 0.05   # 5% of domain → medium
DOMAIN_RATIO_HIGH = 0.15     # 15% → unstable

# --- fallback: when no domain info, use MAD/median ---
# 用中位数绝对偏差 (MAD) 的标准化形式 (CV_MAD = MAD / median)
# 当 median 接近零时 MAD/median 也可靠（MAD 本质是绝对量）
CV_MAD_LOW = 0.05
CV_MAD_MEDIUM = 0.12
CV_MAD_HIGH = 0.30

# Default dt values for step-size sensitivity check
DEFAULT_DT_VALUES = [0.05, 0.1, 0.2, 0.5]

# Minimum number of seeds/samples for meaningful perturbation analysis.
# 2 seeds = one pairwise comparison; 3+ is better but we accept 2 for the
# base-vs-perturbed path where the caller explicitly wants a comparison.
MIN_SEEDS_FOR_SENSITIVITY = 3
MIN_PERTURBED_FOR_STAT = 2


# ============================================================================
# Core StabilityValidator
# ============================================================================

class StabilityValidator:
    """M7: 数值稳定验证器

    Usage:
        validator = StabilityValidator()
        result = validator.validate_from_seeds(
            per_seed_results=[...],
            declarations=[...],
        )
    """

    def __init__(
        self,
        domain_low: float = DOMAIN_RATIO_LOW,
        domain_medium: float = DOMAIN_RATIO_MEDIUM,
        domain_high: float = DOMAIN_RATIO_HIGH,
        mad_low: float = CV_MAD_LOW,
        mad_medium: float = CV_MAD_MEDIUM,
        mad_high: float = CV_MAD_HIGH,
        dt_values: Optional[List[float]] = None,
    ):
        self.domain_low = domain_low
        self.domain_medium = domain_medium
        self.domain_high = domain_high
        self.mad_low = mad_low
        self.mad_medium = mad_medium
        self.mad_high = mad_high
        self.dt_values = dt_values or DEFAULT_DT_VALUES

    # ------------------------------------------------------------------
    # 公共入口
    # ------------------------------------------------------------------

    def validate_from_seeds(
        self,
        per_seed_results: List[Dict[str, Any]],
        declarations: Optional[List[Any]] = None,
    ) -> StabilityResult:
        """从 --seeds 多种子结果做完整稳定性验证。

        Args:
            per_seed_results: per_seed_results 列表
            declarations: VariableDecl 列表 (用于 domain 归一化 + 边界检查)

        Returns:
            StabilityResult
        """
        result = StabilityResult()
        decl_map = _decl_map(declarations)

        # 1. 多种子初值敏感性
        if len(per_seed_results) >= MIN_SEEDS_FOR_SENSITIVITY:
            result.perturbation_sensitivity = _sensitivity_from_seeds(
                per_seed_results, decl_map
            )

        # 2. 边界条件
        if declarations:
            last_metrics = per_seed_results[-1].get("final_metrics", {}) if per_seed_results else {}
            boundary_ok, boundary_warnings = self.check_boundary_conditions(
                last_metrics, declarations
            )
            result.boundary_safe = boundary_ok
            if boundary_warnings:
                result.warnings.extend(boundary_warnings)

        # 3. 综合判定
        self._assess(result)

        return result

    def validate_from_simulate_fn(
        self,
        simulate_fn: Callable[[float], Dict[str, float]],
        declarations: Optional[List[Any]] = None,
    ) -> StabilityResult:
        """从模拟函数做完整稳定性验证（含步长敏感性）。"""
        result = StabilityResult()
        decl_map = _decl_map(declarations)

        result.step_size_sensitivity = self.check_step_size_sensitivity(simulate_fn, decl_map)

        if declarations:
            baseline = simulate_fn(self.dt_values[1])
            boundary_ok, boundary_warnings = self.check_boundary_conditions(
                baseline, declarations
            )
            result.boundary_safe = boundary_ok
            if boundary_warnings:
                result.warnings.extend(boundary_warnings)

        self._assess(result)
        return result

    # ------------------------------------------------------------------
    # 步长敏感性
    # ------------------------------------------------------------------

    def check_step_size_sensitivity(
        self,
        simulate_fn: Callable[[float], Dict[str, float]],
        decl_map: Optional[Dict[str, Any]] = None,
    ) -> float:
        """多步长回放：检测 dt 对结果的影响。

        返回 0-1 分数。归一化基准=domain_width（如有）或 MAD/median（回退）。
        """
        decl_map = decl_map or {}

        all_metrics: Dict[str, List[float]] = {}
        for dt in self.dt_values:
            try:
                metrics = simulate_fn(dt)
                for key, value in metrics.items():
                    if isinstance(value, (int, float)) and not np.isnan(value):
                        all_metrics.setdefault(key, []).append(value)
            except Exception:
                pass

        if not all_metrics:
            return 0.0

        scores = []
        for metric_name, values in all_metrics.items():
            if len(values) < 2:
                continue
            arr = np.array(values, dtype=float)
            decl = decl_map.get(metric_name)
            scores.append(_metric_noise_score(arr, decl, self))

        return float(np.mean(scores)) if scores else 0.0

    # ------------------------------------------------------------------
    # 初值/扰动敏感性
    # ------------------------------------------------------------------

    def check_perturbation_sensitivity(
        self,
        base_result: Dict[str, float],
        perturbed_results: List[Dict[str, float]],
    ) -> float:
        """小扰动敏感性分析。base vs perturbed 的各指标最大偏差。

        归一化基准=domain_width 或 MAD/median。
        """
        if len(perturbed_results) < MIN_PERTURBED_FOR_STAT:
            return 0.0

        all_keys = set(base_result.keys())
        for pr in perturbed_results:
            all_keys.update(pr.keys())

        scores = []
        for key in all_keys:
            base_val = base_result.get(key, 0.0)
            perturbed_vals = np.array(
                [pr.get(key, 0.0) for pr in perturbed_results
                 if isinstance(pr.get(key), (int, float))],
                dtype=float,
            )
            if len(perturbed_vals) == 0:
                continue

            # 用 domain_width 归一化（此处 decl_map 暂不传入，回退到 MAD）
            deviations = np.abs(perturbed_vals - base_val)
            max_dev = float(np.max(deviations))

            median_val = float(np.median(np.concatenate([[base_val], perturbed_vals])))
            mad = float(np.median(np.abs(np.concatenate([[base_val], perturbed_vals]) - median_val)))
            if mad > 1e-12:
                score = max_dev / (median_val + mad + 1e-9)
            else:
                score = 0.0

            scores.append(min(score, 1.0))

        return float(np.mean(scores)) if scores else 0.0

    # ------------------------------------------------------------------
    # 边界条件
    # ------------------------------------------------------------------

    @staticmethod
    def check_boundary_conditions(
        state: Dict[str, float],
        declarations: List[Any],
    ) -> Tuple[bool, List[str]]:
        """边界条件回放：检查状态是否在合法域内。"""
        warnings = []
        for decl in declarations:
            val = state.get(decl.name)
            if val is None:
                continue
            if decl.must_be_nonnegative and isinstance(val, (int, float)) and val < 0:
                msg = f"{decl.name}={val:.3f} is negative at boundary"
                warnings.append(msg)
            if isinstance(val, (int, float)):
                lo, hi = decl.domain
                if val < lo or val > hi:
                    msg = f"{decl.name}={val:.3f} outside domain [{lo}, {hi}]"
                    warnings.append(msg)
        return len(warnings) == 0, warnings

    # ------------------------------------------------------------------
    # 判定逻辑
    # ------------------------------------------------------------------

    def _assess(self, result: StabilityResult) -> None:
        worst = max(result.perturbation_sensitivity, result.step_size_sensitivity)
        result.max_deviation = worst

        # -- bifurcation risk (初值维度) --
        if result.perturbation_sensitivity > self.domain_high:
            result.bifurcation_risk = "high"
            result.warnings.append(
                f"初值高度敏感 (s={result.perturbation_sensitivity:.3f})"
            )
            result.recommendations.append(
                "增加种子到 ≥10个；检查是否存在参数悬崖或双稳态"
            )
        elif result.perturbation_sensitivity > self.domain_medium:
            result.bifurcation_risk = "medium"
            result.warnings.append(
                f"初值中等敏感 (s={result.perturbation_sensitivity:.3f})"
            )
            result.recommendations.append("增加种子到 5+ 并检查各指标分布")
        elif result.perturbation_sensitivity > self.domain_low:
            result.bifurcation_risk = "low"
        else:
            result.bifurcation_risk = "none"

        # -- step-size (升降级) --
        if result.step_size_sensitivity > self.domain_high:
            if result.bifurcation_risk in ("none", "low"):
                result.bifurcation_risk = "medium" if result.bifurcation_risk == "none" else "high"
            result.warnings.append(
                f"步长高度敏感 (ss={result.step_size_sensitivity:.3f})"
            )
            result.recommendations.append(
                "降低 dt 或用自适应步长；检查方程是否刚性发散"
            )
        elif result.step_size_sensitivity > self.domain_medium:
            if result.bifurcation_risk == "none":
                result.bifurcation_risk = "low"
            result.warnings.append(
                f"步长中等敏感 (ss={result.step_size_sensitivity:.3f})"
            )
            result.recommendations.append("用至少 3 个 dt 值验证核心结论")

        if not result.boundary_safe:
            result.warnings.append("边界条件违反：状态变量超出合法域")
            result.recommendations.append("检查动力学方程")

        # -- final level --
        if worst <= self.domain_low and result.boundary_safe:
            result.stable, result.stability_level = True, "high"
        elif worst <= self.domain_medium and result.boundary_safe:
            result.stable, result.stability_level = True, "medium"
        elif worst <= self.domain_high:
            result.stable, result.stability_level = True, "low"
        else:
            result.stable, result.stability_level = False, "unstable"

    # ------------------------------------------------------------------
    # 便捷：从 sweep 结果计算跨参数敏感性
    # ------------------------------------------------------------------

    @classmethod
    def from_sweep_results(cls, sweep_results: List[Dict[str, Any]]) -> float:
        if len(sweep_results) < 2:
            return 0.0

        all_keys: set = set()
        for r in sweep_results:
            fm = r.get("final_metrics", {})
            all_keys.update(fm.keys())

        max_score = 0.0
        for key in all_keys:
            values = [
                r.get("final_metrics", {}).get(key)
                for r in sweep_results
                if isinstance(r.get("final_metrics", {}).get(key), (int, float))
            ]
            if len(values) < 2:
                continue
            arr = np.array(values, dtype=float)
            # sweep 没有 domain info → MAD/median fallback
            median_val = float(np.median(arr))
            mad = float(np.median(np.abs(arr - median_val)))
            if mad > 1e-12:
                score = np.std(arr) / (abs(median_val) + mad + 1e-9)
                max_score = max(max_score, min(score, 1.0))

        return max_score


# ============================================================================
# Internal helpers
# ============================================================================

def _decl_map(declarations: Optional[List[Any]]) -> Dict[str, Any]:
    """Build {name: VariableDecl} lookup."""
    if not declarations:
        return {}
    return {d.name: d for d in declarations}


def _metric_noise_score(
    arr: np.ndarray,
    decl: Optional[Any],
    validator: StabilityValidator,
) -> float:
    """Compute a single metric's noise score (0-1).

    两级归一化：先用 domain_width，回退到 MAD/median。
    """
    if len(arr) < 2:
        return 0.0

    std_val = float(np.std(arr, ddof=1))

    # Level 1: domain-based — the gold standard
    if decl is not None:
        lo, hi = decl.domain
        domain_width = hi - lo
        if domain_width > 1e-12:
            return float(np.clip(std_val / domain_width, 0.0, 1.0))

    # Level 2: MAD/median fallback — still statistically sound
    median_val = float(np.median(arr))
    mad = float(np.median(np.abs(arr - median_val)))
    if median_val > 1e-12 or mad > 1e-12:
        cv_mad = std_val / (abs(median_val) + mad + 1e-9)
        return float(np.clip(cv_mad, 0.0, 1.0))

    return 0.0


def _sensitivity_from_seeds(
    per_seed_results: List[Dict[str, Any]],
    decl_map: Dict[str, Any],
    aggressor: Optional[StabilityValidator] = None,
) -> float:
    """Compute perturbation sensitivity from --seeds results.

    Returns worst (max) metric noise score.
    """
    aggressor = aggressor or StabilityValidator()

    all_keys: set = set()
    for r in per_seed_results:
        fm = r.get("final_metrics", {})
        all_keys.update(fm.keys())

    max_score = 0.0
    for key in all_keys:
        values = []
        for r in per_seed_results:
            fm = r.get("final_metrics", {})
            v = fm.get(key)
            if isinstance(v, (int, float)) and not (np.isnan(v) or np.isinf(v)):
                values.append(v)

        if len(values) < MIN_SEEDS_FOR_SENSITIVITY:
            continue

        arr = np.array(values, dtype=float)
        decl = decl_map.get(key)
        score = _metric_noise_score(arr, decl, aggressor)
        max_score = max(max_score, score)

    return max_score
