from typing import List, Dict, Optional, Tuple, Any
from pydantic import BaseModel, Field
from dataclasses import dataclass, field
from enum import Enum
import uuid


# ============================================================================
# 行动/经验类型
# ============================================================================

class ActionType(str, Enum):
    FORAGE = "forage"
    LOYALTY_DISPLAY = "loyalty_display"
    INTERACT = "interact"
    MOVE = "move"


class ExperienceType(str, Enum):
    ALLOCATION = "allocation"
    INTERACTION = "interaction"
    OBSERVATION = "observation"


# ============================================================================
# 经验与叙事
# ============================================================================

@dataclass
class Experience:
    agent_id: int
    cycle: int
    type: ExperienceType
    received_amount: float
    source: str
    loyalty_score: float = 0.5
    location: List[int] = field(default_factory=lambda: [0, 0])
    energy_before: float = 0.0
    energy_after: float = 0.0
    event_id: str = field(default_factory=lambda: str(uuid.uuid4()))


@dataclass
class StructuredNarrative:
    agent_id: int
    cycle: int
    core_belief: str
    supporting_evidence: List[str] = field(default_factory=list)
    emotional_valence: float = 0.0
    confidence: float = 0.5
    suggested_adjustments: Dict[str, float] = field(default_factory=dict)
    narrative_text: str = ""
    event_id: str = ""
    counterfactual: bool = False


@dataclass
class NarrativeOutput:
    narrative: Optional[StructuredNarrative] = None
    validation_passed: bool = True
    fallback_used: bool = False
    fallback_reason: str = ""


# ============================================================================
# 记忆系统
# ============================================================================

@dataclass
class MemoryQuery:
    agent_id: int
    query: str
    limit: int = 5


@dataclass
class MemoryResult:
    experiences: List[Experience] = field(default_factory=list)
    narratives: List[StructuredNarrative] = field(default_factory=list)
    query: str = ""
    total_found: int = 0


# ============================================================================
# 仿真配置
# ============================================================================

class SimulationConfig(BaseModel):
    num_agents: int = Field(default=100, ge=10, le=10000)
    width: int = Field(default=10, ge=5)
    height: int = Field(default=10, ge=5)
    steps: int = Field(default=100, ge=1)

    # 资源
    center_pool: float = Field(default=100.0, ge=0.0)
    base_gain: float = Field(default=10.0, ge=0.0)
    metabolism: float = Field(default=2.0, ge=0.0)

    # 分配模式
    resource_allocation_mode: str = "proportional"
    monopoly_level: float = Field(default=0.0, ge=0.0, le=1.0)
    top_k_threshold: float = Field(default=0.2, ge=0.0, le=1.0)
    tournament_size: int = Field(default=5, ge=2)

    # 繁殖
    reproduction_threshold: float = Field(default=80.0, ge=1.0)
    mutation_rate: float = Field(default=0.05, ge=0.0, le=1.0)
    mutation_amount: float = Field(default=0.1, ge=0.0, le=0.5)

    # 子系统开关
    enable_memory: bool = True
    enable_narrative: bool = False
    enable_counterfactual: bool = False
    enable_validation: bool = True

    # 记忆
    memory_capacity: int = Field(default=100, ge=1)

    # 实验标记
    experiment_name: str = ""


# ============================================================================
# 世界状态
# ============================================================================

@dataclass
class WorldState:
    cycle: int
    agents: List[Dict[str, Any]] = field(default_factory=list)
    resources: List[Dict[str, Any]] = field(default_factory=list)


# ============================================================================
# 统计验证
# ============================================================================


class ValidationResult(BaseModel):
    hypothesis_supported: bool
    p_value: float = Field(..., ge=0.0, le=1.0)
    confidence_level: float = Field(..., ge=0.0, le=1.0)
    effect_size: float
    conclusion: str


class HypothesisTestData(BaseModel):
    group_a: List[float]
    group_b: List[float]
    test_type: str = "t_test"
    alpha: float = 0.05


class PhaseDiagramData(BaseModel):
    param_space: Dict[str, List[float]]
    results: Dict[str, List[float]]
    phase_boundaries: Optional[List[Tuple[float, float]]] = None


class NetworkMetrics(BaseModel):
    clustering_coefficient: float
    average_path_length: float
    density: float
    centralization_index: float
    num_components: int
    largest_component_size: int