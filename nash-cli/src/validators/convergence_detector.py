"""
收敛检测器
检测模拟是否收敛到理论均衡
"""

import numpy as np
from typing import Dict, Any, List
from dataclasses import dataclass


@dataclass
class DetectionResult:
    """检测结果"""
    converged: bool
    metric_name: str
    current_value: float
    expected_value: float
    confidence: float
    message: str
    suggestions: List[str] = None


class ConvergenceDetector:
    """
    收敛检测器
    使用多种统计方法检测均衡收敛
    """
    
    def __init__(self, window_size: int = 50, confidence_threshold: float = 0.95):
        """
        初始化检测器
        
        Args:
            window_size: 滑动窗口大小
            confidence_threshold: 置信度阈值
        """
        self.window_size = window_size
        self.confidence_threshold = confidence_threshold
    
    def detect(self, 
               metrics_history: Dict[str, List[float]],
               validation_config: Dict[str, Any]) -> List[DetectionResult]:
        """
        检测所有指标是否收敛
        
        Args:
            metrics_history: 指标历史
            validation_config: 验证配置
        
        Returns:
            检测结果列表
        """
        results = []
        metrics_config = validation_config.get("metrics", [])
        
        for metric_config in metrics_config:
            metric_name = metric_config["name"]
            
            if metric_name not in metrics_history:
                continue
            
            history = metrics_history[metric_name]
            if len(history) < self.window_size:
                continue
            
            # 检测收敛
            result = self._detect_single_metric(
                history=history,
                metric_config=metric_config
            )
            results.append(result)
        
        return results
    
    def _detect_single_metric(self, 
                             history: List[float], 
                             metric_config: Dict[str, Any]) -> DetectionResult:
        """检测单个指标是否收敛"""
        metric_name = metric_config["name"]
        expected_value = metric_config.get("expected_value")
        tolerance = metric_config.get("tolerance", 0.05)
        
        # 获取最近窗口的数据
        recent_data = history[-self.window_size:]
        current_value = np.mean(recent_data)
        std_dev = np.std(recent_data)
        
        # 1. 稳定性检测：标准差是否足够小
        is_stable = std_dev < (tolerance / 2)
        
        # 2. 准确性检测：是否在预期值范围内
        if expected_value is not None:
            is_accurate = abs(current_value - expected_value) <= tolerance
            converged = is_stable and is_accurate
        else:
            # 没有预期值，只检测稳定性
            is_accurate = True
            converged = is_stable
        
        # 计算置信度
        confidence = self._compute_confidence(recent_data, tolerance)
        
        # 生成建议
        suggestions = []
        if not is_stable:
            suggestions.append("指标波动较大，可能需要增加模拟轮数或调整学习率")
        if not is_accurate and expected_value is not None:
            suggestions.append(f"当前值{current_value:.3f}与预期值{expected_value:.3f}差距较大")
            suggestions.append("考虑调整环境参数或学习规则")
        
        return DetectionResult(
            converged=converged,
            metric_name=metric_name,
            current_value=current_value,
            expected_value=expected_value if expected_value is not None else 0.0,
            confidence=confidence,
            message=f"{metric_name}: {current_value:.3f} (稳定：{'是' if is_stable else '否'}, 准确：{'是' if is_accurate else '否'})",
            suggestions=suggestions
        )
    
    def _compute_confidence(self, data: List[float], tolerance: float) -> float:
        """计算收敛置信度"""
        if len(data) < 10:
            return 0.0
        
        # 基于标准差和样本量计算置信度
        std_dev = np.std(data)
        n = len(data)
        
        # 标准差越小，置信度越高
        std_confidence = max(0, 1 - (std_dev / tolerance))
        
        # 样本量越大，置信度越高
        sample_confidence = min(1, n / 100)
        
        # 综合置信度
        confidence = 0.7 * std_confidence + 0.3 * sample_confidence
        
        return min(confidence, 1.0)
    
    def detect_trend(self, 
                    history: List[float], 
                    window_size: int = None) -> str:
        """
        检测趋势
        
        Args:
            history: 历史数据
            window_size: 窗口大小
        
        Returns:
            趋势描述："increasing", "decreasing", "stable", "oscillating"
        """
        if window_size is None:
            window_size = self.window_size
        
        if len(history) < window_size * 2:
            return "insufficient_data"
        
        recent = history[-window_size:]
        previous = history[-window_size*2:-window_size]
        
        recent_mean = np.mean(recent)
        previous_mean = np.mean(previous)
        recent_std = np.std(recent)
        
        # 变化率
        change_rate = (recent_mean - previous_mean) / (abs(previous_mean) + 1e-8)
        
        # 振荡检测
        if recent_std > abs(recent_mean - previous_mean) * 2:
            return "oscillating"
        
        # 趋势判断
        if abs(change_rate) < 0.05:
            return "stable"
        elif change_rate > 0:
            return "increasing"
        else:
            return "decreasing"
