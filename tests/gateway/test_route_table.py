"""
RouteTable 测试用例

测试路由表的核心功能
"""

import pytest
import sys
import os

# 添加项目根目录到 Python 路径
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '../..'))
sys.path.insert(0, project_root)
os.environ.setdefault("AUTORESEARCH_TG_CHAT_ID", "-1001234567890")

from src.gateway.route_table import RouteTable

for _route in RouteTable.DEFAULT_ROUTES.values():
    _route["chat_id"] = -1001234567890


class TestRouteTable:
    """RouteTable 测试类"""
    
    def test_initialization_with_default_routes(self):
        """测试使用默认路由初始化"""
        route_table = RouteTable()
        
        assert len(route_table.routes) == 4
        assert "intelligence" in route_table.routes
        assert "content" in route_table.routes
        assert "security" in route_table.routes
        assert "user_input" in route_table.routes
    
    def test_initialization_with_custom_routes(self):
        """测试使用自定义路由初始化"""
        custom_routes = {
            "test": {
                "chat_id": -1009999999999,
                "thread_id": 99,
                "description": "测试路由",
                "enabled": True
            }
        }
        
        route_table = RouteTable(routes=custom_routes)
        
        assert len(route_table.routes) == 1
        assert "test" in route_table.routes
        assert route_table.routes["test"]["chat_id"] == -1009999999999
    
    def test_get_route_success(self):
        """测试成功获取路由"""
        route_table = RouteTable()
        route = route_table.get_route("intelligence")
        
        assert route is not None
        assert route["chat_id"] == -1001234567890
        assert route["thread_id"] == 4
        assert route["description"] == "市场情报话题"
    
    def test_get_route_unknown_type(self):
        """测试获取不存在的路由类型"""
        route_table = RouteTable()
        route = route_table.get_route("unknown")
        
        assert route is None
    
    def test_get_route_disabled(self):
        """测试获取已禁用的路由"""
        route_table = RouteTable()
        route_table.disable_route("intelligence")
        
        route = route_table.get_route("intelligence")
        
        assert route is None
    
    def test_add_route_success(self):
        """测试成功添加新路由"""
        route_table = RouteTable()
        
        result = route_table.add_route(
            "testing",
            -1001111111111,
            30,
            "测试话题"
        )
        
        assert result is True
        assert "testing" in route_table.routes
        assert route_table.routes["testing"]["chat_id"] == -1001111111111
    
    def test_add_route_duplicate(self):
        """测试添加重复路由"""
        route_table = RouteTable()
        
        result = route_table.add_route(
            "intelligence",
            -1001111111111,
            30,
            "重复测试"
        )
        
        assert result is False
    
    def test_update_route_success(self):
        """测试成功更新路由"""
        route_table = RouteTable()
        
        result = route_table.update_route(
            "intelligence",
            description="更新后的描述"
        )
        
        assert result is True
        assert route_table.routes["intelligence"]["description"] == "更新后的描述"
    
    def test_update_route_nonexistent(self):
        """测试更新不存在的路由"""
        route_table = RouteTable()
        
        result = route_table.update_route("unknown", description="测试")
        
        assert result is False
    
    def test_disable_route(self):
        """测试禁用路由"""
        route_table = RouteTable()
        
        result = route_table.disable_route("intelligence")
        
        assert result is True
        assert route_table.routes["intelligence"]["enabled"] is False
    
    def test_enable_route(self):
        """测试启用路由"""
        route_table = RouteTable()
        route_table.disable_route("intelligence")
        
        result = route_table.enable_route("intelligence")
        
        assert result is True
        assert route_table.routes["intelligence"]["enabled"] is True
    
    def test_list_routes(self):
        """测试列出所有路由"""
        route_table = RouteTable()
        
        routes = route_table.list_routes()
        
        assert len(routes) == 4
        assert all("type" in r for r in routes)
        assert all("chat_id" in r for r in routes)
    
    def test_get_backup_route_with_thread(self):
        """测试获取有话题 ID 的路由的备份路由"""
        route_table = RouteTable()
        
        backup = route_table.get_backup_route("intelligence")
        
        assert backup is not None
        assert backup["chat_id"] == -1001234567890
        assert backup["thread_id"] == 104  # 4 + 100
    
    def test_get_backup_route_without_thread(self):
        """测试获取无话题 ID 的路由的备份路由"""
        route_table = RouteTable(routes={
            "group_only": {
                "chat_id": -1001234567890,
                "thread_id": None,
                "description": "群组消息",
                "enabled": True,
            }
        })
        
        backup = route_table.get_backup_route("group_only")
        
        assert backup is None  # 无 thread_id 的路由没有备份
    
    def test_validate_routes_success(self):
        """测试路由验证成功"""
        # 正常情况下不应抛出异常
        route_table = RouteTable()
        route_table._validate_routes()
        
        assert True  # 如果到达这里说明验证通过
    
    def test_validate_routes_missing_chat_id(self):
        """测试路由验证失败（缺少 chat_id）"""
        invalid_routes = {
            "test": {
                "thread_id": 10,
                "description": "无效路由"
            }
        }
        
        with pytest.raises(ValueError, match="missing chat_id"):
            RouteTable(routes=invalid_routes)
    
    def test_validate_routes_invalid_chat_id_type(self):
        """测试路由验证失败（chat_id 类型错误）"""
        invalid_routes = {
            "test": {
                "chat_id": "not_an_int",
                "thread_id": 10,
                "description": "无效路由"
            }
        }
        
        with pytest.raises(ValueError, match="chat_id must be integer"):
            RouteTable(routes=invalid_routes)

    def test_add_route_with_none_thread_id(self):
        """测试新增无话题 ID 的群组路由"""
        route_table = RouteTable(routes={})

        result = route_table.add_route("group_only", -1002222222222, None)

        assert result is True
        assert route_table.get_route("group_only")["thread_id"] is None

    def test_update_route_multiple_fields(self):
        """测试同时更新多个路由字段"""
        route_table = RouteTable(routes={
            "test": {
                "chat_id": -1001234567890,
                "thread_id": 10,
                "description": "测试",
                "enabled": True,
            }
        })

        result = route_table.update_route("test", chat_id=-1009999999999, thread_id=99)

        assert result is True
        assert route_table.get_route("test")["chat_id"] == -1009999999999
        assert route_table.get_route("test")["thread_id"] == 99

    def test_disable_nonexistent_route_returns_false(self):
        """测试禁用不存在的路由返回 False"""
        route_table = RouteTable(routes={})

        assert route_table.disable_route("missing") is False

    def test_enable_nonexistent_route_returns_false(self):
        """测试启用不存在的路由返回 False"""
        route_table = RouteTable(routes={})

        assert route_table.enable_route("missing") is False

    def test_get_backup_route_disabled_returns_none(self):
        """测试已禁用路由不生成备份路由"""
        route_table = RouteTable(routes={
            "test": {
                "chat_id": -1001234567890,
                "thread_id": 10,
                "description": "测试",
                "enabled": False,
            }
        })

        assert route_table.get_backup_route("test") is None

    def test_validate_routes_invalid_thread_id_type(self):
        """测试路由验证失败（thread_id 类型错误）"""
        invalid_routes = {
            "test": {
                "chat_id": -1001234567890,
                "thread_id": "not_an_int",
                "description": "无效路由",
            }
        }

        with pytest.raises(ValueError, match="thread_id must be integer"):
            RouteTable(routes=invalid_routes)
