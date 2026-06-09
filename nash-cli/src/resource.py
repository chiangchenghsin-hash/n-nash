from typing import List, Dict
from src.interfaces import AbstractResourceController, AbstractNashAgent, ResourcePackage

class ResourceController(AbstractResourceController):
    """
    Manages resource distribution based on agent loyalty.
    """
    def __init__(self, num_allocators: int = 1, center_pool: float = 100.0):
        self.num_allocators = num_allocators
        self.center_pool = center_pool
        # Default weights for the 4 beliefs
        self.weights = {
            "hostility": 0.25,
            "pride": 0.25,
            "worship": 0.25,
            "gratitude": 0.25
        }
        
    def calculate_loyalty(self, agent: AbstractNashAgent) -> float:
        """
        Calculate loyalty score as weighted sum of beliefs.
        Assumes agent has 'beliefs' attribute (Dict[str, float]).
        """
        if not hasattr(agent, "beliefs"):
            return 0.0
            
        score = 0.0
        for key, weight in self.weights.items():
            score += agent.beliefs.get(key, 0.0) * weight
        return score
        
    def distribute_resources(self, agents: List[AbstractNashAgent]) -> Dict[int, ResourcePackage]:
        """
        Distribute center_pool to agents proportional to their loyalty.
        """
        if not agents:
            return {}
            
        # Calculate scores
        scores = {agent.unique_id: self.calculate_loyalty(agent) for agent in agents}
        total_score = sum(scores.values())
        
        distribution = {}
        for agent in agents:
            uid = agent.unique_id
            score = scores[uid]
            
            if total_score > 0:
                amount = (score / total_score) * self.center_pool
            else:
                amount = 0.0
                
            distribution[uid] = {
                "amount": amount,
                "source_id": "allocator_0" # Simplified for single allocator
            }
            
        return distribution
