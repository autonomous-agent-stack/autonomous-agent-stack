"""
Bridge API - OpenClaw 任务接收与委派核心

支持：
- 双向鉴权（credentials_ref 解耦调用）
- 接收 OpenClaw 任务
- 对接 Codex 登录与任务委派
"""

from __future__ import annotations

import logging
import asyncio
from typing import Any, Dict, Optional
from pathlib import Path
from datetime import datetime
import hashlib
import json

from .codex_client import CodexClient
from .skill_loader import SkillLoader

logger = logging.getLogger("agent_stack.bridge")


class CredentialsRef:
    """凭证引用 - 解耦敏感凭证的间接引用"""

    def __init__(self, ref_id: str, ref_type: str = "token", metadata: Optional[Dict] = None):
        self.ref_id = ref_id
        self.ref_type = ref_type  # token, api_key, oauth, etc.
        self.metadata = metadata or {}
        self.created_at = datetime.now()

    def to_dict(self) -> Dict:
        return {
            "ref_id": self.ref_id,
            "ref_type": self.ref_type,
            "metadata": self.metadata,
            "created_at": self.created_at.isoformat(),
        }

    @classmethod
    def from_dict(cls, data: Dict) -> "CredentialsRef":
        return cls(
            ref_id=data["ref_id"],
            ref_type=data.get("ref_type", "token"),
            metadata=data.get("metadata", {}),
        )


class BridgeAPI:
    """
    Bridge API - OpenClaw 与外部系统的双向桥梁

    核心功能：
    1. 接收来自 OpenClaw 的任务
    2. 通过 credentials_ref 解耦敏感凭证
    3. 委派任务给 Codex 或外部 Skill
    4. 返回执行结果
    """

    def __init__(
        self,
        codex_endpoint: Optional[str] = None,
        skill_base_path: Optional[Path] = None,
        enable_security_scan: bool = True,
    ):
        """
        初始化 Bridge API

        Args:
            codex_endpoint: Codex 服务端点
            skill_base_path: Skill 基础路径
            enable_security_scan: 是否启用安全扫描
        """
        self.codex_endpoint = codex_endpoint
        self.skill_base_path = skill_base_path or Path.cwd()
        self.enable_security_scan = enable_security_scan

        # 初始化客户端
        self.codex_client = CodexClient(endpoint=codex_endpoint)
        self.skill_loader = SkillLoader(
            base_path=self.skill_base_path,
            enable_security_scan=enable_security_scan,
        )

        # 凭证存储（内存中，生产环境应使用加密存储）
        self._credentials_store: Dict[str, Dict] = {}

        logger.info("[Agent-Stack-Bridge] Bridge API initialized")

    async def receive_task(self, task: Dict[str, Any]) -> Dict[str, Any]:
        """
        接收 OpenClaw 任务

        Args:
            task: 任务字典，包含：
                - task_id: 任务 ID
                - task_type: 任务类型 (codex, skill, direct)
                - credentials_ref: 凭证引用
                - payload: 任务负载
                - options: 可选参数

        Returns:
            执行结果字典
        """
        logger.info(f"[Agent-Stack-Bridge] Task received from OpenClaw: {task.get('task_id')}")

        # 验证任务结构
        self._validate_task(task)

        # 提取凭证引用
        credentials_ref = task.get("credentials_ref")
        if credentials_ref:
            credentials = await self._resolve_credentials(credentials_ref)
        else:
            credentials = None

        # 根据任务类型路由
        task_type = task.get("task_type", "direct")

        try:
            if task_type == "codex":
                result = await self.delegate_to_codex(
                    task=task,
                    credentials=credentials,
                )
            elif task_type == "skill":
                result = await self.delegate_to_skill(
                    task=task,
                    credentials=credentials,
                )
            else:
                # direct 类型，直接处理
                result = await self.handle_direct_task(
                    task=task,
                    credentials=credentials,
                )

            logger.info(f"[Agent-Stack-Bridge] Task completed: {task.get('task_id')}")
            return {
                "status": "success",
                "task_id": task.get("task_id"),
                "result": result,
                "timestamp": datetime.now().isoformat(),
            }

        except Exception as e:
            logger.error(f"[Agent-Stack-Bridge] Task failed: {task.get('task_id')}, error: {str(e)}")
            return {
                "status": "error",
                "task_id": task.get("task_id"),
                "error": str(e),
                "timestamp": datetime.now().isoformat(),
            }

    async def delegate_to_codex(
        self,
        task: Dict[str, Any],
        credentials: Optional[Dict] = None,
    ) -> Dict[str, Any]:
        """
        委派任务给 Codex

        Args:
            task: 任务字典
            credentials: 解析后的凭证

        Returns:
            Codex 执行结果
        """
        logger.info("[Agent-Stack-Bridge] Delegating task to Codex")

        # 确保 Codex 已登录
        if not self.codex_client.is_authenticated():
            if credentials:
                await self.codex_client.login(credentials)
            else:
                raise ValueError("Codex not authenticated and no credentials provided")

        # 委派任务
        result = await self.codex_client.delegate_task(task["payload"])

        logger.info("[Agent-Stack-Bridge] Codex task completed")
        return result

    async def delegate_to_skill(
        self,
        task: Dict[str, Any],
        credentials: Optional[Dict] = None,
    ) -> Dict[str, Any]:
        """
        委派任务给外部 Skill

        Args:
            task: 任务字典
            credentials: 解析后的凭证

        Returns:
            Skill 执行结果
        """
        logger.info("[Agent-Stack-Bridge] Delegating task to Skill")

        skill_path = task["payload"].get("skill_path")
        if not skill_path:
            raise ValueError("skill_path is required for skill tasks")

        # 加载 Skill
        skill = await self.skill_loader.load_skill(skill_path)

        # 执行 Skill
        result = await skill.execute(task["payload"], credentials=credentials)

        logger.info(f"[Agent-Stack-Bridge] Skill task completed: {skill_path}")
        return result

    async def handle_direct_task(
        self,
        task: Dict[str, Any],
        credentials: Optional[Dict] = None,
    ) -> Dict[str, Any]:
        """
        处理直接任务（不委派给 Codex 或 Skill）

        Args:
            task: 任务字典
            credentials: 解析后的凭证

        Returns:
            执行结果
        """
        logger.info("[Agent-Stack-Bridge] Handling direct task")

        # 直接任务的处理逻辑
        payload = task.get("payload", {})

        # 示例：简单的回显任务
        if payload.get("action") == "echo":
            return {"echo": payload.get("message", "")}

        # 示例：健康检查
        if payload.get("action") == "health_check":
            return {
                "status": "healthy",
                "bridge_version": "0.1.0",
                "codex_connected": self.codex_client.is_authenticated(),
            }

        raise ValueError(f"Unknown direct task action: {payload.get('action')}")

    def _validate_task(self, task: Dict[str, Any]) -> None:
        """验证任务结构"""
        required_fields = ["task_id", "task_type"]
        for field in required_fields:
            if field not in task:
                raise ValueError(f"Missing required field: {field}")

        if "payload" not in task:
            raise ValueError("Missing required field: payload")

    async def _resolve_credentials(
        self,
        credentials_ref: Dict[str, Any],
    ) -> Optional[Dict]:
        """
        解析凭证引用

        Args:
            credentials_ref: 凭证引用字典

        Returns:
            解析后的凭证
        """
        ref = CredentialsRef.from_dict(credentials_ref)
        logger.info(f"[Agent-Stack-Bridge] Resolving credentials: {ref.ref_id}")

        # 从存储中获取凭证
        if ref.ref_id in self._credentials_store:
            return self._credentials_store[ref.ref_id]

        # 如果没有找到，返回 None（由具体实现决定如何处理）
        logger.warning(f"[Agent-Stack-Bridge] Credentials not found: {ref.ref_id}")
        return None

    def register_credentials(
        self,
        ref_id: str,
        credentials: Dict[str, Any],
    ) -> CredentialsRef:
        """
        注册凭证（用于测试）

        Args:
            ref_id: 凭证引用 ID
            credentials: 凭证数据

        Returns:
            CredentialsRef 对象
        """
        self._credentials_store[ref_id] = credentials
        return CredentialsRef(ref_id=ref_id)

    async def cleanup(self) -> None:
        """清理资源"""
        logger.info("[Agent-Stack-Bridge] Cleaning up resources")
        await self.codex_client.logout()
