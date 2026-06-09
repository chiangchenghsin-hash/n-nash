# NASH Research Workflows

> **架构版本：v2**（动态原语装配引擎 + Skills v2 重写）
> 适用 Skill 版本：nash-env v2、nash-run v2、nash-analyze v2、nash-game-theory v2、nash-cli

共享工作流模式参考文档。供 `nash-env`、`nash-run`、`nash-analyze` 三个技能共同引用。

---

## 模式 1：完整研究循环

```
nash-env（分类问题） → nash-run（执行模拟） → nash-analyze（验证结果）
```

### 何时使用
用户提出一个开放性的博弈论研究问题，需要端到端的探索流程。

### 步骤

**Step 1 — 问题解构 (nash-env v2)**

1. 与用户讨论研究问题，明确需要建模的经济/社会现象。
2. **提取 14 维特征向量**（非直接选环境）：
   - 信息结构：information_asymmetry、adverse_selection_risk
   - 时间结构：time_horizon_rigidity、repetition_potential
   - 激励结构：incentive_misalignment、moral_hazard_potential
   - 资源/公地：commons_character、public_goods_character、resource_type
   - 网络/扩散：threshold_diffusion_risk、network_density
   - 治理/制度：governance_presence、institutional_layering、exit_cost
   - 冲突/协调：conflict_intensity、coordination_need
   - 信任/声誉：trust_sensitivity、stigma_potential
3. **原语激活**：`PrimitiveLibrary.activate(fv)` 返回匹配的原语及激活原因。
4. **约束编译**：确认状态空间、单调性、相变边界无矛盾。
5. 向用户推荐 1-3 个匹配的 preset 环境，**附特征向量得分和激活理由**，等待用户确认。
   - 辅助：调用 `uv run nash env list` 列出所有可用环境
   - 辅助：调用 `uv run nash env info <game>` 获取候选环境的详细参数与 Nobel 参考

> ⚠️ v2 禁止旧式模板匹配（如"看到冲突→hawk_dove"）。必须先解构特征，再激活原语，最后映射到可执行环境。

**Step 2 — 实验执行 (nash-run)**
1. 根据用户确认的环境和参数，调用 `uv run nash run --preset <name> --seed 42 -o results.json`。
2. **立即并行启动 validate + viz**（不等用户要求）：
   ```bash
   Bash: uv run nash validate --data results.json --type nobel -o validation.json
   Bash: uv run nash viz --data results.json --type all -o charts.png
   ```
3. 如需参数探索，用 sweep 替代单次运行（见模式 3）。

**Step 3 — 结果解读 (nash-analyze v2)**
1. 读取 validation.json，提取 Nobel 验证结论和置信度（>0.9 强支持 / 0.7-0.9 中等 / <0.7 弱）。
2. 查看 charts.png，交叉验证视觉趋势和统计结论。
3. **原语组成识别**：识别结果中哪些原语驱动了核心行为。
4. **贡献分解**：拆解各机制对关键指标的贡献占比（如 social_trust_commons 中：自然修复 / 质量正反馈 / 低质量损耗 / 污名拖累 / 外部冲击）。
5. **断裂点时间线**（social_trust_commons 专用）：标记信任崩塌、质量塌缩、价格归零三类断裂点。
6. **结论强度标注**：每条结论标注为 `模型支持`（方程可推导）/ `启发式解释`（方向正确但非精确量化）/ `评论性隐喻`（语言类比）。
7. 用自然语言向用户解释：收敛情况、与 Nobel 预测的一致性、实际含义。
8. **主动建议下一步**："要不要换个参数看看？" "要不要和多环境对比？"

### 人机讨论闸门
| 闸门 | 位置 | 讨论内容 |
|------|------|----------|
| Gate 1 | env → run | 确认环境选择和参数设置 |
| Gate 2 | run 中途异常 | 模拟是否偏离预期，是否需要调整 |
| Gate 3 | analyze 后 | 结果解读，下一步行动建议 |

---

## 模式 2：并行模型比较 (Agent Team Power)

### 何时使用
用户希望比较同一研究问题在不同博弈模型下的表现（如"不平等在公共品博弈和公地资源博弈中谁更严重"）。

### 步骤
1. **与用户讨论确定 2-4 个候选模型** (nash-env)，统一 agents、rounds、seed 等控制变量。
2. **ALL models in ONE message — 并行启动所有模拟：**
   ```bash
   Bash: uv run nash run --preset hawk_dove --agents 100 --rounds 200 --seed 42 -o compare_hd.json
   Bash: uv run nash run --preset prisoners_dilemma --agents 100 --rounds 200 --seed 42 -o compare_pd.json
   Bash: uv run nash run --preset public_goods --agents 100 --rounds 200 --seed 42 -o compare_pg.json
   Bash: uv run nash run --preset common_pool --agents 100 --rounds 200 --seed 42 -o compare_cp.json
   ```
3. **等待全部完成 → 所有 validate 并行：**
   ```bash
   Bash: uv run nash validate --data compare_hd.json --type nobel
   Bash: uv run nash validate --data compare_pd.json --type nobel
   Bash: uv run nash validate --data compare_pg.json --type nobel
   Bash: uv run nash validate --data compare_cp.json --type nobel
   ```
4. **生成对比表并呈现。**

### Agent Team 增强：多视角解读对比结果

当对比结果有反直觉的发现时，启动 agent team 进行多方解读：

```
Agent({description: "理论经济学家视角",
       prompt: "阅读所有 compare_*.json。从博弈论角度：
                1. 哪个模型的收敛最符合理论预测？哪个最不符合？
                2. 模型间的差异是否可以用理论解释？
                报告在 200 字以内。"})

Agent({description: "政策分析师视角",
       prompt: "阅读所有 compare_*.json。从政策角度：
                1. 哪个模型的结论最具政策含义？
                2. 哪个模型的假设最不符合现实？
                报告在 200 字以内。"})

Agent({description: "统计学家视角",
       prompt: "阅读所有 compare_*.json。从统计角度：
                1. 哪个模拟的结果最稳健（方差最小）？
                2. 哪个可能需要更多轮次/种子？
                报告在 200 字以内。"})
```

汇总三个视角，形成综合解读。

---

## 模式 3：参数空间探索

### 何时使用
用户想了解某个参数对系统行为的影响。

### 小规模探索（<= 100 个配置）
```bash
uv run nash config template --preset hawk_dove -o base_cfg.json
uv run nash sweep \
  --config base_cfg.json --param resource_value \
  --range 1.0,10.0 --step 1.0 --rounds 200 -o sweep_results.json
```

### 大规模探索（> 100 个配置）— Agent Team Split
切分参数范围到 4 个子代理并行执行：
```
Agent({description: "Sweep part 1",
       prompt: "Run: uv run nash sweep --config base_cfg.json --param resource_value --range 0,125 --step 25 --rounds 100 -o sweep_p1.json"})
Agent({description: "Sweep part 2",
       prompt: "Run: uv run nash sweep --config base_cfg.json --param resource_value --range 125,250 --step 25 --rounds 100 -o sweep_p2.json"})
Agent({description: "Sweep part 3",
       prompt: "Run: uv run nash sweep --config base_cfg.json --param resource_value --range 250,375 --step 25 --rounds 100 -o sweep_p3.json"})
Agent({description: "Sweep part 4",
       prompt: "Run: uv run nash sweep --config base_cfg.json --param resource_value --range 375,500 --step 25 --rounds 100 -o sweep_p4.json"})
```

完成后合并：用 Python 脚本拼接所有 `sweep_p*.json` 的 results 数组。

---

## 模式 4：多种子可复现性

### 何时使用
需要严谨的研究报告、发表级结果，或怀疑随机性影响结论时。

### 步骤
1. 与用户确认配置。
2. **使用 `--seeds` 批量执行（一条命令完成 5 个种子）：**
   ```bash
   uv run nash run --preset hawk_dove --agents 100 --rounds 200 --seeds '42,123,456,789,1024' -o batch_results.json
   ```
   输出 JSON 包含 `per_seed_results` 数组，每个元素含 `seed` 和 `final_metrics`。

   **备选：单独执行各种子（更灵活，适合不同参数）：**
   ```bash
   Bash: uv run nash run --preset hawk_dove --agents 100 --rounds 200 --seed 42 -o s42.json
   Bash: uv run nash run --preset hawk_dove --agents 100 --rounds 200 --seed 123 -o s123.json
   Bash: uv run nash run --preset hawk_dove --agents 100 --rounds 200 --seed 456 -o s456.json
   Bash: uv run nash run --preset hawk_dove --agents 100 --rounds 200 --seed 789 -o s789.json
   Bash: uv run nash run --preset hawk_dove --agents 100 --rounds 200 --seed 1024 -o s1024.json
   ```
3. 汇总计算 mean ± std：
   ```bash
   # --seeds 批量模式（单文件）
   python -c "
   import json, numpy as np
   data = json.load(open('batch_results.json'))
   seeds = [r['final_metrics'] for r in data['per_seed_results']]
   for k in seeds[0].keys():
       vals = [s[k] for s in seeds]
       cv = np.std(vals) / (abs(np.mean(vals)) + 1e-9)
       print(f'{k}: {np.mean(vals):.4f} ± {np.std(vals):.4f} (CV: {cv:.1%})')
   "

   # 单独种子模式（多文件）
   python -c "
   import json, glob, numpy as np
   seeds = [json.load(open(f))['final_metrics'] for f in sorted(glob.glob('s*.json'))]
   for k in seeds[0].keys():
       vals = [s[k] for s in seeds]
       cv = np.std(vals) / (abs(np.mean(vals)) + 1e-9)
       print(f'{k}: {np.mean(vals):.4f} ± {np.std(vals):.4f} (CV: {cv:.1%})')
   "
   ```
4. 报告：CV < 10% → 结果稳健；CV >= 10% → 需增加种子或轮次。

### 记忆持久化
保存汇总统计 + 所有原始文件路径。创建 `reproducibility_report` 实体。

---

## 模式 5：记忆支撑的研究日志

### 何时使用
用户在多轮对话中进行长期研究，需要跨会话追踪实验历史。

### 每次实验后保存
```python
mcp__memory__create_entities({
    "entities": [
        {"name": f"exp-{timestamp}", "entityType": "Experiment"}
    ]
})

mcp__memory__add_observations({
    "observations": [
        {
            "entityName": f"exp-{timestamp}",
            "contents": [
                f"环境:{env_id}",
                f"参数:agents={n},rounds={r},seed={s}",
                f"结果:{json.dumps(metrics)}",
                f"Nobel验证:{nobel_conclusion}",
                f"时间:{iso_timestamp}"
            ]
        }
    ]
})

mcp__memory__create_relations({
    "relations": [
        {"from": f"experiment:{env_id}", "to": f"exp-{timestamp}", "relationType": "related_to"}
    ]
})
```

### 查询过往实验
```python
mcp__memory__search_nodes({"query": "Gini 超过 0.5 的实验"})
mcp__memory__search_nodes({"query": "hawk_dove 环境 agent=200"})
mcp__memory__search_nodes({"query": "p < 0.01 的显著结果"})
```

### 研究知识库构建流水线
```
实验前: search_nodes("{研究主题}") → 避免重复
实验中: create_entities + create_relations → 记录过程
实验后: add_observations → 补充结论
阶段结束: 手动整合知识点 → 写入研究日志
```

---

## 模式 6：假设检验循环 (Agent Team Enhanced)

```
形成假设 → 设计实验 → 并行运行 → 统计分析 → 团队解读 → 修正假设
   ^                                                          |
   |__________________________________________________________|
```

### 何时使用
用户有一个可测试的博弈论假设（如"在公地资源博弈中，惩罚机制会提高资源可持续性"）。

### 步骤

**Phase 1 — 形成假设 (nash-env)**
与用户精确定义假设：自变量、因变量、方向预测。用 `uv run nash env info` 确认环境支持。持久化到记忆：`H: "如果引入惩罚，那么 sustainability_index 将上升"`。

**Phase 2 — 设计实验**
设计控制组和实验组。使用 `--params` 注入差异参数：
```bash
# 查看 common_pool 默认参数
uv run nash env info common_pool
# 控制组：默认参数（无惩罚）
# 实验组：通过 --params 注入惩罚相关参数
```

**Phase 3 — 并行运行两组各 5 个种子（10 个模拟同时启动）**
```bash
# 控制组（默认参数）
Bash: uv run nash run --preset common_pool --agents 50 --rounds 200 --seed 42 -o ctrl_s42.json
Bash: uv run nash run --preset common_pool --agents 50 --rounds 200 --seed 43 -o ctrl_s43.json
Bash: uv run nash run --preset common_pool --agents 50 --rounds 200 --seed 44 -o ctrl_s44.json
Bash: uv run nash run --preset common_pool --agents 50 --rounds 200 --seed 45 -o ctrl_s45.json
Bash: uv run nash run --preset common_pool --agents 50 --rounds 200 --seed 46 -o ctrl_s46.json
# 实验组（注入惩罚参数）
Bash: uv run nash run --preset common_pool --agents 50 --rounds 200 --seed 42 --params '{"punishment_strength": 0.5}' -o treat_s42.json
Bash: uv run nash run --preset common_pool --agents 50 --rounds 200 --seed 43 --params '{"punishment_strength": 0.5}' -o treat_s43.json
Bash: uv run nash run --preset common_pool --agents 50 --rounds 200 --seed 44 --params '{"punishment_strength": 0.5}' -o treat_s44.json
Bash: uv run nash run --preset common_pool --agents 50 --rounds 200 --seed 45 --params '{"punishment_strength": 0.5}' -o treat_s45.json
Bash: uv run nash run --preset common_pool --agents 50 --rounds 200 --seed 46 --params '{"punishment_strength": 0.5}' -o treat_s46.json
```

**Phase 4 — 统计分析**
提取关键指标，计算 p 值和效应量。

**Phase 5 — Agent Team 解读**

```
Agent({description: "理论解释",
       prompt: "阅读 ctrl 和 treat 两组结果。从博弈论角度解释观察到的差异。
                如果假设得到支持，机制是什么？如果被推翻，理论原因是什么？"})

Agent({description: "统计严谨性检查",
       prompt: "阅读两组结果。检查：效应量是否足够大？CV是否合理？
                是否存在混淆变量？是否需要更多种子？"})

Agent({description: "下一步建议",
       prompt: "基于 Ctrl vs Treat 的对比结果，建议 3 个最有价值的后续实验。
                每个建议说明：做什么、为什么有价值、预期发现。"})
```

**Phase 6 — 修正假设**
| 结果 | 行动 |
|------|------|
| p < 0.05 且方向正确 | 假设得到支持，讨论机制解释 |
| p < 0.05 但方向相反 | 假设被推翻，形成反向假设 |
| p >= 0.05 | 证据不足，增大样本量或修改参数 |
| 效应量过小 | 统计显著但实际意义有限 |

---

## 模式 7：Agent Team 共识决策（政策建议）

### 何时使用
研究结论涉及政策建议、多利益相关方、或伦理考量时。

### 步骤

1. **完成模拟和分析**（模式 1-6）。
2. **启动 4 人共识团队：**

```
Agent({description: "经济学家",
       prompt: "基于模拟结果，从经济效率角度评估政策含义。
                这个政策会让社会总福利增加还是减少？"})

Agent({description: "公平性分析师",
       prompt: "基于模拟结果，从公平/分配角度评估政策含义。
                谁会受益？谁会受损？分配效应如何？"})

Agent({description: "实施可行性专家",
       prompt: "基于模拟结果，从实施角度评估政策含义。
                信息要求、执行成本、政治可行性如何？"})

Agent({description: "反对意见（魔鬼代言人）",
       prompt: "基于模拟结果，找出最强的反对论点。
                模型的哪些假设在现实中不成立？什么可能出错？"})
```

3. **汇总形成共识报告：**
   - 共识结论
   - 少数派意见（如有）
   - 政策建议（含置信度和前提条件）
   - 需要进一步研究的关键不确定性

---

## 模式 8：长期研究项目 (Memory-Driven)

### 何时使用
用户在多天/多周内进行持续的研究项目。

### 会话启动流程

```
每次新会话：
1. 检查记忆：search_nodes({"query": "NASH 当前研究项目"})
2. 列出历史实验和结论
3. 询问用户："上次我们研究了[X]，得到结论[Y]。要继续深入还是开始新方向？"
```

### 研究状态追踪

```python
# 每次重大进展后更新项目状态
mcp__memory__add_observations({
    "observations": [
        {
            "entityName": "nash:current-project",
            "contents": [
                "项目：[研究主题]",
                "阶段：[探索/实验/分析/撰写]",
                "已完成：[已完成的实验列表]",
                "当前结论：[最新发现]",
                "下一步：[计划中的实验]",
                "更新日期：[日期]"
            ]
        }
    ]
})
```

### 知识图谱构建

```python
# 建立实体间关系
mcp__memory__create_relations({
    "relations": [
        {"from": "project:inequality", "to": "experiment:public_goods_001", "relationType": "contains"},
        {"from": "experiment:public_goods_001", "to": "analysis:pg_001_nobel", "relationType": "analyzed_by"},
        {"from": "analysis:pg_001_nobel", "to": "hypothesis:H1_punishment", "relationType": "supports"},
        {"from": "hypothesis:H1_punishment", "to": "project:inequality", "relationType": "part_of"}
    ]
})
```

---

## 模式 9：原语驱动研究（v2 新增）

### 何时使用
用户的问题不能用单一 preset 环境直接回答，需要组合多个原语（如"社交平台信任崩塌涉及信息不对称 + 公地悲剧 + 重复博弈"）。

### 步骤

**Step 1 — 特征向量提取 (nash-env)**
```
对案例文本做 14 维评分：
  information_asymmetry=0.7  (社交平台存在信息不对称)
  commons_character=0.8      (信任是公地资源)
  repetition_potential=0.8   (长期重复互动)
  trust_sensitivity=0.9      (对信任高度敏感)
  stigma_potential=0.6       (污名化可能)
  ...
```

**Step 2 — 原语激活与耦合规划**
```
PrimitiveLibrary.activate(fv) 返回：
  ✅ social_trust_commons (主原语, commons_character=0.8 激活)
  ✅ spence_signaling     (辅原语, information_asymmetry=0.7 激活)
  ✅ repeated_prisoners_dilemma (辅原语, repetition_potential=0.8 激活)

约束编译：
  CouplingGraph: trust_commons ←→ signaling (series: 信号质量 → 信任修复)
  SymbolicAuditor: 无符号矛盾 ✅
```

**Step 3 — 选择执行路径**

| 情况 | 执行路径 |
|------|---------|
| 主原语有对应 preset | `uv run nash run --preset social_trust_commons --params '...'` |
| 需要纯原语组合（无 preset） | `python -c "from src.primitive_pipeline import PrimitivePipeline; ..."` |

**Step 4 — 运行时约束监测**
运行过程中关注 SymbolicAuditor 告警：
- 单调性违反 → 参数需要调整
- 相变边界接近 → 可能出现断裂点
- 耦合强度过大 → 数值不稳定

**Step 5 — 分析时标注结论来源**
```
结论示例：
  "信任低于 R_crit 时价格归零" → 模型支持（来自 social_trust_commons F4 方程）
  "信号投资与信任恢复正相关"  → 启发式解释（spence_signaling + trust_commons 耦合推导）
  "平台治理类似政府干预"       → 评论性隐喻（无直接方程支撑）
```

### Agent Team 增强：原语耦合审查
```
Agent({description: "耦合一致性审查",
       prompt: "检查以下原语组合的耦合一致性：
                主原语: social_trust_commons
                辅原语: spence_signaling, repeated_prisoners_dilemma
                1. 状态空间是否有变量冲突（同名不同义）？
                2. 单调性规则是否相互矛盾？
                3. 耦合图的环路是否会导致数值发散？"})



                六个机制，分配到对应技能：

机制	嵌入位置	原因
举证锚定	nash-env Step 1 后	特征打分必须有事实依据
对抗检查点	nash-env Step 3 后	原语选择完立刻试图反驳
缺失声明	nash-env Step 5	输出模型时必须列明解释不了什么
预注册	nash-run 运行前	先声明预期，跑完对比
反决策测试	nash-analyze 结论后	什么事实会让结论反转
惊喜审计	nash-analyze 综合后	预期 vs 实际对比
```

---

## 技能使用速查表

| 用户意图 | 技能 | 核心命令 | Agent Team 增强 |
|----------|------|----------|----------------|
| 解构案例特征 | nash-env v2 | 14 维特征向量评分 | 并行子代理研究候选原语 |
| 激活原语组合 | nash-env v2 | `PrimitiveLibrary.activate(fv)` | 耦合一致性审查 |
| 查看可用博弈模型 | nash-env | `uv run nash env list` | 并行子代理研究所有候选 |
| 了解某个博弈机制 | nash-env | `uv run nash env info <game>` | 多角度源码解读 |
| 运行单次模拟 | nash-run | `uv run nash run --preset <name>` | 自动 validate+viz 跟进 |
| 参数扫描 | nash-run | `uv run nash sweep --config cfg.json ...` | 子代理拆分大范围扫描 |
| 多模型对比 | nash-run | 并行 run × N | Agent team 多视角解读 |
| 统计验证 | nash-analyze | `uv run nash validate --type statistical` | 多方统计审查 |
| Nobel 基准验证 | nash-analyze | `uv run nash validate --type nobel` | Agent team 解读差异 |
| 贡献分解分析 | nash-analyze v2 | 读取结果 JSON 分解各机制贡献 | 多视角归因审查 |
| 结论强度标注 | nash-analyze v2 | 标注 `模型支持` / `启发式` / `评论性` | 结论可靠性交叉验证 |
| 生成图表 | nash-analyze | `uv run nash viz --data <file> --type <type>` | 多图表并行生成 |
| 政策建议 | nash-analyze | 共识团队模式 | 4 角色共识决策 |
| 长期研究 | 全部 | 记忆持久化 + 关系图谱 | 跨会话知识积累 |
| 原语驱动研究 | nash-env v2 + nash-run | 特征向量 → 原语激活 → 约束编译 → 仿真 | 耦合审查 + 多视角解读 |

---

## 引用链接

- [[nash-cli]] — CLI 执行引擎（`--preset`, `--params`, `--seeds`, `--config`(仅 sweep)）
- [[nash-env]] — v2 特征向量解构 + 原语激活规划器
- [[nash-run]] — 模拟执行引擎（含约束校验前置要求）
- [[nash-analyze]] — v2 统计验证 + 贡献分解 + 结论强度标注
- [[nash-game-theory]] — v2 原语模块创建（Typed PrimitiveSpec + 耦合规则）