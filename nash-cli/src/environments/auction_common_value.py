"""
Auction with Common Values - 共同价值拍卖
2020 年诺贝尔经济学奖 - Milgrom & Wilson
验证赢家诅咒现象
"""

import numpy as np
from typing import Dict, Any, List
from dataclasses import dataclass
from src.environments.base import BaseEnvironment, ConvergenceResult


@dataclass
class Bidder:
    bidder_id: int
    true_value_estimate: float = 0.0
    bid: float = 0.0
    discount_factor: float = 0.0
    learning_rate: float = 0.03
    auction_count: int = 0

    def estimate_value(self, true_value: float, noise_std: float):
        """估计共同价值（带噪声的信号）"""
        signal = true_value + np.random.normal(0, noise_std)
        self.true_value_estimate = signal

    def place_bid(self, num_bidders: int):
        """出价 — 使用学习的折扣因子规避赢家诅咒"""
        self.bid = max(0, self.true_value_estimate * (1 - self.discount_factor))

    def learn_from_round(self, won: bool, payoff: float, true_value: float, second_price: float):
        """从拍卖结果中学习，调整折扣因子"""
        self.auction_count += 1
        if won:
            if payoff < 0:
                # 赢家诅咒！增加折扣
                loss_ratio = abs(payoff) / max(1.0, true_value)
                self.discount_factor = min(0.5, self.discount_factor + self.learning_rate * loss_ratio)
            else:
                # 盈利中标，略微降低折扣
                self.discount_factor = max(0.0, self.discount_factor - self.learning_rate * 0.05)
        else:
            # 未中标：如果中标者盈利，我们可能出价太保守
            if payoff > 0 and self.bid < second_price:
                self.discount_factor = max(0.0, self.discount_factor - self.learning_rate * 0.02)


class AuctionCommonValueEnvironment(BaseEnvironment):
    """
    共同价值拍卖环境
    
    机制:
    1. 物品有共同但未知的价值 V
    2. 每个竞标者收到带噪声的信号 s_i = V + ε_i
    3. 二级价格密封拍卖
    4. 赢家诅咒：中标者往往高估价值
    """
    
    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        
        def get_val(param, default):
            if isinstance(param, dict):
                return param.get("value", default)
            return param
        
        self.num_bidders = get_val(config["parameters"].get("num_bidders"), 5)
        self.true_value = get_val(config["parameters"].get("true_value"), 100.0)
        self.noise_std = get_val(config["parameters"].get("noise_std"), 15.0)
        
        self.bidders: List[Bidder] = []
        self.history: List[Dict[str, Any]] = []
    
    def initialize_agents(self) -> None:
        for i in range(self.num_bidders):
            discount = np.random.uniform(0.05, 0.25)
            bidder = Bidder(bidder_id=i, discount_factor=discount)
            self.bidders.append(bidder)
    
    def run_step(self) -> Dict[str, Any]:
        self.current_round += 1
        
        # 阶段 1: 接收信号
        for bidder in self.bidders:
            bidder.estimate_value(self.true_value, self.noise_std)
        
        # 阶段 2: 出价
        for bidder in self.bidders:
            bidder.place_bid(self.num_bidders)
        
        # 阶段 3: 确定赢家（最高价）
        bids = [b.bid for b in self.bidders]
        winner_idx = np.argmax(bids)
        winner = self.bidders[winner_idx]
        
        # 二级价格：第二高出价
        second_highest = np.sort(bids)[-2] if len(bids) > 1 else bids[0]
        
        # 计算赢家收益
        winner_payoff = self.true_value - second_highest
        
        # 检查赢家诅咒
        overbid = winner.true_value_estimate > self.true_value

        # 所有竞标者从本轮结果中学习
        for i, bidder in enumerate(self.bidders):
            actual_payoff = winner_payoff if i == winner_idx else 0
            bidder.learn_from_round(
                won=(i == winner_idx),
                payoff=actual_payoff,
                true_value=self.true_value,
                second_price=second_highest
            )

        round_data = {
            "round": self.current_round,
            "winner_id": winner.bidder_id,
            "winning_bid": winner.bid,
            "second_price": second_highest,
            "winner_payoff": winner_payoff,
            "winner_curse": overbid,
            "avg_estimate": np.mean([b.true_value_estimate for b in self.bidders]),
            "avg_discount": np.mean([b.discount_factor for b in self.bidders])
        }
        return round_data
    
    def check_convergence(self) -> ConvergenceResult:
        """检查竞标者是否学会规避赢家诅咒（折扣因子稳定）"""
        if len(self.history) < 20:
            return ConvergenceResult(False, "winner_curse_rate", 0, 0.5, 0.1, "数据不足")

        recent = self.history[-20:]
        early = self.history[:20] if len(self.history) >= 40 else self.history[:max(1, len(self.history)//3)]

        # 赢家诅咒随学习递减
        early_curse = sum(1 for h in early if h["winner_curse"]) / len(early)
        recent_curse = sum(1 for h in recent if h["winner_curse"]) / len(recent)

        # 折扣因子稳定性
        recent_discounts = [h["avg_discount"] for h in recent]
        discount_std = np.std(recent_discounts) if len(recent_discounts) > 1 else 1.0

        # 收敛条件：折扣因子稳定 且 诅咒率下降（学习有效）
        discount_stable = discount_std < 0.02
        curse_declining = recent_curse < early_curse or recent_curse < 0.3
        converged = discount_stable and (curse_declining or len(self.history) >= 50)

        curse_rate = recent_curse

        message = (
            f"{'✅' if converged else '⏳'} 诅咒率: {curse_rate:.1%} (早期: {early_curse:.1%}) | "
            f"折扣因子: {np.mean(recent_discounts):.2%}±{discount_std:.2%}"
        )

        return ConvergenceResult(converged, "winner_curse_rate", curse_rate, 0.3, 0.15, message)
    
    def get_validation_metrics(self) -> Dict[str, float]:
        if not self.history:
            return {"winner_curse_rate": 0.0, "revenue_efficiency": 0.0, "avg_discount": 0.0}

        recent = self.history[-20:]
        early = self.history[:20] if len(self.history) >= 40 else self.history[:max(1, len(self.history)//3)]

        recent_curse = np.mean([1.0 if h["winner_curse"] else 0.0 for h in recent])
        early_curse = np.mean([1.0 if h["winner_curse"] else 0.0 for h in early])

        avg_revenue = np.mean([h["second_price"] for h in recent])
        revenue_efficiency = avg_revenue / self.true_value

        avg_discount = np.mean([h["avg_discount"] for h in recent])

        return {
            "winner_curse_rate": recent_curse,
            "curse_reduction": early_curse - recent_curse,
            "revenue_efficiency": revenue_efficiency,
            "avg_discount": avg_discount
        }


def create_auction_common_value(num_bidders: int = 5, true_value: float = 100.0, noise_std: float = 15.0) -> tuple:
    standard_config = {
        "environment": {
            "type": "auction_common_value",
            "nobel_reference": {
                "year": 2020,
                "laureates": ["Paul Milgrom", "Robert Wilson"],
                "contribution": "拍卖理论改进和新拍卖形式发明"
            }
        },
        "parameters": {
            "num_bidders": {"value": num_bidders},
            "true_value": {"value": true_value},
            "noise_std": {"value": noise_std}
        },
        "validation": {
            "equilibrium_type": "winner_curse",
            "metrics": [
                {"name": "winner_curse_rate", "expected_value": 0.6, "tolerance": 0.15}
            ]
        }
    }
    return AuctionCommonValueEnvironment(standard_config), standard_config
