"""
Skill Registry - 可插拔技能注册表

支持从远端 URL 下载技能，并动态挂载
"""

import asyncio
import json
import logging
import zipfile
import tempfile
from pathlib import Path
from typing import Dict, Any, Optional, List
from dataclasses import dataclass
from datetime import datetime
import aiohttp
import importlib.util
import hashlib

logger = logging.getLogger(__name__)


@dataclass
class Skill:
    """技能对象"""
    skill_id: str
    name: str
    version: str
    description: str
    url: Optional[str]
    installed_at: datetime
    enabled: bool
    module: Optional[Any] = None


class SkillRegistry:
    """技能注册表"""

    def __init__(self, skills_dir: str = "./skills"):
        self.skills_dir = Path(skills_dir)
        self.skills_dir.mkdir(parents=True, exist_ok=True)
        self.registry: Dict[str, Skill] = {}
        self._load_local_skills()

    def _load_local_skills(self):
        """加载本地技能"""
        for skill_dir in self.skills_dir.iterdir():
            if skill_dir.is_dir() and (skill_dir / "skill.json").exists():
                try:
                    with open(skill_dir / "skill.json") as f:
                        manifest = json.load(f)

                    skill_id = manifest.get("id", skill_dir.name)
                    self.registry[skill_id] = Skill(
                        skill_id=skill_id,
                        name=manifest.get("name", skill_id),
                        version=manifest.get("version", "0.0.0"),
                        description=manifest.get("description", ""),
                        url=None,
                        installed_at=datetime.now(),
                        enabled=True
                    )

                    logger.info(f"[SkillRegistry] 📦 已加载本地技能: {skill_id}")

                except Exception as e:
                    logger.error(f"[SkillRegistry] ❌ 加载失败 {skill_dir}: {e}")

    async def fetch_skill_manifest(self, url: str) -> Optional[Dict[str, Any]]:
        """获取技能清单"""
        try:
            # 尝试获取 skill.json
            manifest_url = f"{url.rstrip('/')}/skill.json"

            async with aiohttp.ClientSession() as session:
                async with session.get(manifest_url, timeout=10) as response:
                    if response.status == 200:
                        manifest = await response.json()
                        logger.info(f"[SkillRegistry] 📋 获取清单成功: {url}")
                        return manifest
                    else:
                        logger.warning(f"[SkillRegistry] ⚠️ 清单不存在: {url}")
                        return None

        except Exception as e:
            logger.error(f"[SkillRegistry] ❌ 获取清单失败: {e}")
            return None

    async def download_skill(self, url: str) -> Optional[str]:
        """下载技能（.zip 或 .py）"""
        try:
            # 确定下载类型
            if url.endswith(".zip"):
                return await self._download_zip(url)
            elif url.endswith(".py"):
                return await self._download_py(url)
            else:
                # 尝试下载 zip
                zip_url = f"{url.rstrip('/')}/archive.zip"
                return await self._download_zip(zip_url)

        except Exception as e:
            logger.error(f"[SkillRegistry] ❌ 下载失败: {e}")
            return None

    async def _download_zip(self, url: str) -> Optional[str]:
        """下载 ZIP 文件"""
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url, timeout=30) as response:
                    if response.status != 200:
                        logger.error(f"[SkillRegistry] ❌ 下载失败: HTTP {response.status}")
                        return None

                    # 保存到临时文件
                    with tempfile.NamedTemporaryFile(suffix=".zip", delete=False) as tmp:
                        tmp.write(await response.read())
                        tmp_path = tmp.name

                    # 解压
                    skill_id = Path(url).stem
                    skill_dir = self.skills_dir / skill_id

                    with zipfile.ZipFile(tmp_path, 'r') as zip_ref:
                        zip_ref.extractall(skill_dir)

                    # 清理临时文件
                    Path(tmp_path).unlink()

                    logger.info(f"[SkillRegistry] ✅ ZIP 已解压: {skill_id}")
                    return skill_id

        except Exception as e:
            logger.error(f"[SkillRegistry] ❌ ZIP 下载失败: {e}")
            return None

    async def _download_py(self, url: str) -> Optional[str]:
        """下载单个 Python 文件"""
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url, timeout=10) as response:
                    if response.status != 200:
                        logger.error(f"[SkillRegistry] ❌ 下载失败: HTTP {response.status}")
                        return None

                    # 保存文件
                    skill_id = Path(url).stem
                    skill_dir = self.skills_dir / skill_id
                    skill_dir.mkdir(parents=True, exist_ok=True)

                    skill_file = skill_dir / f"{skill_id}.py"
                    skill_file.write_bytes(await response.read())

                    logger.info(f"[SkillRegistry] ✅ Python 已下载: {skill_id}")
                    return skill_id

        except Exception as e:
            logger.error(f"[SkillRegistry] ❌ Python 下载失败: {e}")
            return None

    async def validate_skill(self, skill_id: str) -> bool:
        """验证技能（AST 审计）"""
        try:
            skill_dir = self.skills_dir / skill_id

            if not skill_dir.exists():
                logger.error(f"[SkillRegistry] ❌ 技能不存在: {skill_id}")
                return False

            # 扫描所有 Python 文件
            for py_file in skill_dir.rglob("*.py"):
                if not await self._validate_py_file(py_file):
                    logger.error(f"[SkillRegistry] ❌ 验证失败: {py_file}")
                    return False

            logger.info(f"[SkillRegistry] ✅ 技能验证通过: {skill_id}")
            return True

        except Exception as e:
            logger.error(f"[SkillRegistry] ❌ 验证异常: {e}")
            return False

    async def _validate_py_file(self, py_file: Path) -> bool:
        """验证 Python 文件（AST 审计）"""
        import ast

        try:
            code = py_file.read_text(encoding="utf-8", errors="ignore")
            tree = ast.parse(code)

            # 危险函数黑名单
            blacklist = {
                'eval', 'exec', 'compile', '__import__',
                'os.system', 'subprocess.call', 'subprocess.Popen'
            }

            for node in ast.walk(tree):
                if isinstance(node, ast.Name):
                    if node.id in blacklist:
                        logger.warning(f"[SkillRegistry] ⚠️ 危险函数: {node.id}")
                        return False

            return True

        except Exception as e:
            logger.error(f"[SkillRegistry] ❌ AST 扫描失败: {e}")
            return False

    async def install_skill(self, url: str) -> Optional[str]:
        """安装技能"""
        try:
            # 获取清单
            manifest = await self.fetch_skill_manifest(url)

            # 下载技能
            skill_id = await self.download_skill(url)
            if not skill_id:
                return None

            # 验证技能
            if not await self.validate_skill(skill_id):
                logger.error(f"[SkillRegistry] ❌ 安装失败（验证不通过）: {skill_id}")
                return None

            # 动态挂载
            await self._mount_skill(skill_id)

            # 注册到列表
            self.registry[skill_id] = Skill(
                skill_id=skill_id,
                name=manifest.get("name", skill_id) if manifest else skill_id,
                version=manifest.get("version", "0.0.0") if manifest else "0.0.0",
                description=manifest.get("description", "") if manifest else "",
                url=url,
                installed_at=datetime.now(),
                enabled=True
            )

            logger.info(f"[SkillRegistry] 🎉 技能已安装: {skill_id}")
            return skill_id

        except Exception as e:
            logger.error(f"[SkillRegistry] ❌ 安装失败: {e}")
            return None

    async def _mount_skill(self, skill_id: str):
        """动态挂载技能"""
        try:
            skill_dir = self.skills_dir / skill_id
            skill_file = skill_dir / f"{skill_id}.py"

            if not skill_file.exists():
                # 查找第一个 .py 文件
                py_files = list(skill_dir.glob("*.py"))
                if py_files:
                    skill_file = py_files[0]
                else:
                    logger.error(f"[SkillRegistry] ❌ 无 Python 文件: {skill_id}")
                    return

            # 动态加载
            spec = importlib.util.spec_from_file_location(skill_id, skill_file)
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)

            # 注册模块
            if skill_id in self.registry:
                self.registry[skill_id].module = module

            logger.info(f"[SkillRegistry] 🔌 已挂载: {skill_id}")

        except Exception as e:
            logger.error(f"[SkillRegistry] ❌ 挂载失败: {e}")

    def list_skills(self) -> List[Skill]:
        """列出所有技能"""
        return list(self.registry.values())

    async def execute_skill(self, skill_id: str, *args, **kwargs) -> Any:
        """执行技能"""
        skill = self.registry.get(skill_id)

        if not skill:
            raise ValueError(f"技能不存在: {skill_id}")

        if not skill.enabled:
            raise ValueError(f"技能未启用: {skill_id}")

        if not skill.module:
            raise ValueError(f"技能未挂载: {skill_id}")

        try:
            # 调用 execute 函数
            if hasattr(skill.module, "execute"):
                result = await skill.module.execute(*args, **kwargs)
                logger.info(f"[SkillRegistry] ✅ 执行成功: {skill_id}")
                return result
            else:
                raise ValueError(f"技能缺少 execute 函数: {skill_id}")

        except Exception as e:
            logger.error(f"[SkillRegistry] ❌ 执行失败: {e}")
            raise


# 单例实例
_skill_registry: Optional[SkillRegistry] = None


def get_skill_registry() -> SkillRegistry:
    """获取技能注册表单例"""
    global _skill_registry
    if _skill_registry is None:
        _skill_registry = SkillRegistry()
    return _skill_registry
