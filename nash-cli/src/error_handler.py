"""
错误处理系统
功能：
1. 统一的异常处理
2. 错误日志记录
3. 自动恢复机制
4. 错误报告生成
"""

import os
import json
import traceback
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, Optional, Callable
from functools import wraps
import logging


# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('logs/error.log', encoding='utf-8'),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger(__name__)


class ExperimentError(Exception):
    """试验基础异常"""
    pass


class ConfigurationError(ExperimentError):
    """配置错误"""
    pass


class ConvergenceError(ExperimentError):
    """收敛失败"""
    pass


class DataSaveError(ExperimentError):
    """数据保存错误"""
    pass


class ErrorHandler:
    """错误处理器"""
    
    def __init__(self, log_dir: str = "logs"):
        self.log_dir = Path(log_dir)
        self.log_dir.mkdir(parents=True, exist_ok=True)
        self.error_history = []
    
    def handle_error(self, error: Exception, context: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        处理错误
        
        Args:
            error: 异常对象
            context: 上下文信息
        
        Returns:
            错误报告
        """
        timestamp = datetime.now().isoformat()
        
        # 生成错误报告
        error_report = {
            "timestamp": timestamp,
            "error_type": type(error).__name__,
            "error_message": str(error),
            "traceback": traceback.format_exc(),
            "context": context or {}
        }
        
        # 保存到历史
        self.error_history.append(error_report)
        
        # 记录日志
        logger.error(f"{error_report['error_type']}: {error_report['error_message']}")
        logger.debug(f"Traceback: {error_report['traceback']}")
        
        # 保存到文件
        self._save_error_report(error_report)
        
        return error_report
    
    def _save_error_report(self, error_report: Dict[str, Any]):
        """保存错误报告到文件"""
        error_file = self.log_dir / f"error_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        
        with open(error_file, 'w', encoding='utf-8') as f:
            json.dump(error_report, f, indent=2, ensure_ascii=False)
    
    def get_error_history(self, limit: int = 10) -> list:
        """获取错误历史"""
        return self.error_history[-limit:]
    
    def clear_error_history(self):
        """清除错误历史"""
        self.error_history.clear()
    
    def retry_on_error(self, max_retries: int = 3, delay: float = 1.0):
        """
        重试装饰器
        
        Args:
            max_retries: 最大重试次数
            delay: 重试延迟（秒）
        
        Returns:
            装饰器函数
        """
        def decorator(func: Callable):
            @wraps(func)
            def wrapper(*args, **kwargs):
                last_error = None
                
                for attempt in range(max_retries):
                    try:
                        return func(*args, **kwargs)
                    except Exception as e:
                        last_error = e
                        logger.warning(f"Attempt {attempt + 1}/{max_retries} failed: {e}")
                        
                        if attempt < max_retries - 1:
                            import time
                            time.sleep(delay)
                
                # 所有重试失败
                error_report = self.handle_error(
                    last_error,
                    context={
                        "function": func.__name__,
                        "args": args,
                        "kwargs": kwargs,
                        "max_retries": max_retries
                    }
                )
                
                raise ExperimentError(f"Function {func.__name__} failed after {max_retries} attempts") from last_error
            
            return wrapper
        return decorator


# 全局错误处理器
error_handler = ErrorHandler()


def safe_execute(func: Callable, default_value: Any = None, context: Dict[str, Any] = None):
    """
    安全执行函数包装器
    
    Args:
        func: 要执行的函数
        default_value: 出错时的默认返回值
        context: 上下文信息
    
    Returns:
        包装后的函数
    """
    @wraps(func)
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except Exception as e:
            error_report = error_handler.handle_error(e, context)
            logger.error(f"Safe execution failed: {e}")
            return default_value
    
    return wrapper


def log_errors(func: Callable):
    """
    记录错误的装饰器
    
    使用方式:
    @log_errors
    def my_function():
        ...
    """
    @wraps(func)
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except Exception as e:
            error_handler.handle_error(
                e,
                context={
                    "function": func.__name__,
                    "module": func.__module__
                }
            )
            raise
    
    return wrapper


_RECOVERY_PLANS: Dict[str, Dict[str, Any]] = {
    "ConfigurationError": {
        "action": "check_config",
        "steps": [
            "检查配置文件是否存在",
            "验证配置参数格式",
            "确认必填参数已提供",
            "使用默认配置重试"
        ]
    },
    "ConvergenceError": {
        "action": "adjust_parameters",
        "steps": [
            "增加试验轮数",
            "调整学习率",
            "降低探索率",
            "检查收益矩阵是否正确"
        ]
    },
    "DataSaveError": {
        "action": "retry_save",
        "steps": [
            "检查磁盘空间",
            "验证文件权限",
            "尝试备用保存路径",
            "减少保存频率"
        ]
    },
    "ImportError": {
        "action": "install_dependency",
        "steps": [
            "检查依赖是否安装",
            "使用 pip install 安装缺失包",
            "检查 Python 版本兼容性",
            "使用虚拟环境"
        ]
    }
}

_DEFAULT_RECOVERY_PLAN: Dict[str, Any] = {
    "action": "manual_intervention",
    "steps": [
        "查看错误日志",
        "分析错误原因",
        "手动修复问题",
        "重新运行试验"
    ]
}


def create_error_recovery_plan(error_type: str) -> Dict[str, Any]:
    """
    创建错误恢复计划

    Args:
        error_type: 错误类型

    Returns:
        恢复计划
    """
    return _RECOVERY_PLANS.get(error_type, _DEFAULT_RECOVERY_PLAN)


def generate_error_report(errors: list) -> str:
    """
    生成错误报告
    
    Args:
        errors: 错误列表
    
    Returns:
        错误报告字符串
    """
    report = []
    report.append("=" * 60)
    report.append("错误报告")
    report.append("=" * 60)
    report.append(f"生成时间：{datetime.now().isoformat()}")
    report.append(f"错误数量：{len(errors)}")
    report.append("")
    
    for i, error in enumerate(errors, 1):
        report.append(f"\n[错误 {i}]")
        report.append(f"时间：{error.get('timestamp', 'N/A')}")
        report.append(f"类型：{error.get('error_type', 'N/A')}")
        report.append(f"消息：{error.get('error_message', 'N/A')}")
        
        if error.get('context'):
            report.append("上下文:")
            for key, value in error['context'].items():
                report.append(f"  - {key}: {value}")
        
        # 添加恢复计划
        recovery = create_error_recovery_plan(error.get('error_type', ''))
        report.append(f"建议操作：{recovery['action']}")
        report.append("恢复步骤:")
        for step in recovery['steps']:
            report.append(f"  {step}")
    
    report.append("\n" + "=" * 60)
    
    return "\n".join(report)
