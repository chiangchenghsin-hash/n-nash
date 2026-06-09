---
name: nash-analyze
description: "Analyze NASH simulation results. Use when the user asks to analyze results, validate a simulation, verify a hypothesis, check convergence, visualize data, plot results, interpret output, or understand what simulation data means. Triggers on: analyze, validate, verify, hypothesis, convergence, visualize, plot, chart, significant, what does this mean."
---

# NASH Analyze — Statistical Validation & Multi-Perspective Interpretation (v2)

你把仿真 JSON 变成可决策的报告。不只解释"跑出来什么"，还解释**该方程组属于哪类原语组合、哪项贡献最大、哪些结论是强支持、哪些只是启发式**。

> **Memory:** Uses Claude Code's native memory system.

## Multilingual Summary

- English: Turn raw simulation JSON into a decision-grade report: identify primitive composition, validate (Nobel/stat), visualize, explain contribution decomposition, label conclusion strength, and synthesize multi-perspective agent team output.
- 中文：把仿真 JSON 变成决策级报告：识别原语组合、验证、可视化、解释贡献分解、标注结论强度、多视角 agent team 综合解读。

## 核心理念：从"跑出来什么"到"为什么跑出来 + 能信多少"

**v2 新增分析维度**：
1. **原语组合识别** — 这个仿真结果对应哪组原语的动力学
2. **贡献分解** — 哪些项（再生/质量/污名/冲击）主导了信任变化
3. **结论强度标注** — 强支持 / 启发式 / 评论性
4. **断裂点时间线** — 特别是 social_trust_commons 的三类断裂点

## 快速决策

```
有 results.json？
├─ 有 "environment_type" → 诺贝尔验证 + 指标可视化
├─ 有 "trust_history" / "stigma_history" → social_trust_commons 专项分析（直接可用）
├─ 有 "breakpoints" → 断裂点时间线（直接可用）
├─ 有 "equilibrium_type" → 稳态分类解读
├─ 有 "history" 数组 → 时间序列可视化
├─ 多个 .json 文件 → 对比分析
└─ 不确定 → 先读文件检查顶层 key
```

## 标准分析流程

### Step 1 — 并行验证 + 可视化

```bash
# 同时启动（同一消息）：
Bash: uv run nash validate --data results.json --type nobel -o validation.json
Bash: uv run nash viz --data results.json --type all -o charts.png
```

### Step 2 — 读取并交叉验证

读取 `validation.json` 和 `charts.png`，检查二者是否一致。

### Step 3 — 原语组合识别

根据结果中的环境类型和指标判断对应原语：
- `social_trust_commons` → social_trust_commons 原语（可含 lemons 辅原语）
- `common_pool_resource` → common_pool_resource 原语
- 等

### Step 4 — 贡献分解（social_trust_commons 专项）

对于 social_trust_commons 结果，从 `history` 数组（含 trust, quality, stigma, price, avg_profit）和 `trust_history`/`quality_history`/`stigma_history`/`price_history` 列表计算逐轮 delta，然后反推各贡献项的相对大小：

```
信任变化的近似贡献分解（从序列 delta 推导）:
  Δtrust ≈ 自然再生项 + 质量反馈项 + 污名拖累项 + 外部冲击项

方法：读取相邻两轮的 trust/quality/stigma/price 变化量，
按动力学方程 F2 的结构反推各分量的符号和相对大小。

注意：这是从观测序列的近似反推，不是精确分解。
如需精确分解，需要在环境代码中导出 per_component 字段。
```

### Step 5 — 断裂点时间线（social_trust_commons 专项）

social_trust_commons 的结果现在通过 run.py 直接输出 `breakpoints` 字段（三类断裂点）。

读取 `breakpoints` 字典，如有 `total_breakpoints > 0` 则输出时间线：
```
轮次    │ 事件
────────┼──────────
Round 8 │ 🔴 崩塌断裂点 — R < R_crit
Round 14│ 🔴 价格断裂点 — 利润连续 10 轮为负
Round 26│ 🔴 生态断裂点 — R < 50%K 且连续净损耗
```

## 诺贝尔基准验证

```bash
uv run nash validate --data results.json --type nobel
```

| confidence | 含义 | 行动 |
|------------|------|------|
| > 0.9 | 强匹配诺贝尔预测 | "该环境收敛到了诺贝尔奖理论预测的均衡。" |
| 0.7-0.9 | 中等匹配 | "基本符合理论预测，存在一些偏差。" |
| < 0.7 | 弱匹配 | "未收敛到预期均衡。检查 suggestions 字段。" |

## 社会信任公地专项指标解读

| 指标 | 含义 | 健康范围 | 危险信号 |
|------|------|---------|---------|
| `trust_depletion_rate` | 信任从初始到最终的枯竭比例 | < 0.2 | > 0.5 |
| `sustainability_index` | 组合式可持续性（五因子加权） | > 0.6 | < 0.3 |
| `price_decline_rate` | 价格从窗口始到末的下降比例 | < 0.1 | > 0.5 |
| `avg_profit_health` | 利润相对 base_price 的健康度 | > 0.3 | < 0.1 |
| `avg_quality` | 平均活动质量 | > 0.5 | < 0.2 |
| `avg_stigma` | 污名存量 | < 200 | > 500 |

## 稳态分类解读

| 稳态类型 | Emoji | 含义 | 行动建议 |
|----------|-------|------|---------|
| `healthy_equilibrium` | ✅ | 高信任 + 正利润 + 稳定 | 当前参数组合可持续 |
| `low_trust_trap` | ⚠️ | 低信任但稳定（"死得很稳"） | 系统僵化，需外部干预打破 |
| `collapsed_equilibrium` | ❌ | 信任归零 + 价格归零 | 市场已拒收，需重建信任 |
| `transitioning` | ⏳ | 仍在变化中 | 增加轮次继续观察 |

## Agent Team 多视角分析

复杂/意外结果时，部署 4 个并行分析 Agent：

```
Agent 1: 经济学理论视角 — 结果是否符合原语理论预测？有无模型误设信号？
Agent 2: 统计/实证视角 — 收敛可信吗？有无趋势漂移？需要更多轮次吗？
Agent 3: 实践/政策视角 — 什么现实含义？外推局限在哪？最有价值的后续实验？
Agent 4: 反对者视角 — 最强反驳论据？什么隐藏假设可能使结果无效？
```

综合为：
1. **共识结论**
2. **分歧观点**
3. **置信度评估**
4. **惊喜发现** — 哪些结果偏离了 nash-run 的预注册声明？各 Agent 对此的解释是什么？
5. **反决策条件共识** — 各 Agent 一致认为"如果 X 为真则结论反转"的条件有哪些？
6. **下一步建议**

## 结论强度标注

每个结论必须标注强度：

| 标签 | 含义 | 示例 |
|------|------|------|
| `模型支持` | 方程可严格推出的结论 | "信任低于 R_crit 后价格归零" |
| `启发式解释` | 方向正确但不能精确量化 | "治理强度每增加 0.1，断裂点大约后移 20-30 轮" |
| `评论性隐喻` | 语言层类比，动力学层不够格 | "这就像平台生态的'公地悲剧'" |

## 展示结果模板

1. **结论一句话**: "社会信任公地模拟收敛到 collapsed_equilibrium — 第 8 轮发生崩塌。"
2. **含义一句话**: "低治理 + 高污名敏感的组合导致信任在第 8 轮跌破临界值，系统快速崩溃。"
3. **验证置信度**: "诺贝尔验证置信度 0.92（2009 Ostrom — 社会信任公地悲剧）。"
4. **断裂点时间线**（如有）
5. **贡献分解**（social_trust_commons 专项）
6. **结论强度标注**
7. **MOI 市场特征指标**（如有）
8. **预注册对比（强制）**：
   ```
   预期 vs 实际:
     ✅ <指标 X>: 预期 [A,B], 实际 <值> ✓
     ❌ <指标 Y>: 预期 [C,D], 实际 <值> ✗ — 可能原因: <简短分析>
     ⚡ <指标 Z>: 预期之外 — 此为惊喜，可能意味着 <什么>
   ```
9. **反决策测试（强制）**：
   ```
   什么事实为真会让上述结论完全反转:
     1. <事实 A> — 如果 X 不是 Y 而是 Z，则结论反转
     2. <事实 B> — 如果 A 与 B 的实际关系与模型假设相反
     3. <事实 C> — 如果阈值不在理论值附近

   当前这些反转条件成立的可能性评估:
     事实 A: <低/中/高> — <简短理由>
     事实 B: <低/中/高> — <简短理由>
     事实 C: <低/中/高> — <简短理由>
   ```
10. **下一步建议**:
    - "需要参数扫描来定位断裂临界点吗？"
    - "要不要对照 physical CPR 看信任公地是否崩塌更快？"
    - "要跑 5 seed 验证可复现性吗？"
    - "上述反决策条件中哪些可以设计实验来测试？"

## 记忆持久化

```python
mcp__memory__add_observations({
    "observations": [{
        "entityName": f"nash-analysis-{date}-{slug}",
        "contents": [
            "分析: <简述>",
            "环境/原语: <type>",
            "结果: <equilibrium_type>",
            "诺贝尔置信度: <confidence>",
            "断裂点: <如有>",
            "下一步建议: <action>",
            "日期: <today>"
        ]
    }]
})
```

## CLI 快速参考

```bash
uv run nash validate --data <file> --type nobel
uv run nash validate --data <file> --type both -o report.json
uv run nash viz --data <file> --type all -o charts.png
```

## 交叉引用

- [[nash-env]] — 建模方案来源
- [[nash-run]] — 生成新仿真数据
- [[nash-game-theory]] — 创建新环境/原语
- `src/primitives.py` — 原语库 + 约束编译器源码
