"""Malu Brand Graph Initialization.

Initializes the knowledge graph with Malu brand entities on cold start.
"""

from __future__ import annotations

import logging
from typing import Optional

from autoresearch.core.memory import LocalGraphMemory

logger = logging.getLogger(__name__)


# ========================================================================
# Malu Brand Knowledge Triples
# ========================================================================

MALU_BRAND_TRIPLES = [
    # Product Features
    ("6g罐装遮瑕膏", "HAS_FEATURE", "挑战游泳级别持妆"),
    ("6g罐装遮瑕膏", "HAS_FEATURE", "遮瑕力强"),
    ("6g罐装遮瑕膏", "HAS_FEATURE", "轻薄不卡粉"),
    ("6g罐装遮瑕膏", "HAS_FEATURE", "防水防汗"),
    ("6g罐装遮瑕膏", "HAS_FEATURE", "24小时持妆"),
    
    # Feature Consequences
    ("遮瑕力强", "LEADS_TO", "不用调色"),
    ("遮瑕力强", "LEADS_TO", "一拍即融"),
    ("轻薄不卡粉", "LEADS_TO", "自然裸妆感"),
    ("防水防汗", "LEADS_TO", "游泳不掉妆"),
    
    # Brand Tone (Prohibited Terms)
    ("玛露文案调性", "STRICTLY_PROHIBITS", "平替"),
    ("玛露文案调性", "STRICTLY_PROHIBITS", "代工厂出货"),
    ("玛露文案调性", "STRICTLY_PROHIBITS", "工厂化词汇/廉价感表达"),
    ("玛露文案调性", "STRICTLY_PROHIBITS", "低端"),
    ("玛露文案调性", "STRICTLY_PROHIBITS", "便宜"),
    ("玛露文案调性", "STRICTLY_PROHIBITS", "批发"),
    ("玛露文案调性", "STRICTLY_PROHIBITS", "清仓"),
    ("玛露文案调性", "STRICTLY_PROHIBITS", "甩卖"),
    ("玛露文案调性", "STRICTLY_PROHIBITS", "特价"),
    
    # Brand Identity
    ("玛露", "HAS_PRODUCT", "6g罐装遮瑕膏"),
    ("玛露", "HAS_TONE", "专业"),
    ("玛露", "HAS_TONE", "高端"),
    ("玛露", "HAS_TONE", "去工厂化"),
    
    # Product Benefits
    ("6g罐装遮瑕膏", "TARGET_AUDIENCE", "精致女性"),
    ("6g罐装遮瑕膏", "USE_CASE", "日常通勤"),
    ("6g罐装遮瑕膏", "USE_CASE", "重要场合"),
    ("6g罐装遮瑕膏", "USE_CASE", "户外运动"),
]


def initialize_malu_brand_graph(graph: Optional[LocalGraphMemory] = None) -> int:
    """Initialize Malu brand knowledge graph.
    
    Args:
        graph: Graph memory instance (default: create new)
        
    Returns:
        Number of triples added
    """
    if graph is None:
        graph = LocalGraphMemory()
    
    # Check if already initialized
    existing_edges = graph.list_edges()
    if len(existing_edges) > 0:
        logger.info(f"图谱已存在 {len(existing_edges)} 条边，跳过初始化")
        return 0
    
    # Add all Malu brand triples
    added_count = 0
    for subject, predicate, obj in MALU_BRAND_TRIPLES:
        graph.add_triple(subject, predicate, obj)
        added_count += 1
    
    logger.info(f"✅ 玛露品牌图谱初始化完成: {added_count} 条三元组")
    return added_count


def verify_malu_brand_graph(graph: Optional[LocalGraphMemory] = None) -> bool:
    """Verify Malu brand graph is properly initialized.
    
    Args:
        graph: Graph memory instance
        
    Returns:
        True if graph is valid
    """
    if graph is None:
        graph = LocalGraphMemory()
    
    # Check for required entities
    required_entities = ["玛露", "6g罐装遮瑕膏", "玛露文案调性"]
    for entity in required_entities:
        node = graph.get_node(entity)
        if node is None:
            logger.warning(f"缺少必需实体: {entity}")
            return False
    
    # Check for required relationships
    required_triples = [
        ("6g罐装遮瑕膏", "HAS_FEATURE", "遮瑕力强"),
        ("玛露文案调性", "STRICTLY_PROHIBITS", "平替"),
    ]
    
    for subject, predicate, obj in required_triples:
        edges = graph.query_triples(subject=subject, predicate=predicate, obj=obj)
        if not edges:
            logger.warning(f"缺少必需三元组: ({subject}, {predicate}, {obj})")
            return False
    
    logger.info("✅ 玛露品牌图谱验证通过")
    return True


def get_malu_brand_summary(graph: Optional[LocalGraphMemory] = None) -> dict:
    """Get summary of Malu brand graph.
    
    Args:
        graph: Graph memory instance
        
    Returns:
        Summary dict with stats
    """
    if graph is None:
        graph = LocalGraphMemory()
    
    nodes = graph.list_nodes()
    edges = graph.list_edges()
    
    # Count by predicate
    predicates = {}
    for edge in edges:
        predicates[edge.predicate] = predicates.get(edge.predicate, 0) + 1
    
    return {
        "total_nodes": len(nodes),
        "total_edges": len(edges),
        "predicates": predicates,
        "entities": nodes,
    }
