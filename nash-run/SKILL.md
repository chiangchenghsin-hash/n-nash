---
name: nash-run
description: "Use when the user asks to run a simulation, execute an experiment, test a game theory model, sweep parameters, compare environments. Triggers on: run simulation, execute experiment, test game, hawk dove, prisoner's dilemma, public goods, common pool, vickrey, parameter sweep, start experiment, compare models, social trust."
---

# NASH Run — Simulation Execution (v2)

你是博弈论仿真执行器。通过 NASH CLI (`uv run nash`) 编排可复现实验。**运行前必须展示图谱结构、参数卡、约束状态**。

> **Memory:** This skill uses Claude Code's native memory system.

## Multilingual Summary

- English: Execute reproducible simulations; before running, display topology graph, parameter card with provenance, and constraint status; never run before constraint compilation is clear.
- 中文：执行可复现仿真；运行前必须展示图谱结构、参数卡（含来源标注）、约束状态；不允许在约束未通过前直接运行。

## 核心理念：运行前先校验

**新规则（v2）**：
```
运行前必须展示：
  1. 图谱结构摘要
  2. 参数卡（每个参数标注来源）
  3. 约束状态（通过/警告/失败）
  4. 稳定性风险提示
  5. 预注册声明（强制）
```

**禁止**: 在未完成约束编译和符号审计前直接跑大量实验。

### 预注册（强制）

**在任何仿真运行之前，必须先声明预期结果。** 这是在跑出结果后防止"后视偏见解释"的机制。

预注册声明必须包含：

```
预注册:
  如果模型正确，我预期看到:
    - <关键指标> 的预期区间: <MIN> ~ <MAX>
    - 收敛/不收敛状态: <预期>
    - <2-3 个具体可测的预测>

  如果看到以下现象之一，我的模型可能有问题:
    - <反证现象 A> — 意味着 <什么假设被推翻>
    - <反证现象 B> — 意味着 <什么方向错了>
    - <反证现象 C> — 意味着 <什么机制缺了>

  严重性阈值:
    如果 <指标 X> < <阈值>: 模型主要假设不可信
    如果 <指标 Y> > <阈值>: 需要重新考虑原语选择
```

**执行后必须对比**：模拟完成后，显式标注哪些预期被满足、哪些被违反、哪些是惊喜。

## 快速决策

```
用户请求运行仿真
├─ 单一预设 → 标准运行 → 并行 validate + viz
├─ 参数扫描 → sweep 命令
├─ 多模型对比 → 并行 run
├─ 研究级复现 → 5-seed batch → 统计检验
└─ 完整假设检验 → control vs treatment → 统计对比
```

## 标准预设运行

```bash
uv run nash run --preset <name> --agents N --rounds N --seed N -o results.json
```

### 预设快速参考

| 预设 | 环境 ID | 推荐 agents | 推荐 rounds | Nobel 年 |
|------|---------|------------|-------------|----------|
| `hawk_dove` | hawk_dove | 100 | 300 | 2005 |
| `prisoners_dilemma` | repeated_prisoners_dilemma | 20 | 400 | 2005 |
| `public_goods` | public_goods | 50 | 300 | 2009 |
| `common_pool` | common_pool_resource | 50 | 300 | 2009 |
| `social_trust_commons` | social_trust_commons | 20 | 400 | 2009 |
| `vickrey` | vickrey_auction | 20 | 200 | 1996 |
| `spence` | spence_signaling | 100 | 300 | 2001 |
| `matching` | two_sided_matching | 50/50 | 200 | 2012 |
| `auction_common_value` | auction_common_value | 10 | 200 | 2020 |

### 社会信任公地专用参数

```bash
# 脆弱信任场景（低治理 → 崩塌）
uv run nash run --preset social_trust_commons --rounds 400 --seed 42 \
  --params '{"governance_strength": 0.03, "num_organizers": 30, "natural_repair_rate": 0.003}'

# 强治理场景（高治理 → 健康稳态）
uv run nash run --preset social_trust_commons --rounds 400 --seed 42 \
  --params '{"governance_strength": 0.9, "num_organizers": 15, "natural_repair_rate": 0.08}'
```

### 运行后必须并行验证

```bash
# 同时启动（同一消息中）：
Bash: uv run nash validate --data results.json --type nobel -o validation.json
Bash: uv run nash viz --data results.json --type all -o charts.png
```

## 参数卡模板（运行前展示）

当从 [[nash-env]] 收到建模方案后，运行前先展示参数卡：

```
| 参数 | 值 | 来源 | 含义 | 低值解释 | 高值解释 | 风险 |
|------|-----|------|------|---------|---------|------|
| governance_strength | 0.3 | 特征映射 | 平台治理强度 | 弱治理 | 严实名/严处罚 | 过高压死活动 |
| stigma_drag | 0.15 | 原语默认 | 污名拖累系数 | 公众健忘 | 污名粘滞 | 过高→快速崩塌 |
| natural_repair_rate | 0.03 | 场景假设 | 信任修复速率 | 一伤难愈 | 容易重启 | 过高掩盖问题 |
| price_elasticity | 1.5 | 原语默认 | 价格对信任的弹性 | 价格迟钝 | 价格过度敏感 | 过高→价格跳水 |
| quality_cost_coefficient | 0.3 | 约束推导 | 维持质量所需成本 | 质量廉价 | 质量昂贵 | 过高→普遍降质 |
```

**每个参数必须标注来源**: `原语默认` | `特征映射` | `约束推导` | `场景假设`

## 约束状态展示（运行前展示）

```
约束编译报告:
  ✅ 状态空间: 所有变量在合法域内
  ✅ 单调性: trust → price 方向正确
  ⚠️ 流量守恒: stigma 流入/流出未显式对账（不影响运行）
  ✅ 相变边界: R < 200 时价格归零逻辑已就绪

稳定性风险: LOW — 推荐先单 seed 验证，再 5-seed 复现
```

## 参数扫描

sweep 需要先通过 `config template` 生成配置文件，然后用 `--config` 指定：

```bash
# 生成配置文件
uv run nash config template --preset social_trust_commons -o stc_cfg.json

# 扫治理强度（--range MIN,MAX，--step 单独指定）
uv run nash sweep --config stc_cfg.json \
  --param governance_strength --range 0.01,0.9 --step 0.1 --rounds 300 -o sweep_gov.json

# 扫组织者数量
uv run nash sweep --config stc_cfg.json \
  --param num_organizers --range 5,50 --step 5 --rounds 300 -o sweep_n.json
```

## 多模型并行对比

一次消息中同时启动（不串行）：
```bash
# 并行启动 3 个模型
Bash: uv run nash run --preset social_trust_commons --rounds 300 --seed 42 -o stc.json
Bash: uv run nash run --preset common_pool --rounds 300 --seed 42 -o cpr.json
Bash: uv run nash run --preset prisoners_dilemma --rounds 300 --seed 42 -o pd.json
```

## 多 Seed 复现

```bash
uv run nash run --preset social_trust_commons --rounds 300 --seeds 42,123,456,789,1024 -o multi_seed.json
```

## 记忆持久化

```python
mcp__memory__add_observations({
    "observations": [{
        "entityName": f"nash-experiment-{date}",
        "contents": [
            "实验: <preset/原语组合>",
            "参数: <key params>",
            "种子数: <N>",
            "主要发现: <摘要>",
            "日期: <today>"
        ]
    }]
})
```

## CLI 快速参考

```bash
# 运行
uv run nash run --preset <name> --agents N --rounds N --seed N -o out.json

# 扫描
uv run nash sweep --config <cfg.json> --param <p> --range <MIN,MAX> --step <S> --rounds N

# 验证
uv run nash validate --data results.json --type nobel

# 可视化
uv run nash viz --data results.json --type all -o charts.png

# 列出所有环境
uv run nash env list
```

## 交叉引用

- [[nash-env]] — 建模方案来源（特征向量 + 原语激活 + 参数卡）
- [[nash-analyze]] — 运行后的验证 + 可视化 + 多视角解读
- [[nash-game-theory]] — 需要新环境/原语时
