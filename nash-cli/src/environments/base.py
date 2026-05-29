"""
诺贝尔奖环境基类
定义所有环境的统一接口
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, List
from dataclasses import dataclass
import sys


@dataclass
class ConvergenceResult:
    """收敛结果"""
    converged: bool
    metric_name: str
    current_value: float
    expected_value: float
    tolerance: float
    message: str


class BaseEnvironment(ABC):
    """
    诺贝尔奖环境基类
    所有具体环境必须实现以下接口
    """
    
    def __init__(self, config: Dict[str, Any]):
        """
        初始化环境
        
        Args:
            config: 标准格式的环境配置
        """
        self.config = config
        self.environment_type = config["environment"]["type"]
        self.parameters = self._extract_parameters(config["parameters"])
        self.validation_config = config["validation"]
        self.auto_calibration_config = config.get("auto_calibration", {})
        
        # 运行状态
        self.current_round = 0
        self.history: List[Dict[str, Any]] = []
        self.metrics_history: Dict[str, List[float]] = {}
    
    @abstractmethod
    def initialize_agents(self) -> None:
        """初始化代理（不预设策略，从零开始学习）"""
        pass
    
    @abstractmethod
    def run_step(self) -> Dict[str, Any]:
        """
        运行一步模拟
        
        Returns:
            当前步的状态信息
        """
        pass
    
    @abstractmethod
    def check_convergence(self) -> ConvergenceResult:
        """
        检查是否收敛到均衡
        
        Returns:
            收敛结果
        """
        pass
    
    @abstractmethod
    def get_validation_metrics(self) -> Dict[str, float]:
        """
        获取验证指标
        
        Returns:
            指标字典
        """
        pass
    
    def _p(self, key: str, default=None):
        """Centralized parameter extraction (Mesa Scenario pattern).

        Reads from self.parameters (already flat after _extract_parameters).
        All subclasses should use this instead of defining their own get_val().
        """
        value = self.parameters.get(key, default)
        if value is None:
            return default
        if isinstance(value, dict):
            return value.get("value", default)
        return value

    def _extract_parameters(self, params_config: Dict[str, Any]) -> Dict[str, Any]:
        """Extract parameter values from config — accepts both nested {'key': {'value': X}} and flat {'key': X} formats."""
        result = {}
        for key, value in params_config.items():
            if isinstance(value, dict) and "value" in value:
                result[key] = value["value"]
            else:
                result[key] = value
        return result
    
    def run_simulation(self, max_rounds: int = None) -> Dict[str, Any]:
        """
        运行完整模拟
        
        Args:
            max_rounds: 最大轮数，默认使用配置值
        
        Returns:
            模拟结果
        """
        if max_rounds is None:
            max_rounds = self.parameters.get("num_rounds", 1000)
        
        self.initialize_agents()
        
        for round in range(max_rounds):
            # 运行一步
            state = self.run_step()
            self.history.append(state)
            
            # 更新指标历史
            metrics = self.get_validation_metrics()
            for metric_name, value in metrics.items():
                if metric_name not in self.metrics_history:
                    self.metrics_history[metric_name] = []
                self.metrics_history[metric_name].append(value)
            
            # 定期检查收敛性
            if self.current_round > 50 and self.current_round % 50 == 0:
                convergence = self.check_convergence()
                if convergence.converged:
                    print(
                        f"✓ 收敛到{convergence.metric_name}均衡 (round {self.current_round})",
                        file=sys.stderr,
                    )
                    break
        
        return self._generate_result()
    
    def _generate_result(self) -> Dict[str, Any]:
        """生成模拟结果"""
        final_metrics = self.get_validation_metrics()
        convergence = self.check_convergence()
        
        return {
            "environment_type": self.environment_type,
            "total_rounds": self.current_round,
            "converged": bool(convergence.converged),
            "convergence_message": convergence.message,
            "final_metrics": final_metrics,
            "metrics_history": self.metrics_history,
            "history": self.history
        }
    
    def __repr__(self) -> str:
        return f"{self.environment_type}(parameters={self.parameters})"
