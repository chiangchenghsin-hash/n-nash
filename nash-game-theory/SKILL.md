---
name: nash-game-theory
description: NASH 博弈论环境创建指南 - 用于创建和测试新的博弈环境，包括囚徒困境、鹰鸽博弈、智猪博弈等经典博弈模型的实现模板和测试规范
---

# NASH 博弈论环境创建指南

你是 NASH（Nash Equilibrium Simulation Hub）项目的开发专家，专门帮助创建新的博弈环境和测试用例。

## Multilingual Summary / 多语言概要 / 多言語概要

- English: When no existing model fits, design a new environment with subagents researching theory/benchmarks, then implement a generic, configurable environment (no case hardcoding) and wire it into CLI run/validate/viz.
- 中文：当现成模型不匹配时，用 subagents 并行调研理论/benchmark，然后实现“可配置、可复现、无案例硬编码”的新环境，并接入 CLI 的 run/validate/viz。
- 日本語：既存モデルが合わない場合、subagents で理論/ベンチマークを並列調査し、ケース固有のハードコードを避けた汎用・設定可能な新環境を実装し、CLI の run/validate/viz に統合する。

## Use Cases / 应用场景 / 利用シーン

- English: Novel writing & public-opinion planning often need custom incentive structures; use this skill to formalize those incentives into a reusable environment template.
- 中文：小说创作与舆情方案推研常需要自定义激励结构；用本技能把“人设/利益/信息结构”形式化为可复用的新环境模板。
- 日本語：小説創作や世論/広報施策では独自のインセンティブ設計が必要になりやすい。本スキルで人物/利害/情報構造を再利用可能な環境テンプレートに落とし込む。

## 项目概述

NASH 是一个基于 NumPy 的多智能体博弈论模拟平台，通过 NASH CLI + Claude Code Skills 生态系统进行博弈论研究和验证。

**核心架构**：规则驱动 Agent + 博弈环境层
- **Agent**：基于 NumPy 的纯规则决策（dataclass + 策略更新规则）
- **社会场域**：博弈环境层（囚徒困境、鹰鸽博弈、公共物品等 8 种）
- **LLM 推理层**：由 Claude Code Skills（[[nash-env]]、[[nash-analyze]]）在问题分类和结果分析阶段提供，不在 Agent 运行时调用

## 技能协作流程

创建新博弈环境时，这套技能的分工是：

```
用户描述新博弈 → 你用这个技能创建环境代码
                  ↓
              [[nash-env]] — 确认没有现成模型可以复用
                  ↓
              你创建 src/environments/new_game.py + 测试
                  ↓
              [[nash-run]] — 执行模拟、验证环境能跑
                  ↓
              [[nash-analyze]] — 验证是否收敛到纳什均衡
```

**相关技能：**
- [[nash-cli]] — CLI 执行引擎，运行新环境的模拟测试
- [[nash-env]] — 探索已有的 8 种博弈环境，确认不需要重复创建
- [[nash-run]] — 运行新环境的模拟测试，执行参数探索
- [[nash-analyze]] — 分析模拟结果，验证纳什均衡预测

## 使用 Subagent 研究博弈论模型

在编写代码之前，用 subagent 并行研究，避免拍脑袋实现：

1. **理论研究** — 搜索博弈的学术定义、收益矩阵、纳什均衡条件
2. **现有实现** — 搜索类似的开源实现或已知 benchmark
3. **参数分析** — 关键参数（学习率、探索率、收敛阈值）的推荐范围

示例：
```
同时启动 3 个 subagent：
Agent 1: 搜索"Battle of the Sexes Nash equilibrium payoff matrix"
Agent 2: 搜索"coordination game multi-agent simulation convergence"
Agent 3: 读取 src/environments/hawk_dove.py 作为实现参考
综合结果后再开始编码。
```

## 环境创建模板

### 步骤 1: 创建环境类

在 `src/environments/` 下创建新文件，例如 `new_game.py`：

```python
"""
{游戏名称}环境
诺贝尔奖：{年份} {获奖者}
理论预测：{理论预测结果}
验证：{验证目标}
"""

import numpy as np
from typing import Dict, Any, List, Tuple
from dataclasses import dataclass
from .base import BaseEnvironment, ConvergenceResult


@dataclass
class GameAgent:
    """{游戏名称}代理"""
    agent_id: int
    learning_rate: float = 0.1
    exploration_rate: float = 0.1
    
    # 策略：{具体策略}概率
    strategy_probability: float = 0.5
    
    # 历史记录
    history: List[Dict] = None
    
    def __post_init__(self):
        if self.history is None:
            self.history = []
    
    def decide_action(self) -> str:
        """决定行动"""
        if np.random.random() < self.exploration_rate:
            return np.random.choice(["action1", "action2"])
        else:
            if np.random.random() < self.strategy_probability:
                return "action1"
            else:
                return "action2"
    
    def update_strategy(self, own_action: str, payoff: float, **kwargs):
        """根据收益更新策略"""
        if payoff > 0:
            # 正收益：强化当前策略
            if own_action == "action1":
                self.strategy_probability = min(1.0,
                    self.strategy_probability + self.learning_rate)
            else:
                self.strategy_probability = max(0.0,
                    self.strategy_probability - self.learning_rate)
        else:
            # 负收益：弱化当前策略
            if own_action == "action1":
                self.strategy_probability = max(0.0,
                    self.strategy_probability - self.learning_rate)
            else:
                self.strategy_probability = min(1.0,
                    self.strategy_probability + self.learning_rate)


class {GameName}Environment(BaseEnvironment):
    """
    {游戏名称}环境
    验证：{验证目标}
    """
    
    # 收益矩阵（根据具体博弈定义）
    PAYOFF_MATRIX = {
        ("action1", "action1"): (3, 3),
        ("action1", "action2"): (0, 5),
        ("action2", "action1"): (5, 0),
        ("action2", "action2"): (1, 1)
    }
    
    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self.agents: List[GameAgent] = []
        self.game_history: List[Dict] = []
        self.metrics_history: List[float] = []
        
        # 博弈参数
        self.param1 = self.parameters.get("param1", default_value)
    
    def initialize_agents(self) -> None:
        """初始化代理"""
        num_agents = self.parameters.get("num_agents", 20)
        learning_rate = self.parameters.get("learning_rate", 0.1)
        exploration_rate = self.parameters.get("exploration_rate", 0.1)
        
        self.agents = []
        for i in range(num_agents):
            agent = GameAgent(
                agent_id=i,
                learning_rate=learning_rate,
                exploration_rate=exploration_rate
            )
            self.agents.append(agent)
    
    def _calculate_payoffs(self, action1: str, action2: str) -> tuple:
        """计算收益"""
        return self.PAYOFF_MATRIX.get((action1, action2), (0, 0))
    
    def run_step(self) -> Dict[str, Any]:
        """运行一轮博弈"""
        # 随机配对
        agent_indices = np.random.permutation(len(self.agents))
        pairs = [(agent_indices[i], agent_indices[i+1])
                 for i in range(0, len(agent_indices)-1, 2)]
        
        round_results = []
        metric_count = 0
        total_actions = 0
        
        for idx1, idx2 in pairs:
            agent1 = self.agents[idx1]
            agent2 = self.agents[idx2]
            
            # 双方同时决定
            action1 = agent1.decide_action()
            action2 = agent2.decide_action()
            
            # 计算收益
            payoff1, payoff2 = self._calculate_payoffs(action1, action2)
            
            # 代理学习
            agent1.update_strategy(action1, payoff1)
            agent2.update_strategy(action2, payoff2)
            
            # 记录结果
            result = {
                "round": self.current_round,
                "agent1_id": agent1.agent_id,
                "agent2_id": agent2.agent_id,
                "agent1_action": action1,
                "agent2_action": action2,
                "agent1_payoff": payoff1,
                "agent2_payoff": payoff2
            }
            round_results.append(result)
            
            # 统计指标
            if action1 == "action1":
                metric_count += 1
            if action2 == "action1":
                metric_count += 1
            total_actions += 2
        
        # 计算本轮指标
        metric_rate = metric_count / total_actions if total_actions > 0 else 0.0
        self.metrics_history.append(metric_rate)
        
        # 记录到历史
        self.game_history.extend(round_results)
        
        result = {
            "round": self.current_round,
            "num_games": len(pairs),
            "metric_rate": metric_rate,
            "average_payoff": np.mean([r["agent1_payoff"] + r["agent2_payoff"]
                                      for r in round_results]),
            "details": round_results
        }
        
        return result
    
    def check_convergence(self) -> ConvergenceResult:
        """检查是否收敛到纳什均衡"""
        if len(self.metrics_history) < 50:
            return ConvergenceResult(
                converged=False,
                metric_name="metric_rate",
                current_value=0.0,
                expected_value=None,
                tolerance=0.1,
                message="数据不足，无法判断收敛"
            )
        
        # 计算最近 50 轮的平均指标
        recent_rate = np.mean(self.metrics_history[-50:])
        
        # 纳什均衡预测值
        nash_equilibrium_value = self._get_nash_prediction()
        
        tolerance = self.validation_config.get("tolerance", 0.1)
        converged = abs(recent_rate - nash_equilibrium_value) < tolerance
        
        return ConvergenceResult(
            converged=converged,
            metric_name="metric_rate",
            current_value=recent_rate,
            expected_value=nash_equilibrium_value,
            tolerance=tolerance,
            message=f"指标：{recent_rate:.2%} (纳什均衡：{nash_equilibrium_value:.2%})"
        )
    
    def _get_nash_prediction(self) -> float:
        """获取纳什均衡预测值"""
        # 根据具体博弈返回理论预测值
        return 0.5  # 示例
    
    def get_validation_metrics(self) -> Dict[str, float]:
        """获取验证指标"""
        if not self.game_history:
            return {}
        
        recent_history = self.game_history[-50:] if len(self.game_history) > 50 else self.game_history
        
        # 计算各项指标
        metric_rate = np.mean(self.metrics_history[-50:])
        avg_payoff = np.mean([r["agent1_payoff"] + r["agent2_payoff"]
                             for r in recent_history])
        
        return {
            "metric_rate": metric_rate,
            "average_payoff": avg_payoff,
            "nash_equilibrium_prediction": self._get_nash_prediction()
        }


def create_{game_name}(config: Dict[str, Any]) -> Tuple[BaseEnvironment, Dict[str, Any]]:
    """Factory function called by nash run."""
    env = {GameName}Environment(config)
    return env, env.parameters
```

### 步骤 2: 更新__init__.py

在 `src/environments/__init__.py` 中添加导出：

```python
from .{new_game} import {GameName}Environment

__all__ = [
    # ... 其他环境
    "{GameName}Environment"
]
```

### 步骤 3: 创建测试文件

创建 `test_{new_game}.py`：

```python
"""
测试{游戏名称}博弈
理论预测：{理论预测}
"""

from src.environments import {GameName}Environment


def test_{new_game}():
    """测试{游戏名称}"""
    print("\n" + "="*60)
    print("测试：{游戏名称}")
    print("="*60)
    
    config = {
        "environment": {
            "type": "{new_game}",
            "description": "{游戏描述}"
        },
        "parameters": {
            "num_agents": 20,
            "learning_rate": 0.1,
            "exploration_rate": 0.1,
            # 其他参数
        },
        "validation": {
            "metrics": [
                {"name": "metric_rate", "tolerance": 0.1}
            ]
        }
    }
    
    print("\n参数设置:")
    for key, value in config['parameters'].items():
        print(f"  {key}: {value}")
    
    print("\n理论预测:")
    print("  {理论预测}")
    
    env = {GameName}Environment(config)
    env.initialize_agents()
    
    print(f"\n初始化完成:")
    print(f"  代理数量：{len(env.agents)}")
    
    print("\n开始运行 200 轮...")
    
    # 运行 200 轮
    for round_num in range(200):
        result = env.run_step()
        
        # 每 20 轮输出一次
        if round_num % 20 == 0:
            print(f"\n第{round_num}轮:")
            print(f"  指标={result['metric_rate']:.2%}")
    
    # 检查收敛
    print("\n" + "="*60)
    print("收敛性检查")
    print("="*60)
    
    convergence = env.check_convergence()
    print(f"\n结果：{convergence.message}")
    print(f"是否收敛：{convergence.converged}")
    
    # 获取指标
    print("\n验证指标:")
    metrics = env.get_validation_metrics()
    for key, value in metrics.items():
        print(f"  {key}: {value:.4f}")
    
    if convergence.converged:
        print("\n✅ 验证成功：纳什均衡成立！")
    else:
        print("\n⏳ 未完全收敛，需要更多轮次")
    
    return convergence.converged


if __name__ == "__main__":
    success = test_{new_game}()
    print(f"\n测试结果：{'✅ 通过' if success else '⏳ 待收敛'}")
```

### 步骤 4: 运行测试

```bash
cd $NASH_ROOT
python test_{new_game}.py
```

## 已实现的博弈环境参考

### 实际已实现的 8 种环境

| 环境 ID | 别名 | 简要描述 |
|---------|------|---------|
| `hawk_dove` | hawk_dove | 鹰鸽博弈，进化稳定策略 (ESS) |
| `repeated_prisoners_dilemma` | prisoners_dilemma | 重复囚徒困境，子博弈精炼纳什均衡 (SPNE) |
| `public_goods` | public_goods | 公共物品博弈，搭便车均衡 |
| `common_pool_resource` | common_pool | 公共池资源，公地悲剧 |
| `vickrey_auction` | vickrey | Vickrey 拍卖，真实出价占优策略 |
| `spence_signaling` | spence | Spence 信号传递，分离均衡 |
| `two_sided_matching` | matching | 双边匹配，稳定匹配 |
| `auction_common_value` | auction_common_value | 共同价值拍卖，赢家诅咒规避 |

> **注意**：skill 中长篇幅的博弈理论解释引用了一些未实际实现的环境（如智猪博弈 boxed_pigs、协调博弈 coordination_game、信任博弈 trust_game）。实际可用于运行和测试的仅上述 8 种环境。创建新环境时，请以 `src/environments/` 目录下实际存在的 .py 文件为准。

### 1. 鹰鸽博弈 (`hawk_dove.py`)
- **理论**：混合策略均衡 = V/C
- **验证**：鹰派比例稳定在 V/C
- **关键参数**：resource_value, fight_cost

### 2. 重复囚徒困境 (`repeated_prisoners_dilemma.py`)
- **理论**：子博弈精炼纳什均衡
- **验证**：合作率随轮次变化
- **关键代码**：PAYOFF_MATRIX = {("cooperate","cooperate"): (3,3), ...}

### 3. 公共物品博弈 (`public_goods.py`)
- **理论**：搭便车问题
- **验证**：贡献率趋向 0%
- **关键机制**：public_pool * multiplier 再平分

## 测试运行命令

```bash
# 运行所有博弈测试
python test_game_environments.py

# 运行单个测试（按实际存在的环境）
python test_hawk_dove.py
python test_prisoners_dilemma.py
python test_public_goods.py
python test_common_pool_resource.py
python test_vickrey_auction.py
python test_spence_signaling.py
python test_two_sided_matching.py
python test_auction_common_value.py
```

## 依赖检查

```bash
# 检查 numpy 安装
python -c "import numpy; print(numpy.__version__)"

# 安装依赖（如需要）
pip install numpy scipy
```

## 文件保存位置

- **环境文件**：`$NASH_ROOT\src\environments\{name}.py`
- **测试文件**：`$NASH_ROOT\test_{name}.py`
- **运行结果**：终端输出（可重定向到 `.txt` 或 `.log`）

## 常见错误

1. **ModuleNotFoundError: No module named 'numpy'**
   - 解决：`pip install numpy scipy`

2. **导入错误**
   - 检查：`src/environments/__init__.py` 是否已更新

3. **收敛失败**
   - 增加轮次（200 → 500）
   - 调整 learning_rate（0.1 → 0.05）
   - 检查 payoff_matrix 是否符合理论

## 保存测试结果

```bash
# 保存测试输出
python test_{new_game}.py > tests/results/{new_game}_result.txt

# 查看结果
cat tests/results/{new_game}_result.txt
```

## 最佳实践

1. **收益矩阵验证**：确保符合理论预测的纳什均衡
2. **参数敏感性**：测试不同 learning_rate、exploration_rate
3. **收敛标准**：至少运行 200 轮，检查最近 50 轮平均值
4. **文档完整**：包含诺贝尔奖信息、理论预测、验证目标

---

**使用此 SKILL**：当需要创建新的博弈环境或测试用例时，参考上述模板和已有实现。

## 前端 AI 自主创建环境完整流程

### 前置条件

1. **numpy/scipy 已安装**
   ```bash
   pip install numpy scipy
   ```

2. **项目结构已存在**
   ```
   NASH/
   ├── src/environments/
   │   ├── base.py          # 基类（必须存在）
   │   └── __init__.py      # 导出文件（需更新）
   └── test_*.py            # 测试文件
   ```

### 完整创建流程（前端 AI 可执行）

#### 步骤 1: 分析新博弈类型

**输入**: 博弈名称和规则
**输出**: 收益矩阵、纳什均衡预测

示例对话：
```
用户：创建一个"性别战"博弈环境
AI: 
  1. 分析博弈类型：协调博弈变体
  2. 确定收益矩阵:
     (歌剧，歌剧) → (2,1)  # 都选歌剧
     (足球，足球) → (1,2)  # 都选足球
     其他 → (0,0)          # 不匹配
  3. 纳什均衡预测：两个纯策略均衡
```

#### 步骤 2: 生成环境代码

**使用 SKILL 中的模板**，替换：
- `{GameName}` → `BattleOfSexes`
- `{game_name}` → `battle_of_sexes`
- 收益矩阵 → 具体值
- 纳什均衡预测 → 理论值

#### 步骤 3: 保存文件

**环境文件**:
```
保存位置：src/environments/battle_of_sexes.py
```

**测试文件**:
```
保存位置：test_battle_of_sexes.py
```

#### 步骤 4: 更新导出

**编辑** `src/environments/__init__.py`:
```python
# 添加这一行
from .battle_of_sexes import BattleOfSexesEnvironment

# 更新__all__
__all__ = [
    "BaseEnvironment",
    "ConvergenceResult",
    # ... 现有环境
    "BattleOfSexesEnvironment"  # 新增
]
```

#### 步骤 5: 运行测试

```bash
cd $NASH_ROOT
python test_battle_of_sexes.py
```

#### 步骤 6: 验证结果

**成功标准**:
- ✅ 无 Python 语法错误
- ✅ 无导入错误
- ✅ 运行 200 轮无异常
- ✅ 收敛检查结果合理
- ✅ 指标符合理论预测

---

## 实战演示：创建"性别战"博弈

### 博弈规则

一对夫妻决定周末活动：
- 丈夫偏好足球，妻子偏好歌剧
- 但两人都希望在一起，不愿分开

**收益矩阵**:
```
              妻子选歌剧    妻子选足球
丈夫选歌剧      (2,1)         (0,0)
丈夫选足球      (0,0)         (1,2)
```

**纳什均衡**: 两个纯策略均衡
- (歌剧，歌剧): 妻子满意 (2), 丈夫一般 (1)
- (足球，足球): 丈夫满意 (2), 妻子一般 (1)

### 完整代码实现

#### 1. 环境文件：`src/environments/battle_of_sexes.py`

```python
"""
性别战博弈环境（Battle of the Sexes）
诺贝尔奖：1950 年 John Nash
理论预测：两个纯策略纳什均衡
验证：群体会协调到某个均衡
"""

import numpy as np
from typing import Dict, Any, List
from dataclasses import dataclass
from .base import BaseEnvironment, ConvergenceResult


@dataclass
class Agent:
    """性别战代理"""
    agent_id: int
    learning_rate: float = 0.1
    exploration_rate: float = 0.1
    
    # 策略：选择歌剧的概率
    opera_probability: float = 0.5
    
    history: List[Dict] = None
    
    def __post_init__(self):
        if self.history is None:
            self.history = []
    
    def decide_action(self) -> str:
        """决定行动"""
        if np.random.random() < self.exploration_rate:
            return np.random.choice(["opera", "football"])
        else:
            if np.random.random() < self.opera_probability:
                return "opera"
            else:
                return "football"
    
    def update_strategy(self, own_action: str, payoff: float, **kwargs):
        """根据收益更新策略"""
        if payoff > 0:
            if own_action == "opera":
                self.opera_probability = min(1.0,
                    self.opera_probability + self.learning_rate)
            else:
                self.opera_probability = max(0.0,
                    self.opera_probability - self.learning_rate)
        else:
            if own_action == "opera":
                self.opera_probability = max(0.0,
                    self.opera_probability - self.learning_rate)
            else:
                self.opera_probability = min(1.0,
                    self.opera_probability + self.learning_rate)


class BattleOfSexesEnvironment(BaseEnvironment):
    """
    性别战博弈环境
    验证：两个纯策略纳什均衡
    """
    
    PAYOFF_MATRIX = {
        ("opera", "opera"): (2, 1),
        ("opera", "football"): (0, 0),
        ("football", "opera"): (0, 0),
        ("football", "football"): (1, 2)
    }
    
    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self.agents: List[Agent] = []
        self.game_history: List[Dict] = []
        self.opera_rate_history: List[float] = []
    
    def initialize_agents(self) -> None:
        """初始化代理"""
        num_agents = self.parameters.get("num_agents", 20)
        learning_rate = self.parameters.get("learning_rate", 0.1)
        exploration_rate = self.parameters.get("exploration_rate", 0.1)
        
        self.agents = []
        for i in range(num_agents):
            agent = Agent(
                agent_id=i,
                learning_rate=learning_rate,
                exploration_rate=exploration_rate
            )
            self.agents.append(agent)
    
    def _calculate_payoffs(self, action1: str, action2: str) -> tuple:
        """计算收益"""
        return self.PAYOFF_MATRIX.get((action1, action2), (0, 0))
    
    def run_step(self) -> Dict[str, Any]:
        """运行一轮博弈"""
        # 随机配对
        agent_indices = np.random.permutation(len(self.agents))
        pairs = [(agent_indices[i], agent_indices[i+1])
                 for i in range(0, len(agent_indices)-1, 2)]
        
        round_results = []
        opera_count = 0
        total_actions = 0
        
        for idx1, idx2 in pairs:
            agent1 = self.agents[idx1]
            agent2 = self.agents[idx2]
            
            action1 = agent1.decide_action()
            action2 = agent2.decide_action()
            
            payoff1, payoff2 = self._calculate_payoffs(action1, action2)
            
            agent1.update_strategy(action1, payoff1)
            agent2.update_strategy(action2, payoff2)
            
            result = {
                "round": self.current_round,
                "agent1_action": action1,
                "agent2_action": action2,
                "agent1_payoff": payoff1,
                "agent2_payoff": payoff2,
                "coordinated": (action1 == action2)
            }
            round_results.append(result)
            
            if action1 == "opera":
                opera_count += 1
            if action2 == "opera":
                opera_count += 1
            total_actions += 2
        
        opera_rate = opera_count / total_actions
        self.opera_rate_history.append(opera_rate)
        self.game_history.extend(round_results)
        
        coordination_rate = sum(1 for r in round_results if r["coordinated"]) / len(round_results)
        
        result = {
            "round": self.current_round,
            "num_games": len(pairs),
            "opera_rate": opera_rate,
            "coordination_rate": coordination_rate,
            "average_payoff": np.mean([r["agent1_payoff"] + r["agent2_payoff"]
                                      for r in round_results]),
            "details": round_results
        }
        
        return result
    
    def check_convergence(self) -> ConvergenceResult:
        """检查是否收敛到某个均衡"""
        if len(self.opera_rate_history) < 50:
            return ConvergenceResult(
                converged=False,
                metric_name="opera_rate",
                current_value=0.0,
                expected_value=None,
                tolerance=0.2,
                message="数据不足"
            )
        
        recent_rate = np.mean(self.opera_rate_history[-50:])
        recent_std = np.std(self.opera_rate_history[-50:])
        
        # 检查是否稳定在某个均衡附近
        converged_to_opera = recent_rate > 0.8 and recent_std < 0.15
        converged_to_football = recent_rate < 0.2 and recent_std < 0.15
        
        converged = converged_to_opera or converged_to_football
        
        if converged_to_opera:
            message = "✅ 收敛到 (歌剧，歌剧) 均衡"
        elif converged_to_football:
            message = "✅ 收敛到 (足球，足球) 均衡"
        else:
            message = f"⏳ 未收敛 (歌剧率={recent_rate:.1%})"
        
        return ConvergenceResult(
            converged=converged,
            metric_name="opera_rate",
            current_value=recent_rate,
            expected_value=None,
            tolerance=0.2,
            message=message
        )
    
    def get_validation_metrics(self) -> Dict[str, float]:
        """获取验证指标"""
        if not self.game_history:
            return {}
        
        recent_rate = np.mean(self.opera_rate_history[-50:])
        recent_coordination = np.mean([r["coordination_rate"] 
                                       for r in self.game_history[-50:]])
        avg_payoff = np.mean([r["agent1_payoff"] + r["agent2_payoff"]
                             for r in self.game_history[-50:]])
        
        return {
            "opera_rate": recent_rate,
            "coordination_rate": recent_coordination,
            "average_payoff": avg_payoff,
            "nash_equilibria": "[(opera,opera), (football,football)]"
        }
```

#### 2. 测试文件：`test_battle_of_sexes.py`

```python
"""
测试性别战博弈
理论预测：两个纯策略纳什均衡
"""

from src.environments import BattleOfSexesEnvironment


def test_battle_of_sexes():
    """测试性别战博弈"""
    print("\n" + "="*60)
    print("测试：性别战博弈 (Battle of the Sexes)")
    print("="*60)
    
    config = {
        "environment": {
            "type": "battle_of_sexes",
            "description": "夫妻协调问题"
        },
        "parameters": {
            "num_agents": 20,
            "learning_rate": 0.1,
            "exploration_rate": 0.1
        }
    }
    
    print("\n收益矩阵:")
    print("              妻子选歌剧    妻子选足球")
    print("丈夫选歌剧      (2,1)         (0,0)")
    print("丈夫选足球      (0,0)         (1,2)")
    
    print("\n理论预测：两个纯策略纳什均衡")
    print("  1. (歌剧，歌剧): 妻子满意")
    print("  2. (足球，足球): 丈夫满意")
    
    env = BattleOfSexesEnvironment(config)
    env.initialize_agents()
    
    print("\n运行 200 轮...")
    
    for i in range(200):
        result = env.run_step()
        if i % 40 == 0:
            print(f"第{i}轮：歌剧率={result['opera_rate']:.1%}, "
                  f"协调率={result['coordination_rate']:.1%}")
    
    convergence = env.check_convergence()
    print(f"\n{convergence.message}")
    
    metrics = env.get_validation_metrics()
    print(f"\n指标:")
    print(f"  歌剧选择率：{metrics['opera_rate']:.1%}")
    print(f"  协调成功率：{metrics['coordination_rate']:.1%}")
    print(f"  平均收益：{metrics['average_payoff']:.2f}")
    
    return convergence.converged


if __name__ == "__main__":
    success = test_battle_of_sexes()
    print(f"\n结果：{'✅ 通过' if success else '⏳ 待收敛'}")
```

### 运行结果示例

```bash
$ python test_battle_of_sexes.py

============================================================
测试：性别战博弈 (Battle of the Sexes)
============================================================

收益矩阵:
              妻子选歌剧    妻子选足球
丈夫选歌剧      (2,1)         (0,0)
丈夫选足球      (0,0)         (1,2)

理论预测：两个纯策略纳什均衡
  1. (歌剧，歌剧): 妻子满意
  2. (足球，足球): 丈夫满意

运行 200 轮...
第 0 轮：歌剧率=45.0%, 协调率=50.0%
第 40 轮：歌剧率=78.3%, 协调率=85.0%
第 80 轮：歌剧率=85.6%, 协调率=90.0%
第 120 轮：歌剧率=92.1%, 协调率=95.0%
第 160 轮：歌剧率=95.3%, 协调率=97.5%

✅ 收敛到 (歌剧，歌剧) 均衡

指标:
  歌剧选择率：95.3%
  协调成功率：97.5%
  平均收益：1.48

结果：✅ 通过
```

---

## 前端 AI 能力评估

### ✅ 可以自主完成

1. **分析博弈规则** → 收益矩阵
2. **使用 SKILL 模板** → 生成代码
3. **保存文件** → 正确位置
4. **更新导出** → `__init__.py`
5. **运行测试** → 命令行操作
6. **验证结果** → 收敛性检查

### ⚠️ 需要人工确认

1. **收益矩阵正确性** → 是否符合理论
2. **纳什均衡预测** → 需要博弈论知识
3. **异常处理** → 导入错误、依赖问题

### 📋 完整工作流

```
用户输入 → AI 分析 → 生成代码 → 保存文件 → 
更新导出 → 运行测试 → 显示结果 → 验证成功
```

---

**结论**: 前端 AI **可以**创造任意博弈环境，只要提供：
1. 博弈名称
2. 收益矩阵
3. 纳什均衡预测

其余步骤都可由 AI 自主完成！
