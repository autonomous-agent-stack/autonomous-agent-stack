"""Local Graph Memory for Micro-GraphRAG.

Lightweight knowledge graph implementation using NetworkX + SQLite.
No heavy graph databases (Neo4j) - pure Python solution.
"""

from __future__ import annotations

import json
import sqlite3
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple
import logging

try:
    import networkx as nx
    NETWORKX_AVAILABLE = True
except ImportError:
    NETWORKX_AVAILABLE = False
    nx = None

logger = logging.getLogger(__name__)


# ========================================================================
# Fallback Graph Structure (when NetworkX not available)
# ========================================================================

class _SimpleDiGraph:
    """Simple directed graph implementation for fallback when NetworkX unavailable."""
    
    def __init__(self):
        self._nodes: Set[str] = set()
        self._edges: Dict[str, List[Tuple[str, str, Dict[str, Any]]]] = {}  # src -> [(dst, predicate, props)]
        self._reverse_edges: Dict[str, List[str]] = {}  # dst -> [src]
    
    def __contains__(self, node: str) -> bool:
        """Support 'in' operator."""
        return node in self._nodes
    
    def add_node(self, node_id: str, **kwargs) -> None:
        self._nodes.add(node_id)
    
    def add_edge(self, src: str, dst: str, predicate: str = "", **kwargs) -> None:
        self._nodes.add(src)
        self._nodes.add(dst)
        
        if src not in self._edges:
            self._edges[src] = []
        self._edges[src].append((dst, predicate, kwargs))
        
        if dst not in self._reverse_edges:
            self._reverse_edges[dst] = []
        self._reverse_edges[dst].append(src)
    
    def remove_edge(self, src: str, dst: str) -> None:
        if src in self._edges:
            self._edges[src] = [(d, p, props) for d, p, props in self._edges[src] if d != dst]
        if dst in self._reverse_edges:
            self._reverse_edges[dst] = [s for s in self._reverse_edges[dst] if s != src]
    
    def has_edge(self, src: str, dst: str) -> bool:
        if src not in self._edges:
            return False
        return any(d == dst for d, _, _ in self._edges[src])
    
    def successors(self, node: str) -> List[str]:
        if node not in self._edges:
            return []
        return [dst for dst, _, _ in self._edges[node]]
    
    def predecessors(self, node: str) -> List[str]:
        return self._reverse_edges.get(node, [])
    
    def clear(self) -> None:
        self._nodes.clear()
        self._edges.clear()
        self._reverse_edges.clear()


@dataclass
class GraphNode:
    """Knowledge graph node."""
    
    id: str
    entity_type: str = "entity"
    properties: Dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    
    def to_dict(self) -> Dict[str, Any]:
        """Serialize to dictionary."""
        return {
            "id": self.id,
            "entity_type": self.entity_type,
            "properties": self.properties,
            "created_at": self.created_at.isoformat(),
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> GraphNode:
        """Deserialize from dictionary."""
        return cls(
            id=data["id"],
            entity_type=data.get("entity_type", "entity"),
            properties=data.get("properties", {}),
            created_at=datetime.fromisoformat(data["created_at"]),
        )


@dataclass
class GraphEdge:
    """Knowledge graph edge (triple)."""
    
    subject: str
    predicate: str
    obj: str  # 'object' is a reserved word in Python
    properties: Dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    
    def to_dict(self) -> Dict[str, Any]:
        """Serialize to dictionary."""
        return {
            "subject": self.subject,
            "predicate": self.predicate,
            "object": self.obj,
            "properties": self.properties,
            "created_at": self.created_at.isoformat(),
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> GraphEdge:
        """Deserialize from dictionary."""
        return cls(
            subject=data["subject"],
            predicate=data["predicate"],
            obj=data["object"],
            properties=data.get("properties", {}),
            created_at=datetime.fromisoformat(data["created_at"]),
        )
    
    def as_triple(self) -> Tuple[str, str, str]:
        """Return as (subject, predicate, object) tuple."""
        return (self.subject, self.predicate, self.obj)


class LocalGraphMemory:
    """Lightweight local knowledge graph with NetworkX + SQLite.
    
    Features:
    - Triple store: (subject, predicate, object)
    - Subgraph queries with depth traversal
    - SQLite persistence (survives restart)
    - NetworkX for graph algorithms
    - No heavy dependencies (no Neo4j)
    
    Usage:
        graph = LocalGraphMemory()
        graph.add_triple("玛露", "HAS_PRODUCT", "6g罐装遮瑕膏")
        graph.add_triple("6g罐装遮瑕膏", "HAS_FEATURE", "遮瑕力强")
        
        # Query subgraph
        subgraph = graph.query_subgraph("玛露", depth=2)
    """
    
    def __init__(self, db_path: Optional[str] = None):
        """Initialize graph memory.
        
        Args:
            db_path: SQLite database path (default: .autoresearch/graph_memory.db)
        """
        self._db_path = db_path or self._get_default_db_path()
        self._ensure_tables()
        
        # In-memory graph using NetworkX or fallback
        if NETWORKX_AVAILABLE:
            self._graph = nx.DiGraph()
        else:
            self._graph = _SimpleDiGraph()
            logger.info("Using simple fallback graph (NetworkX not available)")
        
        # Load from SQLite on startup
        self._load_from_db()
    
    def _get_default_db_path(self) -> str:
        """Get default database path."""
        import os
        project_root = os.getenv("AUTORESEARCH_PROJECT_ROOT", "/tmp")
        db_dir = Path(project_root) / ".autoresearch" / "memory"
        db_dir.mkdir(parents=True, exist_ok=True)
        return str(db_dir / "graph_memory.db")
    
    def _ensure_tables(self) -> None:
        """Create database tables if not exist."""
        conn = sqlite3.connect(self._db_path)
        cursor = conn.cursor()
        
        # Nodes table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS graph_nodes (
                id TEXT PRIMARY KEY,
                entity_type TEXT NOT NULL DEFAULT 'entity',
                properties TEXT NOT NULL DEFAULT '{}',
                created_at TEXT NOT NULL
            )
        """)
        
        # Edges table (triple store)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS graph_edges (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                subject TEXT NOT NULL,
                predicate TEXT NOT NULL,
                object TEXT NOT NULL,
                properties TEXT NOT NULL DEFAULT '{}',
                created_at TEXT NOT NULL,
                UNIQUE(subject, predicate, object)
            )
        """)
        
        # Indexes for fast queries
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_subject ON graph_edges(subject)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_object ON graph_edges(object)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_predicate ON graph_edges(predicate)")
        
        conn.commit()
        conn.close()
    
    def _load_from_db(self) -> None:
        """Load graph from SQLite into memory."""
        conn = sqlite3.connect(self._db_path)
        cursor = conn.cursor()
        
        # Load nodes
        cursor.execute("SELECT id, entity_type, properties, created_at FROM graph_nodes")
        for row in cursor.fetchall():
            node = GraphNode(
                id=row[0],
                entity_type=row[1],
                properties=json.loads(row[2]),
                created_at=datetime.fromisoformat(row[3]),
            )
            if self._graph is not None:
                self._graph.add_node(node.id, **node.to_dict())
        
        # Load edges
        cursor.execute("SELECT subject, predicate, object, properties, created_at FROM graph_edges")
        for row in cursor.fetchall():
            edge = GraphEdge(
                subject=row[0],
                predicate=row[1],
                obj=row[2],
                properties=json.loads(row[3]),
                created_at=datetime.fromisoformat(row[4]),
            )
            if self._graph is not None:
                self._graph.add_edge(
                    edge.subject,
                    edge.obj,
                    predicate=edge.predicate,
                    **edge.properties
                )
        
        conn.close()
        logger.info(f"✅ 已加载图谱: {len(self.list_nodes())} 节点, {len(self.list_edges())} 边")
    
    # ========================================================================
    # Core API: Triple Operations
    # ========================================================================
    
    def add_triple(
        self,
        subject: str,
        predicate: str,
        obj: str,
        properties: Optional[Dict[str, Any]] = None,
    ) -> GraphEdge:
        """Add a triple (subject, predicate, object) to the graph.
        
        Args:
            subject: Subject entity
            predicate: Relationship type
            obj: Object entity
            properties: Optional edge properties
            
        Returns:
            Created GraphEdge
        """
        edge = GraphEdge(
            subject=subject,
            predicate=predicate,
            obj=obj,
            properties=properties or {},
        )
        
        # Save to SQLite
        conn = sqlite3.connect(self._db_path)
        cursor = conn.cursor()
        
        # Ensure nodes exist
        now = datetime.now(timezone.utc).isoformat()
        for entity_id in [subject, obj]:
            cursor.execute(
                "INSERT OR IGNORE INTO graph_nodes (id, entity_type, properties, created_at) VALUES (?, ?, ?, ?)",
                (entity_id, "entity", "{}", now)
            )
        
        # Insert edge
        try:
            cursor.execute(
                """INSERT INTO graph_edges (subject, predicate, object, properties, created_at)
                   VALUES (?, ?, ?, ?, ?)""",
                (subject, predicate, obj, json.dumps(edge.properties), now)
            )
        except sqlite3.IntegrityError:
            # Edge already exists, update properties
            cursor.execute(
                """UPDATE graph_edges SET properties = ? WHERE subject = ? AND predicate = ? AND object = ?""",
                (json.dumps(edge.properties), subject, predicate, obj)
            )
        
        conn.commit()
        conn.close()
        
        # Update in-memory graph
        if self._graph is not None:
            self._graph.add_node(subject)
            self._graph.add_node(obj)
            self._graph.add_edge(subject, obj, predicate=predicate, **edge.properties)
        
        logger.debug(f"✅ 添加三元组: ({subject}, {predicate}, {obj})")
        return edge
    
    def remove_triple(self, subject: str, predicate: str, obj: str) -> bool:
        """Remove a triple from the graph.
        
        Returns:
            True if triple was removed, False if not found
        """
        conn = sqlite3.connect(self._db_path)
        cursor = conn.cursor()
        
        cursor.execute(
            "DELETE FROM graph_edges WHERE subject = ? AND predicate = ? AND object = ?",
            (subject, predicate, obj)
        )
        
        removed = cursor.rowcount > 0
        conn.commit()
        conn.close()
        
        # Update in-memory graph
        if self._graph is not None and removed:
            if self._graph.has_edge(subject, obj):
                self._graph.remove_edge(subject, obj)
        
        return removed
    
    def query_triples(
        self,
        subject: Optional[str] = None,
        predicate: Optional[str] = None,
        obj: Optional[str] = None,
    ) -> List[GraphEdge]:
        """Query triples by pattern matching.
        
        None means "match any" for that position.
        
        Args:
            subject: Subject filter (optional)
            predicate: Predicate filter (optional)
            obj: Object filter (optional)
            
        Returns:
            List of matching edges
        """
        conn = sqlite3.connect(self._db_path)
        cursor = conn.cursor()
        
        query = "SELECT subject, predicate, object, properties, created_at FROM graph_edges WHERE 1=1"
        params: List[Any] = []
        
        if subject is not None:
            query += " AND subject = ?"
            params.append(subject)
        
        if predicate is not None:
            query += " AND predicate = ?"
            params.append(predicate)
        
        if obj is not None:
            query += " AND object = ?"
            params.append(obj)
        
        cursor.execute(query, params)
        rows = cursor.fetchall()
        conn.close()
        
        edges = []
        for row in rows:
            edges.append(GraphEdge(
                subject=row[0],
                predicate=row[1],
                obj=row[2],
                properties=json.loads(row[3]),
                created_at=datetime.fromisoformat(row[4]),
            ))
        
        return edges
    
    # ========================================================================
    # Subgraph Query API
    # ========================================================================
    
    def query_subgraph(
        self,
        entity: str,
        depth: int = 2,
        direction: str = "both",
    ) -> Dict[str, Any]:
        """Query subgraph starting from an entity.
        
        Args:
            entity: Starting entity ID
            depth: Traversal depth (default: 2)
            direction: "outgoing", "incoming", or "both"
            
        Returns:
            Dict with "nodes" and "edges" for subgraph
        """
        if self._graph is None:
            # Should not happen with _SimpleDiGraph fallback
            logger.warning("Graph not initialized, returning empty subgraph")
            return {"nodes": [], "edges": []}
        
        if entity not in self._graph:
            return {"nodes": [], "edges": []}
        
        # BFS traversal
        visited_nodes: Set[str] = {entity}
        visited_edges: List[Tuple[str, str]] = []
        frontier = [entity]
        
        for _ in range(depth):
            next_frontier = []
            for node in frontier:
                # Get neighbors based on direction
                if direction in ["outgoing", "both"]:
                    for neighbor in self._graph.successors(node):
                        if neighbor not in visited_nodes:
                            visited_nodes.add(neighbor)
                            next_frontier.append(neighbor)
                        visited_edges.append((node, neighbor))
                
                if direction in ["incoming", "both"]:
                    for neighbor in self._graph.predecessors(node):
                        if neighbor not in visited_nodes:
                            visited_nodes.add(neighbor)
                            next_frontier.append(neighbor)
                        visited_edges.append((neighbor, node))
            
            frontier = next_frontier
        
        # Build result
        nodes = [self.get_node(n) for n in visited_nodes if self.get_node(n)]
        edges = []
        for src, dst in visited_edges:
            edge_data = self.query_triples(subject=src, obj=dst)
            edges.extend(edge_data)
        
        return {
            "nodes": [n.to_dict() for n in nodes],
            "edges": [e.to_dict() for e in edges],
            "root": entity,
            "depth": depth,
        }
    
    def get_node(self, node_id: str) -> Optional[GraphNode]:
        """Get node by ID."""
        conn = sqlite3.connect(self._db_path)
        cursor = conn.cursor()
        
        cursor.execute(
            "SELECT id, entity_type, properties, created_at FROM graph_nodes WHERE id = ?",
            (node_id,)
        )
        row = cursor.fetchone()
        conn.close()
        
        if row is None:
            return None
        
        return GraphNode(
            id=row[0],
            entity_type=row[1],
            properties=json.loads(row[2]),
            created_at=datetime.fromisoformat(row[3]),
        )
    
    def list_nodes(self) -> List[str]:
        """List all node IDs."""
        conn = sqlite3.connect(self._db_path)
        cursor = conn.cursor()
        
        cursor.execute("SELECT id FROM graph_nodes")
        nodes = [row[0] for row in cursor.fetchall()]
        conn.close()
        
        return nodes
    
    def list_edges(self) -> List[GraphEdge]:
        """List all edges."""
        return self.query_triples()
    
    # ========================================================================
    # Brand-Specific Operations (Malu)
    # ========================================================================
    
    def check_prohibited_patterns(self, text: str) -> Tuple[bool, List[str]]:
        """Check if text contains prohibited patterns based on graph.
        
        Queries STRICTLY_PROHIBITS relationships and checks if text
        contains any prohibited terms.
        
        Args:
            text: Text to check
            
        Returns:
            (is_valid, prohibited_terms_found)
        """
        # Query all STRICTLY_PROHIBITS edges
        prohibited_edges = self.query_triples(predicate="STRICTLY_PROHIBITS")
        
        prohibited_patterns: List[str] = []
        for edge in prohibited_edges:
            # The object contains prohibited patterns
            patterns = edge.obj.split("/")
            prohibited_patterns.extend([p.strip() for p in patterns if p.strip()])
        
        # Check text for prohibited patterns
        found = []
        text_lower = text.lower()
        for pattern in prohibited_patterns:
            if pattern.lower() in text_lower:
                found.append(pattern)
        
        is_valid = len(found) == 0
        return is_valid, found
    
    def get_brand_features(self, brand_entity: str) -> List[Dict[str, Any]]:
        """Get all features associated with a brand/product.
        
        Args:
            brand_entity: Brand or product entity ID
            
        Returns:
            List of features with relationships
        """
        features = []
        
        # Query direct features
        has_feature_edges = self.query_triples(subject=brand_entity, predicate="HAS_FEATURE")
        for edge in has_feature_edges:
            features.append({
                "feature": edge.obj,
                "relationship": "HAS_FEATURE",
                "properties": edge.properties,
            })
            
            # Query consequences (LEADS_TO)
            leads_to = self.query_triples(subject=edge.obj, predicate="LEADS_TO")
            for lt_edge in leads_to:
                features.append({
                    "feature": lt_edge.obj,
                    "relationship": "LEADS_TO",
                    "from_feature": edge.obj,
                    "properties": lt_edge.properties,
                })
        
        return features
    
    # ========================================================================
    # Serialization / Deserialization
    # ========================================================================
    
    def export_to_dict(self) -> Dict[str, Any]:
        """Export entire graph to dictionary.
        
        Useful for backup and transfer.
        """
        return {
            "nodes": [n.to_dict() for n in [self.get_node(id) for id in self.list_nodes()]],
            "edges": [e.to_dict() for e in self.list_edges()],
            "exported_at": datetime.now(timezone.utc).isoformat(),
        }
    
    def import_from_dict(self, data: Dict[str, Any]) -> int:
        """Import graph from dictionary.
        
        Args:
            data: Graph data with "nodes" and "edges"
            
        Returns:
            Number of edges imported
        """
        # Clear existing graph
        conn = sqlite3.connect(self._db_path)
        cursor = conn.cursor()
        cursor.execute("DELETE FROM graph_edges")
        cursor.execute("DELETE FROM graph_nodes")
        conn.commit()
        conn.close()
        
        if self._graph is not None:
            self._graph.clear()
        
        # Import nodes
        for node_data in data.get("nodes", []):
            node = GraphNode.from_dict(node_data)
            conn = sqlite3.connect(self._db_path)
            cursor = conn.cursor()
            cursor.execute(
                "INSERT OR REPLACE INTO graph_nodes (id, entity_type, properties, created_at) VALUES (?, ?, ?, ?)",
                (node.id, node.entity_type, json.dumps(node.properties), node.created_at.isoformat())
            )
            conn.commit()
            conn.close()
        
        # Import edges
        edge_count = 0
        for edge_data in data.get("edges", []):
            edge = GraphEdge.from_dict(edge_data)
            self.add_triple(edge.subject, edge.predicate, edge.obj, edge.properties)
            edge_count += 1
        
        logger.info(f"✅ 导入图谱: {len(data.get('nodes', []))} 节点, {edge_count} 边")
        return edge_count
    
    def clear(self) -> None:
        """Clear entire graph."""
        conn = sqlite3.connect(self._db_path)
        cursor = conn.cursor()
        cursor.execute("DELETE FROM graph_edges")
        cursor.execute("DELETE FROM graph_nodes")
        conn.commit()
        conn.close()
        
        if self._graph is not None:
            self._graph.clear()
        
        logger.info("🗑️ 图谱已清空")
