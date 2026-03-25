import json
from pathlib import Path
from typing import Dict, Any, List, Optional
from dataclasses import dataclass

@dataclass
class MCPTool:
    """MCP工具定义"""
    name: str
    description: str
    input_schema: Dict[str, Any]
    output_schema: Optional[Dict[str, Any]] = None

class MCPRegistry:
    """MCP工具注册表（标准MCP协议兼容）"""
    
    def __init__(self):
        self.tools: Dict[str, MCPTool] = {}
    
    def load_manifest(self, manifest_path: str):
        """加载标准MCP manifest文件"""
        path = Path(manifest_path)
        if not path.exists():
            raise FileNotFoundError(f"Manifest文件不存在: {manifest_path}")
        
        with open(path, 'r', encoding='utf-8') as f:
            manifest = json.load(f)
        
        # 解析manifest
        if "tools" not in manifest:
            raise ValueError("Manifest缺少tools字段")
        
        for tool_def in manifest["tools"]:
            tool = MCPTool(
                name=tool_def["name"],
                description=tool_def.get("description", ""),
                input_schema=tool_def.get("inputSchema", {}),
                output_schema=tool_def.get("outputSchema")
            )
            self.register_tool(tool)
    
    def register_tool(self, tool: MCPTool):
        """注册工具"""
        self.tools[tool.name] = tool
    
    def get_tool(self, name: str) -> Optional[MCPTool]:
        """获取工具"""
        return self.tools.get(name)
    
    def list_tools(self) -> List[str]:
        """列出所有工具"""
        return list(self.tools.keys())
    
    def validate_input(self, tool_name: str, input_data: Dict[str, Any]) -> bool:
        """验证输入数据"""
        tool = self.get_tool(tool_name)
        if not tool:
            return False
        
        # 简单验证（实际应使用JSON Schema验证）
        required_fields = tool.input_schema.get("required", [])
        for field in required_fields:
            if field not in input_data:
                return False
        
        return True
    
    def to_mcp_format(self) -> Dict[str, Any]:
        """转换为MCP标准格式"""
        return {
            "version": "1.0",
            "tools": [
                {
                    "name": tool.name,
                    "description": tool.description,
                    "inputSchema": tool.input_schema,
                    "outputSchema": tool.output_schema
                }
                for tool in self.tools.values()
            ]
        }

# 测试
if __name__ == "__main__":
    registry = MCPRegistry()
    
    # 注册工具
    tool = MCPTool(
        name="web_search",
        description="搜索网页",
        input_schema={
            "type": "object",
            "properties": {
                "query": {"type": "string"}
            },
            "required": ["query"]
        }
    )
    registry.register_tool(tool)
    
    print(f"✅ 注册工具: {registry.list_tools()}")
    
    # 验证输入
    valid = registry.validate_input("web_search", {"query": "test"})
    print(f"✅ 输入验证: {valid}")
    
    # 导出MCP格式
    mcp_format = registry.to_mcp_format()
    print(f"✅ MCP格式: {json.dumps(mcp_format, indent=2)}")
