from typing import List, Dict, Optional, Tuple
from pydantic import BaseModel, Field


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