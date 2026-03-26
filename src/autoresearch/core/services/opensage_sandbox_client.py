"""OpenSage Sandbox Client - 与沙盒容器通信的客户端"""

from __future__ import annotations

import logging
import docker
from typing import Dict, Any, Optional
import httpx
import asyncio

logger = logging.getLogger(__name__)


class OpenSageSandboxClient:
    """OpenSage 沙盒客户端"""
    
    def __init__(
        self,
        sandbox_image: str = "opensage-sandbox:latest",
        cpu_limit: float = 0.5,  # 50% CPU
        memory_limit: str = "512m",  # 512MB
        timeout_seconds: int = 30,
        network_disabled: bool = True,
    ):
        self.sandbox_image = sandbox_image
        self.cpu_limit = cpu_limit
        self.memory_limit = memory_limit
        self.timeout_seconds = timeout_seconds
        self.network_disabled = network_disabled
        self.docker_client = docker.from_env()
        self._container: Optional[docker.models.containers.Container] = None
    
    def start_sandbox(self):
        """启动沙盒容器"""
        try:
            logger.info(f"🚀 启动沙盒容器（镜像: {self.sandbox_image}）")
            
            # 启动容器
            self._container = self.docker_client.containers.run(
                self.sandbox_image,
                detach=True,
                cpu_period=100000,  # 100ms
                cpu_quota=int(100000 * self.cpu_limit),  # 50% CPU
                mem_limit=self.memory_limit,  # 512MB
                network_disabled=self.network_disabled,  # 禁用网络
                ports={'9000/tcp': None},  # 随机端口
                remove=True,  # 自动清理
            )
            
            # 等待容器启动
            asyncio.sleep(2)
            
            # 获取容器端口
            container_info = self._container.attrs
            port_bindings = container_info['NetworkSettings']['Ports']
            sandbox_port = port_bindings['9000/tcp'][0]['HostPort']
            
            self.sandbox_url = f"http://127.0.0.1:{sandbox_port}"
            
            logger.info(f"✅ 沙盒容器已启动（URL: {self.sandbox_url}）")
            
            return True
        
        except Exception as e:
            logger.error(f"❌ 启动沙盒失败: {e}")
            return False
    
    def stop_sandbox(self):
        """停止沙盒容器"""
        if self._container:
            try:
                self._container.stop()
                logger.info("✅ 沙盒容器已停止")
            except Exception as e:
                logger.error(f"❌ 停止沙盒失败: {e}")
    
    async def execute_code(
        self,
        code: str,
        timeout_seconds: Optional[int] = None,
    ) -> Dict[str, Any]:
        """执行代码（通过沙盒）"""
        
        if not self._container:
            raise RuntimeError("沙盒容器未启动")
        
        timeout = timeout_seconds or self.timeout_seconds
        
        try:
            async with httpx.AsyncClient(timeout=timeout + 5) as client:
                response = await client.post(
                    f"{self.sandbox_url}/api/v1/execute",
                    json={
                        "code": code,
                        "timeout_seconds": timeout,
                    }
                )
                
                if response.status_code == 200:
                    return response.json()
                else:
                    return {
                        "success": False,
                        "error": f"HTTP {response.status_code}: {response.text}"
                    }
        
        except httpx.TimeoutException:
            return {
                "success": False,
                "error": f"请求超时（{timeout}秒）"
            }
        
        except Exception as e:
            return {
                "success": False,
                "error": f"执行异常: {str(e)}"
            }


# ========================================================================
# 修改后的 OpenSageEngine
# ========================================================================

class OpenSageEngineV2:
    """OpenSage 动态演化引擎 V2（安全沙盒版）"""
    
    def __init__(self):
        self.sandbox_client = OpenSageSandboxClient()
        self._sandbox_started = False
    
    def start_sandbox(self):
        """启动沙盒"""
        if not self._sandbox_started:
            success = self.sandbox_client.start_sandbox()
            if success:
                self._sandbox_started = True
            else:
                raise RuntimeError("无法启动沙盒容器")
    
    def stop_sandbox(self):
        """停止沙盒"""
        if self._sandbox_started:
            self.sandbox_client.stop_sandbox()
            self._sandbox_started = False
    
    async def synthesize_tool(self, code_snippet: str) -> Dict[str, Any]:
        """动态将 LLM 生成的代码片段转化为临时工具（安全沙盒版）"""
        
        # 1. 确保 AST 审计通过（第一道防线）
        dangerous_keywords = ["os.system", "subprocess.call", "eval", "exec", "__import__"]
        for keyword in dangerous_keywords:
            if keyword in code_snippet:
                return {"status": "blocked", "reason": f"Dangerous keyword: {keyword}"}
        
        # 2. 确保沙盒已启动
        if not self._sandbox_started:
            self.start_sandbox()
        
        # 3. 在沙盒中执行代码（第二道防线：物理隔离）
        result = await self.sandbox_client.execute_code(code_snippet)
        
        if result["success"]:
            # 执行成功，保存代码
            import tempfile
            temp_tool_path = tempfile.mktemp(suffix=".py")
            
            with open(temp_tool_path, 'w') as f:
                f.write(code_snippet)
            
            return {
                "status": "success",
                "path": temp_tool_path,
                "execution_time": result["execution_time_seconds"]
            }
        else:
            # 执行失败
            return {
                "status": "failed",
                "reason": result["error"]
            }
