from mesa import Model
from mesa.space import MultiGrid
from mesa.datacollection import DataCollector
from src.agent import CitizenAgent
from src.resource_controller import ResourceController
from src.advanced_resource_controller import AdvancedResourceController, ResourceAllocationMode
from src.narrative_generator import NarrativeGenerator
from src.memory_system import MemorySystem
from src.statistical_validator import StatisticalValidator
from src.counterfactual_generator import CounterfactualGenerator
from src.config_manager import ConfigManager
from src.contracts import SimulationConfig, WorldState, ValidationResult
import numpy as np
import uuid
from datetime import datetime
from typing import Optional, Dict, Any, List


def compute_gini(model):
    agent_energies = [agent.energy for agent in model.agents]
    x = sorted(agent_energies)
    N = len(agent_energies)
    if N == 0: return 0.0
    if sum(x) == 0: return 0.0
    B = sum(xi * (N-i) for i,xi in enumerate(x)) / (N*sum(x))
    return 1 + (1/N) - 2*B


def compute_mean_hostility(model):
    """计算所有 agent 的平均敌意值"""
    try:
        # 使用 .get() 避免 KeyError，如果 hostility 不存在则返回 0.0
        hostility_values = [a.beliefs.get("hostility", 0.0) for a in model.agents]
        return np.mean(hostility_values)
    except Exception as e:
        print(f"Error computing mean hostility: {e}")
        return 0.0


class NashModel(Model):
    """
    NASH Simulation Model with integrated narrative generation, memory system,
    and statistical validation.
    """
    def __init__(self, config: Optional[SimulationConfig] = None,
                 llm_client: Optional[Any] = None):
        super().__init__()

        # Load configuration
        self.config = config or SimulationConfig()
        self.config_manager = ConfigManager()
        self.config_manager.config = self.config

        # Initialize grid
        self.grid = MultiGrid(self.config.width, self.config.height, torus=True)
        self.running = True

        # Initialize subsystems (resource controller, narrative, memory, validator)
        self._init_subsystems(llm_client)

        # Initialize agents and data collector
        self._init_agents_and_collector()

        # Experiment tracking
        self.experiment_id = str(uuid.uuid4())
        self.start_time = datetime.now()
        self.validation_result: Optional[ValidationResult] = None

    @property
    def current_step(self) -> int:
        """Return the current step count (delegates to Mesa's built-in step counter)."""
        return self.steps

    def _init_subsystems(self, llm_client: Optional[Any]) -> None:
        """Initialize resource controller, narrative generator, memory system,
        and statistical validator based on configuration."""
        # Initialize Resource Controller
        resource_mode_str = getattr(self.config, 'resource_allocation_mode', 'proportional')
        try:
            resource_mode = ResourceAllocationMode(resource_mode_str)
        except ValueError:
            resource_mode = ResourceAllocationMode.PROPORTIONAL

        self.resource_controller = AdvancedResourceController(
            mode=resource_mode,
            center_pool=self.config.center_pool,
            monopoly_level=getattr(self.config, 'monopoly_level', 0.0),
            top_k_threshold=getattr(self.config, 'top_k_threshold', 0.2),
            tournament_size=getattr(self.config, 'tournament_size', 5)
        )

        # Initialize Narrative Generator (if LLM client provided)
        self.narrative_generator = None
        self.counterfactual_generator = None
        if llm_client and self.config.enable_narrative:
            self.narrative_generator = NarrativeGenerator(llm_client)
            if self.config.enable_counterfactual:
                self.counterfactual_generator = CounterfactualGenerator(
                    self.narrative_generator
                )

        # Initialize Memory System (if enabled)
        self.memory_system = None
        if self.config.enable_memory:
            self.memory_system = MemorySystem(
                persist_directory="./data/memory"
            )

        # Initialize Statistical Validator (if enabled)
        self.statistical_validator = None
        if self.config.enable_validation:
            self.statistical_validator = StatisticalValidator(alpha=0.05)

    def _init_agents_and_collector(self) -> None:
        """Create agents and set up the data collector."""
        # Initialize agents
        for i in range(self.config.num_agents):
            a = CitizenAgent(
                self,
                unique_id=i,
                narrative_generator=self.narrative_generator,
                memory_system=self.memory_system,
                config=self.config
            )
            x = self.random.randrange(self.grid.width)
            y = self.random.randrange(self.grid.height)
            self.grid.place_agent(a, (x, y))

        # Initialize Data Collector
        self.datacollector = DataCollector(
            model_reporters={
                "Gini": compute_gini,
                "Mean Hostility": compute_mean_hostility
            },
            agent_reporters={
                "Energy": "energy",
                "Authority Worship": lambda a: a.beliefs.get("authority_worship", 0.0),
                "Promise Gratitude": lambda a: a.beliefs.get("promise_gratitude", 0.0),
                "Outgroup Hostility": lambda a: a.beliefs.get("hostility", 0.0),
                "Group Pride": lambda a: a.beliefs.get("pride", 0.0)
            }
        )

    def step(self):
        """Advance the model by one step."""
        self.steps += 1

        # 1. Agents step (Perceive -> Decide -> Act -> Generate Experience -> Narrative -> Update Beliefs)
        self.agents.shuffle_do("step")
        
        # 2. Resource Allocation (only if there are living agents)
        living_agents = [a for a in self.agents if a.energy > 0]
        
        if living_agents:
            distribution = self.resource_controller.distribute_resources(living_agents)
            
            # Apply distribution
            agent_map = {a.unique_id: a for a in self.agents}
            for uid, pkg in distribution.items():
                if uid in agent_map and agent_map[uid].energy > 0:
                    agent_map[uid].energy += pkg["amount"]
        
        # 3. Collect Data
        self.datacollector.collect(self)
        
        # 4. Remove dead agents (energy <= 0)
        dead_agents = [a for a in self.agents if a.energy <= 0]
        for agent in dead_agents:
            self.grid.remove_agent(agent)
            self.agents.remove(agent)
        
        # 5. Handle reproduction (energy >= reproduction_threshold)
        self._handle_reproduction()

    def _handle_reproduction(self):
        """Handle agent reproduction based on energy threshold."""
        new_agents = []
        
        for agent in list(self.agents):
            if agent.energy >= self.config.reproduction_threshold:
                # Create offspring
                offspring = CitizenAgent(
                    self,
                    unique_id=self.config.num_agents + len(new_agents),
                    narrative_generator=self.narrative_generator,
                    memory_system=self.memory_system,
                    config=self.config
                )
                
                # Inherit beliefs with mutation
                for belief, value in agent.beliefs.items():
                    if self.random.random() < self.config.mutation_rate:
                        mutation = self.random.uniform(-self.config.mutation_amount, 
                                                     self.config.mutation_amount)
                        offspring.beliefs[belief] = max(0.0, min(1.0, value + mutation))
                    else:
                        offspring.beliefs[belief] = value
                
                # Place offspring near parent
                x, y = agent.pos
                dx = self.random.randint(-2, 2)
                dy = self.random.randint(-2, 2)
                new_x = (x + dx) % self.grid.width
                new_y = (y + dy) % self.grid.height
                self.grid.place_agent(offspring, (new_x, new_y))
                
                # Reduce parent energy
                agent.energy /= 2
                
                new_agents.append(offspring)
        
        # Add new agents to the model
        for agent in new_agents:
            self.agents.add(agent)

    def get_world_state(self) -> WorldState:
        """Get the current world state."""
        agent_infos = []
        for agent in self.agents:
            agent_infos.append({
                "id": agent.unique_id,
                "position": list(agent.pos) if agent.pos else [],
                "energy": agent.energy
            })
        
        resource_infos = []
        for cell_contents, coord in self.grid.coord_iter():
            x, y = coord
            for obj in cell_contents:
                if hasattr(obj, 'type') and obj.type == 'resource':
                    resource_infos.append({
                        "position": [x, y],
                        "type": obj.type,
                        "amount": obj.amount
                    })
        
        return WorldState(
            cycle=self.steps,
            agents=agent_infos,
            resources=resource_infos
        )

    def validate_hypothesis(self, baseline_gini: float, 
                            baseline_hostility: float) -> ValidationResult:
        """Validate the hypothesis using statistical tests."""
        if not self.statistical_validator:
            return ValidationResult(
                hypothesis_supported=False,
                p_value=1.0,
                confidence_level=0.0,
                effect_size=0.0,
                conclusion="Statistical validator not enabled"
            )
        
        # Get final metrics
        model_data = self.datacollector.get_model_vars_dataframe()
        final_gini = model_data['Gini'].iloc[-1]
        final_hostility = model_data['Mean Hostility'].iloc[-1]
        
        # Compare to baseline
        gini_comparison = self.statistical_validator.compare_to_baseline(
            [final_gini], [baseline_gini]
        )
        
        hostility_comparison = self.statistical_validator.compare_to_baseline(
            [final_hostility], [baseline_hostility]
        )
        
        # Determine if hypothesis is supported
        # Hypothesis: Central resource allocation increases inequality and hostility
        gini_supported = gini_comparison['significant'] and gini_comparison['difference'] > 0
        hostility_supported = hostility_comparison['significant'] and hostility_comparison['difference'] > 0
        
        hypothesis_supported = gini_supported and hostility_supported
        
        self.validation_result = ValidationResult(
            hypothesis_supported=hypothesis_supported,
            p_value=min(gini_comparison['p_value'], hostility_comparison['p_value']),
            confidence_level=max(gini_comparison['confidence_level'], 
                              hostility_comparison['confidence_level']),
            effect_size=(gini_comparison['effect_size'] + hostility_comparison['effect_size']) / 2,
            conclusion=f"Hypothesis {'supported' if hypothesis_supported else 'not supported'}. "
                      f"Gini: {final_gini:.3f} vs {baseline_gini:.3f}, "
                      f"Hostility: {final_hostility:.3f} vs {baseline_hostility:.3f}"
        )
        
        return self.validation_result

    def get_agent_beliefs(self) -> List[Dict[str, float]]:
        """Get all agent beliefs."""
        return [agent.beliefs.copy() for agent in self.agents]

    def get_agent_energies(self) -> List[float]:
        """Get all agent energies."""
        return [agent.energy for agent in self.agents]

    def get_memory_stats(self) -> Dict[str, Any]:
        """Get memory system statistics."""
        if not self.memory_system:
            return {"enabled": False}
        
        return {
            "enabled": True,
            **self.memory_system.get_stats()
        }

    def export_data(self, output_dir: str = "./data"):
        """Export simulation data to files."""
        import os
        os.makedirs(output_dir, exist_ok=True)
        
        # Export model data
        model_data = self.datacollector.get_model_vars_dataframe()
        model_data.to_csv(f"{output_dir}/model_data.csv", index=False)
        
        # Export agent data
        agent_data = self.datacollector.get_agent_vars_dataframe()
        agent_data.to_csv(f"{output_dir}/agent_data.csv", index=False)
        
        # Export validation result if available
        if self.validation_result:
            with open(f"{output_dir}/validation_result.json", 'w') as f:
                import json
                json.dump(self.validation_result.model_dump(), f, indent=2)
        
        # Export metadata
        metadata = {
            "experiment_id": self.experiment_id,
            "start_time": self.start_time.isoformat(),
            "config": self.config.model_dump(),
            "total_steps": self.steps,
            "final_gini": model_data['Gini'].iloc[-1] if not model_data.empty else 0.0,
            "final_hostility": model_data['Mean Hostility'].iloc[-1] if not model_data.empty else 0.0,
            "final_num_agents": len(self.agents),
            "memory_stats": self.get_memory_stats()
        }
        
        with open(f"{output_dir}/metadata.json", 'w') as f:
            json.dump(metadata, f, indent=2)
