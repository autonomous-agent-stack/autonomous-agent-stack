import pytest
import tempfile
import json
from pathlib import Path
from src.orchestrator.mcp_registry import MCPRegistry, MCPTool

def test_register_tool():
    """测试注册工具"""
    registry = MCPRegistry()
    
    tool = MCPTool(
        name="test_tool",
        description="测试工具",
        input_schema={"type": "object"}
    )
    
    registry.register_tool(tool)
    
    assert "test_tool" in registry.list_tools()

def test_get_tool():
    """测试获取工具"""
    registry = MCPRegistry()
    
    tool = MCPTool(
        name="test_tool",
        description="测试工具",
        input_schema={"type": "object"}
    )
    
    registry.register_tool(tool)
    retrieved = registry.get_tool("test_tool")
    
    assert retrieved is not None
    assert retrieved.name == "test_tool"

def test_validate_input():
    """测试输入验证"""
    registry = MCPRegistry()
    
    tool = MCPTool(
        name="test_tool",
        description="测试工具",
        input_schema={
            "type": "object",
            "required": ["query"]
        }
    )
    
    registry.register_tool(tool)
    
    # 有效输入
    valid = registry.validate_input("test_tool", {"query": "test"})
    assert valid is True
    
    # 无效输入
    invalid = registry.validate_input("test_tool", {})
    assert invalid is False

def test_to_mcp_format():
    """测试导出MCP格式"""
    registry = MCPRegistry()
    
    tool = MCPTool(
        name="test_tool",
        description="测试工具",
        input_schema={"type": "object"}
    )
    
    registry.register_tool(tool)
    mcp_format = registry.to_mcp_format()
    
    assert "version" in mcp_format
    assert "tools" in mcp_format
    assert len(mcp_format["tools"]) == 1

def test_load_manifest():
    """测试加载manifest文件"""
    with tempfile.TemporaryDirectory() as tmpdir:
        manifest_path = Path(tmpdir) / "manifest.json"
        
        # 创建manifest文件
        manifest = {
            "version": "1.0",
            "tools": [
                {
                    "name": "web_search",
                    "description": "搜索网页",
                    "inputSchema": {
                        "type": "object",
                        "required": ["query"]
                    }
                }
            ]
        }
        
        with open(manifest_path, 'w') as f:
            json.dump(manifest, f)
        
        # 加载
        registry = MCPRegistry()
        registry.load_manifest(str(manifest_path))
        
        # 验证
        assert "web_search" in registry.list_tools()

if __name__ == "__main__":
    pytest.main([__file__, "-v"])
