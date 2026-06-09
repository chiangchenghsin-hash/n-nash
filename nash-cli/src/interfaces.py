from abc import ABC, abstractmethod
from typing import TypedDict, List, Dict, Any

class LoyaltySignal(TypedDict):
    agent_id: int
    hostility: float
    pride: float
    worship: float
    gratitude: float

class ResourcePackage(TypedDict):
    amount: float
    source_id: str

class AbstractNashAgent(ABC):
    """Abstract Base Class for NASH Simulation Agents"""
    
    @property
    @abstractmethod
    def unique_id(self) -> int:
        pass
        
    @abstractmethod
    def step(self) -> None:
        pass

class AbstractResourceController(ABC):
    """Abstract Base Class for Resource Allocation Logic"""
    
    @abstractmethod
    def calculate_loyalty(self, agent: AbstractNashAgent) -> float:
        """Calculate loyalty score for a given agent."""
        pass
        
    @abstractmethod
    def distribute_resources(self, agents: List[AbstractNashAgent]) -> Dict[int, ResourcePackage]:
        """Distribute resources to a list of agents based on loyalty."""
        pass
