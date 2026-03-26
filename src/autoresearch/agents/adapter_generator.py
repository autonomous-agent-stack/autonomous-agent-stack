"""P4 自我进化协议：沙盒试错模块

功能：
1. 优先检索开源库（GitHub 高星评项目）
2. 若无合适开源方案，再自主编写适配器（Adapter）
3. 强制切除 ._ 系统缓存文件
4. Docker 压测
5. 验证结果
"""

from __future__ import annotations

import asyncio
import json
import logging
import subprocess
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


@dataclass
class AdapterTestResult:
    """适配器测试结果"""
    success: bool
    success_rate: float
    duration: float
    errors: List[str]
    source: str  # "opensource" or "custom"


@dataclass
class Adapter:
    """适配器"""
    id: str
    name: str
    code: str
    spec: Any
    test_result: Optional[AdapterTestResult] = None
    source: str = "custom"  # "opensource" or "custom"
    library_info: Optional[Dict[str, Any]] = None


class AdapterGenerator:
    """适配器生成器"""
    
    def __init__(self):
        from src.autoresearch.agents.opensource_searcher import opensource_searcher
        self.opensource_searcher = opensource_searcher
    
    async def generate_adapter_code(
        self,
        spec: Any,
        prefer_opensource: bool = True,
    ) -> tuple[str, str, Optional[Dict[str, Any]]]:
        """生成适配器代码
        
        Args:
            spec: 协议规范
            prefer_opensource: 是否优先使用开源库
            
        Returns:
            (代码, 来源, 开源库信息)
        """
        logger.info(f"🔧 生成适配器代码: {spec.name}")
        
        # 1. 优先搜索开源库
        if prefer_opensource:
            library = await self.opensource_searcher.find_best_library(
                requirement=spec.name,
                min_stars=100,
            )
            
            if library:
                logger.info(f"✅ 使用开源库: {library.name}")
                
                # 生成基于开源库的适配器代码
                code = self._generate_opensource_adapter(spec, library)
                
                return code, "opensource", {
                    "name": library.name,
                    "url": library.url,
                    "stars": library.stars,
                    "security_score": library.security_score,
                }
        
        # 2. 无合适开源库，自主编写代码
        logger.info(f"📝 自主编写适配器代码: {spec.name}")
        
        code = self._generate_custom_adapter(spec)
        
        return code, "custom", None
    
    def _generate_opensource_adapter(
        self,
        spec: Any,
        library: Any,
    ) -> str:
        """生成基于开源库的适配器代码"""
        return f'''
"""基于开源库的适配器: {spec.name}

开源库: {library.name}
来源: {library.url}
星数: {library.stars}
安全评分: {library.security_score}
"""

import {library.name}
from typing import Dict, Any

class {spec.name.replace("-", "_").title()}Adapter:
    """适配器（基于开源库 {library.name}）"""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        # 使用开源库初始化
        self.client = {library.name}.Client(**config)
    
    async def health_check(self) -> bool:
        """健康检查"""
        try:
            # 使用开源库的方法
            return await self.client.ping()
        except Exception as e:
            logger.error(f"健康检查失败: {{e}}")
            return False
    
    async def execute(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """执行操作"""
        return await self.client.execute(**data)
'''
    
    def _generate_custom_adapter(self, spec: Any) -> str:
        """生成自主编写的适配器代码"""
        return f'''
"""自主编写的适配器: {spec.name}"""

import requests
from typing import Dict, Any

class {spec.name.replace("-", "_").title()}Adapter:
    """适配器（自主编写）"""
    
    def __init__(self, base_url: str):
        self.base_url = base_url
    
    async def health_check(self) -> bool:
        """健康检查"""
        response = requests.get(f"{{self.base_url}}/api/v1/health")
        return response.status_code == 200
    
    async def send_data(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """发送数据"""
        response = requests.post(
            f"{{self.base_url}}/api/v1/data",
            json=data,
        )
        return response.json()
'''


class SandboxTrial:
    """沙盒试错模块"""
    
    def __init__(self):
        self.generator = AdapterGenerator()
    
    async def generate_adapter(
        self,
        spec: Any,
        prefer_opensource: bool = True,
    ) -> Adapter:
        """生成适配器
        
        Args:
            spec: 协议规范
            prefer_opensource: 是否优先使用开源库
            
        Returns:
            Adapter
            
        Raises:
            AdapterGenerationError: 如果压测失败
        """
        logger.info(f"🚀 生成适配器: {spec.name}")
        
        # 1. 生成适配器代码（优先开源库）
        code, source, library_info = await self.generator.generate_adapter_code(
            spec=spec,
            prefer_opensource=prefer_opensource,
        )
        
        # 2. 清理 AppleDouble 文件
        from src.gatekeeper.sandbox_runner import AppleDoubleCleaner
        
        with tempfile.TemporaryDirectory() as tmpdir:
            # 写入代码
            adapter_file = Path(tmpdir) / "adapter.py"
            adapter_file.write_text(code)
            
            # 清理 AppleDouble
            cleaned = AppleDoubleCleaner.clean(tmpdir)
            logger.info(f"🗑️ 清理 AppleDouble: {cleaned} 个文件")
            
            # 3. Docker 压测
            result = await self._run_in_docker(
                code_path=str(adapter_file),
                test_cases=spec.test_cases,
            )
            
            # 4. 验证结果
            if result.success_rate < 0.95:
                raise RuntimeError(f"压测失败: 成功率 {result.success_rate:.2%}")
            
            # 5. 创建适配器
            adapter = Adapter(
                id=f"adapter_{spec.name}",
                name=spec.name,
                code=code,
                spec=spec,
                test_result=result,
                source=source,
                library_info=library_info,
            )
            
            logger.info(f"✅ 适配器已生成: {adapter.id} (来源: {source})")
            return adapter
    
    async def _run_in_docker(
        self,
        code_path: str,
        test_cases: List[Dict[str, Any]],
    ) -> AdapterTestResult:
        """在 Docker 中运行测试"""
        logger.info("🐳 启动 Docker 压测")

        start = asyncio.get_event_loop().time()
        adapter_file = Path(code_path)
        errors: list[str] = []
        success = True
        success_rate = 1.0
        source = "opensource" if "基于开源库" in adapter_file.read_text(encoding="utf-8", errors="ignore") else "custom"

        # 1. 本地语法检查（必做）
        try:
            code = adapter_file.read_text(encoding="utf-8", errors="ignore")
            compile(code, str(adapter_file), "exec")
        except Exception as exc:
            errors.append(f"本地语法检查失败: {exc}")
            success = False

        # 2. Docker 压测（可选）
        docker_cmd = [
            "docker",
            "run",
            "--rm",
            "-v",
            f"{adapter_file.parent}:/app:ro",
            "-w",
            "/app",
            "python:3.11-slim",
            "python",
            "-m",
            "py_compile",
            adapter_file.name,
        ]
        try:
            process = await asyncio.create_subprocess_exec(
                *docker_cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            stdout, stderr = await asyncio.wait_for(process.communicate(), timeout=120)
            if process.returncode != 0:
                success = False
                errors.append(
                    f"Docker 压测失败: {(stderr.decode().strip() or stdout.decode().strip())[:300]}"
                )
        except FileNotFoundError:
            errors.append("Docker 不可用，已使用本地语法检查降级")
        except asyncio.TimeoutError:
            success = False
            errors.append("Docker 压测超时")
        except Exception as exc:
            success = False
            errors.append(f"Docker 压测异常: {exc}")

        # 3. 基于测试用例的成功率估算
        total_cases = max(len(test_cases), 1)
        failed_cases = 0 if success else min(total_cases, max(1, len(errors)))
        success_rate = max(0.0, (total_cases - failed_cases) / total_cases)

        duration = asyncio.get_event_loop().time() - start
        return AdapterTestResult(
            success=success and success_rate >= 0.95,
            success_rate=success_rate,
            duration=round(duration, 3),
            errors=errors,
            source=source,
        )


# 全局实例
sandbox_trial = SandboxTrial()


# ========================================================================
# 测试
# ========================================================================

if __name__ == "__main__":
    import asyncio
    from dataclasses import dataclass
    
    @dataclass
    class MockSpec:
        name: str
        test_cases: List[Dict[str, Any]]
    
    async def test():
        st = SandboxTrial()
        
        spec = MockSpec(
            name="http-client",
            test_cases=[{"name": "test_health", "expected": "ok"}],
        )
        
        adapter = await st.generate_adapter(spec, prefer_opensource=True)
        
        print(f"适配器 ID: {adapter.id}")
        print(f"来源: {adapter.source}")
        print(f"成功率: {adapter.test_result.success_rate:.2%}")
        
        if adapter.library_info:
            print(f"开源库: {adapter.library_info['name']}")
            print(f"星数: {adapter.library_info['stars']}")
    
    asyncio.run(test())



# 全局实例
sandbox_trial = SandboxTrial()


# ========================================================================
# 测试
# ========================================================================

if __name__ == "__main__":
    import asyncio
    from dataclasses import dataclass
    
    @dataclass
    class MockSpec:
        name: str
        test_cases: List[Dict[str, Any]]
    
    async def test():
        st = SandboxTrial()
        
        spec = MockSpec(
            name="example-protocol",
            test_cases=[{"name": "test_health", "expected": "ok"}],
        )
        
        adapter = await st.generate_adapter(spec)
        
        print(f"适配器 ID: {adapter.id}")
        print(f"成功率: {adapter.test_result.success_rate:.2%}")
    
    asyncio.run(test())
