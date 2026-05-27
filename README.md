# NASH -- 纳什均衡仿真枢纽

> **Nash Equilibrium Simulation Hub** -- 覆盖 8 个诺贝尔经济学奖博弈模型的多智能体仿真平台，Claude Code Agent Team 智能编排 + Python CLI 科学计算引擎。

[![Python](https://img.shields.io/badge/python-3.10+-blue.svg)](https://python.org)
[![License](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)

---

## 项目简介

NASH 将经典博弈模型与现代化仿真引擎相结合，为研究人员提供从问题建模、实验执行到结果分析的全流程工具链。

**两层架构**：

- **Layer 1 -- Claude Code Agent Team**：5 个 Skill 组成的智能编排层，负责问题分类、并行实验调度、多视角结果分析和记忆持久化。
- **Layer 2 -- Python CLI 计算核心**：基于 Mesa 的正式博弈仿真引擎，提供环境查询、模拟运行、参数扫描、统计验证和可视化等命令行工具。

**核心能力**：

- **Agent Team 并行** -- 4 子代理同时研究候选模型、多视角并行分析、多种子可复现运行
- **诺贝尔均衡验证** -- 每个环境内置理论预测的均衡检测，输出置信度和改进建议
- **记忆持久化** -- 跨会话保持研究决策和实验结果，构建知识图谱
- **可复现设计** -- 基于种子的确定性运行，多种子汇总统计（均值 +/- 标准差）

---

## 覆盖的诺贝尔博弈模型

| 环境 | 诺贝尔年 | 获奖者 | 均衡类型 |
|------|---------|--------|---------|
| Hawk-Dove（鹰鸽博弈） | 2005 | Aumann, Schelling | 进化稳定策略 (ESS) |
| Repeated Prisoner's Dilemma（重复囚徒困境） | 2005 | Aumann, Schelling | 子博弈精炼纳什均衡 (SPNE) |
| Public Goods（公共物品） | 2009 | Ostrom | 搭便车均衡 |
| Common Pool Resource（公共池资源） | 2009 | Ostrom | 公地悲剧 |
| Vickrey Auction（Vickrey 拍卖） | 1996 | Vickrey | 真实出价（占优策略） |
| Spence Signaling（Spence 信号传递） | 2001 | Akerlof, Spence, Stiglitz | 分离均衡 |
| Two-Sided Matching（双边匹配） | 2012 | Roth, Shapley | 稳定匹配 |
| Common Value Auction（共同价值拍卖） | 2020 | Milgrom, Wilson | 赢家诅咒规避 |

---

## 快速开始

### 环境要求

- Python 3.10 或更高版本
- uv 或 pip 包管理器
- Claude Code（用于 Skill 智能编排层）

### 安装

```bash
# 克隆项目
git clone <repo-url> nash
cd nash/nash-cli

# 使用 uv 安装依赖（推荐）
uv sync

# 或使用 pip
pip install -e .
```

### 验证安装

```bash
uv run nash env list
```

### 第一个实验

```bash
# 1) 查看鹰鸽博弈环境详情
uv run nash env info hawk_dove

# 2) 运行一次仿真（100 个智能体，200 轮）
uv run nash run --preset hawk_dove --agents 100 --rounds 200 --seed 42 -o results.json

# 3) 诺贝尔均衡验证
uv run nash validate --data results.json --type nobel -o validation.json

# 4) 生成可视化图表
uv run nash viz --data results.json --type all -o charts.png
```

### 参数扫描

```bash
# 生成配置模板
uv run nash config template --preset hawk_dove -o cfg.json

# 对 resource_value 参数从 1 到 10 进行扫描
uv run nash sweep --config cfg.json --param resource_value --range 1,10 --step 1 --rounds 200 -o sweep.json
```

---

## Skills 说明

### 1. `nash-env` -- 博弈环境探索与问题分类

将用户的真实世界研究问题映射到正确的博弈模型。核心能力：

- 查看全部 8 个诺贝尔博弈的环境参数、理论背景和实现细节
- 基于决策树的交互式问题分类（确认参与者目标、信息结构、时间维度、外部性）
- **Agent Team 模式** -- 当问题跨多个领域时，同时启动 4 个子代理并行研究所有候选模型，汇总匹配度评分和对比表，最终向用户推荐最佳模型

### 2. `nash-run` -- 仿真实验执行

高性能并行模拟调度引擎。核心能力：

- 单次预设环境运行（自动跟进 validate + viz 并行验证）
- 大规模模拟的后台执行（rounds > 200 / agents > 500）
- **多模型并行比较** -- 同时启动 4 个环境，2 个消息完成全流程
- 参数扫描（小规模用 sweep 命令，大规模切分到 4 个子代理并行）
- **多种子可复现** -- 5 种子并行运行，自动汇总 mean +/- std，计算变异系数
- 完整假设检验循环（控制组 vs 实验组，各 5 种子 + 统计推断）

### 3. `nash-analyze` -- 结果分析

多维度结果验证与解读。核心能力：

- 诺贝尔均衡基准验证（置信度 + 结论 + 改进建议）
- 可视化图表生成（时间序列、不平等趋势、冲突演变）
- **Agent Team 多视角分析** -- 理论经济学家 + 统计学家 + 政策分析师 + 魔鬼代言人，4 角色并行解读，汇总共识结论和少数派意见
- 多文件对比分析（跨环境或跨参数的对比表）
- 结论持久化到记忆系统，建立跨会话知识库

### 4. `nash-cli` -- Python 计算核心

所有其他 Skill 依赖的计算引擎。基于 Mesa Agent-Based Modeling 框架实现 8 个博弈环境。

CLI 命令速查：

| 命令 | 用途 |
|------|------|
| `env list` | 列出所有 8 个环境（JSON 输出） |
| `env info <name>` | 查看环境详情（参数、诺贝尔奖信息） |
| `run --preset <name>` | 运行预设环境仿真 |
| `sweep --config <file> --param <n> --range <a,b> --step <s>` | 参数空间扫描 |
| `validate --data <file> --type nobel\|statistical\|both` | 统计验证与均衡检测 |
| `viz --data <file> --type all\|gini\|hostility -o <out>` | 生成可视化图表 |
| `config template --preset <name> -o <file>` | 生成环境配置模板 |
| `config validate <file>` | 验证配置文件正确性 |

### 5. `nash-game-theory` -- 环境创建指南

教 Claude 如何创建新的博弈模型环境。提供：

- 完整的 Python 环境创建模板（继承 `BaseEnvironment` 基类）
- 收益矩阵定义、代理学习策略、收敛检测逻辑
- 并行 Subagent 研究流程（理论背景 + 现有实现 + 参数参考查找）
- 测试用例模板和验证流程
- 实战演示：如何从零创建"性别战"博弈

---

## 技术栈

| 组件 | 技术 |
|------|------|
| 仿真引擎 | Mesa 2.x (Agent-Based Modeling) |
| 数值计算 | NumPy 1.24+, SciPy 1.10+ |
| 可视化 | Matplotlib 3.7+ |
| 数据模型 | Pydantic 2.x |
| 数据处理 | Pandas 2.x, NetworkX 3.x |
| 配置格式 | YAML (via PyYAML) |
| 包管理 | uv |
| 编程语言 | Python 3.10+ |

### 依赖清单

```python
# 来自 nash-cli/pyproject.toml
pydantic>=2.0.0
numpy>=1.24.0
scipy>=1.10.0
matplotlib>=3.7.0
mesa>=2.0.0
pandas>=2.0.0
networkx>=3.0
pyyaml>=6.0
```

---

## 项目结构

```
n-nash/
├── nash-cli/                     # Python CLI 计算核心
│   ├── pyproject.toml
│   ├── src/
│   │   ├── environments/         # 8 个诺贝尔博弈环境实现
│   │   │   ├── base.py
│   │   │   ├── hawk_dove.py, repeated_prisoners_dilemma.py
│   │   │   ├── public_goods.py, common_pool_resource.py
│   │   │   ├── vickrey_auction.py, spence_signaling.py
│   │   │   ├── two_sided_matching.py, auction_common_value.py
│   │   ├── statistical_validator.py
│   │   ├── visualization.py
│   │   └── validators/
│   │       ├── convergence_detector.py
│   │       └── nobel_validator.py
│   └── scripts/nash_cli/
│       ├── main.py               # 命令行入口与参数解析
│       └── commands/             # run, env_cmd, validate, viz, sweep, config
├── nash-env/SKILL.md             # 环境探索与问题分类 Skill
├── nash-run/SKILL.md             # 仿真执行 Skill
├── nash-analyze/SKILL.md         # 结果分析 Skill
├── nash-game-theory/SKILL.md     # 环境创建指南 Skill
└── NASH-RESEARCH-WORKFLOWS.md    # 共享研究工作流文档
```

---

## 典型工作流

### 完整研究循环

```
nash-env（问题分类） --> nash-run（执行模拟） --> nash-analyze（结果验证）
```

1. **问题匹配** -- 用 `nash-env` 将研究问题映射到博弈模型，Agent Team 并行评估候选模型
2. **实验执行** -- 用 `nash-run` 运行仿真，自动跟进 validate + viz 并行验证
3. **结果解读** -- 用 `nash-analyze` 进行诺贝尔均衡检测、多视角解读和可视化

### 并行模型比较

```
同时启动 4 个环境模拟 --> 同时验证 4 组结果 --> Agent Team 多视角对比解读
```

### 假设检验

```
形成假设 --> 设计对照实验 --> 控制组 + 实验组各 5 种子并行运行
    --> 统计推断（p 值、效应量） --> Agent Team 解读 --> 修正假设
```

---

## 许可

MIT License

---

## 相关资源

- [NASH Research Workflows](NASH-RESEARCH-WORKFLOWS.md) -- 8 种研究工作流完整文档
- [Mesa Documentation](https://mesa.readthedocs.io/) -- Agent-Based Modeling 框架
- [Claude Code Skills](https://docs.anthropic.com/) -- Claude Code Skill 系统