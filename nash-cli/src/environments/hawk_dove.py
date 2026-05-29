"""
Hawk-Dove Game - 鹰鸽博弈
演化博弈论经典模型，验证 ESS (Evolutionarily Stable Strategy)
"""

import numpy as np
from typing import Dict, Any, List
from dataclasses import dataclass
from src.environments.base import BaseEnvironment, ConvergenceResult


@dataclass
class Agent:
    """代理"""
    agent_id: int
    strategy: str = "dove"  # "hawk" 或 "dove"
    payoff: float = 0.0
    
    def choose_strategy(self) -> str:
        """选择策略（简单版本：保持不变）"""
        return self.strategy
    
    def update_strategy(self, opponent_strategy: str, opponent_payoff: float):
        """根据对手策略和收益更新自己的策略"""
        # 模仿成功者
        if opponent_payoff > self.payoff:
            # 以一定概率模仿对手
            if np.random.random() < 0.3:  # 30% 模仿率
                self.strategy = opponent_strategy


class HawkDoveEnvironment(BaseEnvironment):
    """
    鹰鸽博弈环境
    
    收益矩阵 (V=资源价值，C=冲突成本):
                鹰         鸽
    鹰      (V-C)/2     V
    鸽      0           V/2
    
    ESS 分析:
    - 如果 V > C: 鹰是 ESS
    - 如果 V < C: 混合策略 ESS，鹰的比例 = V/C
    """
    
    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        
        def get_val(param, default):
            if isinstance(param, dict):
                return param.get("value", default)
            return param if param is not None else default
        
        # 参数
        self.V = get_val(config["parameters"].get("resource_value"), 4.0)  # 资源价值
        self.C = get_val(config["parameters"].get("conflict_cost"), 6.0)   # 冲突成本
        self.num_agents = get_val(config["parameters"].get("num_agents"), 100)
        
        # 理论预测的 ESS 比例
        if self.V > self.C:
            self.ess_hawk_ratio = 1.0  # 纯鹰均衡
        else:
            self.ess_hawk_ratio = self.V / self.C  # 混合均衡
        
        # 状态
        self.agents: List[Agent] = []
        self.history: List[Dict[str, Any]] = []
    
    def initialize_agents(self) -> None:
        """初始化代理（均匀随机策略，让演化自然发生）"""
        for i in range(self.num_agents):
            strategy = "hawk" if np.random.random() < 0.5 else "dove"
            agent = Agent(agent_id=i, strategy=strategy)
            self.agents.append(agent)
    
    def get_payoff(self, strategy1: str, strategy2: str) -> tuple:
        """计算收益"""
        if strategy1 == "hawk" and strategy2 == "hawk":
            return ((self.V - self.C) / 2, (self.V - self.C) / 2)
        elif strategy1 == "hawk" and strategy2 == "dove":
            return (self.V, 0)
        elif strategy1 == "dove" and strategy2 == "hawk":
            return (0, self.V)
        else:  # both dove
            return (self.V / 2, self.V / 2)
    
    def run_step(self) -> Dict[str, Any]:
        """运行一步模拟"""
        self.current_round += 1
        
        total_payoff_hawk = 0
        total_payoff_dove = 0
        count_hawk = 0
        count_dove = 0
        
        # 随机配对互动
        indices = np.random.permutation(len(self.agents))
        
        for i in range(0, len(indices) - 1, 2):
            agent1 = self.agents[indices[i]]
            agent2 = self.agents[indices[i + 1]]
            
            # 计算收益
            payoff1, payoff2 = self.get_payoff(agent1.strategy, agent2.strategy)
            agent1.payoff = payoff1
            agent2.payoff = payoff2
            
            # 统计
            if agent1.strategy == "hawk":
                total_payoff_hawk += payoff1
                count_hawk += 1
            else:
                total_payoff_dove += payoff1
                count_dove += 1
            
            if agent2.strategy == "hawk":
                total_payoff_hawk += payoff2
                count_hawk += 1
            else:
                total_payoff_dove += payoff2
                count_dove += 1
            
        # 策略更新：平滑Replicator Dynamics（种群级别进化选择）
        # 替代逐对模仿机制，解决鸽→鹰单向不可逆问题
        avg_h = total_payoff_hawk / max(1, count_hawk)
        avg_d = total_payoff_dove / max(1, count_dove)
        payoff_range = max(abs(avg_h), abs(avg_d), 1.0)
        lr = 0.05  # 学习率：只有5%的agent可能切换，防止震荡
        
        for agent in self.agents:
            if agent.strategy == "dove" and avg_h > avg_d:
                prob = lr * min(1.0, (avg_h - avg_d) / payoff_range)
                if np.random.random() < prob:
                    agent.strategy = "hawk"
            elif agent.strategy == "hawk" and avg_d > avg_h:
                prob = lr * min(1.0, (avg_d - avg_h) / payoff_range)
                if np.random.random() < prob:
                    agent.strategy = "dove"
        
        # 计算当前鹰的比例
        hawk_count = sum(1 for a in self.agents if a.strategy == "hawk")
        hawk_ratio = hawk_count / len(self.agents)
        
        # 记录历史
        round_data = {
            "round": self.current_round,
            "hawk_ratio": hawk_ratio,
            "avg_payoff_hawk": total_payoff_hawk / max(1, count_hawk),
            "avg_payoff_dove": total_payoff_dove / max(1, count_dove),
            "ess_deviation": abs(hawk_ratio - self.ess_hawk_ratio)
        }
        return round_data
    
    def check_convergence(self) -> ConvergenceResult:
        """检查是否收敛到 ESS"""
        if len(self.history) < 50:
            return ConvergenceResult(
                converged=False,
                metric_name="hawk_ratio",
                current_value=0.0,
                expected_value=self.ess_hawk_ratio,
                tolerance=0.1,
                message="数据不足，需要至少 50 轮"
            )
        
        # 计算最近 30 轮的平均鹰比例
        recent = self.history[-30:]
        avg_hawk_ratio = np.mean([h["hawk_ratio"] for h in recent])
        
        # 收敛标准：与 ESS 预测的偏差 < 10%
        deviation = abs(avg_hawk_ratio - self.ess_hawk_ratio)
        threshold = 0.1
        converged = deviation < threshold
        
        message = (
            f"{'✅' if converged else '⏳'} 鹰比例：{avg_hawk_ratio:.1%} "
            f"(ESS 预测：{self.ess_hawk_ratio:.1%}) | "
            f"偏差：{deviation:.1%} (阈值：{threshold:.0%})"
        )
        
        return ConvergenceResult(
            converged=converged,
            metric_name="hawk_ratio",
            current_value=avg_hawk_ratio,
            expected_value=self.ess_hawk_ratio,
            tolerance=threshold,
            message=message
        )
    
    def get_validation_metrics(self) -> Dict[str, float]:
        """获取验证指标"""
        if not self.history:
            return {
                "hawk_ratio": 0.0,
                "ess_deviation": 1.0,
                "strategy_stability": 0.0
            }
        
        recent = self.history[-30:] if len(self.history) >= 30 else self.history
        
        avg_hawk_ratio = np.mean([h["hawk_ratio"] for h in recent])
        ess_deviation = abs(avg_hawk_ratio - self.ess_hawk_ratio)
        
        # 策略稳定性：比例的方差越小越稳定
        variance = np.var([h["hawk_ratio"] for h in recent])
        strategy_stability = 1.0 - min(1.0, variance * 10)  # 归一化
        
        return {
            "hawk_ratio": avg_hawk_ratio,
            "ess_deviation": ess_deviation,
            "strategy_stability": strategy_stability
        }


# 便捷创建函数
def create_hawk_dove(
    num_agents: int = 100,
    resource_value: float = 4.0,
    conflict_cost: float = 6.0,
    num_rounds: int = 200
) -> tuple:
    """创建鹰鸽博弈环境"""
    standard_config = {
        "environment": {
            "type": "hawk_dove",
            "nobel_reference": {
                "year": 2005,
                "laureates": ["Robert Aumann", "Thomas Schelling"],
                "contribution": "通过博弈论分析增强了我们对冲突和合作的理解"
            }
        },
        "parameters": {
            "num_agents": {"value": num_agents},
            "resource_value": {"value": resource_value},
            "conflict_cost": {"value": conflict_cost},
            "num_rounds": {"value": num_rounds}
        },
        "validation": {
            "equilibrium_type": "ess",
            "metrics": [
                {"name": "hawk_ratio", "expected_value": resource_value / conflict_cost, "tolerance": 0.1},
                {"name": "strategy_stability", "expected_value": 0.8, "tolerance": 0.15}
            ]
        }
    }
    
    env = HawkDoveEnvironment(standard_config)
    return env, standard_config
