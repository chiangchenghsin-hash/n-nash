"""
NASH 系统错误码定义

统一错误管理规范，便于日志追踪和问题诊断
"""
from enum import Enum


class ErrorCode(Enum):
    """
    错误码枚举
    
    命名规范：
    - M1xxx: Memory System (记忆系统)
    - A2xxx: Agent System (智能体系统)
    - S3xxx: Simulation (模拟引擎)
    - V4xxx: Validation (验证系统)
    - C5xxx: Configuration (配置管理)
    - X6xxx: External API (外部接口)
    """
    
    # ========== Memory System Errors (M1xxx) ==========
    MEMORY_DB_CLOSED = "M1001"
    MEMORY_QUERY_FAILED = "M1002"
    MEMORY_CONNECTION_ERROR = "M1003"
    MEMORY_INVALID_METADATA = "M1004"
    
    # ========== Agent System Errors (A2xxx) ==========
    AGENT_LANGGRAPH_FAILED = "A2001"
    AGENT_BELIEF_UPDATE_FAILED = "A2002"
    AGENT_PERCEPTION_FAILED = "A2003"
    AGENT_DECISION_FAILED = "A2004"
    AGENT_ACTION_INVALID = "A2005"
    
    # ========== Simulation Errors (S3xxx) ==========
    SIM_STEP_FAILED = "S3001"
    SIM_CONFIG_INVALID = "S3002"
    SIM_AGENT_NOT_FOUND = "S3003"
    SIM_RESOURCE_ALLOCATION_FAILED = "S3004"
    SIM_STATE_SERIALIZATION_FAILED = "S3005"
    
    # ========== Validation Errors (V4xxx) ==========
    VALIDATION_SPEC_INVALID = "V4001"
    VALIDATION_BREAKPOINT_TRIGGERED = "V4002"
    VALIDATION_STATISTICAL_ERROR = "V4003"
    VALIDATION_HYPOTHESIS_REJECTED = "V4004"
    
    # ========== Configuration Errors (C5xxx) ==========
    CONFIG_MISSING_API_KEY = "C5001"
    CONFIG_INVALID_PATH = "C5002"
    CONFIG_PORT_CONFLICT = "C5003"
    CONFIG_DATABASE_UNREACHABLE = "C5004"
    
    # ========== External API Errors (X6xxx) ==========
    API_DEEPSEEK_RATE_LIMIT = "X6001"
    API_DEEPSEEK_AUTH_FAILED = "X6002"
    API_DEEPSEEK_TIMEOUT = "X6003"
    API_DEEPSEEK_INVALID_RESPONSE = "X6004"


class NashError(Exception):
    """
    NASH 系统统一错误类
    
    使用示例:
        raise NashError(
            code=ErrorCode.MEMORY_DB_CLOSED,
            message="ChromaDB 数据库连接已关闭",
            context={
                "agent_id": 42,
                "step": 15,
                "experiment_id": "exp_123"
            }
        )
    """
    
    def __init__(self, code: ErrorCode, message: str, context: dict = None):
        self.code = code
        self.message = message
        self.context = context or {}
        self.timestamp = self._get_timestamp()
        
        # 构建完整的错误消息
        full_message = f"[{code.value}] {message}"
        if self.context:
            full_message += f" | Context: {self.context}"
        
        super().__init__(full_message)
    
    def _get_timestamp(self) -> str:
        """获取 ISO 格式时间戳"""
        from datetime import datetime
        return datetime.now().isoformat()
    
    def to_dict(self) -> dict:
        """转换为字典格式，便于日志记录"""
        return {
            "code": self.code.value,
            "message": self.message,
            "context": self.context,
            "timestamp": self.timestamp
        }


# ========== 便捷错误工厂函数 ==========

def memory_error(message: str, **context) -> NashError:
    """快速创建记忆系统错误"""
    return NashError(ErrorCode.MEMORY_QUERY_FAILED, message, context)


def agent_error(message: str, **context) -> NashError:
    """快速创建智能体错误"""
    return NashError(ErrorCode.AGENT_LANGGRAPH_FAILED, message, context)


def simulation_error(message: str, **context) -> NashError:
    """快速创建模拟引擎错误"""
    return NashError(ErrorCode.SIM_STEP_FAILED, message, context)


def config_error(message: str, **context) -> NashError:
    """快速创建配置错误"""
    return NashError(ErrorCode.CONFIG_INVALID_PATH, message, context)
