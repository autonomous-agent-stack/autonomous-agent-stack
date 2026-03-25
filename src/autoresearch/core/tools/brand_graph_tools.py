"""MCP Tools for Brand Knowledge Graph.

Provides Query_Brand_Graph tool for Agent to query brand knowledge.
"""

from __future__ import annotations

import json
from typing import Any, Dict, List, Optional
import logging

from autoresearch.core.memory import LocalGraphMemory

logger = logging.getLogger(__name__)


# ========================================================================
# Brand Graph MCP Tools
# ========================================================================

def create_brand_graph_tools(graph: Optional[LocalGraphMemory] = None) -> List[Dict[str, Any]]:
    """Create MCP tools for brand knowledge graph.
    
    Args:
        graph: LocalGraphMemory instance (default: create new)
        
    Returns:
        List of MCP tool definitions
    """
    if graph is None:
        graph = LocalGraphMemory()
    
    return [
        {
            "name": "Query_Brand_Graph",
            "description": "查询品牌知识图谱，获取产品特性、卖点、禁止用语等信息",
            "parameters": {
                "type": "object",
                "properties": {
                    "entity": {
                        "type": "string",
                        "description": "查询的实体（如产品名、品牌名）",
                    },
                    "depth": {
                        "type": "integer",
                        "description": "查询深度（默认2）",
                        "default": 2,
                    },
                    "query_type": {
                        "type": "string",
                        "enum": ["features", "prohibited", "subgraph", "all"],
                        "description": "查询类型：features=产品特性, prohibited=禁止用语, subgraph=完整子图, all=全部",
                        "default": "all",
                    },
                },
                "required": ["entity"],
            },
            "handler": lambda **kwargs: query_brand_graph_handler(graph, **kwargs),
        },
        {
            "name": "Check_Text_Compliance",
            "description": "检查文案是否符合品牌规范，识别禁止用语",
            "parameters": {
                "type": "object",
                "properties": {
                    "text": {
                        "type": "string",
                        "description": "待检查的文案内容",
                    },
                },
                "required": ["text"],
            },
            "handler": lambda **kwargs: check_text_compliance_handler(graph, **kwargs),
        },
        {
            "name": "Get_Brand_Story",
            "description": "获取品牌故事和调性要求",
            "parameters": {
                "type": "object",
                "properties": {
                    "brand": {
                        "type": "string",
                        "description": "品牌名称（默认：玛露）",
                        "default": "玛露",
                    },
                },
                "required": [],
            },
            "handler": lambda **kwargs: get_brand_story_handler(graph, **kwargs),
        },
    ]


# ========================================================================
# Tool Handlers
# ========================================================================

def query_brand_graph_handler(
    graph: LocalGraphMemory,
    entity: str,
    depth: int = 2,
    query_type: str = "all",
) -> Dict[str, Any]:
    """Handler for Query_Brand_Graph tool.
    
    Args:
        graph: Graph memory instance
        entity: Entity to query
        depth: Query depth
        query_type: Type of query (features, prohibited, subgraph, all)
        
    Returns:
        Query result
    """
    result = {
        "entity": entity,
        "query_type": query_type,
        "success": True,
    }
    
    try:
        if query_type in ["features", "all"]:
            features = graph.get_brand_features(entity)
            result["features"] = features
        
        if query_type in ["prohibited", "all"]:
            # Query STRICTLY_PROHIBITS relationships
            prohibited_edges = graph.query_triples(predicate="STRICTLY_PROHIBITS")
            prohibited_terms = []
            for edge in prohibited_edges:
                patterns = edge.obj.split("/")
                prohibited_terms.extend([p.strip() for p in patterns if p.strip()])
            result["prohibited_terms"] = prohibited_terms
        
        if query_type in ["subgraph", "all"]:
            subgraph = graph.query_subgraph(entity, depth=depth)
            result["subgraph"] = subgraph
        
    except Exception as e:
        logger.error(f"Query_Brand_Graph failed: {e}")
        result["success"] = False
        result["error"] = str(e)
    
    return result


def check_text_compliance_handler(
    graph: LocalGraphMemory,
    text: str,
) -> Dict[str, Any]:
    """Handler for Check_Text_Compliance tool.
    
    Args:
        graph: Graph memory instance
        text: Text to check
        
    Returns:
        Compliance check result
    """
    try:
        is_valid, prohibited_found = graph.check_prohibited_patterns(text)
        
        return {
            "text": text,
            "is_compliant": is_valid,
            "prohibited_terms_found": prohibited_found,
            "message": "文案符合品牌规范" if is_valid else f"文案包含禁止用语: {', '.join(prohibited_found)}",
            "success": True,
        }
    
    except Exception as e:
        logger.error(f"Check_Text_Compliance failed: {e}")
        return {
            "text": text,
            "is_compliant": False,
            "success": False,
            "error": str(e),
        }


def get_brand_story_handler(
    graph: LocalGraphMemory,
    brand: str = "玛露",
) -> Dict[str, Any]:
    """Handler for Get_Brand_Story tool.
    
    Args:
        graph: Graph memory instance
        brand: Brand name
        
    Returns:
        Brand story and tone requirements
    """
    try:
        # Query brand entity
        brand_node = graph.get_node(brand)
        
        # Query brand features
        features = graph.get_brand_features(brand)
        
        # Query prohibited terms
        prohibited_edges = graph.query_triples(predicate="STRICTLY_PROHIBITS")
        prohibited_terms = []
        for edge in prohibited_edges:
            patterns = edge.obj.split("/")
            prohibited_terms.extend([p.strip() for p in patterns if p.strip()])
        
        return {
            "brand": brand,
            "features": features,
            "prohibited_terms": prohibited_terms,
            "tone_guidance": "专业、高端、去工厂化",
            "success": True,
        }
    
    except Exception as e:
        logger.error(f"Get_Brand_Story failed: {e}")
        return {
            "brand": brand,
            "success": False,
            "error": str(e),
        }


# ========================================================================
# Tool Registration Helper
# ========================================================================

def register_brand_tools_to_mcp(mcp_registry: Any, graph: Optional[LocalGraphMemory] = None) -> None:
    """Register brand graph tools to MCP registry.
    
    Args:
        mcp_registry: MCP tool registry
        graph: Graph memory instance
    """
    tools = create_brand_graph_tools(graph)
    
    for tool_def in tools:
        # MCP tool registration format
        mcp_registry.register_tool(
            name=tool_def["name"],
            description=tool_def["description"],
            parameters=tool_def["parameters"],
            handler=tool_def["handler"],
        )
    
    logger.info(f"✅ 已注册 {len(tools)} 个品牌图谱 MCP 工具")
