"""
诺贝尔奖模型验证器
验证模拟结果是否符合诺贝尔奖理论预测
"""

from typing import Dict, Any, List, Optional
from dataclasses import dataclass


@dataclass
class ValidationResult:
    """验证结果"""
    model_name: str
    nobel_year: int
    hypothesis_supported: bool
    confidence: float
    metrics: Dict[str, float]
    conclusion: str
    suggestions: List[str] = None


class NobelValidator:
    """
    诺贝尔奖模型验证器
    验证模拟结果是否符合理论预测
    """
    
    # 诺贝尔奖模型定义
    NOBEL_MODELS = {
        "vickrey_auction": {
            "name": "维克瑞拍卖",
            "year": 1996,
            "laureates": ["William Vickrey", "James Mirrlees"],
            "prediction": "说真话是弱占优策略",
            "key_metrics": ["truthful_bidding_rate", "allocative_efficiency"]
        },
        "vickrey": {
            "name": "维克瑞拍卖",
            "year": 1996,
            "laureates": ["William Vickrey", "James Mirrlees"],
            "prediction": "说真话是弱占优策略",
            "key_metrics": ["truthful_bidding_rate", "allocative_efficiency"]
        },
        "spence_signaling": {
            "name": "斯彭斯信号发送",
            "year": 2001,
            "laureates": ["George Akerlof", "Michael Spence", "Joseph Stiglitz"],
            "prediction": "分离均衡（高能力者选择高教育）",
            "key_metrics": ["separation_index", "education_premium"]
        },
        "spence": {
            "name": "斯彭斯信号发送",
            "year": 2001,
            "laureates": ["George Akerlof", "Michael Spence", "Joseph Stiglitz"],
            "prediction": "分离均衡（高能力者选择高教育）",
            "key_metrics": ["separation_index", "education_premium"]
        },
        "repeated_prisoners_dilemma": {
            "name": "重复囚徒困境",
            "year": 2005,
            "laureates": ["Robert Aumann", "Thomas Schelling"],
            "prediction": "当δ足够大时，合作可作为 SPNE 出现",
            "key_metrics": ["cooperation_rate", "network_reciprocity"]
        },
        "prisoners_dilemma": {
            "name": "重复囚徒困境",
            "year": 2005,
            "laureates": ["Robert Aumann", "Thomas Schelling"],
            "prediction": "当δ足够大时，合作可作为 SPNE 出现",
            "key_metrics": ["cooperation_rate", "network_reciprocity"]
        },
        "common_pool_resource": {
            "name": "公地悲剧",
            "year": 2009,
            "laureates": ["Elinor Ostrom"],
            "prediction": "个人理性导致集体非理性（资源枯竭）",
            "key_metrics": ["resource_depletion_rate", "sustainability_index"]
        },
        "common_pool": {
            "name": "公地悲剧",
            "year": 2009,
            "laureates": ["Elinor Ostrom"],
            "prediction": "个人理性导致集体非理性（资源枯竭）",
            "key_metrics": ["resource_depletion_rate", "sustainability_index"]
        },
        "two_sided_matching": {
            "name": "稳定匹配",
            "year": 2012,
            "laureates": ["Alvin Roth", "Lloyd Shapley"],
            "prediction": "盖尔 - 沙普利算法产生稳定匹配",
            "key_metrics": ["stability_index", "blocking_pairs"]
        },
        "matching": {
            "name": "稳定匹配",
            "year": 2012,
            "laureates": ["Alvin Roth", "Lloyd Shapley"],
            "prediction": "盖尔 - 沙普利算法产生稳定匹配",
            "key_metrics": ["stability_index", "blocking_pairs"]
        },
        "auction_common_value": {
            "name": "共同价值拍卖",
            "year": 2020,
            "laureates": ["Paul Milgrom", "Robert Wilson"],
            "prediction": "赢家诅咒存在",
            "key_metrics": ["winner_curse_indicator", "revenue"]
        },
        "public_goods": {
            "name": "公共物品博弈",
            "year": 2009,
            "laureates": ["Elinor Ostrom"],
            "prediction": "趋向搭便车",
            "key_metrics": ["contribution_rate", "free_riding_index"]
        },
        "hawk_dove": {
            "name": "鹰鸽博弈",
            "year": 2005,
            "laureates": ["Robert Aumann", "Thomas Schelling"],
            "prediction": "ESS 策略",
            "key_metrics": ["hawk_ratio", "ess_deviation"]
        }
    }

    def validate(self,
                environment_type: str,
                metrics: Dict[str, float],
                config: Dict[str, Any]) -> ValidationResult:
        """
        验证模拟结果
        
        Args:
            environment_type: 环境类型
            metrics: 验证指标
            config: 完整配置
        
        Returns:
            验证结果
        """
        if environment_type not in self.NOBEL_MODELS:
            return ValidationResult(
                model_name=environment_type,
                nobel_year=0,
                hypothesis_supported=False,
                confidence=0.0,
                metrics=metrics,
                conclusion=f"未知的环境类型：{environment_type}"
            )
        
        model_info = self.NOBEL_MODELS[environment_type]
        
        # 根据环境类型调用特定验证方法
        validation_method = getattr(self, f"_validate_{environment_type}", None)
        if validation_method:
            return validation_method(metrics, config, model_info)
        else:
            return self._validate_generic(metrics, config, model_info)
    
    def _validate_vickrey_auction(self,
                                 metrics: Dict[str, float],
                                 config: Dict[str, Any],
                                 model_info: Dict) -> ValidationResult:
        """验证维克瑞拍卖"""
        return self._validate_vickrey(metrics, config, model_info)

    def _validate_vickrey(self,
                         metrics: Dict[str, float],
                         config: Dict[str, Any],
                         model_info: Dict) -> ValidationResult:
        """验证维克瑞拍卖"""
        truthful_rate = metrics.get("truthful_bidding_rate", 0.0)
        efficiency = metrics.get("allocative_efficiency", 0.0)
        
        # 验证标准：说真话比率 > 95%
        threshold = 0.95
        supported = truthful_rate > threshold
        
        confidence = min(1.0, truthful_rate / threshold)
        
        conclusion = (
            f"✓ 理论验证成功：说真话比率 {truthful_rate:.1%}" if supported
            else f"✗ 未收敛到说真话均衡：{truthful_rate:.1%} < {threshold:.0%}"
        )
        
        suggestions = []
        if not supported:
            suggestions.append("增加模拟轮数")
            suggestions.append("降低学习率或探索率")
            suggestions.append("检查收益计算是否正确")
        
        return ValidationResult(
            model_name=model_info["name"],
            nobel_year=model_info["year"],
            hypothesis_supported=supported,
            confidence=confidence,
            metrics=metrics,
            conclusion=conclusion,
            suggestions=suggestions
        )
    
    def _validate_spence_signaling(self,
                                  metrics: Dict[str, float],
                                  config: Dict[str, Any],
                                  model_info: Dict) -> ValidationResult:
        """验证斯彭斯信号发送"""
        return self._validate_spence(metrics, config, model_info)

    def _validate_spence(self,
                        metrics: Dict[str, float],
                        config: Dict[str, Any],
                        model_info: Dict) -> ValidationResult:
        """验证斯彭斯信号发送"""
        separation_index = metrics.get("separation_index", 0.0)
        
        # 验证标准：分离指数 > 0.9
        threshold = 0.9
        supported = separation_index > threshold
        
        confidence = min(1.0, separation_index / threshold)
        
        conclusion = (
            f"✓ 分离均衡验证成功：分离指数 {separation_index:.1%}" if supported
            else f"✗ 混同均衡：分离指数 {separation_index:.1%} < {threshold:.0%}"
        )
        
        suggestions = []
        if not supported:
            suggestions.append("增加教育成本差异")
            suggestions.append("延长模拟时间")
        
        return ValidationResult(
            model_name=model_info["name"],
            nobel_year=model_info["year"],
            hypothesis_supported=supported,
            confidence=confidence,
            metrics=metrics,
            conclusion=conclusion,
            suggestions=suggestions
        )
    
    def _validate_repeated_prisoners_dilemma(self,
                                            metrics: Dict[str, float],
                                            config: Dict[str, Any],
                                            model_info: Dict) -> ValidationResult:
        """验证重复囚徒困境"""
        return self._validate_prisoners_dilemma(metrics, config, model_info)

    def _validate_prisoners_dilemma(self,
                                   metrics: Dict[str, float],
                                   config: Dict[str, Any],
                                   model_info: Dict) -> ValidationResult:
        """验证重复囚徒困境"""
        cooperation_rate = metrics.get("cooperation_rate", 0.0)
        spne_supported = metrics.get("spne_supported", 0.0)

        # 验证标准：合作率 > 80% 且 δ条件满足
        threshold = 0.8
        supported = cooperation_rate > threshold and spne_supported > 0.5

        confidence = min(1.0, cooperation_rate / threshold)

        conclusion = (
            f"✓ SPNE 验证成功：合作率 {cooperation_rate:.1%}" if supported
            else f"✗ 未收敛到合作均衡：{cooperation_rate:.1%} < {threshold:.0%}"
        )

        suggestions = []
        if not supported:
            suggestions.append("增加折扣因子δ（建议>0.7）")
            suggestions.append("增加模拟轮数以充分学习")
            suggestions.append("降低探索率以促进策略稳定")

        return ValidationResult(
            model_name=model_info["name"],
            nobel_year=model_info["year"],
            hypothesis_supported=supported,
            confidence=confidence,
            metrics=metrics,
            conclusion=conclusion,
            suggestions=suggestions
        )
    
    def _validate_common_pool_resource(self,
                                      metrics: Dict[str, float],
                                      config: Dict[str, Any],
                                      model_info: Dict) -> ValidationResult:
        """验证公共资源博弈"""
        return self._validate_common_pool(metrics, config, model_info)

    def _validate_common_pool(self,
                             metrics: Dict[str, float],
                             config: Dict[str, Any],
                             model_info: Dict) -> ValidationResult:
        """验证公共资源博弈 — Ostrom 理论：无制度时公地悲剧必然发生"""
        depletion_rate = metrics.get("resource_depletion_rate", 0.0)
        tragedy_indicator = metrics.get("tragedy_indicator", 0.0)
        sustainability_index = metrics.get("sustainability_index", 0.0)

        # Ostrom 理论验证：公地悲剧 = 资源显著枯竭 或 过度抽取频繁
        tragedy_occurred = tragedy_indicator > 0.5 or depletion_rate > 0.3
        resource_depleted = depletion_rate > 0.5

        if resource_depleted:
            confidence = min(1.0, depletion_rate)
            conclusion = (
                f"✓ 公地悲剧验证成功：资源枯竭率 {depletion_rate:.1%}，"
                f"过度抽取频率 {tragedy_indicator:.1%}"
            )
        elif tragedy_occurred:
            confidence = 0.7
            conclusion = (
                f"✓ 公地悲剧趋势确认：过度抽取频率 {tragedy_indicator:.1%}，"
                f"可持续指数 {sustainability_index:.1%}"
            )
        else:
            confidence = max(0.0, 1.0 - depletion_rate - tragedy_indicator)
            conclusion = (
                f"✗ 未观察到公地悲剧：枯竭率 {depletion_rate:.1%}，"
                f"过度抽取频率 {tragedy_indicator:.1%}"
            )

        suggestions = []
        if not tragedy_occurred:
            suggestions.append("增加代理数量以加剧竞争")
            suggestions.append("降低资源再生速率")
            suggestions.append("延长模拟轮数以观察长期趋势")
            suggestions.append("移除任何隐式合作机制")

        return ValidationResult(
            model_name=model_info["name"],
            nobel_year=model_info["year"],
            hypothesis_supported=tragedy_occurred,
            confidence=confidence,
            metrics=metrics,
            conclusion=conclusion,
            suggestions=suggestions
        )
    
    def _validate_hawk_dove(self,
                           metrics: Dict[str, float],
                           config: Dict[str, Any],
                           model_info: Dict) -> ValidationResult:
        """验证鹰鸽博弈 ESS"""
        hawk_ratio = metrics.get("hawk_ratio", 0.0)
        ess_deviation = metrics.get("ess_deviation", 1.0)
        
        # 验证标准：与 ESS 预测偏差 < 10%
        threshold = 0.1
        supported = ess_deviation < threshold
        
        confidence = 1.0 - min(1.0, ess_deviation / threshold)
        
        v = config["parameters"].get("resource_value", {}).get("value", 4.0)
        c = config["parameters"].get("conflict_cost", {}).get("value", 6.0)
        ess_prediction = v / c if v < c else 1.0
        
        conclusion = (
            f"✓ ESS 验证成功：鹰比例 {hawk_ratio:.1%} ≈ 预测 {ess_prediction:.1%}" if supported
            else f"✗ 未收敛到 ESS：偏差 {ess_deviation:.1%}"
        )
        
        suggestions = []
        if not supported:
            suggestions.append("增加模拟轮数")
            suggestions.append("调整学习率以促进策略稳定")
            suggestions.append("检查收益矩阵计算")
        
        return ValidationResult(
            model_name=model_info["name"],
            nobel_year=model_info["year"],
            hypothesis_supported=supported,
            confidence=confidence,
            metrics=metrics,
            conclusion=conclusion,
            suggestions=suggestions
        )
    
    def _validate_public_goods(self,
                              metrics: Dict[str, float],
                              config: Dict[str, Any],
                              model_info: Dict) -> ValidationResult:
        """验证公共物品博弈"""
        contribution_rate = metrics.get("contribution_rate", 0.0)
        free_riding_index = metrics.get("free_riding_index", 0.0)
        
        # 理论预测：趋向搭便车（贡献率<20%）
        threshold = 0.2
        supported = contribution_rate < threshold
        
        confidence = 1.0 - (contribution_rate / threshold) if contribution_rate < threshold else 0.0
        
        conclusion = (
            f"✓ 搭便车现象验证：贡献率 {contribution_rate:.1%} (<{threshold:.0%})" if supported
            else f"✗ 合作水平过高：{contribution_rate:.1%}，预期趋向搭便车"
        )
        
        suggestions = []
        if not supported:
            suggestions.append("增加群体规模")
            suggestions.append("降低边际回报率")
            suggestions.append("允许匿名决策")
        
        return ValidationResult(
            model_name=model_info["name"],
            nobel_year=model_info["year"],
            hypothesis_supported=supported,
            confidence=confidence,
            metrics=metrics,
            conclusion=conclusion,
            suggestions=suggestions
        )
    
    def _validate_two_sided_matching(self,
                                    metrics: Dict[str, float],
                                    config: Dict[str, Any],
                                    model_info: Dict) -> ValidationResult:
        """验证双边匹配稳定性"""
        return self._validate_matching(metrics, config, model_info)

    def _validate_matching(self,
                          metrics: Dict[str, float],
                          config: Dict[str, Any],
                          model_info: Dict) -> ValidationResult:
        """验证双边匹配稳定性"""
        stability_index = metrics.get("stability_index", 0.0)
        matching_efficiency = metrics.get("matching_efficiency", 0.0)
        
        # 验证标准：稳定性指数 > 95%
        threshold = 0.95
        supported = stability_index > threshold
        
        confidence = min(1.0, stability_index / threshold)
        
        conclusion = (
            f"✓ 稳定匹配验证成功：稳定性 {stability_index:.1%}" if supported
            else f"✗ 存在阻塞对：稳定性 {stability_index:.1%} < {threshold:.0%}"
        )
        
        suggestions = []
        if not supported:
            suggestions.append("确保偏好列表完整且无并列")
            suggestions.append("检查 Gale-Shapley 算法实现")
            suggestions.append("增加市场厚度（参与人数）")
        
        return ValidationResult(
            model_name=model_info["name"],
            nobel_year=model_info["year"],
            hypothesis_supported=supported,
            confidence=confidence,
            metrics=metrics,
            conclusion=conclusion,
            suggestions=suggestions
        )
    
    def _validate_auction_common_value(self,
                                      metrics: Dict[str, float],
                                      config: Dict[str, Any],
                                      model_info: Dict) -> ValidationResult:
        """验证共同价值拍卖的赢家诅咒"""
        winner_curse_rate = metrics.get("winner_curse_rate", 0.0)
        revenue_efficiency = metrics.get("revenue_efficiency", 0.0)
        
        # 理论预测：赢家诅咒普遍存在 (>=50%)
        threshold = 0.5
        supported = winner_curse_rate >= threshold
        
        confidence = min(1.0, winner_curse_rate / threshold)
        
        conclusion = (
            f"✓ 赢家诅咒验证成功：发生率 {winner_curse_rate:.1%}" if supported
            else f"✗ 赢家诅咒不明显：{winner_curse_rate:.1%} < {threshold:.0%}"
        )
        
        suggestions = []
        if not supported:
            suggestions.append("增加竞标者数量")
            suggestions.append("提高价值估计的不确定性")
            suggestions.append("减少 bidder 的经验学习")
        
        return ValidationResult(
            model_name=model_info["name"],
            nobel_year=model_info["year"],
            hypothesis_supported=supported,
            confidence=confidence,
            metrics=metrics,
            conclusion=conclusion,
            suggestions=suggestions
        )
    
    def _validate_generic(self,
                         metrics: Dict[str, float],
                         config: Dict[str, Any],
                         model_info: Dict) -> ValidationResult:
        """通用验证方法"""
        # 默认：检查所有指标是否稳定
        if not metrics:
            return ValidationResult(
                model_name=model_info["name"],
                nobel_year=model_info["year"],
                hypothesis_supported=False,
                confidence=0.0,
                metrics=metrics,
                conclusion="无可用指标进行验证"
            )
        
        # 简单验证：有数据即认为部分成功
        avg_value = sum(metrics.values()) / len(metrics)
        supported = avg_value > 0
        
        return ValidationResult(
            model_name=model_info["name"],
            nobel_year=model_info["year"],
            hypothesis_supported=supported,
            confidence=0.5,
            metrics=metrics,
            conclusion=f"通用验证：平均指标值 {avg_value:.3f}"
        )
