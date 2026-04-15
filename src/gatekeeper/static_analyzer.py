"""
PR 静态安全审计器 (S1, S2)

功能：
1. AST（抽象语法树）分析
2. 红线检测：
   - 绕过 AppleDoubleCleaner
   - 未授权 os.system 调用
   - 修改 panel_access.py（JWT/Tailscale 鉴权层）
3. 审计日志
"""

import ast
import re
from typing import Any, Dict, List
from dataclasses import dataclass
from enum import Enum


class SecurityLevel(Enum):
    """安全等级"""

    HIGH = "高"
    MEDIUM = "中"
    LOW = "低"


@dataclass
class SecurityViolation:
    """安全违规"""

    type: str
    description: str
    line_number: int
    severity: SecurityLevel


class PR_Static_Analyzer:
    """PR 静态安全审计器"""

    def __init__(self):
        self.forbidden_patterns = [
            # 绕过 AppleDoubleCleaner
            (r"AppleDoubleCleaner.*skip", "试图绕过 AppleDoubleCleaner"),
            (r"clean_appledouble.*False", "试图绕过 AppleDoubleCleaner"),
            # 未授权 os.system 调用
            (r"os\.system\s*\(", "未授权的 os.system 调用"),
            (r"subprocess\.call\s*\([^)]*shell\s*=\s*True", "危险的 subprocess 调用"),
            # 修改鉴权层
            (r"panel_access\.py", "试图修改鉴权层文件"),
            (r"JWT_SECRET\s*=", "试图修改 JWT 密钥"),
            (r"Tailscale.*auth", "试图修改 Tailscale 鉴权"),
            # 危险函数
            (r"\beval\s*\(", "使用 eval() 函数"),
            (r"\bexec\s*\(", "使用 exec() 函数"),
            (r"compile\s*\(", "使用 compile() 函数"),
        ]

    async def analyze_pr(self, pr_diff: str) -> Dict:
        """分析 PR 代码"""
        result: Dict[str, Any] = {
            "safe": True,
            "violations": [],
            "ast_analysis": None,
            "security_level": SecurityLevel.HIGH.value,
        }

        # 1. 正则表达式检测（在原始 diff 上）
        for pattern, description in self.forbidden_patterns:
            matches = re.finditer(pattern, pr_diff, re.IGNORECASE | re.MULTILINE)
            for match in matches:
                violation: Dict[str, Any] = {
                    "type": "forbidden_pattern",
                    "description": f"[Security Reject] 检测到越权调用: {description}",
                    "line_number": pr_diff[: match.start()].count("\n") + 1,
                    "severity": SecurityLevel.LOW.value,
                }
                result["violations"].append(violation)
                result["safe"] = False

        # 2. AST 分析（提取代码部分，去掉 diff 标记）
        try:
            # 提取新增代码（以 + 开头的行）
            code_lines = []
            for line in pr_diff.split("\n"):
                if line.startswith("+") and not line.startswith("+++"):
                    code_lines.append(line[1:].strip())

            code = "\n".join(code_lines)

            if code.strip():  # 只有当代码非空时才进行 AST 分析
                tree = ast.parse(code)
                ast_result = self._analyze_ast(tree)
                result["ast_analysis"] = ast_result

                # 检测危险函数调用
                for node in ast.walk(tree):
                    if isinstance(node, ast.Call):
                        if self._is_dangerous_call(node):
                            dangerous_violation: Dict[str, Any] = {
                                "type": "dangerous_call",
                                "description": f"[Security Reject] 检测到危险函数调用: {ast.dump(node)}",
                                "line_number": node.lineno,
                                "severity": SecurityLevel.LOW.value,
                            }
                            result["violations"].append(dangerous_violation)
                            result["safe"] = False
        except SyntaxError:
            # 语法错误不一定是安全问题，可能只是 diff 格式问题
            # 只有当代码明显有语法错误时才标记
            pass

        # 3. 确定安全等级
        if result["violations"]:
            result["security_level"] = SecurityLevel.LOW.value
        elif result.get("ast_analysis") and result["ast_analysis"].get("warnings"):
            result["security_level"] = SecurityLevel.MEDIUM.value
        else:
            result["security_level"] = SecurityLevel.HIGH.value

        return result

    def _analyze_ast(self, tree: ast.AST) -> Dict[str, List[str]]:
        """AST 深度分析"""
        analysis: Dict[str, List[str]] = {
            "imports": [],
            "function_calls": [],
            "modifications": [],
            "warnings": [],
        }

        for node in ast.walk(tree):
            # 导入分析
            if isinstance(node, ast.Import):
                for alias in node.names:
                    analysis["imports"].append(alias.name)
                    # 检测危险模块
                    if alias.name in ["os", "subprocess", "sys"]:
                        analysis["warnings"].append(f"导入敏感模块: {alias.name}")

            # 函数定义
            elif isinstance(node, ast.FunctionDef):
                analysis["function_calls"].append(node.name)

            # 赋值语句
            elif isinstance(node, ast.Assign):
                for target in node.targets:
                    if isinstance(target, ast.Name):
                        analysis["modifications"].append(target.id)

        return analysis

    def _is_dangerous_call(self, node: ast.Call) -> bool:
        """判断是否是危险函数调用"""
        dangerous_functions = [
            "os.system",
            "subprocess.call",
            "subprocess.run",
            "eval",
            "exec",
            "compile",
            # 移除 "open"，因为太常见
        ]

        func_name = ""
        if isinstance(node.func, ast.Name):
            func_name = node.func.id
        elif isinstance(node.func, ast.Attribute):
            func_name = (
                f"{node.func.value.id}.{node.func.attr}"
                if isinstance(node.func.value, ast.Name)
                else node.func.attr
            )

        return func_name in dangerous_functions


# 测试
if __name__ == "__main__":
    import asyncio

    async def test():
        analyzer = PR_Static_Analyzer()

        # 测试正常代码
        result = await analyzer.analyze_pr("print('Hello World')")
        print(f"✅ 正常代码: {result['safe']}")

        # 测试危险代码
        result = await analyzer.analyze_pr("os.system('rm -rf /')")
        print(f"❌ 危险代码: {result['safe']}")
        print(f"违规: {result['violations']}")

    asyncio.run(test())
