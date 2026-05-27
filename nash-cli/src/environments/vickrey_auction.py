"""
维克瑞拍卖环境（第二价格密封拍卖）
诺贝尔奖：1996 年 William Vickrey
理论预测：说真话是弱占优策略均衡
"""

import numpy as np
from typing import Dict, Any, List, Optional
from dataclasses import dataclass
from .base import BaseEnvironment, ConvergenceResult


@dataclass
class BidderAgent:
    """竞拍代理"""
    agent_id: int
    true_value: float
    learning_rate: float = 0.1
    exploration_rate: float = 0.1
    
    # 策略：出价相对于真实价值的比例
    bidding_strategies: np.ndarray = None
    strategy_preferences: np.ndarray = None
    
    # 历史记录
    auction_history: List[Dict] = None
    
    def __post_init__(self):
        if self.bidding_strategies is None:
            # 策略空间：0.5x 到 1.5x 真实价值
            self.bidding_strategies = np.linspace(0.5, 1.5, 21)
        if self.strategy_preferences is None:
            # 初始均匀分布
            self.strategy_preferences = np.ones(len(self.bidding_strategies))
        if self.auction_history is None:
            self.auction_history = []
    
    def decide_bid(self, history: List, round_num: int) -> float:
        """基于学习到的策略决定出价"""
        # ε-贪婪策略
        if np.random.random() < self.exploration_rate:
            # 探索：随机选择策略
            strategy_idx = np.random.randint(len(self.bidding_strategies))
        else:
            # 利用：选择最优策略
            strategy_idx = np.argmax(self.strategy_preferences)
        
        bid_multiplier = self.bidding_strategies[strategy_idx]
        return self.true_value * bid_multiplier
    
    def update_strategy(self, own_bid: float, won: bool, payoff: float, **kwargs):
        """根据结果更新策略偏好"""
        # 找到使用的策略索引
        used_multiplier = own_bid / self.true_value if self.true_value > 0 else 1.0
        strategy_idx = np.argmin(np.abs(self.bidding_strategies - used_multiplier))
        
        # 强化学习更新
        if payoff > 0:
            # 正收益：增强该策略
            self.strategy_preferences[strategy_idx] += self.learning_rate * payoff
        elif won and payoff < 0:
            # 赢家诅咒：赢了但亏钱，惩罚高估行为
            self.strategy_preferences[strategy_idx] -= self.learning_rate * abs(payoff)
        
        # 保持偏好非负
        self.strategy_preferences = np.maximum(self.strategy_preferences, 0.01)


def create_vickrey_auction(
    num_bidders: int = 5,
    true_value: float = 100.0,
    noise_std: float = 15.0,
    learning_rate: float = 0.1,
    exploration_rate: float = 0.1,
    num_rounds: int = 500
) -> tuple:
    """Create a Vickrey auction (second-price sealed-bid) environment.

    Nobel Prize 1996 — William Vickrey.
    Theoretical prediction: truthful bidding is a weakly dominant strategy.
    """
    standard_config = {
        "environment": {
            "type": "vickrey_auction",
            "nobel_reference": {
                "year": 1996,
                "laureates": ["William Vickrey"],
                "contribution": "Second-price sealed-bid auction — truthful bidding as dominant strategy"
            }
        },
        "parameters": {
            "num_bidders": {"value": num_bidders, "description": "Number of bidders"},
            "value_range": {"value": [0, int(true_value * 2)], "description": "Private value range"},
            "learning_rate": {"value": learning_rate, "description": "Strategy learning rate"},
            "exploration_rate": {"value": exploration_rate, "description": "Exploration vs exploitation"},
            "num_rounds": {"value": num_rounds, "description": "Number of auction rounds"}
        },
        "validation": {
            "equilibrium_type": "truthful_bidding_dominant_strategy",
            "metrics": [
                {"name": "truthful_bidding_rate", "expected_value": 1.0, "tolerance": 0.05},
                {"name": "allocative_efficiency", "expected_value": 1.0, "tolerance": 0.1}
            ]
        }
    }

    env = VickreyAuctionEnvironment(standard_config)
    return env, standard_config


class VickreyAuctionEnvironment(BaseEnvironment):
    """
    维克瑞拍卖环境
    验证：说真话是弱占优策略
    """
    
    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self.bidders: List[BidderAgent] = []
        self.auction_history: List[Dict] = []
        self.truthful_bidding_rate_history: List[float] = []
    
    def initialize_agents(self) -> None:
        """初始化竞拍者"""
        num_bidders = self.parameters.get("num_bidders", 5)
        value_range = self.parameters.get("value_range", [0, 100])
        learning_rate = self.parameters.get("learning_rate", 0.1)
        exploration_rate = self.parameters.get("exploration_rate", 0.1)
        
        self.bidders = []
        for i in range(num_bidders):
            # 从均匀分布采样私人价值
            true_value = np.random.uniform(*value_range)
            
            bidder = BidderAgent(
                agent_id=i,
                true_value=true_value,
                learning_rate=learning_rate,
                exploration_rate=exploration_rate
            )
            self.bidders.append(bidder)
    
    def run_step(self) -> Dict[str, Any]:
        """运行一轮拍卖"""
        # 1. 代理自主出价
        bids = []
        for bidder in self.bidders:
            bid = bidder.decide_bid(
                history=self.auction_history,
                round_num=self.current_round
            )
            bids.append(bid)
        
        # 2. 确定赢家（最高价）
        winner_idx = np.argmax(bids)
        winner_bid = bids[winner_idx]
        
        # 3. 第二价格规则（赢家支付第二高价）
        sorted_bids = np.sort(bids)
        second_highest_bid = sorted_bids[-2] if len(bids) > 1 else winner_bid
        
        # 4. 计算收益
        winner_true_value = self.bidders[winner_idx].true_value
        winner_payoff = winner_true_value - second_highest_bid
        
        # 5. 代理学习更新（含反事实反馈）
        for i, bidder in enumerate(self.bidders):
            actual_payoff = winner_payoff if i == winner_idx else 0
            bidder.update_strategy(
                own_bid=bids[i],
                won=(i == winner_idx),
                payoff=actual_payoff,
                second_price=second_highest_bid
            )
            # 反事实反馈：计算"如果说真话"的收益，让Agent自己比较学习
            truthful_bid = bidder.true_value
            if truthful_bid >= second_highest_bid:
                cf_payoff = bidder.true_value - second_highest_bid
            else:
                cf_payoff = 0
            # 如果真实出价的反事实收益更高，向真实出价方向更新
            if cf_payoff > actual_payoff:
                truthful_strategy_idx = np.argmin(np.abs(bidder.bidding_strategies - 1.0))
                gain = cf_payoff - actual_payoff
                bidder.strategy_preferences[truthful_strategy_idx] += bidder.learning_rate * min(gain, 1.0)
            elif cf_payoff < actual_payoff:
                # 当前策略确实更好，不改变
                pass
        
        # 6. 记录结果
        result = {
            "round": self.current_round,
            "bids": bids,
            "winner_id": winner_idx,
            "winning_bid": winner_bid,
            "price_paid": second_highest_bid,
            "winner_value": winner_true_value,
            "winner_payoff": winner_payoff
        }
        self.auction_history.append(result)
        
        # 7. 计算说真话比率
        truthful_bids = sum(
            1 for i, bid in enumerate(bids)
            if abs(bid - self.bidders[i].true_value) < 1.0  # 误差范围内
        )
        truthful_rate = truthful_bids / len(bids)
        self.truthful_bidding_rate_history.append(truthful_rate)
        
        self.current_round += 1
        return result
    
    def check_convergence(self) -> ConvergenceResult:
        """检查是否收敛到说真话均衡"""
        if len(self.truthful_bidding_rate_history) < 50:
            return ConvergenceResult(
                converged=False,
                metric_name="truthful_bidding_rate",
                current_value=0.0,
                expected_value=1.0,
                tolerance=0.05,
                message="数据不足，无法判断收敛"
            )
        
        # 计算最近 50 轮的平均说真话比率
        recent_rate = np.mean(self.truthful_bidding_rate_history[-50:])
        
        # 验证指标配置
        metrics_config = self.validation_config.get("metrics", [])
        tolerance = 0.05
        for metric in metrics_config:
            if metric["name"] == "truthful_bidding_rate":
                tolerance = metric.get("tolerance", 0.05)
                break
        
        converged = recent_rate > (1.0 - tolerance)
        
        return ConvergenceResult(
            converged=converged,
            metric_name="truthful_bidding_rate",
            current_value=recent_rate,
            expected_value=1.0,
            tolerance=tolerance,
            message=f"说真话比率：{recent_rate:.2%} (目标：>{1.0-tolerance:.0%})"
        )
    
    def get_validation_metrics(self) -> Dict[str, float]:
        """获取验证指标"""
        if not self.auction_history:
            return {}
        
        recent_history = self.auction_history[-50:] if len(self.auction_history) > 50 else self.auction_history
        
        # 说真话比率
        recent_truthful_rate = np.mean(self.truthful_bidding_rate_history[-50:]) if self.truthful_bidding_rate_history else 0.0
        
        # 配置效率：最高价值者赢得拍卖的比例
        efficient_wins = sum(
            1 for result in recent_history
            if result["winner_id"] == np.argmax([b.true_value for b in self.bidders])
        )
        allocative_efficiency = efficient_wins / len(recent_history)
        
        # 平均收益
        avg_revenue = np.mean([result["price_paid"] for result in recent_history])
        
        return {
            "truthful_bidding_rate": recent_truthful_rate,
            "allocative_efficiency": allocative_efficiency,
            "revenue": avg_revenue
        }
