"""
公共资源博弈环境 (Common Pool Resource Game)
2009 年诺贝尔经济学奖 - Elinor Ostrom
验证：个人理性导致集体非理性（资源枯竭），但通过制度设计可以实现可持续管理
"""

import numpy as np
from typing import Dict, Any, List
from dataclasses import dataclass
from src.environments.base import BaseEnvironment, ConvergenceResult


@dataclass
class Agent:
    """资源抽取者代理"""
    agent_id: int
    extraction_strategy: float  # 抽取策略 (0-1)，0=不抽取，1=最大抽取
    learning_rate: float = 0.05
    cooperation_tendency: float = 0.5  # 合作倾向
    
    def choose_extraction(self, resource_level: float, num_agents: int = 100) -> float:
        """选择抽取量 —— 修复：每人最多抽取公平份额的1.5倍，而非20%总资源"""
        fair_share = resource_level / max(num_agents, 1)
        max_extraction = fair_share * 1.5  # 最多公平份额的1.5倍
        base_extraction = self.extraction_strategy * max_extraction
        
        # 加入一些随机性
        noise = np.random.normal(0, max_extraction * 0.1)
        actual_extraction = max(0, min(max_extraction, base_extraction + noise))
        
        return actual_extraction
    
    def update_strategy(self, payoff: float, avg_payoff: float):
        """根据收益更新策略 —— 修复：移除正向反馈加速过度抽取"""
        if payoff < 0.5:
            self.extraction_strategy = max(0.05, self.extraction_strategy - self.learning_rate)
        elif payoff > avg_payoff * 1.5:  # 阈值从1.2提高到1.5，减少正向反馈
            self.extraction_strategy = min(1.0, self.extraction_strategy + self.learning_rate * 0.2)


class CommonPoolResourceEnvironment(BaseEnvironment):
    """
    公共资源博弈环境
    
    核心动态:
    1. 公共资源按固定速率再生
    2. 每个代理决定抽取多少资源
    3. 个人理性：最大化个人抽取
    4. 集体理性：可持续抽取（不超过再生速率）
    5. 悲剧：如果总抽取 > 再生，资源枯竭
    """
    
    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        
        # 辅助方法：从 dict 中提取值
        def get_val(param, default):
            if isinstance(param, dict):
                return param.get("value", default)
            return param if param is not None else default
        
        # 资源参数
        self.initial_resource = get_val(config["parameters"].get("initial_resource"), 1000.0)
        self.regeneration_rate = get_val(config["parameters"].get("regeneration_rate"), 0.05)
        self.max_resource = get_val(config["parameters"].get("max_resource"), 1000.0)
        self.current_resource = self.initial_resource
        
        # 代理参数
        self.num_agents = get_val(config["parameters"].get("num_agents"), 20)
        
        # 初始化代理
        self.agents: List[Agent] = []
        self.history: List[Dict[str, Any]] = []
        self._round_history: List[Dict[str, Any]] = []
    
    def initialize_agents(self) -> None:
        """初始化代理"""
        for i in range(self.num_agents):
            agent = Agent(
                agent_id=i,
                extraction_strategy=np.random.uniform(0.3, 0.7),  # 初始随机策略
                learning_rate=self.parameters.get("learning_rate", 0.05)
            )
            self.agents.append(agent)
    
    def regenerate_resource(self) -> float:
        """资源再生（逻辑斯蒂增长模型）"""
        # 再生量 = r * R * (1 - R/K)
        regeneration = (
            self.regeneration_rate * 
            self.current_resource * 
            (1 - self.current_resource / self.max_resource)
        )
        return max(0, regeneration)
    
    def run_step(self) -> Dict[str, Any]:
        """运行一步模拟"""
        self.current_round += 1
        
        # 步骤 1: 代理选择抽取量
        extractions = []
        for agent in self.agents:
            extraction = agent.choose_extraction(self.current_resource, self.num_agents)
            extractions.append(extraction)
        
        total_extraction = sum(extractions)
        
        # 步骤 2: 资源再生
        regeneration = self.regenerate_resource()
        
        # 步骤 3: 更新资源水平
        old_resource = self.current_resource
        self.current_resource = min(
            self.max_resource,
            max(0, old_resource + regeneration - total_extraction)
        )
        
        # 步骤 4: 计算收益
        # 收益 = 抽取量 * (资源质量因子)
        resource_quality = self.current_resource / self.max_resource
        payoffs = [e * resource_quality for e in extractions]
        avg_payoff = np.mean(payoffs) if payoffs else 0
        
        # 步骤 5: 代理学习
        for i, agent in enumerate(self.agents):
            agent.update_strategy(payoffs[i], avg_payoff)
        
        # 记录历史
        round_data = {
            "round": self.current_round,
            "resource_before": old_resource,
            "regeneration": regeneration,
            "total_extraction": total_extraction,
            "resource_after": self.current_resource,
            "extractions": extractions,
            "payoffs": payoffs,
            "avg_payoff": avg_payoff,
            "sustainability_index": self._calculate_sustainability(total_extraction, regeneration)
        }
        self._round_history.append(round_data)
        
        return {
            "round": self.current_round,
            "resource_level": self.current_resource,
            "total_extraction": total_extraction,
            "sustainability": round_data["sustainability_index"]
        }
    
    def _calculate_sustainability(self, total_extraction: float, regeneration: float) -> float:
        """计算可持续性指数"""
        if regeneration == 0:
            return 0.0
        
        # 可持续性 = 1 - (过度抽取比例)
        over_extraction_ratio = max(0, total_extraction - regeneration) / max(1, regeneration)
        sustainability = 1.0 - min(1.0, over_extraction_ratio)
        
        return sustainability
    
    def check_convergence(self) -> ConvergenceResult:
        """检查系统是否达到稳态（资源枯竭或可持续均衡）

        Ostrom 理论：没有制度机制时，公地悲剧是预期结果。
        收敛 = 系统达到稳态（资源不再显著变化），无论是否可持续。
        """
        if len(self._round_history) < 50:
            return ConvergenceResult(
                converged=False,
                metric_name="sustainability_index",
                current_value=0.0,
                expected_value=0.0,
                tolerance=0.1,
                message="数据不足，需要至少 50 轮互动"
            )

        recent_history = self._round_history[-20:]
        recent_resources = [h["resource_after"] for h in recent_history]
        resource_std = np.std(recent_resources)
        avg_resource = np.mean(recent_resources)
        is_stable = resource_std < (self.max_resource * 0.05)

        avg_sustainability = np.mean([h["sustainability_index"] for h in recent_history])
        tragedy_indicator = sum(
            1 for h in recent_history
            if h["total_extraction"] > h["regeneration"]
        ) / len(recent_history)

        converged = is_stable

        if avg_resource < self.max_resource * 0.1:
            state_desc = "资源枯竭（公地悲剧）"
        elif avg_resource > self.max_resource * 0.5:
            state_desc = "资源维持"
        else:
            state_desc = "资源衰减中"

        message = (
            f"{'✅' if converged else '⏳'} {state_desc} | "
            f"资源: {avg_resource:.0f}/{self.max_resource:.0f} | "
            f"过度抽取频率: {tragedy_indicator:.1%}"
        )

        return ConvergenceResult(
            converged=converged,
            metric_name="sustainability_index",
            current_value=avg_sustainability,
            expected_value=0.0,
            tolerance=0.1,
            message=message
        )
    
    def get_validation_metrics(self) -> Dict[str, float]:
        """获取验证指标"""
        if not self._round_history:
            return {
                "resource_depletion_rate": 0.0,
                "sustainability_index": 0.5,
                "tragedy_indicator": 0.0,
                "collective_efficiency": 0.5
            }
        
        recent_history = self._round_history[-20:] if len(self._round_history) >= 20 else self._round_history
        
        # 资源枯竭率
        initial = self._round_history[0]["resource_after"]
        current = self._round_history[-1]["resource_after"]
        depletion_rate = (initial - current) / max(1, initial)
        
        # 可持续性指数
        avg_sustainability = np.mean([h["sustainability_index"] for h in recent_history])
        
        # 悲剧指标（过度抽取频率）
        over_extraction_count = sum(
            1 for h in recent_history
            if h["total_extraction"] > h["regeneration"]
        )
        tragedy_indicator = over_extraction_count / len(recent_history)
        
        # 集体效率（实际总收益/最优总收益）
        total_payoff = sum(np.sum(h["payoffs"]) for h in recent_history)
        optimal_payoff = len(recent_history) * self.num_agents * 3.0  # 理论最优
        collective_efficiency = total_payoff / max(1, optimal_payoff)
        
        return {
            "resource_depletion_rate": depletion_rate,
            "sustainability_index": avg_sustainability,
            "tragedy_indicator": tragedy_indicator,
            "collective_efficiency": collective_efficiency
        }


# 便捷创建函数
def create_common_pool_resource(
    num_agents: int = 20,
    initial_resource: float = 1000.0,
    regeneration_rate: float = 0.05,
    learning_rate: float = 0.05,
    num_rounds: int = 300
) -> tuple:
    """
    创建公共资源博弈环境
    
    Args:
        num_agents: 代理数量
        initial_resource: 初始资源量
        regeneration_rate: 再生速率
        learning_rate: 学习率
        num_rounds: 模拟轮数
    
    Returns:
        (environment, standard_config)
    """
    standard_config = {
        "environment": {
            "type": "common_pool_resource",
            "nobel_reference": {
                "year": 2009,
                "laureates": ["Elinor Ostrom"],
                "contribution": "对经济治理的分析，特别是公共池资源的研究"
            }
        },
        "parameters": {
            "num_agents": {"value": num_agents, "description": "资源使用者数量"},
            "initial_resource": {"value": initial_resource, "description": "初始资源总量"},
            "regeneration_rate": {"value": regeneration_rate, "description": "资源自然再生速率"},
            "max_resource": {"value": 1000.0, "description": "环境承载能力"},
            "learning_rate": {"value": learning_rate, "description": "策略调整学习率"},
            "num_rounds": {"value": num_rounds, "description": "模拟轮数"}
        },
        "validation": {
            "equilibrium_type": "tragedy_of_commons",
            "metrics": [
                {
                    "name": "sustainability_index",
                    "expected_value": 0.8,
                    "tolerance": 0.1,
                    "description": "资源可持续性指数"
                },
                {
                    "name": "tragedy_indicator",
                    "expected_value": 0.2,
                    "tolerance": 0.1,
                    "description": "公地悲剧发生频率"
                }
            ]
        }
    }
    
    env = CommonPoolResourceEnvironment(standard_config)
    return env, standard_config
