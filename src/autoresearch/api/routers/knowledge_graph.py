"""Knowledge Graph Visualization Router.

Provides API endpoints for graph visualization in TWA panel.
Reuses DAG rendering logic with light-themed UI.
"""

from __future__ import annotations

import json
from typing import Any, Dict, List, Optional
import logging

from fastapi import APIRouter, Depends, HTTPException, Query

from autoresearch.core.memory import LocalGraphMemory
from autoresearch.core.initialization.malu_brand_graph import (
    initialize_malu_brand_graph,
    get_malu_brand_summary,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/knowledge", tags=["knowledge", "graph"])


# Global graph instance (initialized on startup)
_graph_instance: Optional[LocalGraphMemory] = None


def get_graph() -> LocalGraphMemory:
    """Get or create graph instance."""
    global _graph_instance
    if _graph_instance is None:
        _graph_instance = LocalGraphMemory()
        initialize_malu_brand_graph(_graph_instance)
    return _graph_instance


# ========================================================================
# Graph Query Endpoints
# ========================================================================

@router.get("/health")
def knowledge_graph_health() -> Dict[str, str]:
    """Health check endpoint."""
    return {"status": "ok", "service": "knowledge_graph"}


@router.get("/summary")
def get_graph_summary(
    graph: LocalGraphMemory = Depends(get_graph),
) -> Dict[str, Any]:
    """Get graph summary statistics."""
    return get_malu_brand_summary(graph)


@router.get("/nodes")
def list_nodes(
    graph: LocalGraphMemory = Depends(get_graph),
) -> List[Dict[str, Any]]:
    """List all nodes in the graph."""
    nodes = []
    for node_id in graph.list_nodes():
        node = graph.get_node(node_id)
        if node:
            nodes.append(node.to_dict())
    return nodes


@router.get("/edges")
def list_edges(
    graph: LocalGraphMemory = Depends(get_graph),
) -> List[Dict[str, Any]]:
    """List all edges in the graph."""
    edges = graph.list_edges()
    return [edge.to_dict() for edge in edges]


@router.get("/subgraph/{entity}")
def query_subgraph(
    entity: str,
    depth: int = Query(default=2, ge=1, le=5),
    graph: LocalGraphMemory = Depends(get_graph),
) -> Dict[str, Any]:
    """Query subgraph for an entity."""
    return graph.query_subgraph(entity, depth=depth)


@router.get("/features/{product}")
def get_product_features(
    product: str,
    graph: LocalGraphMemory = Depends(get_graph),
) -> List[Dict[str, Any]]:
    """Get all features for a product."""
    return graph.get_brand_features(product)


@router.post("/check-compliance")
def check_text_compliance(
    text: str,
    graph: LocalGraphMemory = Depends(get_graph),
) -> Dict[str, Any]:
    """Check if text complies with brand guidelines."""
    is_valid, prohibited = graph.check_prohibited_patterns(text)
    return {
        "text": text,
        "is_compliant": is_valid,
        "prohibited_terms_found": prohibited,
    }


# ========================================================================
# Visualization Endpoints (DAG Format)
# ========================================================================

@router.get("/visualize/dag")
def get_graph_as_dag(
    root_entity: Optional[str] = Query(default=None),
    depth: int = Query(default=2, ge=1, le=5),
    graph: LocalGraphMemory = Depends(get_graph),
) -> Dict[str, Any]:
    """Get graph in DAG format for visualization.
    
    Reuses existing DAG rendering logic with light-themed UI.
    
    Args:
        root_entity: Root entity for subgraph (optional, default: full graph)
        depth: Traversal depth
        
    Returns:
        DAG-formatted graph data
    """
    if root_entity:
        subgraph = graph.query_subgraph(root_entity, depth=depth)
        nodes_data = subgraph["nodes"]
        edges_data = subgraph["edges"]
    else:
        nodes_data = [graph.get_node(n).to_dict() for n in graph.list_nodes() if graph.get_node(n)]
        edges_data = [e.to_dict() for e in graph.list_edges()]
    
    # Convert to DAG format (compatible with existing DAG renderer)
    dag_nodes = []
    for node_data in nodes_data:
        dag_nodes.append({
            "id": node_data["id"],
            "label": node_data["id"],
            "type": node_data.get("entity_type", "entity"),
            "properties": node_data.get("properties", {}),
            # Light-themed colors
            "color": _get_node_color(node_data.get("entity_type", "entity")),
            "style": {
                "backgroundColor": "#f8f9fa",
                "borderColor": "#dee2e6",
                "textColor": "#495057",
            },
        })
    
    dag_edges = []
    for edge_data in edges_data:
        dag_edges.append({
            "id": f"{edge_data['subject']}-{edge_data['predicate']}-{edge_data['object']}",
            "source": edge_data["subject"],
            "target": edge_data["object"],
            "label": edge_data["predicate"],
            "type": "arrow",
            "style": {
                "color": "#6c757d",
                "width": 2,
            },
        })
    
    return {
        "nodes": dag_nodes,
        "edges": dag_edges,
        "metadata": {
            "total_nodes": len(dag_nodes),
            "total_edges": len(dag_edges),
            "root": root_entity,
            "depth": depth,
            "theme": "light",
        },
    }


def _get_node_color(entity_type: str) -> str:
    """Get node color based on entity type (light-themed)."""
    colors = {
        "entity": "#e3f2fd",  # Light blue
        "brand": "#fff3e0",   # Light orange
        "product": "#e8f5e9", # Light green
        "feature": "#fce4ec", # Light pink
        "tone": "#f3e5f5",    # Light purple
    }
    return colors.get(entity_type, "#f8f9fa")


# ========================================================================
# Graph Management Endpoints
# ========================================================================

@router.post("/admin/clear")
def clear_graph(
    graph: LocalGraphMemory = Depends(get_graph),
) -> Dict[str, str]:
    """Clear entire graph (admin only)."""
    graph.clear()
    return {"status": "ok", "message": "Graph cleared"}


@router.post("/admin/reinitialize")
def reinitialize_graph(
    graph: LocalGraphMemory = Depends(get_graph),
) -> Dict[str, Any]:
    """Reinitialize graph with Malu brand data."""
    graph.clear()
    count = initialize_malu_brand_graph(graph)
    return {
        "status": "ok",
        "triples_added": count,
        "message": f"Graph reinitialized with {count} triples",
    }
