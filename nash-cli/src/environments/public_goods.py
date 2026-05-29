"""
Public Goods Game - 公共物品博弈
验证搭便车问题和公共物品供给不足
"""

import numpy as np
from typing import Dict, Any, List
from dataclasses import dataclass
from src.environments.base import BaseEnvironment, ConvergenceResult


@dataclass
class Agent:
    agent_id: int
    contribution: float = 0.5  # 贡献比例 (0-1)
    
    def update_contribution(self, personal_payoff: float, free_ride_payoff: float, endowment: float):
        """根据个人收益 vs 搭便车收益调整贡献"""
        # 关键是：比较"我实际赚的"vs"我如果完全不贡献能赚的"
        if personal_payoff <= free_ride_payoff:  # 贡献不划算 → 减少
            self.contribution = max(0.05, self.contribution - 0.08)
        else:  # 贡献划算 → 增加
            self.contribution = min(1.0, self.contribution + 0.02)


class PublicGoodsEnvironment(BaseEnvironment):
    """
    公共物品博弈环境
    
    机制:
    1. 每个代理有初始禀赋 E
    2. 选择贡献 c_i 到公共池
    3. 公共池总量乘以因子 r (>1, <N)
    4. 平均分配给所有成员
    
    个人理性：不贡献 (搭便车)
    集体理性：全部贡献 (最大化总收益)
    """
    
    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        
        def get_val(param, default):
            if isinstance(param, dict):
                return param.get("value", default)
            return param if param is not None else default
        
        self.num_agents = get_val(config["parameters"].get("num_agents"), 20)
        self.endowment = get_val(config["parameters"].get("endowment"), 10.0)
        self.multiplier = get_val(config["parameters"].get("multiplier"), 1.6)
        
        self.agents: List[Agent] = []
        self.history: List[Dict[str, Any]] = []
    
    def initialize_agents(self) -> None:
        for i in range(self.num_agents):
            agent = Agent(agent_id=i, contribution=np.random.uniform(0.3, 0.7))
            self.agents.append(agent)
    
    def run_step(self) -> Dict[str, Any]:
        self.current_round += 1
        
        total_contribution = sum(a.contribution * self.endowment for a in self.agents)
        public_good = total_contribution * self.multiplier
        individual_return = public_good / self.num_agents
        
        # 计算个人收益
        payoffs = []
        for agent in self.agents:
            private_retention = self.endowment * (1 - agent.contribution)
            payoff = private_retention + individual_return
            payoffs.append(payoff)
            
            # 计算如果该agent贡献0能获得的收益（搭便车收益）
            others_contribution = total_contribution - agent.contribution * self.endowment
            free_ride_public = others_contribution * self.multiplier
            free_ride_return = free_ride_public / self.num_agents
            free_ride_payoff = self.endowment + free_ride_return  # 留10 + 搭便车分
            
            # 更新贡献策略（比较实际收益 vs 搭便车收益）
            agent.update_contribution(payoff, free_ride_payoff, self.endowment)
        
        avg_contribution = np.mean([a.contribution for a in self.agents])
        
        round_data = {
            "round": self.current_round,
            "avg_contribution": avg_contribution,
            "total_contribution": total_contribution,
            "avg_payoff": np.mean(payoffs)
        }
        return round_data
    
    def check_convergence(self) -> ConvergenceResult:
        if len(self.history) < 30:
            return ConvergenceResult(
                converged=False,
                metric_name="contribution_rate",
                current_value=0.0,
                expected_value=0.5,
                tolerance=0.1,
                message="数据不足"
            )
        
        recent = self.history[-20:]
        avg_contrib = np.mean([h["avg_contribution"] for h in recent])
        
        # 理论预测：趋向于 0（搭便车）
        threshold = 0.2
        free_riding = avg_contrib < threshold
        
        message = f"{'✅' if free_riding else '⏳'} 平均贡献：{avg_contrib:.1%} (搭便车：<20%)"
        
        return ConvergenceResult(
            converged=free_riding,
            metric_name="contribution_rate",
            current_value=avg_contrib,
            expected_value=0.0,
            tolerance=threshold,
            message=message
        )
    
    def get_validation_metrics(self) -> Dict[str, float]:
        if not self.history:
            return {"contribution_rate": 0.0, "free_riding_index": 0.0}
        
        recent = self.history[-20:]
        avg_contrib = np.mean([h["avg_contribution"] for h in recent])
        
        return {
            "contribution_rate": avg_contrib,
            "free_riding_index": 1.0 - avg_contrib
        }


def create_public_goods(num_agents: int = 20, endowment: float = 10.0, multiplier: float = 1.6) -> tuple:
    standard_config = {
        "environment": {
            "type": "public_goods",
            "nobel_reference": {
                "year": 2009,
                "laureates": ["Elinor Ostrom"],
                "contribution": "对公共物品与公共资源的治理研究"
            },
        },
        "parameters": {
            "num_agents": {"value": num_agents},
            "endowment": {"value": endowment},
            "multiplier": {"value": multiplier}
        },
        "validation": {
            "equilibrium_type": "free_riding",
            "metrics": [
                {"name": "contribution_rate", "expected_value": 0.2, "tolerance": 0.1}
            ]
        }
    }
    return PublicGoodsEnvironment(standard_config), standard_config
