# NASH Research Workflows

共享工作流模式参考文档。供 `nash-env`、`nash-run`、`nash-analyze` 三个技能共同引用。

---

## 模式 1：完整研究循环

```
nash-env（分类问题） → nash-run（执行模拟） → nash-analyze（验证结果）
```

### 何时使用
用户提出一个开放性的博弈论研究问题，需要端到端的探索流程。

### 步骤

**Step 1 — 问题匹配 (nash-env)**
1. 与用户讨论研究问题，明确需要建模的经济/社会现象。
2. 调用 `uv run nash env list` 列出所有可用环境。
3. 调用 `uv run nash env info <game>` 获取候选环境的详细参数与 Nobel 参考。
4. 向用户推荐 1-3 个匹配的环境，说明选择理由，等待用户确认。

**Step 2 — 实验执行 (nash-run)**
1. 根据用户确认的环境和参数，调用 `uv run nash run --preset <name> --seed 42 -o results.json`。
2. 如需参数探索，用 `uv run nash sweep` 替代单次运行。
3. 监控 stderr 输出判断进度，记录运行时出现的异常。

**Step 3 — 结果分析 (nash-analyze)**
1. 调用 `uv run nash validate --data results.json --type both -o validation.json` 进行统计和 Nobel 验证。
2. 对关键发现调用 `uv run nash viz --data results.json --type all -o charts.png` 生成可视化。
3. 用自然语言向用户解释 p 值、效应量、收敛情况、与 Nobel 预测的一致性。

### 人机讨论闸门
| 闸门 | 位置 | 讨论内容 |
|------|------|----------|
| Gate 1 | env → run | 确认环境选择和参数设置 |
| Gate 2 | run 中途异常 | 模拟是否偏离预期，是否需要调整 |
| Gate 3 | analyze 后 | 结果解读，下一步行动建议 |

### DevFlowMemory 持久化
每步保存：环境ID、参数、结果摘要、统计量。关联链：env entity → run entity → analysis entity。
保存格式：`create_memory({"content": "NASH: {env}/{date}\n\n{summary}", "tags": ["nash", "experiment"], "type": "semantic"})`

---

## 模式 2：并行模型比较

### 何时使用
用户希望比较同一研究问题在不同博弈模型下的表现（如"不平等在公共品博弈和公地资源博弈中谁更严重"）。

### 步骤
1. **与用户讨论确定 2-4 个候选模型** (nash-env)，统一 agents、rounds、seed 等控制变量。
2. **为每个模型启动并行子 agent：**
   ```
   Agent("用 nash-run 运行 {model}，agents=100, rounds=200, seed=42，输出 results_{model}.json")
   ```
3. **等待全部完成**，失败则单独重试。
4. **创建汇总 agent** 读取所有 `results_*.json`，提取 final_gini 和 final_mean_hostility，生成比较表格。
5. **对每个模型运行 `uv run nash viz`**，并排展示图表，向用户报告。

---

## 模式 3：参数空间探索

### 何时使用
用户想了解某个参数（资源池大小、垄断程度、轮次数）对系统行为的影响。

### 小规模探索（< 10 个配置）
```bash
uv run nash sweep \
  --config base_config.json --param center_pool \
  --range 50,500 --step 50 --steps 100 -o sweep_results.json
```
Note: sweep results use a different format (parameter→metric pairs). Use custom plotting, not the standard `viz` command.

### 大规模探索（10+ 个配置）
切分参数范围到多个子 agent 并行执行：
```
Agent("uv run nash sweep --param X --range 0,125 --step 25 -o sweep_p1.json")
Agent("uv run nash sweep --param X --range 125,250 --step 25 -o sweep_p2.json")
Agent("uv run nash sweep --param X --range 250,375 --step 25 -o sweep_p3.json")
Agent("uv run nash sweep --param X --range 375,500 --step 25 -o sweep_p4.json")
```
完成后创建汇总 agent 读取所有 `sweep_p*.json`，拼接为完整参数-指标映射表。Note: sweep results use a different format (parameter→metric pairs). Use custom plotting, not the standard `viz` command.

---

## 模式 4：多种子可复现性

### 何时使用
需要严谨的研究报告、发表级结果，或怀疑随机性影响结论时。

### 步骤
1. 与用户确认配置，固定为单个 JSON。
2. **并行执行 3-5 个种子：**
   ```
   # Launch 5 parallel Bash calls:
   Bash("uv run nash run --config config.json --seed 42 -o run_s42.json")
   Bash("uv run nash run --config config.json --seed 123 -o run_s123.json")
   Bash("uv run nash run --config config.json --seed 456 -o run_s456.json")
   Bash("uv run nash run --config config.json --seed 789 -o run_s789.json")
   Bash("uv run nash run --config config.json --seed 999 -o run_s999.json")
   # All launched simultaneously in one message, results collected when all complete.
   ```
3. 汇总 agent 读取所有结果，计算 final_gini、final_mean_hostility 的 mean/std/CI。
4. 报告用户：变异系数 < 10% 则结果稳健，否则需增加种子或检查收敛。

### DevFlowMemory
保存所有原始数据 + `reproducibility_report.json`，记录配置 + 种子列表 + 汇总统计。

---

## 模式 5：记忆支撑的研究日志

### 何时使用
用户在多轮对话中进行长期研究，需要跨会话追踪实验历史。

### 每次实验后保存
```
create_entities([{name: "exp-{ts}", entityType: "Experiment"}])
add_observations("exp-{ts}", ["环境:{env_id}", "参数:agents={n},rounds={r},seed={s}",
               "结果:Gini={g},Hostility={h}", "统计:p={p},d={d}"])
create_relations([{from: "experiment:{env_id}", to: "exp-{ts}", relationType: "related_to"}])
```

### 查询过往实验
```
search_memory("Gini 超过 0.5 的实验")
search_memory("{env_id} 环境 agent=200 的实验")
search_memory("p < 0.01 的显著结果")
```

### 研究知识库构建流水线
```
实验前: search_memory("{研究主题}") → 避免重复
实验中: create_entities + create_relations → 记录过程
实验后: add_observations → 补充结论
阶段结束: memory_consolidate → 整合知识点
```
- 定期运行 `memory_consolidate` 将碎片观察合并为结构化知识。
- 将每个环境的实验汇总为一个 `{env_id}_research_log` 实体。

---

## 模式 6：假设检验循环

```
形成假设 → 设计实验 → 运行模拟 → 分析验证 → 修正假设
   ^                                                  |
   |__________________________________________________|
```

### 何时使用
用户有一个可测试的博弈论假设（如"在公地资源博弈中，惩罚机制会提高资源可持续性"）。

### 步骤

**Phase 1 — 形成假设 (nash-env)**
与用户精确定义假设：自变量、因变量、方向预测。用 `uv run nash env info` 确认环境支持。写入 DevFlowMemory：`H: "如果引入惩罚，那么 pool_end/pool_start 将上升"`。

**Phase 2 — 设计实验 (nash-run 准备)**
设计控制组和实验组配置。用 `uv run nash config template` 生成基线，手动编辑添加实验变量。每组至少 5 个种子。

**Phase 3 — 运行模拟 (nash-run)**
并行运行两组各 5 个种子：
```bash
# 控制组                   # 实验组
uv run nash run --config ctrl.json --seed 42 -o ctrl_1.json    uv run nash run --config treat.json --seed 42 -o treat_1.json
uv run nash run --config ctrl.json --seed 43 -o ctrl_2.json    uv run nash run --config treat.json --seed 43 -o treat_2.json
# ... ×5                                              # ... ×5
```

**Phase 4 — 分析验证 (nash-analyze)**
提取关键指标，构建 `control_values` 和 `treatment_values`。调用 `uv run nash validate --type statistical`，检查 p 值和效应量，生成对比图。

**Phase 5 — 修正假设**
| 结果 | 行动 |
|------|------|
| p < 0.05 且方向正确 | 假设得到支持，讨论机制解释 |
| p < 0.05 但方向相反 | 假设被推翻，形成反向假设 |
| p >= 0.05 | 证据不足，增大样本量或修改参数 |
| 效应量过小 | 统计显著但实际意义有限 |

迭代追踪：`add_observations("H-{id}", "迭代{n}: p={p}, d={d}, 结论:{支持/推翻/不足}")`

---

## 技能使用速查表

| 用户意图 | 技能 | 核心命令 |
|----------|------|----------|
| 查看可用博弈模型 | nash-env | `uv run nash env list` |
| 了解某个博弈机制 | nash-env | `uv run nash env info <game>` |
| 运行单次模拟 | nash-run | `uv run nash run --preset <name>` |
| 参数扫描 | nash-run | `uv run nash sweep --param X --range a,b` |
| 生成配置文件 | nash-run | `uv run nash config template --preset <name>` |
| 统计验证 | nash-analyze | `uv run nash validate --type statistical` |
| Nobel 基准验证 | nash-analyze | `uv run nash validate --type nobel` |
| 生成图表 | nash-analyze | `uv run nash viz --data <file> --type <type>` |
| 创建新博弈环境 | nash-game-theory | 按模板创建新环境文件 |

---

## 引用链接

- [[nash-env]] — 博弈环境目录与探索
- [[nash-run]] — 模拟执行引擎
- [[nash-analyze]] — 统计验证与可视化
- [[nash-game-theory]] — 自定义博弈环境创建
