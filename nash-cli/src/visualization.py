from typing import List, Dict, Any, Optional, Tuple
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.animation as animation
from matplotlib.figure import Figure
import networkx as nx
import logging

from src.contracts import PhaseDiagramData, NetworkMetrics

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class BeliefVisualizer:
    def __init__(self, figsize: Tuple[int, int] = (12, 8)):
        self.figsize = figsize

    def visualize_belief_evolution(self, beliefs_history: List[Dict[str, float]], 
                                   save_path: Optional[str] = None) -> Figure:
        try:
            fig, axes = plt.subplots(2, 2, figsize=self.figsize)
            fig.suptitle('Belief Evolution Over Time', fontsize=16)
            
            belief_types = ['authority_worship', 'promise_gratitude', 
                          'outgroup_hostility', 'group_pride']
            
            for idx, belief_type in enumerate(belief_types):
                ax = axes[idx // 2, idx % 2]
                
                values = [b.get(belief_type, 0.0) for b in beliefs_history]
                cycles = range(len(values))
                
                ax.plot(cycles, values, linewidth=2, label=belief_type)
                ax.set_xlabel('Cycle')
                ax.set_ylabel('Belief Value')
                ax.set_title(belief_type.replace('_', ' ').title())
                ax.set_ylim([0, 1])
                ax.grid(True, alpha=0.3)
                ax.legend()
            
            plt.tight_layout()
            
            if save_path:
                plt.savefig(save_path, dpi=300, bbox_inches='tight')
                logger.info(f"Saved belief evolution plot to {save_path}")
            
            return fig

        except Exception as e:
            logger.error(f"Belief evolution visualization failed: {e}")
            return None

    def visualize_belief_distribution(self, beliefs: List[Dict[str, float]], 
                                      cycle: int,
                                      save_path: Optional[str] = None) -> Figure:
        try:
            fig, axes = plt.subplots(2, 2, figsize=self.figsize)
            fig.suptitle(f'Belief Distribution at Cycle {cycle}', fontsize=16)
            
            belief_types = ['authority_worship', 'promise_gratitude', 
                          'outgroup_hostility', 'group_pride']
            
            for idx, belief_type in enumerate(belief_types):
                ax = axes[idx // 2, idx % 2]
                
                values = [b.get(belief_type, 0.0) for b in beliefs]
                
                ax.hist(values, bins=20, alpha=0.7, edgecolor='black')
                ax.axvline(np.mean(values), color='red', linestyle='--', 
                          label=f'Mean: {np.mean(values):.3f}')
                ax.set_xlabel('Belief Value')
                ax.set_ylabel('Frequency')
                ax.set_title(belief_type.replace('_', ' ').title())
                ax.set_xlim([0, 1])
                ax.legend()
            
            plt.tight_layout()
            
            if save_path:
                plt.savefig(save_path, dpi=300, bbox_inches='tight')
                logger.info(f"Saved belief distribution plot to {save_path}")
            
            return fig

        except Exception as e:
            logger.error(f"Belief distribution visualization failed: {e}")
            return None

    def visualize_belief_heatmap(self, beliefs_history: List[List[Dict[str, float]]], 
                                 belief_type: str,
                                 save_path: Optional[str] = None) -> Figure:
        try:
            num_cycles = len(beliefs_history)
            num_agents = len(beliefs_history[0]) if beliefs_history else 0
            
            matrix = np.zeros((num_agents, num_cycles))
            
            for cycle_idx, cycle_beliefs in enumerate(beliefs_history):
                for agent_idx, beliefs in enumerate(cycle_beliefs):
                    matrix[agent_idx, cycle_idx] = beliefs.get(belief_type, 0.0)
            
            fig, ax = plt.subplots(figsize=(max(12, num_cycles * 0.3), max(8, num_agents * 0.1)))
            
            im = ax.imshow(matrix, aspect='auto', cmap='RdYlBu_r', 
                          vmin=0, vmax=1, interpolation='nearest')
            
            ax.set_xlabel('Cycle')
            ax.set_ylabel('Agent ID')
            ax.set_title(f'{belief_type.replace("_", " ").title()} Heatmap')
            
            cbar = plt.colorbar(im, ax=ax)
            cbar.set_label('Belief Value')
            
            plt.tight_layout()
            
            if save_path:
                plt.savefig(save_path, dpi=300, bbox_inches='tight')
                logger.info(f"Saved belief heatmap to {save_path}")
            
            return fig

        except Exception as e:
            logger.error(f"Belief heatmap visualization failed: {e}")
            return None


class PhaseDiagramGenerator:
    def __init__(self, figsize: Tuple[int, int] = (12, 10)):
        self.figsize = figsize

    def generate_phase_diagram(self, data: PhaseDiagramData, 
                               save_path: Optional[str] = None) -> Figure:
        try:
            param_names = list(data.param_space.keys())
            
            if len(param_names) != 2:
                logger.error("Phase diagram requires exactly 2 parameters")
                return None
            
            param1_name, param2_name = param_names
            param1_values = data.param_space[param1_name]
            param2_values = data.param_space[param2_name]
            
            result_name = list(data.results.keys())[0]
            results = data.results[result_name]
            
            results_matrix = np.array(results).reshape(
                len(param2_values), len(param1_values)
            )
            
            fig, ax = plt.subplots(figsize=self.figsize)
            
            im = ax.imshow(results_matrix, aspect='auto', cmap='viridis',
                          extent=[param1_values[0], param1_values[-1],
                                 param2_values[0], param2_values[-1]],
                          origin='lower', interpolation='bicubic')
            
            cbar = plt.colorbar(im, ax=ax)
            cbar.set_label(result_name)
            
            ax.set_xlabel(param1_name)
            ax.set_ylabel(param2_name)
            ax.set_title('Phase Diagram')
            
            if data.phase_boundaries:
                for boundary in data.phase_boundaries:
                    ax.axvline(x=boundary[0], color='red', linestyle='--', alpha=0.7)
                    ax.axhline(y=boundary[1], color='red', linestyle='--', alpha=0.7)
            
            plt.tight_layout()
            
            if save_path:
                plt.savefig(save_path, dpi=300, bbox_inches='tight')
                logger.info(f"Saved phase diagram to {save_path}")
            
            return fig

        except Exception as e:
            logger.error(f"Phase diagram generation failed: {e}")
            return None

    def generate_3d_phase_diagram(self, data: PhaseDiagramData,
                                   save_path: Optional[str] = None) -> Figure:
        try:
            from mpl_toolkits.mplot3d import Axes3D
            
            param_names = list(data.param_space.keys())
            
            if len(param_names) != 2:
                logger.error("3D phase diagram requires exactly 2 parameters")
                return None
            
            param1_name, param2_name = param_names
            param1_values = data.param_space[param1_name]
            param2_values = data.param_space[param2_name]
            
            result_name = list(data.results.keys())[0]
            results = data.results[result_name]
            
            X, Y = np.meshgrid(param1_values, param2_values)
            Z = np.array(results).reshape(len(param2_values), len(param1_values))
            
            fig = plt.figure(figsize=self.figsize)
            ax = fig.add_subplot(111, projection='3d')
            
            surf = ax.plot_surface(X, Y, Z, cmap='viridis', alpha=0.8)
            
            ax.set_xlabel(param1_name)
            ax.set_ylabel(param2_name)
            ax.set_zlabel(result_name)
            ax.set_title('3D Phase Diagram')
            
            fig.colorbar(surf, ax=ax, shrink=0.5, aspect=5)
            
            if save_path:
                plt.savefig(save_path, dpi=300, bbox_inches='tight')
                logger.info(f"Saved 3D phase diagram to {save_path}")
            
            return fig

        except Exception as e:
            logger.error(f"3D phase diagram generation failed: {e}")
            return None


class NetworkAnalyzer:
    def __init__(self):
        self.graph = nx.Graph()

    def build_interaction_network(self, interactions: List[Dict[str, Any]]) -> nx.Graph:
        try:
            self.graph = nx.Graph()
            
            for interaction in interactions:
                agent_a = interaction.get('agent_a')
                agent_b = interaction.get('agent_b')
                weight = interaction.get('weight', 1.0)
                
                if agent_a is not None and agent_b is not None:
                    if self.graph.has_edge(agent_a, agent_b):
                        self.graph[agent_a][agent_b]['weight'] += weight
                    else:
                        self.graph.add_edge(agent_a, agent_b, weight=weight)
            
            logger.info(f"Built network with {self.graph.number_of_nodes()} nodes "
                       f"and {self.graph.number_of_edges()} edges")
            
            return self.graph

        except Exception as e:
            logger.error(f"Network building failed: {e}")
            return nx.Graph()

    def compute_metrics(self) -> NetworkMetrics:
        try:
            if self.graph.number_of_nodes() == 0:
                return NetworkMetrics(
                    clustering_coefficient=0.0,
                    average_path_length=0.0,
                    density=0.0,
                    centralization_index=0.0,
                    num_components=0,
                    largest_component_size=0
                )
            
            clustering = nx.average_clustering(self.graph, weight='weight')
            density = nx.density(self.graph)
            
            if nx.is_connected(self.graph):
                avg_path_length = nx.average_shortest_path_length(self.graph, weight='weight')
                num_components = 1
                largest_component_size = self.graph.number_of_nodes()
            else:
                components = list(nx.connected_components(self.graph))
                num_components = len(components)
                largest_component = max(components, key=len)
                largest_component_size = len(largest_component)
                avg_path_length = 0.0
            
            centralization = self._compute_centralization()
            
            return NetworkMetrics(
                clustering_coefficient=clustering,
                average_path_length=avg_path_length,
                density=density,
                centralization_index=centralization,
                num_components=num_components,
                largest_component_size=largest_component_size
            )

        except Exception as e:
            logger.error(f"Metrics computation failed: {e}")
            return NetworkMetrics(
                clustering_coefficient=0.0,
                average_path_length=0.0,
                density=0.0,
                centralization_index=0.0,
                num_components=0,
                largest_component_size=0
            )

    def _compute_centralization(self) -> float:
        try:
            if self.graph.number_of_nodes() == 0:
                return 0.0
            
            degrees = dict(self.graph.degree(weight='weight'))
            max_degree = max(degrees.values()) if degrees else 0
            
            if max_degree == 0:
                return 0.0
            
            n = self.graph.number_of_nodes()
            sum_diff = sum(max_degree - d for d in degrees.values())
            
            max_possible = (n - 1) * max_degree
            
            if max_possible == 0:
                return 0.0
            
            return sum_diff / max_possible

        except Exception as e:
            logger.error(f"Centralization computation failed: {e}")
            return 0.0

    def visualize_network(self, save_path: Optional[str] = None,
                         node_color: Optional[str] = None) -> Figure:
        try:
            if self.graph.number_of_nodes() == 0:
                logger.warning("Cannot visualize empty network")
                return None
            
            fig, ax = plt.subplots(figsize=(12, 10))
            
            pos = nx.spring_layout(self.graph, weight='weight', k=0.3, iterations=50)
            
            if node_color:
                node_values = [self.graph.nodes[n].get(node_color, 0.5) 
                              for n in self.graph.nodes()]
                cmap = plt.cm.RdYlBu_r
            else:
                node_values = None
                cmap = plt.cm.viridis
            
            nx.draw_networkx_nodes(self.graph, pos, node_size=50,
                                  node_color=node_values, cmap=cmap,
                                  alpha=0.8, ax=ax)
            
            nx.draw_networkx_edges(self.graph, pos, width=0.5,
                                  alpha=0.5, ax=ax)
            
            if self.graph.number_of_nodes() <= 50:
                nx.draw_networkx_labels(self.graph, pos, font_size=8, ax=ax)
            
            ax.set_title('Social Network Topology')
            ax.axis('off')
            
            if node_color:
                cbar = plt.colorbar(plt.cm.ScalarMappable(cmap=cmap), ax=ax)
                cbar.set_label(node_color)
            
            plt.tight_layout()
            
            if save_path:
                plt.savefig(save_path, dpi=300, bbox_inches='tight')
                logger.info(f"Saved network visualization to {save_path}")
            
            return fig

        except Exception as e:
            logger.error(f"Network visualization failed: {e}")
            return None

    def visualize_degree_distribution(self, save_path: Optional[str] = None) -> Figure:
        try:
            if self.graph.number_of_nodes() == 0:
                logger.warning("Cannot visualize degree distribution of empty network")
                return None
            
            degrees = [d for n, d in self.graph.degree(weight='weight')]
            
            fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(14, 6))
            
            ax1.hist(degrees, bins=30, alpha=0.7, edgecolor='black')
            ax1.set_xlabel('Degree')
            ax1.set_ylabel('Frequency')
            ax1.set_title('Degree Distribution')
            ax1.grid(True, alpha=0.3)
            
            sorted_degrees = sorted(degrees, reverse=True)
            ax2.loglog(range(1, len(sorted_degrees) + 1), sorted_degrees, 'o-')
            ax2.set_xlabel('Rank')
            ax2.set_ylabel('Degree')
            ax2.set_title('Degree Distribution (Log-Log)')
            ax2.grid(True, alpha=0.3)
            
            plt.tight_layout()
            
            if save_path:
                plt.savefig(save_path, dpi=300, bbox_inches='tight')
                logger.info(f"Saved degree distribution to {save_path}")
            
            return fig

        except Exception as e:
            logger.error(f"Degree distribution visualization failed: {e}")
            return None

    def detect_communities(self) -> List[Dict[str, Any]]:
        try:
            if self.graph.number_of_nodes() == 0:
                return []
            
            communities = list(nx.community.greedy_modularity_communities(self.graph))
            
            community_info = []
            for idx, community in enumerate(communities):
                community_info.append({
                    'community_id': idx,
                    'size': len(community),
                    'members': list(community)
                })
            
            logger.info(f"Detected {len(communities)} communities")
            return community_info

        except Exception as e:
            logger.error(f"Community detection failed: {e}")
            return []
