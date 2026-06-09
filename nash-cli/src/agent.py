from mesa import Agent
from src.interfaces import AbstractNashAgent
import random
from typing import Dict, Optional
import uuid
import logging

from src.narrative_generator import NarrativeGenerator
from src.memory_system import MemorySystem
from src.contracts import Experience, StructuredNarrative, ActionType, SimulationConfig

logger = logging.getLogger(__name__)


# ==================== 智能体类 ====================

class CitizenAgent(Agent, AbstractNashAgent):
    """
    Citizen Agent for NASH simulation.

    核心特性:
    - 规则式决策（能量阈值驱动）
    - 记忆系统增强
    - 叙事生成能力
    """
    
    _unique_id: int = -1
    
    def __init__(self, model, unique_id: int,
                 narrative_generator: Optional[NarrativeGenerator] = None,
                 memory_system: Optional[MemorySystem] = None,
                 config: Optional[SimulationConfig] = None):
        super().__init__(model)
        
        self._unique_id = unique_id
        self.narrative_generator = narrative_generator
        self.memory_system = memory_system
        self.config = config or SimulationConfig()
        
        # 核心状态
        self.energy = 50.0
        self.beliefs = {
            "authority_worship": self.random.random(),
            "promise_gratitude": self.random.random(),
            "outgroup_hostility": self.random.random(),
            "group_pride": self.random.random()
        }
        
        # 经验追踪
        self.last_experience: Optional[Experience] = None
        self.last_narrative: Optional[StructuredNarrative] = None
        
        # 统计
        self.steps_executed = 0
    
    @property
    def unique_id(self) -> int:
        return self._unique_id
        
    @unique_id.setter
    def unique_id(self, value: int):
        self._unique_id = value

    def get_energy(self) -> float:
        return self.energy

    def set_energy(self, value: float):
        self.energy = max(0.0, min(100.0, value))

    def get_beliefs(self) -> Dict[str, float]:
        return self.beliefs.copy()

    def _rule_decide(self) -> str:
        """Rule-based decision: forage when energy is low, display loyalty otherwise."""
        if self.energy < 20:
            return "forage"
        return "loyalty_display"

    def step(self) -> None:
        """
        执行一个时间步

        流程:
        1. 检索记忆（如果启用）
        2. 规则式决策
        3. 执行行动
        4. 生成经验和叙事
        5. 更新信念
        """
        if self.energy <= 0:
            return
        
        energy_before = self.energy
        
        # 1. 检索记忆
        if self.memory_system and self.config.enable_memory:
            try:
                from src.contracts import MemoryQuery
                query = MemoryQuery(
                    agent_id=self.unique_id,
                    query=f"Current beliefs: {self.beliefs}",
                    limit=min(5, self.config.memory_capacity)
                )
                self.memory_system.search(query)
            except Exception as e:
                logger.debug(f"Agent {self.unique_id} memory retrieval failed: {e}")

        # 2. 规则式决策（无需 LLM — 清晰的边界问题）
        action = self._rule_decide()

        # 3. 执行行动
        self.act(action)
        
        # 4. 生成经验记录
        energy_after = self.energy
        self._record_experience(action, energy_before, energy_after)
        
        # 5. 生成叙事（如果启用）
        if self.narrative_generator and self.config.enable_narrative:
            self._generate_narrative(action)
        
        self.steps_executed += 1

    def act(self, action: str) -> None:
        """
        执行具体行动
        
        行动类型:
        - forage: 觅食（消耗能量，获取资源）
        - loyalty_display: 展示忠诚（消耗能量，可能获得分配）
        - interact: 互动（消耗少量能量，可能改变信念）
        - move: 移动（消耗能量，改变位置）
        """
        action_costs = {
            "forage": 2.0,
            "loyalty_display": 3.0,
            "interact": 1.0,
            "move": 3.0
        }
        
        cost = action_costs.get(action, 2.0)
        self.energy -= cost
        
        # 行动效果
        if action == "forage":
            # 觅食：随机获取资源
            gain = self.random.uniform(5.0, 15.0)
            self.energy += gain
            
        elif action == "loyalty_display":
            # 忠诚展示：消耗能量展示忠诚，资源由 model.step() 统一分配
            # The cost is already deducted above; allocation happens
            # globally via model.resource_controller.distribute_resources()
            pass
        
        elif action == "interact":
            # 互动：可能改变信念
            self._update_beliefs_from_interaction()
        
        elif action == "move":
            # 移动：随机移动
            self._move_randomly()
        
        # 确保能量在有效范围
        self.energy = max(0.0, min(100.0, self.energy))
    
    def _update_beliefs_from_interaction(self) -> None:
        """互动导致的信念更新"""
        # 获取邻居
        neighbors = self.model.grid.get_neighbors(
            self.pos, moore=True, include_center=False, radius=1
        )
        
        if neighbors:
            # 随机选择一个邻居进行信念交流
            other = self.random.choice(neighbors)
            if hasattr(other, 'beliefs'):
                # 信念平均化（简化版）
                for belief in self.beliefs:
                    if belief in other.beliefs:
                        self.beliefs[belief] = (
                            self.beliefs[belief] * 0.7 + 
                            other.beliefs[belief] * 0.3
                        )
    
    def _move_randomly(self) -> None:
        """随机移动"""
        # 获取可能的位置
        possible_steps = self.model.grid.get_neighborhood(
            self.pos, moore=True, include_center=False
        )
        
        if possible_steps:
            new_pos = self.random.choice(possible_steps)
            self.model.grid.move_agent(self, new_pos)
    
    def _record_experience(self, action: str, energy_before: float, energy_after: float) -> None:
        """记录经验到记忆系统"""
        if not self.memory_system or not self.config.enable_memory:
            return
        
        try:
            from src.contracts import Experience, ExperienceType
            
            # 确定经验类型
            if action == "forage":
                exp_type = ExperienceType.ALLOCATION
                source = "environment"
            elif action in ["loyalty_display", "interact"]:
                exp_type = ExperienceType.INTERACTION
                source = f"action_{action}"
            else:
                exp_type = ExperienceType.OBSERVATION
                source = "self"
            
            experience = Experience(
                agent_id=self.unique_id,
                cycle=self.model.current_step,
                type=exp_type,
                received_amount=energy_after - energy_before,
                source=source,
                loyalty_score=self.beliefs.get("promise_gratitude", 0.5),
                location=list(self.pos) if hasattr(self, 'pos') and self.pos else [0, 0],
                energy_before=energy_before,
                energy_after=energy_after,
                event_id=str(uuid.uuid4())
            )
            
            # 存储经验
            self.memory_system.store_experience(experience, self.beliefs)
            self.last_experience = experience
            
        except Exception as e:
            logger.debug(f"Agent {self.unique_id} experience recording failed: {e}")
    
    def _generate_narrative(self, action: str) -> None:
        """生成叙事"""
        if not self.narrative_generator or not self.last_experience:
            return
        
        try:
            # 调用正确的方法名：generate_narrative(experience, beliefs)
            narrative_output = self.narrative_generator.generate_narrative(
                self.last_experience, 
                self.beliefs
            )
            
            # 从 NarrativeOutput 中提取 narrative
            narrative = narrative_output.narrative
            
            if narrative:
                self.last_narrative = narrative
                
                # 存储叙事
                if self.memory_system:
                    self.memory_system.store_narrative(narrative)
                
                # 根据叙事更新信念
                self._update_beliefs_from_narrative(narrative)
                
        except Exception as e:
            logger.debug(f"Agent {self.unique_id} narrative generation failed: {e}")
    
    def _update_beliefs_from_narrative(self, narrative: StructuredNarrative) -> None:
        """根据叙事更新信念"""
        if narrative.suggested_adjustments:
            for belief, adjustment in narrative.suggested_adjustments.items():
                if belief in self.beliefs:
                    self.beliefs[belief] = max(0.0, min(1.0, 
                        self.beliefs[belief] + adjustment * 0.1
                    ))
