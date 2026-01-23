"""
Node Graph representation for ComfyUI workflows.

This module provides classes for representing and manipulating ComfyUI node graphs
during automatic workflow generation.
"""

import logging
from typing import Dict, List, Any, Optional, Set
from dataclasses import dataclass, field
from collections import defaultdict

logger = logging.getLogger(__name__)


@dataclass
class Node:
    """Represents a ComfyUI node in the graph."""
    id: str
    type: str
    position: Dict[str, int] = field(default_factory=lambda: {"x": 0, "y": 0})
    properties: Dict[str, Any] = field(default_factory=dict)
    inputs: Dict[str, Any] = field(default_factory=dict)
    outputs: Dict[str, Any] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self):
        """Validate node after initialization."""
        if not self.id:
            raise ValueError("Node ID cannot be empty")
        if not self.type:
            raise ValueError("Node type cannot be empty")


@dataclass
class Connection:
    """Represents a connection between nodes."""
    source: str  # Source node ID
    target: str  # Target node ID
    source_output: int = 0  # Output slot index
    target_input: int = 0   # Input slot index
    metadata: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self):
        """Validate connection after initialization."""
        if not self.source or not self.target:
            raise ValueError("Connection source and target cannot be empty")


@dataclass
class NodeGraph:
    """Represents a complete ComfyUI node graph."""
    nodes: Dict[str, Node] = field(default_factory=dict)
    connections: List[Connection] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def add_node(self, node: Node) -> None:
        """
        Add a node to the graph.

        Args:
            node: Node to add

        Raises:
            ValueError: If node ID already exists
        """
        if node.id in self.nodes:
            raise ValueError(f"Node with ID '{node.id}' already exists")
        self.nodes[node.id] = node

    def remove_node(self, node_id: str) -> bool:
        """
        Remove a node from the graph.

        Args:
            node_id: ID of node to remove

        Returns:
            True if node was removed, False if not found
        """
        if node_id not in self.nodes:
            return False

        # Remove the node
        del self.nodes[node_id]

        # Remove all connections involving this node
        self.connections = [
            conn for conn in self.connections
            if conn.source != node_id and conn.target != node_id
        ]

        return True

    def add_connection(self, connection: Connection) -> None:
        """
        Add a connection between nodes.

        Args:
            connection: Connection to add

        Raises:
            ValueError: If connection is invalid
        """
        # Validate nodes exist
        if connection.source not in self.nodes:
            raise ValueError(f"Source node '{connection.source}' does not exist")
        if connection.target not in self.nodes:
            raise ValueError(f"Target node '{connection.target}' does not exist")

        # Check for duplicate connections
        for existing in self.connections:
            if (existing.source == connection.source and
                existing.target == connection.target and
                existing.source_output == connection.source_output and
                existing.target_input == connection.target_input):
                logger.warning(f"Duplicate connection already exists: {connection}")
                return

        self.connections.append(connection)

    def remove_connection(self, source: str, target: str,
                         source_output: int = 0, target_input: int = 0) -> bool:
        """
        Remove a connection between nodes.

        Args:
            source: Source node ID
            target: Target node ID
            source_output: Source output slot
            target_input: Target input slot

        Returns:
            True if connection was removed
        """
        for i, conn in enumerate(self.connections):
            if (conn.source == source and conn.target == target and
                conn.source_output == source_output and conn.target_input == target_input):
                del self.connections[i]
                return True
        return False

    def get_node_connections(self, node_id: str) -> Dict[str, List[Connection]]:
        """
        Get all connections for a specific node.

        Args:
            node_id: Node ID to query

        Returns:
            Dict with 'incoming' and 'outgoing' connection lists
        """
        incoming = []
        outgoing = []

        for conn in self.connections:
            if conn.target == node_id:
                incoming.append(conn)
            if conn.source == node_id:
                outgoing.append(conn)

        return {
            "incoming": incoming,
            "outgoing": outgoing
        }

    def get_connected_nodes(self, node_id: str) -> Set[str]:
        """
        Get all nodes connected to the specified node.

        Args:
            node_id: Node ID to query

        Returns:
            Set of connected node IDs
        """
        connected = set()
        for conn in self.connections:
            if conn.source == node_id:
                connected.add(conn.target)
            if conn.target == node_id:
                connected.add(conn.source)
        return connected

    def validate_graph(self) -> Dict[str, Any]:
        """
        Validate the graph structure.

        Returns:
            Dict with 'valid' boolean and 'errors' list
        """
        errors = []

        # Check for orphaned connections
        node_ids = set(self.nodes.keys())
        for conn in self.connections:
            if conn.source not in node_ids:
                errors.append(f"Connection references non-existent source node: {conn.source}")
            if conn.target not in node_ids:
                errors.append(f"Connection references non-existent target node: {conn.target}")

        # Check for cycles (simplified check)
        if self._has_cycles():
            errors.append("Graph contains cycles")

        # Check for disconnected components
        components = self._find_components()
        if len(components) > 1:
            logger.warning(f"Graph has {len(components)} disconnected components")

        return {
            "valid": len(errors) == 0,
            "errors": errors,
            "warnings": []  # Could add warnings here
        }

    def _has_cycles(self) -> bool:
        """Check if the graph has cycles using DFS."""
        visited = set()
        rec_stack = set()

        def dfs(node_id: str) -> bool:
            visited.add(node_id)
            rec_stack.add(node_id)

            for conn in self.connections:
                if conn.source == node_id:
                    neighbor = conn.target
                    if neighbor not in visited:
                        if dfs(neighbor):
                            return True
                    elif neighbor in rec_stack:
                        return True

            rec_stack.remove(node_id)
            return False

        for node_id in self.nodes:
            if node_id not in visited:
                if dfs(node_id):
                    return True

        return False

    def _find_components(self) -> List[Set[str]]:
        """Find disconnected components in the graph."""
        visited = set()
        components = []

        def dfs_component(node_id: str, component: Set[str]):
            visited.add(node_id)
            component.add(node_id)

            for neighbor in self.get_connected_nodes(node_id):
                if neighbor not in visited:
                    dfs_component(neighbor, component)

        for node_id in self.nodes:
            if node_id not in visited:
                component = set()
                dfs_component(node_id, component)
                components.append(component)

        return components

    def get_topological_order(self) -> List[str]:
        """
        Get nodes in topological order for execution.

        Returns:
            List of node IDs in execution order

        Raises:
            ValueError: If graph has cycles
        """
        if self._has_cycles():
            raise ValueError("Cannot get topological order: graph has cycles")

        # Kahn's algorithm
        in_degree = defaultdict(int)
        for conn in self.connections:
            in_degree[conn.target] += 1

        # Nodes with no incoming connections
        queue = [node_id for node_id in self.nodes if in_degree[node_id] == 0]
        result = []

        while queue:
            node_id = queue.pop(0)
            result.append(node_id)

            # Reduce in-degree of neighbors
            for conn in self.connections:
                if conn.source == node_id:
                    in_degree[conn.target] -= 1
                    if in_degree[conn.target] == 0:
                        queue.append(conn.target)

        if len(result) != len(self.nodes):
            raise ValueError("Topological sort failed: not all nodes included")

        return result

    def clone(self) -> 'NodeGraph':
        """
        Create a deep copy of the graph.

        Returns:
            New NodeGraph instance
        """
        import copy
        return copy.deepcopy(self)

    def to_dict(self) -> Dict[str, Any]:
        """Convert graph to dictionary representation."""
        return {
            "nodes": {
                node_id: {
                    "id": node.id,
                    "type": node.type,
                    "position": node.position,
                    "properties": node.properties,
                    "inputs": node.inputs,
                    "outputs": node.outputs,
                    "metadata": node.metadata
                }
                for node_id, node in self.nodes.items()
            },
            "connections": [
                {
                    "source": conn.source,
                    "target": conn.target,
                    "source_output": conn.source_output,
                    "target_input": conn.target_input,
                    "metadata": conn.metadata
                }
                for conn in self.connections
            ],
            "metadata": self.metadata
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'NodeGraph':
        """Create graph from dictionary representation."""
        graph = cls(metadata=data.get("metadata", {}))

        # Add nodes
        for node_data in data.get("nodes", {}).values():
            node = Node(
                id=node_data["id"],
                type=node_data["type"],
                position=node_data.get("position", {"x": 0, "y": 0}),
                properties=node_data.get("properties", {}),
                inputs=node_data.get("inputs", {}),
                outputs=node_data.get("outputs", {}),
                metadata=node_data.get("metadata", {})
            )
            graph.add_node(node)

        # Add connections
        for conn_data in data.get("connections", []):
            connection = Connection(
                source=conn_data["source"],
                target=conn_data["target"],
                source_output=conn_data.get("source_output", 0),
                target_input=conn_data.get("target_input", 0),
                metadata=conn_data.get("metadata", {})
            )
            graph.add_connection(connection)

        return graph

    def __len__(self) -> int:
        """Return number of nodes in graph."""
        return len(self.nodes)

    def __contains__(self, node_id: str) -> bool:
        """Check if node exists in graph."""
        return node_id in self.nodes