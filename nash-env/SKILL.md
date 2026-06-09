---
name: nash-env
description: "Use when the user asks what game models exist, wants to classify a real-world problem into a Nobel economic model, or needs to understand environment mechanics before running simulations. Triggers on: 博弈模型, 环境, 诺贝尔, classify, what game, which model, environment, game theory, 分类, 模型推荐, 原语, 特征提取, 解构."
---

# NASH Env — 结构解构 + 原语激活规划器 (v2)

你不是"模型推荐器"。
你是**受约束的建模师** — 先把现实案例解构成结构特征向量，再从经济学原语库中激活并组装候选模型，最后通过约束校验保证数学合法性。

> **范式升级**: 从 `案例 → 模型分类 → 套公式 → 跑结果` 升级为 `案例 → 语义解构 → 特征向量 → 原语激活 → 类型化组装 → 约束校验 → 推荐输出`

## Multilingual Summary / 多语言概要

- English: Deconstruct real-world cases into structural feature vectors, activate economics primitives from the typed library, propose couplings with constraint checks — not a template matcher but a constrained model architect.
- 中文：把现实案例解构成结构特征向量 → 从原语库激活经济学原语 → 在约束下组装候选模型。不是模板匹配器，是受约束的建模师。

## 核心理念：先解构，再组装，最后校验

**旧范式（禁止）**：
```
看到"共享资源" → common_pool_resource
看到"冲突" → hawk_dove
看到"长期互动" → repeated_prisoners_dilemma
```

**新范式（必须）**：
```
输入案例
→ 提取结构特征向量 (FeatureVector)
→ 激活匹配原语 (PrimitiveLibrary.activate)
→ 判定主原语 + 辅助原语 + 层级
→ 构造耦合图谱 (CouplingGraph)
→ 约束编译校验 (ConstraintCompiler)
→ 解释边界控制 (BoundaryController)
→ 输出建模方案
```

## 何时使用此技能

- 用户描述一个现实问题，想知道适合用什么模型
- 用户问「有哪些博弈模型？」「列出所有环境」
- 用户想了解某个环境/原语的机制
- 用户关键词：env、模型、分类、博弈、环境、原语、解构、特征

## 标准工作流（五步法）

### Step 1 — 提取结构特征向量

在接触任何模型之前，**先构造 `FeatureVector`**。读取用户案例，对以下维度打分 (0-1)：

```
信息结构:
  information_asymmetry     — 信息是否不对称？谁掌握私人信息？
  adverse_selection_risk    — 是否存在事前逆向选择？

时间结构:
  time_horizon_rigidity     — 是否存在硬截止日/有限任期？
  repetition_potential      — 交互是否可能重复？

激励结构:
  incentive_misalignment    — 委托人和代理人目标是否错位？
  moral_hazard_potential    — 是否存在事后道德风险？

资源与公地:
  commons_character         — 是否存在被集体抽取的共享资源？
  resource_type             — "physical"（物理）/ "trust"（信任）/ "none"
  public_goods_character    — 是否存在搭便车问题？

网络与扩散:
  threshold_diffusion_risk  — 是否存在临界点后加速扩散的风险？
  network_density           — 群体密度/互动频率？

治理与制度:
  governance_presence       — 是否存在外部治理机制？
  institutional_layering    — 是单层还是多层制度嵌套？
  exit_cost                 — 退出成本有多高？

冲突与协调:
  conflict_intensity        — 竞争/冲突强度？
  coordination_need         — 是否需要多方协调才能达成目标？

信任与声誉:
  trust_sensitivity         — 对信任/声誉的依赖度？
  stigma_potential          — 是否存在标签污染/污名化风险？
```

**输出格式**：直接在回复中输出一个 Python 可读的 `FeatureVector(...)` 初始化代码块，方便用户审阅和调整。

### Step 1.5 — 举证锚定（强制）

**在提取 FeatureVector 之后、激活原语之前，必须给出举证表。** 不允许无事实依据的任意打分。

对每个被赋予了非默认值的维度，必须在表中锚定到用户案例中的具体事实：

```
| 维度 | 打分 | 证据（来自案例原文） | 为什么不是最低分？ | 为什么不是最高分？ |
|------|------|---------------------|--------------------|--------------------|
| information_asymmetry | 0.7 | "买家看不到产品质量，只有卖家知道" | 存在市场机制（退款）小幅降低 | 无第三方认证/信号机制 |
| commons_character | 0.8 | "平台流量是共享池，每个卖家都在抽取" | 存在平台规则限制 | 没有产权界定，纯公共接入 |
```

**规则**：
- 涉及关键判断的维度必须填写全部 5 列
- 如果某个维度为 0 或 1.0，必须说明"极端值的依据是什么"
- `<0.2` 或 `>0.8` 的高信度打分需要额外的审慎论证
- **禁止的行为**：无案例引用直接填数字；用"经验之谈""常识""一般来说"规避举证

### Step 2 — 激活原语

将 FeatureVector 输入 `PrimitiveLibrary.activate()`，获取激活的原语列表。

**Python 参考实现**（可用 `uv run python -c` 直接执行）：

```python
import sys; sys.path.insert(0, 'src')
from primitives import FeatureVector, PrimitiveLibrary

fv = FeatureVector(
    information_asymmetry=0.7,
    commons_character=0.8,
    resource_type="trust",
    trust_sensitivity=0.9,
    stigma_potential=0.7,
    adverse_selection_risk=0.5,
    institutional_layering=0.6,
)
activated, reasons = PrimitiveLibrary.activate(fv)
for p in activated:
    print(f"  [{p.domain.value}] {p.primitive_id}: {reasons[p.primitive_id]}")
```

**在回复中必须输出**：
1. 激活的原语列表（按 domain 分组）
2. 激活原因
3. 被抑制的原语及原因
4. 是否需要双层/多层建模建议（institutional_layering > 0.5 → 双层）

### Step 3 — 规划主辅原语 + 耦合图谱

从激活原语中选出：
- **主原语** (1个)：最能刻画核心动力学的原语
- **辅助原语** (0-3个)：补充机制的次要原语
- **层级判定**：single / dual / multi

构造耦合图谱（文字版即可）：
```
[主原语] ──串联──> [辅助原语 A]
    │
    └──反馈──> [辅助原语 B]
```

**关键校验**：
- 检查 `can_couple_with` / `cannot_couple_with`
- 检查层级混杂：如果 institutional_layering > 0.5 但只选了一个原语 → 警告

### Step 3.5 — 对抗检查点（强制）

**在锁定原语组合后、进入约束编译前，必须尝试推翻自己的选择。**

逐一检视：

```
1. "如果我的主原语选错了，最可能是因为什么？"
      ── 列出 1-3 个最可能误判的信号
2. "是否存在另一个原语，能用更少的假设解释同样的现象？"
      ── 强制搜索替代方案
3. "有没有我为了凑这个原语而刻意忽略的案例特征？"
      ── 列出 2+ 个被忽略或不匹配的特征，评估其严重性
4. "这个原语组合在现实中最容易失灵的边界条件是什么？"
      ── 列出 2+ 个失效场景
```

**输出格式**（在回复中必须可见）：
```
对抗检查:
  主原语替代方案: <候选> — <为什么没选>
  被忽略的特征: 
    - <特征 A> — 严重性: <高/中/低>
    - <特征 B> — 严重性: <高/中/低>
  最可能的失效边界: <场景 1>, <场景 2>
  结论: 通过 / 需重新考虑（含理由）
```

若对抗检查未通过（存在严重被忽视的特征或明显更优的替代方案），**必须**回到 Step 1 重新审视特征向量或 Step 3 更换原语组合。

### Step 4 — 约束编译 + 符号审计

对选定的原语组合，逐项校验：

1. **状态空间**：所有变量在合法域内？比例变量归一？存量变量非负？
2. **单调性**：声明的导数方向是否与实际一致？
   - 例如："信任下降 → 价格必须下降"
3. **相变边界**：触发阈值后行为是否符合预期？
4. **符号一致性**：原语声明与耦合后行为有无矛盾？

在回复中用表格呈现：
```
| 约束类型 | 状态 | 说明 |
|----------|------|------|
| 状态空间 | ✅ | 所有变量在域内 |
| 单调性   | ⚠️ | stigma → trust 方向正确，但缺少显式耦合项 |
| 相变边界 | ✅ | R < R_crit 触发价格归零 |
```

### Step 5 — 输出建模方案 + 解释边界

最终输出包含：

1. **特征向量摘要**
2. **原语激活方案**（主/辅/层）
3. **对抗检查结果**（来自 Step 3.5）
4. **参数卡**（每个参数的来源标注：原语默认/特征映射/约束推导/场景假设）
5. **解释边界**：
   - `模型支持` — 方程可推出的结论
   - `启发式解释` — 方向正确但不可精确量化
   - `评论性隐喻` — 语言层面类比，动力学层面不够格
6. **缺失声明（强制）**：
   ```
   此模型本质上无法解释:
     - <X> — 因为 <理论盲区>
     - <Y> — 因为 <数学结构限制>
     - <Z> — 因为 <假设前提不覆盖>
   
   如果你关心的是 <X/Y/Z> 中的任何一项，这个模型会给你错误的信心。
   ```
   - **至少 3 条**，逐条说明"为什么模型中不存在"
   - 禁止使用"可能""在某些条件下"等模糊措辞 — 必须是明确的"不能解释"
7. **下一步建议** → 切换到 [[nash-run]] 或 [[nash-game-theory]]

**极端案例自动保护**：如果案例涉及暴力/自杀/刑事/死亡等关键词，必须自动附加：
> "该方程组可解释结构性风险积累与系统性高危背景，但不能机械推出具体极端事件的必然发生。"

## 原语库快速参考

### 信息与信号矩阵
| 原语 ID | 名称 | 核心机制 | 关键变量 |
|---------|------|---------|---------|
| `lemons_market` | 柠檬市场 | 信息不对称 → 劣币驱逐良币 | quality_ratio, price |
| `spence_signaling` | 信号发送 | 高成本信号实现分离均衡 | education_level, wage |
| `adverse_selection` | 逆向选择 | 事前信息不对称 → 风险池恶化 | risk_pool_quality |

### 契约与组织矩阵
| 原语 ID | 名称 | 核心机制 | 关键变量 |
|---------|------|---------|---------|
| `principal_agent` | 委托代理 | 激励错位 → 代理人不努力 | effort, output |
| `moral_hazard` | 道德风险 | 被保险后更冒险 | risk_taking |

### 群体协同矩阵
| 原语 ID | 名称 | 核心机制 | 关键变量 |
|---------|------|---------|---------|
| `stag_hunt` | 猎鹿博弈 | 协同收益大但背叛安全 | cooperation_rate |
| `schelling_threshold` | 阈值扩散 | 微观动机 → 宏观相变 | adoption_rate, threshold |

### 公地与资源矩阵
| 原语 ID | 名称 | 核心机制 | 关键变量 |
|---------|------|---------|---------|
| `common_pool_resource` | 公共池资源 | 物理资源的公地悲剧 | resource_stock |
| `social_trust_commons` | 社会信任公地 | 信任/声誉/标签的公地悲剧 | trust, quality, stigma, price |
| `public_goods` | 公共物品 | 搭便车 → 贡献不足 | contribution_rate |

### 动态演化矩阵
| 原语 ID | 名称 | 核心机制 | 关键变量 |
|---------|------|---------|---------|
| `replicator_dynamics` | 复制者动态 | 策略比例按适应度演化 | strategy_share |

### 冲突矩阵
| 原语 ID | 名称 | 核心机制 | 关键变量 |
|---------|------|---------|---------|
| `hawk_dove` | 鹰鸽博弈 | 冲突成本 vs 资源价值的 ESS | hawk_ratio |
| `repeated_prisoners_dilemma` | 重复囚徒困境 | 重复互动下合作可作为 SPNE | cooperation_rate |

## 可执行环境参考表（兼容旧版）

当原语激活后确定单一环境足够时，直接使用以下预设运行：

| 环境 ID | 短 ID | 诺贝尔年 | 均衡类型 |
|---------|-------|---------|---------|
| `hawk_dove` | hawk_dove | 2005 | ESS |
| `repeated_prisoners_dilemma` | prisoners_dilemma | 2005 | 合作 SPNE |
| `public_goods` | public_goods | 2009 | 搭便车 |
| `common_pool_resource` | common_pool | 2009 | 公地悲剧 |
| `social_trust_commons` | social_trust_commons | 2009 | 社会信任公地悲剧 |
| `vickrey_auction` | vickrey | 1996 | 真实出价占优 |
| `spence_signaling` | spence | 2001 | 分离均衡 |
| `two_sided_matching` | matching | 2012 | 稳定匹配 |
| `auction_common_value` | auction_common_value | 2020 | 赢家诅咒 |

## 旧版兼容：简单模型查询

如果用户只是问「列出所有环境」或「X 环境是什么」，不走完整五步法，直接用旧版快速路径：

```bash
uv run nash env list
uv run nash env info <short_id>
```

## 参数卡模板

每个推荐参数必须标注来源：

```
| 参数 | 推荐值 | 来源 | 含义 | 低值解释 | 高值解释 | 风险 |
|------|--------|------|------|---------|---------|------|
| governance_strength | 0.3 | 特征映射 | 平台治理强度 | 弱治理/自由放任 | 强实名/严处罚 | 过高会压死正常活动 |
| stigma_drag | 0.15 | 原语默认 | 污名对信任的拖累系数 | 公众健忘/宽容 | 污名极其粘滞 | 过高导致快速崩塌 |
| natural_repair_rate | 0.03 | 场景假设 | 信任自然修复速率 | 修复极慢/一伤难愈 | 公众容易遗忘重启 | 过高会掩盖结构性问题 |
```

## 硬凑检测清单

在最终推荐前，逐项检查：

- [ ] 层级混杂：是否把制度层变量和个体层变量混写为同一个？
- [ ] 中介变量缺失：A→C 是否跳过了必要的 B？
- [ ] 修辞一致但机制不一致：语言层面像，但动力学层面不对？
- [ ] 过度复杂化：真实草地案例不需要 lemons_market + schelling_threshold

## 强制流程决策树

```
用户案例分析请求
├─ 简单查询（"有哪些模型？"/"X 环境是什么？"）
│   └─ env list / env info → 快速回复，不走机制
├─ 建模请求（"这个问题适合什么模型？"/"帮我分析这个案例"）
│   ├─ Step 1: 提取 FeatureVector
│   ├─ Step 1.5: 举证锚定（强制 — 每维度锚定到案例事实）
│   ├─ Step 2: PrimitiveLibrary.activate(fv)
│   ├─ Step 3: 规划 主原语 + 辅助原语 + 层级
│   ├─ Step 3.5: 对抗检查点（强制 — 尝试推翻自己的选择）
│   ├─ Step 4: 约束编译 + 符号审计
│   ├─ Step 5: 输出建模方案 + 解释边界 + 缺失声明（强制）
│   │   ├─ 单一环境足够 → 切换到 [[nash-run]]
│   │   ├─ 多原语组合 → 讨论是否需要自定义组装环境 → [[nash-game-theory]]
│   │   └─ 完全不匹配 → 与用户讨论补充原语
│   └─ 极端案例检测 → 自动附加非决定论声明
├─ 「运行仿真」→ 切换到 [[nash-run]]
├─ 「分析结果」→ 切换到 [[nash-analyze]]
└─ 「创建新环境/原语」→ 切换到 [[nash-game-theory]]
```

## 记忆持久化

每次建模决策持久化到记忆系统：
```python
mcp__memory__add_observations({
    "observations": [{
        "entityName": "nash:primitive-activation",
        "contents": [
            "案例: <简述>",
            "特征向量: <关键维度>",
            "主原语: <primitive_id>",
            "辅助原语: <primitive_id list>",
            "层级: <single/dual/multi>",
            "约束状态: <passed/warnings>",
            "日期: <today>"
        ]
    }]
})
```

## 交叉引用

- [[nash-run]] — 执行仿真实验
- [[nash-analyze]] — 统计验证 + 可视化
- [[nash-game-theory]] — 创建新环境/原语
- `src/primitives.py` — 原语库 + 约束编译器 + 符号审计器源码
