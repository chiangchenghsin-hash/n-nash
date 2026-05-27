"""
Two-Sided Matching - 双边匹配 (Gale-Shapley 算法)
2012 年诺贝尔经济学奖 - Roth & Shapley
"""

import numpy as np
from typing import Dict, Any, List
from src.environments.base import BaseEnvironment, ConvergenceResult


class TwoSidedMatchingEnvironment(BaseEnvironment):
    """
    双边匹配环境
    
    使用 Gale-Shapley 延迟接受算法实现稳定匹配
    """
    
    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        
        def get_val(param, default):
            if isinstance(param, dict):
                return param.get("value", default)
            return param
        
        self.num_men = get_val(config["parameters"].get("num_men"), 10)
        self.num_women = get_val(config["parameters"].get("num_women"), 10)
        
        # 随机生成偏好列表
        self.men_prefs = [np.random.permutation(self.num_women).tolist() 
                         for _ in range(self.num_men)]
        self.women_prefs = [np.random.permutation(self.num_men).tolist() 
                           for _ in range(self.num_women)]
        
        self.matches: List[tuple] = []
        self.history: List[Dict[str, Any]] = []
    
    def initialize_agents(self) -> None:
        pass  # 偏好已初始化
    
    def gale_shapley(self) -> List[tuple]:
        """执行 Gale-Shapley 算法（男性求婚版本）"""
        men_free = list(range(self.num_men))
        men_next_proposal = [0] * self.num_men
        women_partner = [-1] * self.num_women
        
        while men_free:
            man = men_free.pop(0)
            woman = self.men_prefs[man][men_next_proposal[man]]
            men_next_proposal[man] += 1
            
            if women_partner[woman] == -1:
                women_partner[woman] = man
            else:
                current = women_partner[woman]
                # 女方比较
                if self.women_prefs[woman].index(man) < self.women_prefs[woman].index(current):
                    women_partner[woman] = man
                    men_free.append(current)
                else:
                    men_free.append(man)
        
        return [(w, women_partner[w]) for w in range(self.num_women) if women_partner[w] >= 0]
    
    def run_step(self) -> Dict[str, Any]:
        self.current_round += 1

        # 每轮重新生成随机偏好，验证Gale-Shapley对不同输入的稳定性
        self.men_prefs = [np.random.permutation(self.num_women).tolist()
                         for _ in range(self.num_men)]
        self.women_prefs = [np.random.permutation(self.num_men).tolist()
                           for _ in range(self.num_women)]

        matches = self.gale_shapley()
        self.matches = matches
        
        # 检查稳定性
        blocking_pairs = self._count_blocking_pairs(matches)
        
        round_data = {
            "round": self.current_round,
            "num_matches": len(matches),
            "blocking_pairs": blocking_pairs,
            "stability_index": 1.0 - blocking_pairs / (self.num_men * self.num_women)
        }
        self.history.append(round_data)
        
        return round_data
    
    def _count_blocking_pairs(self, matches: List[tuple]) -> int:
        """计算阻塞对数量"""
        blocked = 0
        wife_of = {w: m for w, m in matches}
        husband_of = {m: w for w, m in matches}
        
        for m in range(self.num_men):
            for w in range(self.num_women):
                if m not in husband_of or w not in wife_of:
                    continue
                if husband_of[m] != w and wife_of[w] != m:
                    # 检查是否互相偏好
                    m_prefers_w = self.men_prefs[m].index(w) < self.men_prefs[m].index(husband_of.get(m, -1))
                    w_prefers_m = self.women_prefs[w].index(m) < self.women_prefs[w].index(wife_of.get(w, -1))
                    
                    if m_prefers_w and w_prefers_m:
                        blocked += 1
        
        return blocked
    
    def check_convergence(self) -> ConvergenceResult:
        if len(self.history) < 10:
            return ConvergenceResult(False, "stability_index", 0, 0.9, 0.1, "数据不足")
        
        recent = self.history[-10:]
        avg_stability = np.mean([h["stability_index"] for h in recent])
        
        converged = avg_stability > 0.95
        message = f"{'✅' if converged else '⏳'} 稳定性指数：{avg_stability:.1%}"
        
        return ConvergenceResult(converged, "stability_index", avg_stability, 0.95, 0.05, message)
    
    def get_validation_metrics(self) -> Dict[str, float]:
        if not self.history:
            return {"stability_index": 0.0, "matching_efficiency": 0.0}
        
        recent = self.history[-10:]
        stability = np.mean([h["stability_index"] for h in recent])
        efficiency = len(self.matches) / min(self.num_men, self.num_women)
        
        return {"stability_index": stability, "matching_efficiency": efficiency}


def create_two_sided_matching(num_men: int = 10, num_women: int = 10) -> tuple:
    standard_config = {
        "environment": {
            "type": "two_sided_matching",
            "nobel_reference": {
                "year": 2012,
                "laureates": ["Alvin Roth", "Lloyd Shapley"],
                "contribution": "稳定分配理论和市场设计实践"
            }
        },
        "parameters": {
            "num_men": {"value": num_men},
            "num_women": {"value": num_women}
        },
        "validation": {
            "equilibrium_type": "stable_matching",
            "metrics": [
                {"name": "stability_index", "expected_value": 0.95, "tolerance": 0.05}
            ]
        }
    }
    return TwoSidedMatchingEnvironment(standard_config), standard_config
