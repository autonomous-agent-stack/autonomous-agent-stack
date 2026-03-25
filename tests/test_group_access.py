import pytest
from src.security.group_access import GroupAccessManager, MembershipStatus

def test_load_internal_groups():
    """测试加载内部群组"""
    import os
    os.environ["AUTORESEARCH_INTERNAL_GROUPS"] = "[-10012345678, -10098765432]"
    
    manager = GroupAccessManager("test-secret")
    assert len(manager.internal_groups) == 2
    assert -10012345678 in manager.internal_groups

def test_is_internal_group():
    """测试判断内部群"""
    manager = GroupAccessManager("test-secret")
    manager.internal_groups = [-10012345678]
    
    assert manager.is_internal_group(-10012345678) is True
    assert manager.is_internal_group(-10099999999) is False

def test_generate_magic_link():
    """测试生成魔法链接"""
    manager = GroupAccessManager("test-secret")
    manager.internal_groups = [-10012345678]
    
    # 内部群
    link = manager.generate_magic_link(123456, -10012345678)
    assert "token=" in link
    
    # 解析JWT验证scope
    import jwt
    token = link.split("token=")[1]
    payload = jwt.decode(token, "test-secret", algorithms=["HS256"])
    assert payload["scope"] == "group"

def test_is_access_allowed():
    """测试访问权限判断"""
    manager = GroupAccessManager("test-secret")
    
    # 允许访问的状态
    assert manager.is_access_allowed(MembershipStatus.MEMBER) is True
    assert manager.is_access_allowed(MembershipStatus.ADMINISTRATOR) is True
    assert manager.is_access_allowed(MembershipStatus.CREATOR) is True
    
    # 拒绝访问的状态
    assert manager.is_access_allowed(MembershipStatus.LEFT) is False
    assert manager.is_access_allowed(MembershipStatus.KICKED) is False
    assert manager.is_access_allowed(MembershipStatus.UNKNOWN) is False

@pytest.mark.asyncio
async def test_log_access():
    """测试审计日志"""
    manager = GroupAccessManager("test-secret")
    
    await manager.log_access(-10012345678, 123456, "test_action", "allowed")
    
    assert len(manager.audit_logs) == 1
    assert manager.audit_logs[0].chat_id == -10012345678
    assert manager.audit_logs[0].user_id == 123456

if __name__ == "__main__":
    pytest.main([__file__, "-v"])
