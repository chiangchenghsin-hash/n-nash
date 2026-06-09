---
name: nash-game-theory
description: NASH 原语模块与耦合规则创建指南 — 从"如何创建单个环境"升级为"如何创建类型化原语模块、声明不变量、定义耦合许可，并注册到原语库供动态组装使用"
---

# NASH 原语模块与耦合规则创建指南 (v2)

**范式升级**：从「创建固定博弈环境」升级为「创建可被动态组装、带类型约束、带耦合声明的经济学原语模块」。

## Multilingual Summary

- English: Create typed primitive modules (not fixed environments): declare state/control/derived variables with domains, invariants, monotonicity rules, phase boundaries, and coupling permits — then register into PrimitiveLibrary for dynamic composition.
- 中文：创建带类型声明的经济学原语模块（非固定环境），包含变量域、不变量、单调性规则、相变边界、耦合许可，注册到原语库供动态组装。
- 日本語：型付きプリミティブモジュール（変数ドメイン・不変量・単調性・相転移境界・結合許可）を作成し、PrimitiveLibrary に登録して動的組立を可能にする。

## 核心理念

旧版：做一个完整的、自包含的环境类 → CLI 单独运行
新版：做一个**带接口声明的原语模块** → 可以单独运行，也可以被 nash-env 动态组装进更大的耦合系统

每个原语模块必须回答五个问题：
1. **我的状态空间是什么？**（变量声明 + 域约束）
2. **什么不能违反？**（不变量）
3. **什么方向必须对？**（单调性规则）
4. **我能和谁耦合？**（can_couple_with / cannot_couple_with）
5. **我的边界行为是什么？**（相变边界 + 极限行为）

## 两种创建方式

### 方式 A：完整环境创建（旧版兼容）

当需要一个全新的、自包含的仿真环境时，走完整路径：
1. 创建 `src/environments/new_game.py` — 继承 `BaseEnvironment`
2. 实现 `initialize_agents()`, `run_step()`, `check_convergence()`, `get_validation_metrics()`
3. 创建 `create_new_game()` 工厂函数
4. 自动注册（`get_environment_registry()` 自动发现 `src/environments/*.py`）
5. 可通过 `nash run --preset new_game` 直接运行

### 方式 B：纯原语注册（新增）

当一个经济学机制不需要独立环境，只需要被其他原语引用和耦合时：
1. 在 `src/primitives.py` 的 `_register_all_primitives()` 中添加 `PrimitiveSpec`
2. 声明变量、不变量、单调性、耦合许可
3. 由 `nash-env` Skill 在解构阶段自动激活
4. 不需要单独的 `.py` 环境和测试

## 原语模块规范模板

### 1. PrimitiveSpec 完整字段

```python
from src.primitives import (
    PrimitiveSpec, PrimitiveDomain, VariableDecl, InvariantDecl,
    MonotonicityRule, PhaseBoundary
)

spec = PrimitiveSpec(
    primitive_id="my_primitive",          # 唯一 ID（snake_case）
    name="我的原语",                       # 人类可读名称
    domain=PrimitiveDomain.INFORMATION_SIGNAL,  # 所属领域
    description="简短的一句话描述核心机制",

    # 状态变量 — 描述系统状态的变量（存量/比例/价格等）
    state_variables=[
        VariableDecl("x", (0, 1),
                     is_probability=True,
                     description="策略比例"),
        VariableDecl("S", (0, float('inf')),
                     is_stock=True,
                     description="资源存量"),
    ],

    # 控制变量 — 外部可调节的变量
    control_variables=[
        VariableDecl("learning_rate", (0.001, 1.0), description="学习率"),
    ],

    # 派生变量 — 从状态变量计算得出的变量
    derived_variables=[
        VariableDecl("payoff", (-float('inf'), float('inf')),
                     is_flow=True, description="瞬时收益"),
    ],

    # 接口 — 声明输入输出的变量名（用于耦合匹配）
    input_variables=["price", "governance_strength"],
    output_variables=["quality_ratio", "trust_delta"],

    # 不变量 — 绝对不可违反的恒等式/不等式
    invariants=[
        InvariantDecl("shares_sum_to_one",
                      "所有策略份额之和为 1",
                      "Σ share_i = 1",
                      severity="hard"),
        InvariantDecl("price_nonnegative",
                      "价格不得为负",
                      "price >= 0",
                      severity="hard"),
    ],

    # 单调性规则 — 声明导数方向
    monotonicity_rules=[
        MonotonicityRule("information_asymmetry", "quality_ratio", "decreasing"),
        MonotonicityRule("governance", "quality_ratio", "increasing"),
    ],

    # 相变边界 — 阈值触发后的行为跃迁
    phase_boundaries=[
        PhaseBoundary("x", 0.5, "above", "超过 50% 后加速扩散"),
    ],

    # 耦合许可
    can_couple_with=["lemons_market", "schelling_threshold"],
    cannot_couple_with=[],

    # 数值提示
    recommended_dt=0.1,
    stiffness_warning=False,

    # 激活条件
    activation_conditions=[
        "information_asymmetry > 0.4",
        "adverse_selection_risk > 0.3",
    ],
)

# 注册
from src.primitives import PrimitiveLibrary
PrimitiveLibrary.register(spec)
```

### 2. VariableDecl 约束

| 参数 | 类型 | 说明 |
|------|------|------|
| `name` | str | 变量名 |
| `domain` | (lower, upper) | 合法值域 |
| `is_probability` | bool | True → 必须 ∈ [0,1] 且可要求归一 |
| `is_stock` | bool | True → 必须非负（存量变量） |
| `is_flow` | bool | True → 流量变量（可正可负） |

### 3. MonotonicityRule 方向值

| direction | 含义 | 示例 |
|-----------|------|------|
| `"increasing"` | 严格递增 | 信任 ↑ → 价格 ↑ |
| `"decreasing"` | 严格递减 | 污名 ↑ → 信任 ↓ |
| `"non_decreasing"` | 非递减 | 治理 ↑ → 质量 ≥ 不变 |
| `"non_increasing"` | 非递增 | 密度 ↑ → 质量 ≤ 不变 |

### 4. 耦合兼容性矩阵

声明 `can_couple_with` 时考虑：

| 耦合类型 | 含义 | 示例 |
|----------|------|------|
| 串联 | A 的输出 → B 的输入 | lemons_market.quality_ratio → social_trust_commons 的信任损耗 |
| 并联 | A 和 B 共同影响同一变量 | adverse_selection + moral_hazard 共同影响风险池 |
| 嵌套 | B 在 A 内部运行 | replicator_dynamics 作为任何策略演化的外层 |
| 反馈 | A → B → A | schelling_threshold 加速 stigma 扩散，stigma 降低 adoption 阈值 |

声明 `cannot_couple_with` 时考虑：
- 有内在矛盾（lemons_market 假设无信号，spence_signaling 假设有信号）
- 层级冲突（个体层原语不能直接和制度层原语串联）
- 数值不稳定（两个刚性系统耦合可能爆炸）

## 完整环境创建流程

### 方法 A 检查清单

```
□ Step 1: 用 Subagents 并行调研理论 + benchmark + 参考实现
□ Step 2: 创建 src/environments/new_game.py
    □ 继承 BaseEnvironment
    □ 实现 initialize_agents() → 重置所有状态
    □ 实现 run_step() → 单步动力学
    □ 实现 check_convergence() → ConvergenceResult
    □ 实现 get_validation_metrics() → Dict[str, float]
    □ 实现 create_new_game() 工厂函数
□ Step 3: 在 src/primitives.py 注册 PrimitiveSpec（如是新原语）
□ Step 4: 创建 tests/test_new_game.py
    □ 环境骨架测试（初始化、运行、输出字段）
    □ 动力学正确性测试（方向验证）
    □ 收敛测试（均衡分类）
□ Step 5: 运行全量测试确认无回归
□ Step 6: 在 PARAM_SPECS 中注册参数规格（如需要 --params CLI 支持）
```

### 方法 B 检查清单

```
□ Step 1: 在 src/primitives.py 的 _register_all_primitives() 添加 PrimitiveSpec
□ Step 2: 至少声明 state_variables + monotonicity_rules + coupling permits
□ Step 3: 更新 can_couple_with / cannot_couple_with 在其他相关原语中
□ Step 4: 在 tests/test_primitives.py 添加激活测试
□ Step 5: 运行测试
```

## 环境实现模板

完整实现模板请参考 `src/environments/social_trust_commons.py` — 这是最新且最完整的参考实现，包含：

- 状态变量：trust, quality, stigma, price
- 派生量：p(R) 价格函数, π_i 组织者利润
- 动力学方程：F2 信任演化, F4 质量演化, F5 污名演化
- 三类断裂点检测：price, ecological, collapse
- 四态均衡分类：healthy / low_trust_trap / collapsed / transitioning
- 组合式可持续性指标

## 原语注册示例

在 `src/primitives.py` 的 `_register_all_primitives()` 中添加新原语：

```python
PrimitiveLibrary.register(PrimitiveSpec(
    primitive_id="my_new_primitive",
    name="我的新原语",
    domain=PrimitiveDomain.COLLECTIVE_COORDINATION,
    description="核心机制的一句话描述",
    state_variables=[
        VariableDecl("adoption_rate", (0, 1), is_probability=True,
                     description="采纳比例"),
    ],
    invariants=[
        InvariantDecl("rate_in_range", "采纳比例在 [0,1]", severity="hard"),
    ],
    monotonicity_rules=[
        MonotonicityRule("network_density", "adoption_rate", "increasing"),
    ],
    can_couple_with=["schelling_threshold", "replicator_dynamics"],
    cannot_couple_with=["lemons_market"],
    activation_conditions=["network_density > 0.5"],
))
```

## 测试命令

```bash
# 运行所有环境测试
uv run python -m pytest tests/ -v

# 运行原语系统测试
uv run python -m pytest tests/test_primitives.py -v

# 运行特定新环境测试
uv run python -m pytest tests/test_new_game.py -v

# 验证新环境在 CLI 中可见
uv run nash env list
```

## 最佳实践

1. **先声明再实现**：先把 PrimitiveSpec 写好，再写环境代码 — 约束驱动开发
2. **不变量是硬约束**：hard severity 的不变量必须在每轮 `run_step()` 后满足
3. **单调性规则用于审计**：写好后用 SymbolicAuditor 自查 — 它能发现你忘了的符号矛盾
4. **耦合声明要诚实**：不要为了灵活性把所有原语都放进 can_couple_with
5. **先让系统学会"不能乱写"，再让它学会"能自由组装"** — 这是本版 PRD 的核心原则

## 交叉引用

- [[nash-env]] — 动态原语激活 + 组装规划
- [[nash-run]] — 执行仿真实验
- [[nash-analyze]] — 结果分析 + 验证
- `src/primitives.py` — PrimitiveSpec, PrimitiveLibrary, ConstraintCompiler, SymbolicAuditor 源码
- `src/environments/social_trust_commons.py` — 最新完整参考实现
