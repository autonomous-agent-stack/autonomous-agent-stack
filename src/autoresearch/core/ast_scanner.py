"""AST Security Scanner - 安全哨兵

静态安全审计，阻断越权调用
"""

import ast
import logging
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


@dataclass
class SecurityViolation:
    """安全违规"""
    severity: str  # high, medium, low
    category: str  # file_access, network, system_call, etc
    description: str
    line_number: int
    code_snippet: str
    timestamp: datetime = field(default_factory=datetime.now)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "severity": self.severity,
            "category": self.category,
            "description": self.description,
            "line_number": self.line_number,
            "code_snippet": self.code_snippet,
            "timestamp": self.timestamp.isoformat(),
        }


@dataclass
class ScanResult:
    """扫描结果"""
    status: str  # passed, failed, warning
    violations: List[SecurityViolation] = field(default_factory=list)
    scanned_files: int = 0
    scan_time: float = 0.0
    timestamp: datetime = field(default_factory=datetime.now)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "status": self.status,
            "violations": [v.to_dict() for v in self.violations],
            "scanned_files": self.scanned_files,
            "scan_time": self.scan_time,
            "timestamp": self.timestamp.isoformat(),
        }


class ASTScanner:
    """AST 静态安全扫描器
    
    工程红线：
    - 禁止执行未经 AST 扫描的外部 Python 代码
    - 使用 logger.info("[环境防御] ...") 记录所有操作
    """
    
    # 危险函数黑名单
    DANGEROUS_FUNCTIONS = {
        # 系统调用
        "os.system",
        "os.popen",
        "subprocess.call",
        "subprocess.run",
        "subprocess.Popen",
        "eval",
        "exec",
        "compile",
        
        # 文件操作
        "os.remove",
        "os.unlink",
        "shutil.rmtree",
        
        # 网络操作
        "socket.socket",
        "urllib.request.urlopen",
        
        # 环境变量
        "os.environ",
    }
    
    # 危险模块黑名单
    DANGEROUS_MODULES = {
        "pickle",
        "marshal",
        "shelve",
        "ctypes",
    }
    
    def __init__(self):
        self.violations: List[SecurityViolation] = []
        
    async def scan_code(self, code: str, filename: str = "<unknown>") -> ScanResult:
        """扫描 Python 代码
        
        Args:
            code: Python 代码
            filename: 文件名
            
        Returns:
            扫描结果
        """
        logger.info(f"[环境防御] AST 扫描: {filename}")
        
        start_time = datetime.now()
        self.violations = []
        
        try:
            # 解析 AST
            tree = ast.parse(code, filename=filename)
            
            # 遍历 AST
            for node in ast.walk(tree):
                await self._check_node(node, code)
                
        except SyntaxError as e:
            # 语法错误
            self.violations.append(SecurityViolation(
                severity="high",
                category="syntax_error",
                description=f"语法错误: {e.msg}",
                line_number=e.lineno or 0,
                code_snippet=""
            ))
            
        # 计算扫描时间
        scan_time = (datetime.now() - start_time).total_seconds()
        
        # 确定状态
        status = "passed"
        if any(v.severity == "high" for v in self.violations):
            status = "failed"
        elif any(v.severity == "medium" for v in self.violations):
            status = "warning"
            
        logger.info(f"[环境防御] AST 扫描完成: {status}, {len(self.violations)} 违规")
        
        return ScanResult(
            status=status,
            violations=self.violations,
            scanned_files=1,
            scan_time=scan_time
        )
        
    async def _check_node(self, node: ast.AST, code: str):
        """检查 AST 节点"""
        
        # 检查函数调用
        if isinstance(node, ast.Call):
            await self._check_function_call(node, code)
            
        # 检查导入
        elif isinstance(node, (ast.Import, ast.ImportFrom)):
            await self._check_import(node, code)
            
        # 检查属性访问
        elif isinstance(node, ast.Attribute):
            await self._check_attribute(node, code)
            
    async def _check_function_call(self, node: ast.Call, code: str):
        """检查函数调用"""
        
        # 获取函数名
        func_name = self._get_full_name(node.func)
        
        if func_name in self.DANGEROUS_FUNCTIONS:
            self.violations.append(SecurityViolation(
                severity="high",
                category="dangerous_function",
                description=f"禁止调用危险函数: {func_name}",
                line_number=node.lineno,
                code_snippet=self._get_code_line(code, node.lineno)
            ))
            
    async def _check_import(self, node: ast.AST, code: str):
        """检查导入"""
        
        modules = []
        
        if isinstance(node, ast.Import):
            modules = [alias.name for alias in node.names]
        elif isinstance(node, ast.ImportFrom):
            modules = [node.module] if node.module else []
            
        for module in modules:
            if module in self.DANGEROUS_MODULES:
                self.violations.append(SecurityViolation(
                    severity="high",
                    category="dangerous_module",
                    description=f"禁止导入危险模块: {module}",
                    line_number=node.lineno,
                    code_snippet=self._get_code_line(code, node.lineno)
                ))
                
    async def _check_attribute(self, node: ast.Attribute, code: str):
        """检查属性访问"""
        
        # 检查 os.environ
        if isinstance(node.value, ast.Attribute):
            if self._get_full_name(node.value) == "os" and node.attr == "environ":
                self.violations.append(SecurityViolation(
                    severity="medium",
                    category="environment_access",
                    description="访问环境变量需要审批",
                    line_number=node.lineno,
                    code_snippet=self._get_code_line(code, node.lineno)
                ))
                
    def _get_full_name(self, node: ast.AST) -> str:
        """获取完整名称"""
        
        if isinstance(node, ast.Name):
            return node.id
        elif isinstance(node, ast.Attribute):
            return f"{self._get_full_name(node.value)}.{node.attr}"
        else:
            return ""
            
    def _get_code_line(self, code: str, line_number: int) -> str:
        """获取代码行"""
        
        lines = code.split("\n")
        if 0 < line_number <= len(lines):
            return lines[line_number - 1].strip()
        return ""
