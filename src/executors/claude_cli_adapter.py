"""Claude CLI Adapter - Claude CLI 执行器适配

通过 subprocess 封装 claude 命令行工具
"""

import asyncio
import json
import subprocess
import logging
from typing import Optional, AsyncIterator, List, Dict, Any

logger = logging.getLogger(__name__)


class ClaudeCLIAdapter:
    """Claude CLI 适配器"""
    
    def __init__(
        self,
        cli_path: str = "claude",
        model: str = "claude-3-5-sonnet-20241022",
        timeout: int = 300
    ):
        self.cli_path = cli_path
        self.model = model
        self.timeout = timeout
        self._validate_cli()
        
    def _validate_cli(self):
        """验证 Claude CLI 是否可用"""
        try:
            result = subprocess.run(
                [self.cli_path, "--version"],
                capture_output=True,
                text=True,
                timeout=5
            )
            if result.returncode == 0:
                logger.info(f"✅ Claude CLI 可用: {result.stdout.strip()}")
            else:
                logger.warning(f"⚠️ Claude CLI 返回非零状态: {result.stderr}")
        except FileNotFoundError:
            logger.warning(f"⚠️ Claude CLI 未找到: {self.cli_path}")
        except subprocess.TimeoutExpired:
            logger.warning("⚠️ Claude CLI 验证超时")
            
    async def execute(
        self,
        prompt: str,
        context: Optional[List[Dict[str, str]]] = None,
        system: Optional[str] = None
    ) -> str:
        """执行 Claude CLI
        
        Args:
            prompt: 用户输入
            context: 对话上下文（历史消息）
            system: 系统提示
            
        Returns:
            Claude 的响应
        """
        logger.info(f"[Claude CLI] 执行任务: {prompt[:50]}...")
        
        # 构建命令
        cmd = [self.cli_path]
        
        # 添加模型参数
        cmd.extend(["--model", self.model])
        
        # 添加系统提示
        if system:
            cmd.extend(["--system", system])
            
        # 构建完整提示（包含上下文）
        full_prompt = prompt
        if context:
            context_str = "\n".join([
                f"{msg['role']}: {msg['content']}"
                for msg in context
            ])
            full_prompt = f"{context_str}\n\nuser: {prompt}"
            
        # 执行命令
        try:
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdin=asyncio.subprocess.PIPE,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            
            stdout, stderr = await asyncio.wait_for(
                process.communicate(full_prompt.encode()),
                timeout=self.timeout
            )
            
            if process.returncode == 0:
                response = stdout.decode().strip()
                logger.info(f"[Claude CLI] 执行成功: {len(response)} 字符")
                return response
            else:
                error = stderr.decode().strip()
                logger.error(f"[Claude CLI] 执行失败: {error}")
                raise RuntimeError(f"Claude CLI 失败: {error}")
                
        except asyncio.TimeoutError:
            logger.error(f"[Claude CLI] 执行超时 ({self.timeout}s)")
            raise TimeoutError(f"Claude CLI 执行超时 ({self.timeout}s)")
            
    async def stream(
        self,
        prompt: str,
        context: Optional[List[Dict[str, str]]] = None,
        system: Optional[str] = None
    ) -> AsyncIterator[str]:
        """流式执行 Claude CLI
        
        Args:
            prompt: 用户输入
            context: 对话上下文
            system: 系统提示
            
        Yields:
            生成的文本片段
        """
        logger.info(f"[Claude CLI] 流式执行: {prompt[:50]}...")
        
        # 构建命令
        cmd = [self.cli_path, "--model", self.model, "--stream"]
        
        if system:
            cmd.extend(["--system", system])
            
        # 构建完整提示
        full_prompt = prompt
        if context:
            context_str = "\n".join([
                f"{msg['role']}: {msg['content']}"
                for msg in context
            ])
            full_prompt = f"{context_str}\n\nuser: {prompt}"
            
        # 执行流式命令
        try:
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdin=asyncio.subprocess.PIPE,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            
            # 写入输入
            process.stdin.write(full_prompt.encode())
            process.stdin.close()
            
            # 流式读取输出
            while True:
                line = await process.stdout.readline()
                if not line:
                    break
                    
                chunk = line.decode().strip()
                if chunk:
                    yield chunk
                    
            await process.wait()
            
            if process.returncode != 0:
                stderr = await process.stderr.read()
                error = stderr.decode().strip()
                logger.error(f"[Claude CLI] 流式执行失败: {error}")
                raise RuntimeError(f"Claude CLI 失败: {error}")
                
            logger.info("[Claude CLI] 流式执行完成")
            
        except asyncio.TimeoutError:
            logger.error(f"[Claude CLI] 流式执行超时 ({self.timeout}s)")
            raise TimeoutError(f"Claude CLI 执行超时 ({self.timeout}s)")
            
    async def execute_with_tools(
        self,
        prompt: str,
        tools: List[Dict[str, Any]],
        context: Optional[List[Dict[str, str]]] = None
    ) -> Dict[str, Any]:
        """执行带工具调用的任务
        
        Args:
            prompt: 用户输入
            tools: 工具列表
            context: 对话上下文
            
        Returns:
            包含响应和工具调用的结果
        """
        tool_calls = await self._collect_tool_calls(prompt, tools)
        augmented_prompt = prompt
        if tool_calls:
            tool_result_lines = []
            for call in tool_calls:
                tool_result_lines.append(
                    f"[tool:{call['name']}] args={json.dumps(call['arguments'], ensure_ascii=False)} "
                    f"result={json.dumps(call.get('result'), ensure_ascii=False)}"
                )
            augmented_prompt = f"{prompt}\n\n工具执行结果:\n" + "\n".join(tool_result_lines)

        response = await self.execute(augmented_prompt, context)
        tokens_used = self._estimate_tokens(augmented_prompt) + self._estimate_tokens(response)

        return {
            "response": response,
            "tool_calls": tool_calls,
            "tokens_used": tokens_used,
        }

    async def _collect_tool_calls(
        self,
        prompt: str,
        tools: List[Dict[str, Any]],
    ) -> List[Dict[str, Any]]:
        """从提示中提取并执行工具调用."""
        if not tools:
            return []

        indexed_tools: Dict[str, Dict[str, Any]] = {}
        for tool in tools:
            name = str(tool.get("name", "")).strip()
            if name:
                indexed_tools[name] = tool

        calls: List[Dict[str, Any]] = []
        for match in self._iter_tool_invocations(prompt):
            tool_name = match["name"]
            tool = indexed_tools.get(tool_name)
            if tool is None:
                calls.append(
                    {
                        "name": tool_name,
                        "arguments": match["arguments"],
                        "error": "tool_not_found",
                    }
                )
                continue

            callable_obj = tool.get("callable") or tool.get("function")
            if callable_obj is None:
                calls.append(
                    {
                        "name": tool_name,
                        "arguments": match["arguments"],
                        "error": "tool_callable_missing",
                    }
                )
                continue

            try:
                if asyncio.iscoroutinefunction(callable_obj):
                    result = await callable_obj(**match["arguments"])
                else:
                    result = await asyncio.to_thread(callable_obj, **match["arguments"])
                calls.append(
                    {
                        "name": tool_name,
                        "arguments": match["arguments"],
                        "result": result,
                    }
                )
            except Exception as exc:
                calls.append(
                    {
                        "name": tool_name,
                        "arguments": match["arguments"],
                        "error": str(exc),
                    }
                )
        return calls

    def _iter_tool_invocations(self, prompt: str) -> List[Dict[str, Any]]:
        """解析提示里的工具调用语法: [[tool:name {"k":"v"}]]."""
        import re

        pattern = re.compile(r"\[\[tool:(?P<name>[a-zA-Z0-9_\-]+)\s*(?P<args>\{.*?\})?\]\]")
        invocations: List[Dict[str, Any]] = []
        for match in pattern.finditer(prompt):
            name = match.group("name")
            raw_args = (match.group("args") or "{}").strip()
            try:
                arguments = json.loads(raw_args)
                if not isinstance(arguments, dict):
                    arguments = {}
            except json.JSONDecodeError:
                arguments = {}
            invocations.append({"name": name, "arguments": arguments})
        return invocations

    @staticmethod
    def _estimate_tokens(text: str) -> int:
        return max(1, len(text) // 4) if text else 0


# 单例实例
_claude_adapter: Optional[ClaudeCLIAdapter] = None


def get_claude_adapter() -> ClaudeCLIAdapter:
    """获取 Claude CLI 适配器单例"""
    global _claude_adapter
    if _claude_adapter is None:
        _claude_adapter = ClaudeCLIAdapter()
    return _claude_adapter
