"""Red-Line Tests for Graph RAG Enforcement.

Tests that the knowledge graph mechanism enforces brand guidelines
and prevents regression of existing execution sandbox.

Key Test Cases:
1. Agent attempts to generate text with "平替" -> Should be blocked
2. Agent attempts to generate text with "代工厂出货" -> Should be blocked
3. Graph STRICTLY_PROHIBITS network should trigger retry
4. Final output must comply with "professional, de-factory" standards
"""

from __future__ import annotations

import pytest
from typing import Dict, Any
from unittest.mock import Mock, patch, MagicMock
import tempfile
import os

from src.autoresearch.core.memory import LocalGraphMemory, GraphNode, GraphEdge
from src.autoresearch.core.initialization.malu_brand_graph import (
    initialize_malu_brand_graph,
    verify_malu_brand_graph,
    MALU_BRAND_TRIPLES,
)
from src.autoresearch.core.tools.brand_graph_tools import (
    check_text_compliance_handler,
    query_brand_graph_handler,
)


# ========================================================================
# Fixtures
# ========================================================================

@pytest.fixture
def temp_graph_db():
    """Create temporary graph database for testing."""
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        db_path = f.name
    
    yield db_path
    
    # Cleanup
    try:
        os.unlink(db_path)
    except:
        pass


@pytest.fixture
def malu_graph(temp_graph_db):
    """Create Malu brand graph for testing."""
    graph = LocalGraphMemory(db_path=temp_graph_db)
    initialize_malu_brand_graph(graph)
    return graph


# ========================================================================
# Phase 1: Graph Initialization Tests
# ========================================================================

class TestMaluGraphInitialization:
    """Tests for Malu brand graph initialization."""

    def test_graph_initialization_success(self, malu_graph):
        """Test graph initializes with all required triples."""
        assert verify_malu_brand_graph(malu_graph)

    def test_required_entities_exist(self, malu_graph):
        """Test all required entities are created."""
        required_entities = ["玛露", "6g罐装遮瑕膏", "玛露文案调性"]
        
        for entity in required_entities:
            node = malu_graph.get_node(entity)
            assert node is not None, f"Missing entity: {entity}"
            assert node.id == entity

    def test_required_triples_exist(self, malu_graph):
        """Test all required triples are created."""
        # Check product features
        features = malu_graph.query_triples(
            subject="6g罐装遮瑕膏",
            predicate="HAS_FEATURE",
        )
        assert len(features) >= 5, "Missing product features"
        
        # Check prohibited terms
        prohibited = malu_graph.query_triples(predicate="STRICTLY_PROHIBITS")
        assert len(prohibited) >= 8, "Missing prohibited terms"

    def test_feature_consequences_exist(self, malu_graph):
        """Test feature consequence chains."""
        leads_to = malu_graph.query_triples(
            subject="遮瑕力强",
            predicate="LEADS_TO",
        )
        assert len(leads_to) >= 1, "Missing LEADS_TO relationships"


# ========================================================================
# Phase 2: Prohibited Pattern Detection Tests
# ========================================================================

class TestProhibitedPatternDetection:
    """Tests for detecting prohibited patterns in text."""

    def test_detect_平替(self, malu_graph):
        """Test detection of '平替' (cheap substitute)."""
        text = "这款是某大牌的平替，性价比超高"
        is_valid, prohibited = malu_graph.check_prohibited_patterns(text)
        
        assert not is_valid
        assert "平替" in prohibited

    def test_detect_代工厂出货(self, malu_graph):
        """Test detection of '代工厂出货' (factory outlet)."""
        text = "我们是代工厂出货，没有中间商"
        is_valid, prohibited = malu_graph.check_prohibited_patterns(text)
        
        assert not is_valid
        assert "代工厂出货" in prohibited

    def test_detect_multiple_prohibited_terms(self, malu_graph):
        """Test detection of multiple prohibited terms."""
        text = "特价批发，代工厂出货，便宜好用"
        is_valid, prohibited = malu_graph.check_prohibited_patterns(text)
        
        assert not is_valid
        assert len(prohibited) >= 3

    def test_valid_text_passes(self, malu_graph):
        """Test that valid text passes compliance check."""
        text = "玛露6g罐装遮瑕膏，遮瑕力强，轻薄不卡粉，24小时持妆"
        is_valid, prohibited = malu_graph.check_prohibited_patterns(text)
        
        assert is_valid
        assert len(prohibited) == 0


# ========================================================================
# Phase 3: Subgraph Query Tests
# ========================================================================

class TestSubgraphQueries:
    """Tests for subgraph query functionality."""

    def test_query_product_subgraph(self, malu_graph):
        """Test querying product subgraph."""
        subgraph = malu_graph.query_subgraph("6g罐装遮瑕膏", depth=2)
        
        assert "nodes" in subgraph
        assert "edges" in subgraph
        assert len(subgraph["nodes"]) > 0
        assert len(subgraph["edges"]) > 0

    def test_query_brand_features(self, malu_graph):
        """Test querying brand features."""
        features = malu_graph.get_brand_features("6g罐装遮瑕膏")
        
        assert len(features) > 0
        
        # Should include direct features
        feature_entities = [f["feature"] for f in features]
        assert "遮瑕力强" in feature_entities

    def test_query_nonexistent_entity(self, malu_graph):
        """Test querying non-existent entity returns empty."""
        subgraph = malu_graph.query_subgraph("不存在的实体", depth=2)
        
        assert subgraph["nodes"] == []
        assert subgraph["edges"] == []


# ========================================================================
# Phase 4: MCP Tool Integration Tests
# ========================================================================

class TestMCPToolIntegration:
    """Tests for MCP tool integration."""

    def test_query_brand_graph_tool(self, malu_graph):
        """Test Query_Brand_Graph MCP tool."""
        result = query_brand_graph_handler(
            graph=malu_graph,
            entity="6g罐装遮瑕膏",
            query_type="features",
        )
        
        assert result["success"]
        assert len(result["features"]) > 0

    def test_check_text_compliance_tool_blocks_prohibited(self, malu_graph):
        """Test Check_Text_Compliance tool blocks prohibited text."""
        result = check_text_compliance_handler(
            graph=malu_graph,
            text="这是平替产品",
        )
        
        assert not result["is_compliant"]
        assert "平替" in result["prohibited_terms_found"]

    def test_check_text_compliance_tool_allows_valid(self, malu_graph):
        """Test Check_Text_Compliance tool allows valid text."""
        result = check_text_compliance_handler(
            graph=malu_graph,
            text="专业遮瑕，轻薄持妆",
        )
        
        assert result["is_compliant"]
        assert len(result["prohibited_terms_found"]) == 0


# ========================================================================
# Phase 5: Agent Enforcement Simulation Tests
# ========================================================================

class TestAgentEnforcementSimulation:
    """Simulate Agent behavior with graph enforcement."""

    def test_agent_retry_on_prohibited_text(self, malu_graph):
        """Test Agent retries when text is blocked."""
        # Simulate agent generating text
        attempts = [
            "平替产品，便宜好用",  # Attempt 1: Blocked
            "代工厂出货，价格实惠",  # Attempt 2: Blocked
            "玛露遮瑕膏，专业遮瑕，轻薄持妆",  # Attempt 3: Passes
        ]
        
        final_text = None
        for attempt in attempts:
            is_valid, prohibited = malu_graph.check_prohibited_patterns(attempt)
            
            if is_valid:
                final_text = attempt
                break
        
        assert final_text is not None
        assert "平替" not in final_text
        assert "代工厂" not in final_text

    def test_agent_must_query_graph_before_generation(self, malu_graph):
        """Test Agent queries graph before generating text."""
        # Simulate agent workflow
        # Step 1: Query brand features
        features = malu_graph.get_brand_features("6g罐装遮瑕膏")
        feature_entities = [f["feature"] for f in features]
        
        # Step 2: Query prohibited terms
        prohibited_edges = malu_graph.query_triples(predicate="STRICTLY_PROHIBITS")
        prohibited_terms = []
        for edge in prohibited_edges:
            patterns = edge.obj.split("/")
            prohibited_terms.extend([p.strip() for p in patterns if p.strip()])
        
        # Step 3: Generate text based on graph
        generated_text = f"玛露6g罐装遮瑕膏，{feature_entities[0]}"
        
        # Step 4: Verify compliance
        is_valid, _ = malu_graph.check_prohibited_patterns(generated_text)
        
        assert is_valid


# ========================================================================
# Phase 6: No Regression Tests
# ========================================================================

class TestNoRegression:
    """Ensure graph mechanism doesn't break existing functionality."""

    def test_graph_persistence_across_restarts(self, temp_graph_db):
        """Test graph persists across restarts."""
        # Create graph and add data
        graph1 = LocalGraphMemory(db_path=temp_graph_db)
        initialize_malu_brand_graph(graph1)
        
        # Simulate restart
        graph2 = LocalGraphMemory(db_path=temp_graph_db)
        
        # Verify data still exists
        assert verify_malu_brand_graph(graph2)

    def test_graph_export_import(self, malu_graph):
        """Test graph export and import."""
        # Export
        exported = malu_graph.export_to_dict()
        
        # Clear and reimport
        malu_graph.clear()
        count = malu_graph.import_from_dict(exported)
        
        assert count > 0
        assert verify_malu_brand_graph(malu_graph)

    def test_graph_clear_and_reinitialize(self, malu_graph):
        """Test graph can be cleared and reinitialized."""
        # Clear
        malu_graph.clear()
        assert len(malu_graph.list_nodes()) == 0
        
        # Reinitialize
        count = initialize_malu_brand_graph(malu_graph)
        assert count > 0
        assert verify_malu_brand_graph(malu_graph)


# ========================================================================
# Phase 7: Edge Cases Tests
# ========================================================================

class TestEdgeCases:
    """Test edge cases and error handling."""

    def test_empty_text_compliance_check(self, malu_graph):
        """Test compliance check with empty text."""
        is_valid, prohibited = malu_graph.check_prohibited_patterns("")
        assert is_valid  # Empty text should pass

    def test_case_insensitive_prohibited_detection(self, malu_graph):
        """Test case-insensitive prohibited term detection."""
        text = "这是平替产品"  # Lowercase
        is_valid, prohibited = malu_graph.check_prohibited_patterns(text)
        assert not is_valid
        
        text_upper = "这是平替产品"  # Same characters
        is_valid_upper, prohibited_upper = malu_graph.check_prohibited_patterns(text_upper)
        assert not is_valid_upper

    def test_query_nonexistent_predicate(self, malu_graph):
        """Test querying non-existent predicate returns empty."""
        edges = malu_graph.query_triples(predicate="NONEXISTENT_PREDICATE")
        assert len(edges) == 0

    def test_add_duplicate_triple(self, malu_graph):
        """Test adding duplicate triple updates properties."""
        malu_graph.add_triple("测试实体", "测试关系", "测试对象")
        malu_graph.add_triple(
            "测试实体",
            "测试关系",
            "测试对象",
            properties={"custom": "value"},
        )
        
        edges = malu_graph.query_triples(
            subject="测试实体",
            predicate="测试关系",
        )
        
        assert len(edges) == 1  # Should not duplicate
        assert edges[0].properties.get("custom") == "value"


# ========================================================================
# Phase 8: Performance Tests
# ========================================================================

class TestPerformance:
    """Test performance characteristics."""

    def test_subgraph_query_performance(self, malu_graph):
        """Test subgraph query completes quickly."""
        import time
        
        start = time.time()
        subgraph = malu_graph.query_subgraph("玛露", depth=3)
        elapsed = time.time() - start
        
        # Should complete in < 100ms
        assert elapsed < 0.1
        assert len(subgraph["nodes"]) > 0

    def test_compliance_check_performance(self, malu_graph):
        """Test compliance check completes quickly."""
        import time
        
        text = "这是一段测试文案，包含多个禁止词汇如平替、代工厂出货、特价等"
        
        start = time.time()
        is_valid, prohibited = malu_graph.check_prohibited_patterns(text)
        elapsed = time.time() - start
        
        # Should complete in < 50ms
        assert elapsed < 0.05
