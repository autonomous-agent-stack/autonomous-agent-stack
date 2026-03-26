"""
Universal OpenSpace Adapter
职责：对接 HKUDS/OpenSpace 框架，管理基于 Markdown SOP 的技能生命周期，替换原有的 Python 动态执行模式。

注意：OpenSpace 实际 API（v0.1.0）与描述不同，这里使用真实接口进行适配。
"""
import logging
from pathlib import Path
from typing import Dict, Any, Optional
import asyncio

# 适配现有的原生异步 API 引擎（提供超时熔断与自动重试保障）
from autoresearch.core.services.claude_api_adapter import ClaudeAPIAdapter

try:
    from openspace import OpenSpace, OpenSpaceConfig
    OPENSPACE_AVAILABLE = True
except ImportError:
    OPENSPACE_AVAILABLE = False
    OpenSpace, OpenSpaceConfig = None, None

logger = logging.getLogger(__name__)


class OpenSpaceAdapter:
    """
    OpenSpace 适配器，将 OpenSpace 框架集成到现有系统
    
    注意：由于 OpenSpace v0.1.0 的 API 与描述不一致，此适配器提供：
    1. 技能目录管理（SKILL.md 文件）
    2. 与 ClaudeAPIAdapter 的桥接
    3. 降级处理（当 OpenSpace 不可用时）
    """
    
    def __init__(self, skills_dir: str = "data/openspace_skills"):
        self.skills_dir = Path(skills_dir)
        self.skills_dir.mkdir(parents=True, exist_ok=True)
        self.llm_client = ClaudeAPIAdapter()
        
        # OpenSpace 实例（延迟初始化）
        self._openspace: Optional["OpenSpace"] = None
        
        if OPENSPACE_AVAILABLE:
            logger.info("[OpenSpace] 框架已加载，准备初始化...")
    
    def _get_openspace(self) -> Optional["OpenSpace"]:
        """延迟初始化 OpenSpace 实例"""
        if not OPENSPACE_AVAILABLE:
            return None
            
        if self._openspace is None:
            try:
                # 使用默认配置初始化 OpenSpace
                config = OpenSpaceConfig()
                self._openspace = OpenSpace(config)
                logger.info("[OpenSpace] 实例初始化成功")
            except Exception as e:
                logger.error(f"[OpenSpace] 初始化失败: {e}")
                return None
        
        return self._openspace
    
    async def execute_skill(
        self,
        intent: str,
        payload: Dict[str, Any],
        auto_learn: bool = True
    ) -> Dict[str, Any]:
        """
        执行技能流程
        
        Args:
            intent: 任务意图（技能匹配关键词）
            payload: 输入数据
            auto_learn: 是否在无技能时自动学习
        
        Returns:
            执行结果字典，包含 status、output/error、skill_used
        """
        openspace = self._get_openspace()
        
        if not openspace:
            return {
                "status": "error",
                "message": "未检测到 OpenSpace 框架，请先执行依赖安装。"
            }
        
        logger.info(f"[OpenSpace] 正在处理任务意图: {intent}")
        
        try:
            # 1. 尝试匹配现有技能
            skill_path = self._find_skill(intent)
            
            if skill_path:
                logger.info(f"[OpenSpace] 命中现有技能: {skill_path.name}")
                result = await self._execute_skill_file(skill_path, payload)
                return {
                    "status": "success" if result.get("success") else "error",
                    "output": result.get("output", result.get("error")),
                    "skill_used": skill_path.stem
                }
            
            # 2. 无技能时自动学习（如果启用）
            elif auto_learn:
                logger.info("[OpenSpace] 无匹配技能，触发 AUTO-LEARN...")
                new_skill_path = await self._learn_new_skill(intent, payload)
                
                if new_skill_path:
                    # 使用新技能执行
                    result = await self._execute_skill_file(new_skill_path, payload)
                    return {
                        "status": "success" if result.get("success") else "error",
                        "output": result.get("output", result.get("error")),
                        "skill_used": new_skill_path.stem
                    }
                else:
                    return {
                        "status": "error",
                        "message": "AUTO-LEARN 学习失败"
                    }
            
            else:
                return {
                    "status": "error",
                    "message": f"未找到匹配的技能: {intent}"
                }
        
        except Exception as e:
            logger.error(f"[OpenSpace] 执行失败: {str(e)}")
            return {
                "status": "error",
                "message": str(e)
            }
    
    def _find_skill(self, intent: str) -> Optional[Path]:
        """在技能目录中查找匹配的 SKILL.md 文件"""
        # 简单实现：查找包含意图关键词的技能文件
        for skill_file in self.skills_dir.glob("**/*.md"):
            try:
                content = skill_file.read_text()
                if intent.lower() in content.lower():
                    return skill_file
            except Exception:
                continue
        return None
    
    async def _execute_skill_file(self, skill_path: Path, payload: Dict[str, Any]) -> Dict[str, Any]:
        """执行单个技能文件"""
        try:
            # 读取技能定义
            skill_content = skill_path.read_text()
            
            # 解析技能内容（简化版：实际应解析 YAML + SOP）
            # 这里我们调用 Claude API 来执行技能描述
            messages = [
                {
                    "role": "user",
                    "content": f"""根据以下技能定义执行任务：

技能文件：{skill_path.name}

{skill_content}

输入数据：{payload}

请严格按照技能定义的标准作业程序（SOP）执行任务。"""
                }
            ]
            
            result = await self.llm_client.call(
                messages=messages,
                model="claude-3-5-sonnet-20241022",
                max_tokens=4096,
                temperature=0.7
            )
            
            if result["status"] == "success":
                return {
                    "success": True,
                    "output": result["content"]
                }
            else:
                return {
                    "success": False,
                    "error": result.get("error", "Unknown error")
                }
        
        except Exception as e:
            logger.error(f"[OpenSpace] 执行技能文件失败: {str(e)}")
            return {
                "success": False,
                "error": str(e)
            }
    
    async def _learn_new_skill(self, intent: str, payload: Dict[str, Any]) -> Optional[Path]:
        """从零学习新技能（AUTO-LEARN）"""
        try:
            # 使用 Claude API 生成技能定义
            messages = [
                {
                    "role": "user",
                    "content": f"""请为以下任务生成一个标准的技能定义（SKILL.md 格式）：

任务意图：{intent}
输入数据示例：{payload}

请按照以下格式生成：

---
name: <技能名称（snake_case）>
version: 1.0.0
intent: <任务意图描述>

# 标准作业程序 (SOP)

步骤 1: <步骤名称>
  - 执行内容：...
  - 约束条件：...

步骤 2: <步骤名称>
  - 执行内容：...
  - 约束条件：...

# 执行历史

[初始创建] 自动学习生成
---
"""
                }
            ]
            
            result = await self.llm_client.call(
                messages=messages,
                model="claude-3-5-sonnet-20241022",
                max_tokens=4096,
                temperature=0.7
            )
            
            if result["status"] == "success":
                # 保存技能文件
                skill_name = intent.lower().replace(" ", "_").replace("：", "_")[:50]
                skill_path = self.skills_dir / f"{skill_name}.md"
                skill_path.write_text(result["content"])
                
                logger.info(f"[OpenSpace] 新技能已保存: {skill_path}")
                return skill_path
            
            return None
        
        except Exception as e:
            logger.error(f"[OpenSpace] 学习新技能失败: {str(e)}")
            return None
    
    def list_skills(self) -> list[str]:
        """列出所有可用的技能"""
        if not self.skills_dir.exists():
            return []
        
        return [
            f.stem for f in self.skills_dir.glob("*.md")
            if not f.name.startswith("_")
        ]
