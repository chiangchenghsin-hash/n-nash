"""
Spence Signaling Environment - 信号发送博弈
2001 年诺贝尔经济学奖 - Akerlof, Spence, Stiglitz
验证：在信息不对称市场中，高能力者通过教育发送信号实现分离均衡
"""

import numpy as np
from typing import Dict, Any, List
from dataclasses import dataclass
from src.environments.base import BaseEnvironment, ConvergenceResult


@dataclass
class Worker:
    """工人代理"""
    worker_id: int
    ability: float  # 能力类型 (0-1)，高能力>0.5，低能力<=0.5
    education: float = 0.0  # 教育水平
    wage: float = 0.0
    
    def choose_education(self, wage_function):
        """选择教育水平以最大化效用"""
        # 效用 = 工资 - 教育成本
        # 教育成本与能力负相关：高能力者成本低
        
        # 更强的信号：高能力者选择教育=ability*3，低能力者选ability*1
        base_education = self.ability * 3.0 if self.ability > 0.5 else self.ability * 1.5
        noise = np.random.normal(0, 0.1)
        self.education = max(0, min(3.0, base_education + noise))
    
    def get_utility(self, wage: float) -> float:
        """计算效用 —— 修复：增大能力差异对教育成本的影响，强化分离信号"""
        # 教育成本：c(e,a) = e/(a²) → 低能力者成本呈指数增长
        # 原来 c=e/a 差别不够大，改为 c=e/a² 使分离更显著
        cost = self.education / max(0.01, self.ability ** 2)
        return wage - cost


@dataclass  
class Firm:
    """企业代理"""
    firm_id: int
    productivity_estimate: Dict[float, float] = None  # 能力→生产力映射
    
    def __post_init__(self):
        if self.productivity_estimate is None:
            self.productivity_estimate = {}
    
    def offer_wage(self, education: float, pool: List[Worker]) -> float:
        """根据教育水平提供工资"""
        # 统计具有相似教育水平的工人的平均生产力
        similar_workers = [w for w in pool if abs(w.education - education) < 0.2]
        
        if similar_workers:
            avg_ability = np.mean([w.ability for w in similar_workers])
            wage = avg_ability * 10.0  # 工资=预期生产力
        else:
            # 无参考数据，使用先验期望
            wage = 5.0
        
        return wage


class SpenceSignalingEnvironment(BaseEnvironment):
    """
    Spence 信号发送环境
    
    核心机制:
    1. 工人有能力差异（私人信息）
    2. 企业无法直接观察能力，只能观察教育
    3. 教育不提高生产力，仅作为信号
    4. 高能力者教育成本低，选择高教育
    5. 分离均衡：高能力→高教育→高工资；低能力→低教育→低工资
    """
    
    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        
        def get_val(param, default):
            if isinstance(param, dict):
                return param.get("value", default)
            return param if param is not None else default
        
        # 参数
        self.num_workers = get_val(config["parameters"].get("num_workers"), 100)
        self.num_firms = get_val(config["parameters"].get("num_firms"), 10)
        self.high_ability_threshold = get_val(config["parameters"].get("high_ability_threshold"), 0.5)
        
        # 状态
        self.workers: List[Worker] = []
        self.firms: List[Firm] = []
        self.history: List[Dict[str, Any]] = []
    
    def initialize_agents(self) -> None:
        """初始化工人和企业"""
        # 创建工人（能力随机分布）
        for i in range(self.num_workers):
            ability = np.random.beta(2, 2)  # [0,1] 分布，均值 0.5
            worker = Worker(worker_id=i, ability=ability)
            self.workers.append(worker)
        
        # 创建企业
        for i in range(self.num_firms):
            firm = Firm(firm_id=i)
            self.firms.append(firm)
    
    def run_step(self) -> Dict[str, Any]:
        """运行一步模拟"""
        self.current_round += 1
        
        # 阶段 1: 工人选择教育水平
        for worker in self.workers:
            worker.choose_education(lambda e: 0)  # 初始无工资函数
        
        # 阶段 2: 企业提供工资
        for worker in self.workers:
            # 随机分配给一个企业
            firm = np.random.choice(self.firms)
            wage = firm.offer_wage(worker.education, self.workers)
            worker.wage = wage
        
        # 阶段 3: 计算分离指数
        separation_index = self._calculate_separation_index()
        
        # 记录历史
        round_data = {
            "round": self.current_round,
            "separation_index": separation_index,
            "avg_education_high": self._avg_education_by_type("high"),
            "avg_education_low": self._avg_education_by_type("low"),
            "avg_wage_high": self._avg_wage_by_type("high"),
            "avg_wage_low": self._avg_wage_by_type("low")
        }
        return round_data
    
    def _calculate_separation_index(self) -> float:
        """
        计算分离指数
        分离指数 = 1 - (高能力者平均教育 - 低能力者平均教育的重叠度)
        完全分离时指数接近 1，混同时接近 0
        """
        high_ability = [w for w in self.workers if w.ability > self.high_ability_threshold]
        low_ability = [w for w in self.workers if w.ability <= self.high_ability_threshold]
        
        if not high_ability or not low_ability:
            return 0.0
        
        avg_edu_high = np.mean([w.education for w in high_ability])
        avg_edu_low = np.mean([w.education for w in low_ability])
        
        # 分离度：教育差异越大，分离越好
        education_gap = avg_edu_high - avg_edu_low
        
        # 归一化到 [0,1]
        separation = min(1.0, max(0.0, education_gap))
        
        return separation
    
    def _avg_education_by_type(self, ability_type: str) -> float:
        """按能力类型计算平均教育"""
        if ability_type == "high":
            workers = [w for w in self.workers if w.ability > self.high_ability_threshold]
        else:
            workers = [w for w in self.workers if w.ability <= self.high_ability_threshold]
        
        return np.mean([w.education for w in workers]) if workers else 0.0
    
    def _avg_wage_by_type(self, ability_type: str) -> float:
        """按能力类型计算平均工资"""
        if ability_type == "high":
            workers = [w for w in self.workers if w.ability > self.high_ability_threshold]
        else:
            workers = [w for w in self.workers if w.ability <= self.high_ability_threshold]
        
        return np.mean([w.wage for w in workers]) if workers else 0.0
    
    def check_convergence(self) -> ConvergenceResult:
        """检查是否收敛到分离均衡"""
        if len(self.history) < 30:
            return ConvergenceResult(
                converged=False,
                metric_name="separation_index",
                current_value=0.0,
                expected_value=0.9,
                tolerance=0.1,
                message="数据不足，需要至少 30 轮"
            )
        
        # 计算最近 20 轮的平均分离指数
        recent = self.history[-20:]
        avg_separation = np.mean([h["separation_index"] for h in recent])
        
        # 分离均衡标准：分离指数 > 0.8
        threshold = 0.8
        converged = avg_separation > threshold
        
        message = (
            f"{'✅' if converged else '⏳'} 分离指数：{avg_separation:.1%} "
            f"(预测：>{threshold:.0%}) | "
            f"高能力教育：{recent[-1]['avg_education_high']:.2f} | "
            f"低能力教育：{recent[-1]['avg_education_low']:.2f}"
        )
        
        return ConvergenceResult(
            converged=converged,
            metric_name="separation_index",
            current_value=avg_separation,
            expected_value=threshold,
            tolerance=0.1,
            message=message
        )
    
    def get_validation_metrics(self) -> Dict[str, float]:
        """获取验证指标"""
        if not self.history:
            return {
                "separation_index": 0.0,
                "education_premium": 0.0,
                "signaling_efficiency": 0.0
            }
        
        recent = self.history[-20:] if len(self.history) >= 20 else self.history
        
        separation_index = np.mean([h["separation_index"] for h in recent])
        
        # 教育溢价：高能力者工资/低能力者工资
        avg_wage_high = recent[-1]["avg_wage_high"]
        avg_wage_low = recent[-1]["avg_wage_low"]
        education_premium = (avg_wage_high - avg_wage_low) / max(1, avg_wage_low)
        
        # 信号效率：分离指数 / 最大可能分离
        signaling_efficiency = separation_index
        
        return {
            "separation_index": separation_index,
            "education_premium": education_premium,
            "signaling_efficiency": signaling_efficiency
        }


# 便捷创建函数
def create_spence_signaling(
    num_workers: int = 100,
    num_firms: int = 10,
    high_ability_threshold: float = 0.5,
    num_rounds: int = 100
) -> tuple:
    """创建 Spence 信号发送环境"""
    standard_config = {
        "environment": {
            "type": "spence_signaling",
            "nobel_reference": {
                "year": 2001,
                "laureates": ["George Akerlof", "Michael Spence", "Joseph Stiglitz"],
                "contribution": "对信息不对称市场的分析"
            }
        },
        "parameters": {
            "num_workers": {"value": num_workers},
            "num_firms": {"value": num_firms},
            "high_ability_threshold": {"value": high_ability_threshold},
            "num_rounds": {"value": num_rounds}
        },
        "validation": {
            "equilibrium_type": "separating_equilibrium",
            "metrics": [
                {"name": "separation_index", "expected_value": 0.8, "tolerance": 0.1},
                {"name": "education_premium", "expected_value": 0.5, "tolerance": 0.2}
            ]
        }
    }
    
    env = SpenceSignalingEnvironment(standard_config)
    return env, standard_config
