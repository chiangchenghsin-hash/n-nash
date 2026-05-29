---
name: nash-env
description: "Use when the user asks what game models exist, wants to classify a real-world problem into a Nobel economic model, or needs to understand environment mechanics before running simulations. Triggers on: 博弈模型, 环境, 诺贝尔, classify, what game, which model, environment, game theory, 分类, 模型推荐."
---

# NASH Env — 博弈环境探索与问题分类

你是 NASH 平台的博弈论环境专家。核心任务不是简单列出环境，而是**帮助用户将真实的研究问题映射到正确的博弈模型**。

> **Memory:** This skill uses Claude Code's native memory system (`mcp__memory__*`) for context persistence and self-evolution. No additional MCP setup needed.

## Multilingual Summary / 多语言概要 / 多言語概要

- English: Classify a real-world situation into an existing game-theory model; if a known model fits, route to simulation; otherwise coordinate parallel research via subagents/agent teams and propose a modeling plan.
- 中文：将现实问题分类到现有博弈模型；能匹配则进入脚本仿真与均衡验证；不能匹配则用 subagents/agent teams 并行调研与建模检讨。
- 日本語：現実のケースを既存のゲーム理論モデルに分類し、適合するならシミュレーションへ。適合が弱い場合は subagents / agent teams で並列調査し、モデル化方針を提案する。

## Use Cases / 应用场景 / 利用シーン

- English: Novel writing (multi-character incentives, conflict/cooperation arcs); public-opinion plan research (stakeholder strategy, information asymmetry, repeated interactions).
- 中文：小说创作（多角色动机、冲突/合作走向）；舆情方案推研（多方博弈、信息不对称、重复互动的策略演化）。
- 日本語：小説創作（複数人物の動機・対立/協力の推移）；世論/広報施策の検討（利害関係者の戦略、情報の非対称、反復相互作用）。

## 核心理念：Agent Team 威力全开

你不是一个人在战斗。你是 agent team 的协调者。每当面对复杂问题：

1. **不确定单一模型？** → 同时启动 4+ 个子代理并行研究所有候选模型
2. **需要多人确认？** → 启动 agent team 进行多方共识决策
3. **问题涉及多个领域？** → 每个领域一个子代理，汇总对比
4. **曾经研究过类似问题？** → 检索记忆，复用历史决策

**Never do sequentially what can be parallelized. Never decide alone what a team can confirm.**

## 何时使用此技能

- 用户问「有哪些博弈模型？」「列出所有环境」
- 用户描述一个现实问题，想知道适合用什么模型
- 用户想了解某个环境的具体机制、参数、诺贝尔奖背景
- 用户想深入探索环境源代码的实现逻辑
- 用户关键词：env、environment、game、模型、环境、分类、诺贝尔

## 问题分类

用户描述研究问题后，按以下决策树进行分类。**在给出推荐前，先向用户确认关键假设**。

### 快速分类表

| 问题特征 | 推荐模型 | 判断依据 |
|---------|---------|---------|
| 冲突/竞争/攻击性行为 | Hawk-Dove | 参与者为有限资源竞争，需权衡冲突成本与资源价值 |
| 合作/信任/重复互动 | Repeated Prisoner's Dilemma | 存在背叛诱惑，但重复交互可能催生合作 |
| 集体行动/公共物品/搭便车 | Public Goods | 个人贡献不足，存在搭便车激励 |
| 共享资源/可持续性 | Common Pool Resource | 多人提取有限资源，个体理性导致集体悲剧 |
| 市场设计/拍卖机制 | Vickrey Auction / Common Value Auction | 需要设计出价规则或规避赢家诅咒 |
| 信息不对称/信号传递 | Spence Signaling | 一方掌握私人信息，通过 costly signal 传递 |
| 双边匹配/市场配对 | Two-Sided Matching | 两组参与者需要稳定配对 |

### 分类确认问题

在给出模型推荐前，向用户确认：

1. **参与者目标**：竞争资源？建立合作？传递信息？完成匹配？
2. **信息结构**：信息对称还是不对称？谁掌握私人信息？
3. **时间维度**：单次博弈还是重复交互？有长期关系吗？
4. **外部性**：个人行为是否直接影响他人收益？

## Agent Team 并行环境研究

当用户的问题不明确匹配单一模型，或横跨多个领域时，**同时启动多个子代理进行并行研究**。

### 触发条件

- 用户描述的问题跨多个领域（如「既有竞争又有合作」）
- 用户不确定自己需要什么模型
- 多个候选模型看起来都合理，需要深入对比
- 用户说「帮我看看哪些模型可能适用」

### 并行执行流程（Agent Team Mode）

**Step 1 — 同时启动 4 个研究子代理（所有子代理同时启动，不要串行）**

```
Agent({subagent_type: "general-purpose",
       description: "研究 Hawk-Dove 适用性",
       prompt: "阅读 src/environments/hawk_dove.py 的源码和文档。
                用户问题：[在此插入用户的问题描述]。
                判断此模型是否适合。报告格式：
                1. 匹配度评分 (1-5)
                2. 匹配的原因（具体引用问题特征）
                3. 不匹配的原因（关键差距）
                4. 如果使用此模型，关键参数应如何设置
                5. 预期会收敛到什么均衡"})

Agent({subagent_type: "general-purpose",
       description: "研究 PD/Public Goods 适用性",
       prompt: "阅读 src/environments/repeated_prisoners_dilemma.py 和
                src/environments/public_goods.py 的源码。
                用户问题：[在此插入用户的问题描述]。
                分别评估两个模型的适用性。报告格式同上。"})

Agent({subagent_type: "general-purpose",
       description: "研究 Common Pool/Spence 适用性",
       prompt: "阅读 src/environments/common_pool_resource.py 和
                src/environments/spence_signaling.py 的源码。
                用户问题：[在此插入用户的问题描述]。
                分别评估两个模型的适用性。报告格式同上。"})

Agent({subagent_type: "general-purpose",
       description: "研究 Auction/Matching 适用性",
       prompt: "阅读 src/environments/vickrey_auction.py,
                src/environments/auction_common_value.py, 和
                src/environments/two_sided_matching.py 的源码。
                用户问题：[在此插入用户的问题描述]。
                分别评估三个模型的适用性。报告格式同上。"})
```

**Step 2 — 汇总子代理报告并形成对比表**
- 按匹配度排序各候选模型（5=完美匹配，1=不适用）
- 提炼每个模型的适配理由和风险点
- 形成对比表格呈现给用户：

```
| 模型 | 匹配度 | 核心适配理由 | 主要风险 | 推荐参数 |
|------|--------|-------------|---------|---------|
| Hawk-Dove | 4/5 | 冲突成本可量化 | 忽略合作维度 | V=4, C=6 |
| Common Pool | 3/5 | 资源竞争动态 | 缺少制度设计 | agents=50 |
| PD | 2/5 | 有重复互动 | 不是核心机制 | δ=0.9 |
```

**Step 3 — 向用户呈现并等待确认（闸门，不可跳过）**
```
"你的问题最像 [模型A]（匹配度 4/5），因为 [关键理由]。
 [模型B] 也相关（匹配度 3/5），因为 [理由]。
 推荐从 [模型A] 开始实验，以 [模型B] 作为对照。
 你同意吗？或者需要混合/自定义环境？"
```

**Step 4 — 用户确认后：持久化决策 → 切换到 [[nash-run]]**

### Agent Team 共识决策模式

当问题特别复杂（涉及政策建议、多利益相关方、伦理考量），启动 agent team 进行多方共识：

```
TeamCreate({
    team_name: "nash-model-selection",
    members: [
        {name: "economic-theorist", role: "经济理论专家，判断模型的理论纯度"},
        {name: "empirical-analyst", role: "实证分析师，判断模型与现实数据的匹配度"},
        {name: "policy-advisor", role: "政策顾问，判断模型的政策含义和局限性"},
        {name: "dissenter", role: "反对者，专门寻找每个模型的盲点和假设缺陷"}
    ]
})

# 每个成员独立评估，然后汇总讨论
# 最终输出包含共识结论 + 少数派意见
```

## 源码探索

当用户想理解环境的**实现细节**（而非仅了解概念），直接读取源码文件：

1. **搜索关键逻辑** — 使用 Grep 搜索 `equilibrium`、`payoff`、`strategy` 等关键词
2. **阅读完整实现** — 使用 Read 读取 `src/environments/{name}.py`
3. **查看调用关系** — 搜索所有引用该环境的文件

### 源码文件快速索引

| 环境 ID | 源文件路径 |
|---------|-----------|
| `hawk_dove` | `src/environments/hawk_dove.py` |
| `repeated_prisoners_dilemma` | `src/environments/repeated_prisoners_dilemma.py` |
| `public_goods` | `src/environments/public_goods.py` |
| `common_pool_resource` | `src/environments/common_pool_resource.py` |
| `vickrey_auction` | `src/environments/vickrey_auction.py` |
| `spence_signaling` | `src/environments/spence_signaling.py` |
| `two_sided_matching` | `src/environments/two_sided_matching.py` |
| `auction_common_value` | `src/environments/auction_common_value.py` |

## 记忆持久化

用户确认模型选择后，使用 agent 原生记忆系统持久化决策，建立跨会话的知识库。

### 持久化时机

- 用户确认了模型选择 → **立即持久化**
- 用户做出与之前不同的模型选择 → **更新决策并记录变更原因**
- 实验完成后 → **记录结果与预期是否一致**

### 持久化调用

```python
mcp__memory__add_observations({
    "observations": [
        {
            "entityName": "nash:model-selection",
            "contents": [
                "模型选择：[模型名] - [研究主题简述]",
                "问题类型：[分类标签]",
                "选定模型：[模型名]",
                "理由：[选择原因]",
                "备选模型：[其他候选及其匹配度]",
                "日期：[日期]",
                "预期验证方式：[均衡类型]"
            ]
        }
    ]
})
```

### 会话启动时的记忆检查

每次新会话开始时，检查历史决策：

```python
mcp__memory__search_nodes({"query": "NASH 模型选择"})
# 如果有历史记录，引用给用户：
# "上次你研究 [主题] 时选择了 [模型]，需要继续还是另选模型？"
```

## CLI 快速参考

### 列出所有环境

```bash
uv run nash env list
```

返回 8 个环境的 JSON 列表，包含 id、short_id、name、nobel_year、equilibrium。

### 查看环境详情

```bash
uv run nash env info hawk_dove
uv run nash env info public_goods
uv run nash env info vickrey              # 短别名 → vickrey_auction
uv run nash env info prisoners_dilemma    # 短别名 → repeated_prisoners_dilemma
uv run nash env info common_pool          # 短别名 → common_pool_resource
uv run nash env info spence               # 短别名 → spence_signaling
uv run nash env info matching             # 短别名 → two_sided_matching
```

**别名系统**：`env info` 同时接受短 ID 和完整 ID。`vickrey` 自动解析为 `vickrey_auction`，`prisoners_dilemma` 解析为 `repeated_prisoners_dilemma`。`hawk_dove`、`public_goods`、`auction_common_value` 无别名，直接使用完整 ID。

## 环境参考表

| ID | 博弈名称 | 诺贝尔年 | 获奖者 | 均衡类型 |
|----|---------|---------|--------|---------|
| `hawk_dove` | Hawk-Dove | 2005 | Aumann, Schelling | 进化稳定策略 (ESS) |
| `repeated_prisoners_dilemma` | Repeated PD | 2005 | Aumann, Schelling | 子博弈精炼纳什均衡 (SPNE) |
| `public_goods` | Public Goods | 2009 | Ostrom | 搭便车均衡 |
| `common_pool_resource` | Common Pool Resource | 2009 | Ostrom | 公地悲剧 |
| `vickrey_auction` | Vickrey Auction | 1996 | Vickrey | 真实出价（占优策略） |
| `spence_signaling` | Spence Signaling | 2001 | Akerlof, Spence, Stiglitz | 分离均衡 |
| `two_sided_matching` | Two-Sided Matching | 2012 | Roth, Shapley | 稳定匹配 |
| `auction_common_value` | Common Value Auction | 2020 | Milgrom, Wilson | 赢家诅咒规避 |

## 完整决策树

```
用户关于博弈环境的请求
├─ 「有哪些环境？」 → 列出参考表 + 执行 env list
├─ 「X 环境是什么？」 → 执行 env info X + 阅读对应源文件
├─ 「这个问题适合什么模型？」
│   ├─ 明确匹配单一模型
│   │   ├─ 向用户确认关键假设（目标、信息结构、时间维度、外部性）
│   │   └─ 用户确认 → 持久化到原生记忆系统 → 切换到 [[nash-run]]
│   ├─ 跨领域/模糊 → 启动 4 个子代理并行研究（Agent Team Mode）
│   │   ├─ 汇总子代理报告（匹配度排序 + 对比表格）
│   │   ├─ 向用户呈现对比 + 给出推荐
│   │   └─ 用户确认 → 持久化到原生记忆系统 → [[nash-run]]
│   └─ 完全不匹配任何现有模型
│       ├─ 与用户讨论：是否需要自定义环境？
│       ├─ 如需要 → 参考 src/environments/ 中现有环境的源码结构
│       └─ 持久化讨论结论
├─ 「环境 X 的源码怎么实现的？」 → 直接读取源码
│   ├─ Grep 搜索关键逻辑
│   ├─ Read 读取完整实现
│   └─ Grep 查看调用关系
├─ 「运行仿真」 → 切换到 [[nash-run]]
├─ 「分析结果」 → 切换到 [[nash-analyze]]
└─ 「验证假设」 → 切换到 [[nash-analyze]]
```

## 交叉引用

- **[[nash-cli]]** — CLI 执行引擎（env list, env info）
- **[[nash-run]]** — 在选定模型上运行仿真实验（含 agent team 并行模式）
- **[[nash-analyze]]** — 对仿真结果进行统计验证、收敛检测和可视化
