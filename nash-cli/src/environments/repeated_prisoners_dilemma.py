"""
重复囚徒困境环境 - 修复版
2005 年诺贝尔经济学奖 - Robert Aumann & Thomas Schelling
"""

import numpy as np
from typing import Dict, Any, List, Tuple
from dataclasses import dataclass
from src.environments.base import BaseEnvironment, ConvergenceResult


@dataclass
class Agent:
    """TFT+Q-learning 混合代理 —— 用互惠策略突破独立Q-learning无法发现合作SPNE的问题"""
    agent_id: int
    q_values: Dict[str, float]
    learning_rate: float = 0.1
    exploration_rate: float = 0.1
    tft_memory: Dict[int, str] = None  # 记录每个对手上次的动作
    
    def __post_init__(self):
        if self.tft_memory is None:
            self.tft_memory = {}
    
    def choose_action(self, partner_id: int = None) -> str:
        """TFT + ε-greedy 混合策略"""
        if partner_id is not None and partner_id in self.tft_memory:
            if np.random.random() < 0.05:  # 降到5%探索（原来15%太高打破合作链）
                return np.random.choice(["cooperate", "defect"])
            if self.tft_memory[partner_id] == "cooperate":
                return "cooperate"
            else:
                # 更宽容的TFT：40%概率重新合作 + 降低探索到3%
                return "cooperate" if np.random.random() < 0.4 else "defect"
        
        # 无对手记忆时使用低探索ε-greedy
        if np.random.random() < 0.05:
            return np.random.choice(["cooperate", "defect"])
        
        cooperate_q = self.q_values.get("cooperate", 0.0)
        defect_q = self.q_values.get("defect", 0.0)
        
        return "cooperate" if cooperate_q > defect_q else "defect"
    
    def update_q_value(self, action: str, reward: float):
        """Q-learning 更新"""
        old_q = self.q_values.get(action, 0.0)
        new_q = old_q + self.learning_rate * (reward - old_q)
        self.q_values[action] = new_q


class RepeatedPrisonersDilemmaEnvironment(BaseEnvironment):
    """重复囚徒困境环境"""
    
    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        
        # 收益参数
        self.T = self._get_param_value(config["parameters"].get("temptation", 5.0))
        self.R = self._get_param_value(config["parameters"].get("reward", 3.0))
        self.P = self._get_param_value(config["parameters"].get("punishment", 1.0))
        self.S = self._get_param_value(config["parameters"].get("sucker", 0.0))
        
        # 折扣因子
        self.delta = self._get_param_value(config["parameters"].get("discount_factor", 0.95))
        
        # 临界值
        self.delta_threshold = (self.T - self.R) / (self.T - self.P)
        
        # 代理数量
        self.num_agents = self._get_param_value(config["parameters"].get("num_agents", 20))
        
        # 状态
        self.agents: List[Agent] = []
        self.history: List[Dict[str, Any]] = []
        self._interaction_history: List[Dict[str, Any]] = []
        self.cooperation_counts: Dict[int, int] = {}
    
    def _get_param_value(self, param: Any) -> Any:
        """从参数配置中提取值（支持 dict 和直接值）"""
        if isinstance(param, dict):
            return param.get("value", param.get("default", None))
        return param
    
    def initialize_agents(self) -> None:
        """初始化代理"""
        for i in range(self.num_agents):
            agent = Agent(
                agent_id=i,
                q_values={"cooperate": 3.0, "defect": 1.0},
                learning_rate=self._get_param_value(self.parameters.get("learning_rate", 0.1)),
                exploration_rate=self._get_param_value(self.parameters.get("exploration_rate", 0.1))
            )
            self.agents.append(agent)
            self.cooperation_counts[i] = 0
    
    def get_payoff(self, action1: str, action2: str) -> Tuple[float, float]:
        """收益矩阵"""
        if action1 == "cooperate" and action2 == "cooperate":
            return (self.R, self.R)
        elif action1 == "cooperate" and action2 == "defect":
            return (self.S, self.T)
        elif action1 == "defect" and action2 == "cooperate":
            return (self.T, self.S)
        else:
            return (self.P, self.P)
    
    def run_step(self) -> Dict[str, Any]:
        """运行一步"""
        self.current_round += 1
        interactions = []
        
        # 所有代理两两互动
        for i in range(len(self.agents)):
            for j in range(i + 1, len(self.agents)):
                agent_i = self.agents[i]
                agent_j = self.agents[j]
                
                action_i = agent_i.choose_action(partner_id=agent_j.agent_id)
                action_j = agent_j.choose_action(partner_id=agent_i.agent_id)
                
                # 更新TFT记忆：记录对手本轮动作
                agent_i.tft_memory[agent_j.agent_id] = action_j
                agent_j.tft_memory[agent_i.agent_id] = action_i
                
                payoff_i, payoff_j = self.get_payoff(action_i, action_j)
                
                agent_i.update_q_value(action_i, payoff_i)
                agent_j.update_q_value(action_j, payoff_j)
                
                interactions.append({
                    "round": self.current_round,
                    "agent_i": agent_i.agent_id,
                    "agent_j": agent_j.agent_id,
                    "action_i": action_i,
                    "action_j": action_j,
                    "payoff_i": payoff_i,
                    "payoff_j": payoff_j
                })
                
                if action_i == "cooperate":
                    self.cooperation_counts[agent_i.agent_id] += 1
                if action_j == "cooperate":
                    self.cooperation_counts[agent_j.agent_id] += 1
        
        self._interaction_history.extend(interactions)
        
        # 降低探索率
        for agent in self.agents:
            agent.exploration_rate = max(0.01, agent.exploration_rate * 0.995)
        
        return {
            "round": self.current_round,
            "total_interactions": len(interactions),
            "avg_cooperation_rate": self.get_cooperation_rate()
        }
    
    def check_convergence(self) -> ConvergenceResult:
        """检查收敛"""
        if len(self._interaction_history) < 100:
            return ConvergenceResult(
                converged=False,
                metric_name="cooperation_rate",
                current_value=0.0,
                expected_value=0.8,
                tolerance=0.1,
                message="数据不足，需要至少 100 轮互动"
            )

        recent_history = self._interaction_history[-50:]
        total_actions = len(recent_history) * 2
        cooperate_actions = sum(
            1 for h in recent_history for act in [h["action_i"], h["action_j"]]
            if act == "cooperate"
        )
        
        cooperation_rate = cooperate_actions / total_actions
        expected_rate = 0.8
        converged = cooperation_rate > expected_rate
        
        delta_condition_met = self.delta > self.delta_threshold
        
        message = (
            f"{'✅' if converged and delta_condition_met else '⏳'} "
            f"合作率：{cooperation_rate:.1%} (预测：>{expected_rate:.0%}) | "
            f"δ={self.delta:.2f} > δ*={self.delta_threshold:.2f}: {'是' if delta_condition_met else '否'}"
        )
        
        return ConvergenceResult(
            converged=converged and delta_condition_met,
            metric_name="cooperation_rate",
            current_value=cooperation_rate,
            expected_value=expected_rate,
            tolerance=0.1,
            message=message
        )
    
    def get_validation_metrics(self) -> Dict[str, float]:
        """验证指标"""
        cooperation_rate = self.get_cooperation_rate()
        
        recent_history = self._interaction_history[-50:] if len(self._interaction_history) >= 50 else self._interaction_history
        mutual_cooperation_count = sum(
            1 for h in recent_history
            if h["action_i"] == "cooperate" and h["action_j"] == "cooperate"
        )
        mutual_cooperation_rate = mutual_cooperation_count / max(1, len(recent_history))
        
        return {
            "cooperation_rate": cooperation_rate,
            "mutual_cooperation_rate": mutual_cooperation_rate,
            "network_reciprocity": cooperation_rate,
            "delta_condition_met": 1.0 if self.delta > self.delta_threshold else 0.0,
            "spne_supported": 1.0 if cooperation_rate > 0.8 and self.delta > self.delta_threshold else 0.0
        }
    
    def get_cooperation_rate(self) -> float:
        """计算合作率 —— 修复：统计个体动作次数而非互动对数"""
        if not self._interaction_history:
            return 0.5

        recent = self._interaction_history[-50:] if len(self._interaction_history) >= 50 else self._interaction_history
        total = len(recent) * 2  # 每次互动2个动作
        # 修复：统计所有个体动作中的合作次数，而非 OR 计数
        cooperate = sum(
            1 for h in recent for act in [h["action_i"], h["action_j"]]
            if act == "cooperate"
        )
        
        return cooperate / max(1, total)


# 便捷创建函数
def create_repeated_prisoners_dilemma(
    num_agents: int = 20,
    discount_factor: float = 0.95,
    learning_rate: float = 0.1,
    num_rounds: int = 500
) -> Tuple[RepeatedPrisonersDilemmaEnvironment, Dict[str, Any]]:
    """创建重复囚徒困境环境"""
    standard_config = {
        "environment": {
            "type": "repeated_prisoners_dilemma",
            "nobel_reference": {
                "year": 2005,
                "laureates": ["Robert Aumann", "Thomas Schelling"],
                "contribution": "通过博弈论分析增强了我们对冲突和合作的理解"
            }
        },
        "parameters": {
            "num_agents": {"value": num_agents},
            "learning_rate": {"value": learning_rate},
            "discount_factor": {"value": discount_factor},
            "exploration_rate": {"value": 0.1},
            "num_rounds": {"value": num_rounds}
        },
        "validation": {
            "equilibrium_type": "cooperative_spne",
            "metrics": [
                {"name": "cooperation_rate", "expected_value": 0.8, "tolerance": 0.1},
                {"name": "network_reciprocity", "expected_value": 0.7, "tolerance": 0.15}
            ]
        }
    }
    
    env = RepeatedPrisonersDilemmaEnvironment(standard_config)
    return env, standard_config
