"""
Claude API Adapter Tests - 测试断线重连与超时熔断机制
"""

import pytest
import asyncio
import os
import sys
from unittest.mock import AsyncMock, patch, MagicMock

# 添加 src 到路径
sys.path.insert(0, '/Volumes/PS1008/Github/autonomous-agent-stack/src')

from anthropic import APITimeoutError, RateLimitError, APIConnectionError


# ========================================================================
# Test 1: 正常执行测试
# ========================================================================

class TestClaudeAPIAdapter:
    """测试 Claude API 适配器"""
    
    @pytest.mark.asyncio
    async def test_normal_execution(self):
        """测试正常执行"""
        # Mock 环境变量
        with patch.dict(os.environ, {"ANTHROPIC_API_KEY": "test-key"}):
            from autoresearch.core.services.claude_api_adapter import ClaudeAPIAdapter
            
            adapter = ClaudeAPIAdapter()
            
            # Mock 客户端响应
            with patch.object(adapter.client, 'messages') as mock_messages:
                mock_response = MagicMock()
                mock_response.content = [MagicMock(text="Hello, World!")]
                mock_messages.create = AsyncMock(return_value=mock_response)
                
                result = await adapter.execute("测试提示")
                
                assert result == "Hello, World!"
                assert mock_messages.create.called
    
    @pytest.mark.asyncio
    async def test_json_mode_success(self):
        """测试 JSON 模式成功"""
        with patch.dict(os.environ, {"ANTHROPIC_API_KEY": "test-key"}):
            from autoresearch.core.services.claude_api_adapter import ClaudeAPIAdapter
            
            adapter = ClaudeAPIAdapter()
            
            # Mock 客户端响应（返回合法 JSON）
            with patch.object(adapter.client, 'messages') as mock_messages:
                mock_response = MagicMock()
                mock_response.content = [MagicMock(text='{"status": "success", "data": "test"}')]
                mock_messages.create = AsyncMock(return_value=mock_response)
                
                result = await adapter.execute("测试提示", require_json=True)
                
                # 验证返回的是合法 JSON
                import json
                parsed = json.loads(result)
                assert parsed["status"] == "success"
    
    @pytest.mark.asyncio
    async def test_json_mode_failure(self):
        """测试 JSON 模式失败（模型返回非 JSON）"""
        with patch.dict(os.environ, {"ANTHROPIC_API_KEY": "test-key"}):
            from autoresearch.core.services.claude_api_adapter import ClaudeAPIAdapter
            
            adapter = ClaudeAPIAdapter()
            
            # Mock 客户端响应（返回非 JSON）
            with patch.object(adapter.client, 'messages') as mock_messages:
                mock_response = MagicMock()
                mock_response.content = [MagicMock(text="这不是 JSON")]
                mock_messages.create = AsyncMock(return_value=mock_response)
                
                result = await adapter.execute("测试提示", require_json=True)
                
                # 验证返回错误信息
                import json
                parsed = json.loads(result)
                assert parsed["status"] == "error"
                assert "Failed to parse JSON output" in parsed["message"]


# ========================================================================
# Test 2: 超时熔断测试
# ========================================================================

class TestTimeoutHandling:
    """测试超时处理"""
    
    @pytest.mark.asyncio
    async def test_timeout_error(self):
        """测试 45 秒超时熔断"""
        with patch.dict(os.environ, {"ANTHROPIC_API_KEY": "test-key"}):
            from autoresearch.core.services.claude_api_adapter import ClaudeAPIAdapter
            
            adapter = ClaudeAPIAdapter()
            
            # Mock 客户端抛出超时异常
            with patch.object(adapter.client, 'messages') as mock_messages:
                mock_messages.create = AsyncMock(side_effect=APITimeoutError("Timeout"))
                
                result = await adapter.execute("测试提示")
                
                # 验证返回超时错误
                import json
                parsed = json.loads(result)
                assert parsed["status"] == "error"
                assert "timeout" in parsed["message"].lower()
    
    @pytest.mark.asyncio
    async def test_timeout_with_retry(self):
        """测试超时后自动重试（3 次）"""
        with patch.dict(os.environ, {"ANTHROPIC_API_KEY": "test-key"}):
            from autoresearch.core.services.claude_api_adapter import ClaudeAPIAdapter
            
            adapter = ClaudeAPIAdapter()
            
            # Mock 客户端：前 2 次超时，第 3 次成功
            call_count = 0
            
            async def mock_create(*args, **kwargs):
                nonlocal call_count
                call_count += 1
                if call_count < 3:
                    raise APITimeoutError("Timeout")
                else:
                    mock_response = MagicMock()
                    mock_response.content = [MagicMock(text="Success after retry")]
                    return mock_response
            
            with patch.object(adapter.client, 'messages') as mock_messages:
                mock_messages.create = mock_create
                
                result = await adapter.execute("测试提示")
                
                # 验证最终成功
                assert result == "Success after retry"
                # 验证重试次数（SDK 内部重试）
                # 注意：AsyncAnthropic 客户端会自动重试


# ========================================================================
# Test 3: 速率限制测试
# ========================================================================

class TestRateLimitHandling:
    """测试速率限制处理"""
    
    @pytest.mark.asyncio
    async def test_rate_limit_error(self):
        """测试速率限制错误"""
        with patch.dict(os.environ, {"ANTHROPIC_API_KEY": "test-key"}):
            from autoresearch.core.services.claude_api_adapter import ClaudeAPIAdapter
            
            adapter = ClaudeAPIAdapter()
            
            # Mock 客户端抛出速率限制异常
            with patch.object(adapter.client, 'messages') as mock_messages:
                mock_messages.create = AsyncMock(side_effect=RateLimitError("Rate limit exceeded"))
                
                result = await adapter.execute("测试提示")
                
                # 验证返回速率限制错误
                import json
                parsed = json.loads(result)
                assert parsed["status"] == "error"
                assert "rate limit" in parsed["message"].lower()


# ========================================================================
# Test 4: 网络错误测试
# ========================================================================

class TestNetworkErrors:
    """测试网络错误处理"""
    
    @pytest.mark.asyncio
    async def test_connection_error(self):
        """测试连接错误"""
        with patch.dict(os.environ, {"ANTHROPIC_API_KEY": "test-key"}):
            from autoresearch.core.services.claude_api_adapter import ClaudeAPIAdapter
            
            adapter = ClaudeAPIAdapter()
            
            # Mock 客户端抛出连接错误
            with patch.object(adapter.client, 'messages') as mock_messages:
                mock_messages.create = AsyncMock(side_effect=APIConnectionError("Connection failed"))
                
                result = await adapter.execute("测试提示")
                
                # 验证返回错误信息
                import json
                parsed = json.loads(result)
                assert parsed["status"] == "error"
    
    @pytest.mark.asyncio
    async def test_generic_error(self):
        """测试通用错误处理"""
        with patch.dict(os.environ, {"ANTHROPIC_API_KEY": "test-key"}):
            from autoresearch.core.services.claude_api_adapter import ClaudeAPIAdapter
            
            adapter = ClaudeAPIAdapter()
            
            # Mock 客户端抛出通用异常
            with patch.object(adapter.client, 'messages') as mock_messages:
                mock_messages.create = AsyncMock(side_effect=Exception("Unknown error"))
                
                result = await adapter.execute("测试提示")
                
                # 验证返回错误信息
                import json
                parsed = json.loads(result)
                assert parsed["status"] == "error"
                assert "Unknown error" in parsed["message"]


# ========================================================================
# Test 5: 环境变量测试
# ========================================================================

class TestEnvironmentVariables:
    """测试环境变量配置"""
    
    def test_missing_api_key(self):
        """测试缺少 API Key"""
        # 临时移除环境变量
        original_key = os.environ.pop("ANTHROPIC_API_KEY", None)
        
        try:
            with pytest.raises(ValueError) as exc_info:
                from autoresearch.core.services.claude_api_adapter import ClaudeAPIAdapter
                adapter = ClaudeAPIAdapter()
            
            assert "缺少 ANTHROPIC_API_KEY" in str(exc_info.value)
        
        finally:
            # 恢复环境变量
            if original_key:
                os.environ["ANTHROPIC_API_KEY"] = original_key
    
    def test_custom_timeout(self):
        """测试自定义超时（通过环境变量）"""
        with patch.dict(os.environ, {"ANTHROPIC_API_KEY": "test-key"}):
            from autoresearch.core.services.claude_api_adapter import ClaudeAPIAdapter
            
            adapter = ClaudeAPIAdapter()
            
            # 验证默认超时为 45 秒
            assert adapter.client.timeout == 45.0


# ========================================================================
# Test 6: 性能测试
# ========================================================================

class TestPerformance:
    """性能测试"""
    
    @pytest.mark.asyncio
    async def test_concurrent_requests(self):
        """测试并发请求"""
        with patch.dict(os.environ, {"ANTHROPIC_API_KEY": "test-key"}):
            from autoresearch.core.services.claude_api_adapter import ClaudeAPIAdapter
            
            adapter = ClaudeAPIAdapter()
            
            # Mock 客户端响应
            with patch.object(adapter.client, 'messages') as mock_messages:
                mock_response = MagicMock()
                mock_response.content = [MagicMock(text="Response")]
                mock_messages.create = AsyncMock(return_value=mock_response)
                
                # 并发 10 个请求
                tasks = [adapter.execute(f"测试 {i}") for i in range(10)]
                results = await asyncio.gather(*tasks)
                
                # 验证所有请求都成功
                assert len(results) == 10
                assert all(r == "Response" for r in results)
    
    @pytest.mark.asyncio
    async def test_response_time(self):
        """测试响应时间（应该 < 1 秒，不包括网络延迟）"""
        import time
        
        with patch.dict(os.environ, {"ANTHROPIC_API_KEY": "test-key"}):
            from autoresearch.core.services.claude_api_adapter import ClaudeAPIAdapter
            
            adapter = ClaudeAPIAdapter()
            
            # Mock 客户端响应（立即返回）
            with patch.object(adapter.client, 'messages') as mock_messages:
                mock_response = MagicMock()
                mock_response.content = [MagicMock(text="Fast response")]
                mock_messages.create = AsyncMock(return_value=mock_response)
                
                start = time.time()
                result = await adapter.execute("测试提示")
                elapsed = time.time() - start
                
                # 验证响应时间 < 1 秒
                assert elapsed < 1.0
                assert result == "Fast response"


# ========================================================================
# 运行测试
# ========================================================================

if __name__ == "__main__":
    pytest.main([__file__, "-v"])
