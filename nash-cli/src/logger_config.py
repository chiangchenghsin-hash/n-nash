"""
NASH 统一日志配置

功能:
1. 添加 correlation ID 追踪
2. 结构化日志输出
3. 错误码集成
4. 支持前端展示
"""

import logging
import sys
from datetime import datetime
from typing import Optional, Dict, Any
import uuid


class CorrelationIdFilter(logging.Filter):
    """为每条日志添加 correlation ID"""
    
    def filter(self, record):
        # 如果没有 correlation_id，生成一个新的
        if not hasattr(record, 'correlation_id'):
            record.correlation_id = str(uuid.uuid4())[:8]
        return True


class StructuredFormatter(logging.Formatter):
    """
    结构化日志格式器
    
    输出格式:
    [ERROR] [M1001] [correlation_id=abc123] [memory_system] ChromaDB 连接失败 | {'agent_id': 42}
    """
    
    def format(self, record):
        # 获取错误码（如果有）
        error_code = getattr(record, 'error_code', '')
        error_code_str = f" [{error_code}]" if error_code else ""
        
        # 获取 correlation_id
        correlation_id = getattr(record, 'correlation_id', 'unknown')[:8]
        
        # 构建上下文信息
        context = getattr(record, 'context', {})
        context_str = f" | {context}" if context else ""
        
        # 格式化日志消息
        log_message = super().format(record)
        
        return (
            f"[{record.levelname}] "
            f"{error_code_str}"
            f"[correlation_id={correlation_id}] "
            f"[{record.name}] "
            f"{record.message}"
            f"{context_str}"
        )


def setup_logger(
    name: str,
    level: int = logging.INFO,
    correlation_id: Optional[str] = None
) -> logging.Logger:
    """
    设置 logger
    
    Args:
        name: logger 名称
        level: 日志级别
        correlation_id: 可选的 correlation ID（用于追踪一次请求）
    
    Returns:
        配置好的 logger 实例
    """
    logger = logging.getLogger(name)
    logger.setLevel(level)
    
    # 避免重复添加 handler
    if logger.handlers:
        return logger
    
    # 创建 console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(level)
    
    # 设置 formatter
    formatter = StructuredFormatter()
    console_handler.setFormatter(formatter)
    
    # 添加 correlation ID filter
    correlation_filter = CorrelationIdFilter()
    console_handler.addFilter(correlation_filter)
    
    # 添加 handler
    logger.addHandler(console_handler)
    
    return logger


# ========== 便捷函数 ==========

class LogContext:
    """
    日志上下文管理器
    
    使用示例:
        with LogContext('experiment_start', logger) as ctx:
            ctx.log("开始实验", experiment_id="exp_123")
            # 自动包含 experiment_id 在所有日志中
    """
    
    def __init__(self, operation: str, logger: logging.Logger):
        self.operation = operation
        self.logger = logger
        self.correlation_id = str(uuid.uuid4())[:8]
        self.context: Dict[str, Any] = {}
    
    def __enter__(self):
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        if exc_type:
            self.error(f"{self.operation} 失败", error=str(exc_val))
        else:
            self.info(f"{self.operation} 完成")
    
    def info(self, message: str, **kwargs):
        """记录 INFO 级别日志"""
        extra = {
            'context': {**self.context, **kwargs},
            'correlation_id': self.correlation_id
        }
        self.logger.info(message, extra=extra)
    
    def error(self, message: str, error_code: Optional[str] = None, **kwargs):
        """记录 ERROR 级别日志"""
        extra = {
            'context': {**self.context, **kwargs},
            'correlation_id': self.correlation_id,
            'error_code': error_code
        }
        self.logger.error(message, extra=extra)
    
    def debug(self, message: str, **kwargs):
        """记录 DEBUG 级别日志"""
        extra = {
            'context': {**self.context, **kwargs},
            'correlation_id': self.correlation_id
        }
        self.logger.debug(message, extra=extra)


# ========== 全局默认 logger ==========

default_logger = setup_logger('nash')
