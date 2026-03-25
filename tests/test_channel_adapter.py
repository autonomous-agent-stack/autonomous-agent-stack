import pytest
from src.adapters.channel_adapter import ChannelAdapter

def test_twa_interface():
    """测试TWA接口"""
    adapter = ChannelAdapter()
    data = adapter.get_twa_data(session_id="test123")
    assert "nodes" in data
    assert len(data["nodes"]) > 0

def test_jwt_magic_link():
    """测试魔法链接JWT验证"""
    adapter = ChannelAdapter()
    token = adapter.generate_magic_link(chat_id="test_chat")
    assert token is not None
    # 验证token
    payload = adapter.verify_magic_link(token)
    assert payload["chat_id"] == "test_chat"

def test_light_dashboard():
    """测试浅色看板数据输出"""
    adapter = ChannelAdapter()
    dashboard = adapter.render_light_dashboard(session_id="test123")
    assert "nodes" in dashboard
    assert "session" in dashboard
    # 验证数据结构
    for node in dashboard["nodes"]:
        assert "id" in node
        assert "status" in node
        assert "progress" in node

def test_telegram_webhook_error_handling():
    """测试Telegram Webhook错误处理"""
    adapter = ChannelAdapter()
    # 模拟无效请求
    with pytest.raises(ValueError):
        adapter.handle_webhook(data={})

if __name__ == "__main__":
    pytest.main([__file__, "-v"])
