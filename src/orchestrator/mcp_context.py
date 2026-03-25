"""
MCP ContextBlock - 无缝挂载 MCP 网关

这个模块实现 MASFactory 的 ContextBlock，统一管理 MCP 工具链。
"""

from typing import Dict, Any, Optional
import json


class MCPContextBlock:
    """
    MCP 上下文块
    
    将 InfoQuest/MCP 的工具链统一桥接到 MASFactory。
    当任何 Node 需要调用外部 API 或读取本地文件时，
    直接从这个统一的上下文中获取权限。
    """
    
    def __init__(self, mcp_endpoint: str = "https://mcp.infoquest.bytepluses.com/mcp"):
        self.mcp_endpoint = mcp_endpoint
        self.tools: Dict[str, Any] = {}
        self.cache: Dict[str, Any] = {}
        self.session_token: Optional[str] = None
    
    def register_tool(self, tool_name: str, tool_config: Dict[str, Any]):
        """
        注册 MCP 工具
        
        Args:
            tool_name: 工具名称
            tool_config: 工具配置（endpoint, auth, etc.）
        """
        self.tools[tool_name] = tool_config
        print(f"✅ 注册 MCP 工具: {tool_name}")
    
    async def call_tool(
        self,
        tool_name: str,
        params: Dict[str, Any],
        use_cache: bool = True
    ) -> Dict[str, Any]:
        """
        调用 MCP 工具
        
        Args:
            tool_name: 工具名称
            params: 工具参数
            use_cache: 是否使用缓存
        
        Returns:
            工具执行结果
        """
        # 1. 检查缓存
        cache_key = f"{tool_name}:{json.dumps(params, sort_keys=True)}"
        if use_cache and cache_key in self.cache:
            print(f"📦 使用缓存: {tool_name}")
            return self.cache[cache_key]
        
        # 2. 检查工具是否注册
        if tool_name not in self.tools:
            raise ValueError(f"Tool {tool_name} not registered")
        
        # 3. 调用 MCP 工具
        # 简化版：模拟调用
        print(f"🔧 调用 MCP 工具: {tool_name}")
        
        # 模拟 MCP 调用
        result = {
            "tool": tool_name,
            "params": params,
            "result": "success",
            "data": f"Processed {params}"
        }
        
        # 4. 缓存结果
        if use_cache:
            self.cache[cache_key] = result
        
        return result
    
    def discover_tools(self) -> list[str]:
        """
        动态发现 MCP 工具
        
        Returns:
            可用工具列表
        """
        # 简化版：返回预定义工具
        available_tools = [
            "web_search",
            "link_reader",
            "file_reader",
            "code_analyzer",
            "data_processor"
        ]
        
        print(f"🔍 发现 {len(available_tools)} 个 MCP 工具")
        return available_tools
    
    def set_session_token(self, token: str):
        """设置会话令牌"""
        self.session_token = token
    
    def clear_cache(self):
        """清空缓存"""
        self.cache.clear()
        print("🗑️ 缓存已清空")


class MCPToolRegistry:
    """
    MCP 工具注册表
    
    管理所有可用的 MCP 工具。
    """
    
    def __init__(self):
        self.tools: Dict[str, Dict[str, Any]] = {}
    
    def register(self, name: str, description: str, endpoint: str, auth_required: bool = False):
        """注册工具"""
        self.tools[name] = {
            "name": name,
            "description": description,
            "endpoint": endpoint,
            "auth_required": auth_required
        }
    
    def get(self, name: str) -> Optional[Dict[str, Any]]:
        """获取工具信息"""
        return self.tools.get(name)
    
    def list_all(self) -> list[str]:
        """列出所有工具"""
        return list(self.tools.keys())


# 预定义的 MCP 工具
def create_default_mcp_registry() -> MCPToolRegistry:
    """创建默认 MCP 工具注册表"""
    registry = MCPToolRegistry()
    
    # 注册常用工具
    registry.register(
        name="web_search",
        description="网络搜索工具",
        endpoint="https://mcp.infoquest.bytepluses.com/mcp/web_search",
        auth_required=False
    )
    
    registry.register(
        name="link_reader",
        description="链接读取工具",
        endpoint="https://mcp.infoquest.bytepluses.com/mcp/link_reader",
        auth_required=False
    )
    
    registry.register(
        name="file_reader",
        description="文件读取工具",
        endpoint="https://mcp.infoquest.bytepluses.com/mcp/file_reader",
        auth_required=True
    )
    
    registry.register(
        name="code_analyzer",
        description="代码分析工具",
        endpoint="https://mcp.infoquest.bytepluses.com/mcp/code_analyzer",
        auth_required=False
    )
    
    return registry


# 使用示例
async def main():
    """演示 MCP ContextBlock"""
    print("=" * 60)
    print("🔧 MCP ContextBlock 演示")
    print("=" * 60)
    
    # 创建 MCP 上下文块
    mcp = MCPContextBlock()
    
    # 创建工具注册表
    registry = create_default_mcp_registry()
    
    # 注册工具
    for tool_name in registry.list_all():
        tool_info = registry.get(tool_name)
        mcp.register_tool(tool_name, tool_info)
    
    # 发现工具
    available_tools = mcp.discover_tools()
    print(f"\n可用工具: {available_tools}")
    
    # 调用工具
    result = await mcp.call_tool(
        "web_search",
        {"query": "AI agent architecture 2026"}
    )
    print(f"\n工具调用结果: {result}")


if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
