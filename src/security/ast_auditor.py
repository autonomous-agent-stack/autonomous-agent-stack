"""
AST 静态审计器

通过 AST（抽象语法树）分析 Python 代码，检测潜在的安全风险。
"""

import ast
import logging
from typing import List, Dict, Any, Set, Optional
from dataclasses import dataclass, field
from enum import Enum

logger = logging.getLogger(__name__)


class Severity(Enum):
    """问题严重级别"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


@dataclass
class SecurityIssue:
    """安全问题"""
    line: int
    col: int
    function: str
    severity: Severity
    message: str
    code_snippet: Optional[str] = None


class ASTAuditor:
    """
    AST 静态代码审计器
    
    检测以下危险模式：
    - 危险函数调用（os.system, eval, exec, 等）
    - 不安全的模块导入
    - 动态代码执行
    - 敏感信息泄露风险
    """
    
    # 危险函数列表
    DANGEROUS_FUNCTIONS = {
        # 系统命令执行
        "os.system": Severity.CRITICAL,
        "os.popen": Severity.CRITICAL,
        "subprocess.call": Severity.HIGH,
        "subprocess.run": Severity.HIGH,
        "subprocess.Popen": Severity.HIGH,
        "subprocess.check_output": Severity.HIGH,
        "commands.getoutput": Severity.CRITICAL,
        
        # 动态代码执行
        "eval": Severity.CRITICAL,
        "exec": Severity.CRITICAL,
        "execfile": Severity.CRITICAL,
        "compile": Severity.HIGH,
        
        # 动态导入
        "__import__": Severity.HIGH,
        "importlib.import_module": Severity.MEDIUM,
        
        # 危险内置函数
        "globals": Severity.MEDIUM,
        "locals": Severity.MEDIUM,
        "vars": Severity.MEDIUM,
        "dir": Severity.LOW,
        
        # 反射相关
        "getattr": Severity.MEDIUM,
        "setattr": Severity.MEDIUM,
        "delattr": Severity.MEDIUM,
        "hasattr": Severity.LOW,
        
        # pickle（反序列化风险）
        "pickle.loads": Severity.CRITICAL,
        "pickle.load": Severity.CRITICAL,
        "cPickle.loads": Severity.CRITICAL,
        
        # yaml（代码执行风险）
        "yaml.load": Severity.HIGH,
        "yaml.unsafe_load": Severity.CRITICAL,
        
        # 其他
        "input": Severity.LOW,  # Python 2 中的 input() 相当于 eval()
        "raw_input": Severity.LOW,
    }
    
    # 危险模块列表
    DANGEROUS_MODULES = {
        "os": Severity.MEDIUM,
        "subprocess": Severity.MEDIUM,
        "sys": Severity.LOW,
        "ctypes": Severity.HIGH,
        "multiprocessing": Severity.MEDIUM,
        "threading": Severity.LOW,
        "socket": Severity.MEDIUM,
        "pickle": Severity.HIGH,
        "marshal": Severity.HIGH,
        "shelve": Severity.MEDIUM,
        "shlex": Severity.LOW,
        "pty": Severity.HIGH,
        "fcntl": Severity.HIGH,
    }
    
    def __init__(self, strict_mode: bool = False):
        """
        初始化审计器
        
        Args:
            strict_mode: 严格模式，降低严重级别阈值
        """
        self.strict_mode = strict_mode
        self._issues: List[SecurityIssue] = []
        self._imports: Set[str] = set()
        self._from_imports: Dict[str, str] = {}  # alias -> module
    
    def scan_code(self, code: str, filename: str = "<string>") -> dict:
        """
        扫描代码，检测危险调用
        
        Args:
            code: Python 代码字符串
            filename: 文件名（用于错误报告）
            
        Returns:
            {
                "safe": False,
                "issues": [
                    {
                        "line": 42,
                        "function": "os.system",
                        "severity": "high",
                        "message": "..."
                    }
                ],
                "imports": ["os", "subprocess"],
                "summary": {...}
            }
        """
        self._issues = []
        self._imports = set()
        self._from_imports = {}
        
        # 解析 AST
        try:
            tree = ast.parse(code, filename=filename)
        except SyntaxError as e:
            return {
                "safe": False,
                "issues": [{
                    "line": e.lineno or 0,
                    "col": e.offset or 0,
                    "function": "syntax_error",
                    "severity": "critical",
                    "message": f"语法错误: {e.msg}"
                }],
                "imports": [],
                "summary": {"total_issues": 1, "by_severity": {"critical": 1}}
            }
        
        # 执行审计
        self._audit_tree(tree, code)
        
        # 生成结果
        issues_data = [
            {
                "line": issue.line,
                "col": issue.col,
                "function": issue.function,
                "severity": issue.severity.value,
                "message": issue.message,
                "code_snippet": issue.code_snippet
            }
            for issue in self._issues
        ]
        
        summary = self._generate_summary()
        
        logger.info(
            f"[Agent-Stack-Bridge] AST scan complete: "
            f"{len(self._issues)} issues found"
        )
        
        return {
            "safe": len(self._issues) == 0,
            "issues": issues_data,
            "imports": list(self._imports),
            "summary": summary
        }
    
    def scan_file(self, filepath: str) -> dict:
        """
        扫描文件
        
        Args:
            filepath: 文件路径
            
        Returns:
            扫描结果
        """
        try:
            with open(filepath, "r", encoding="utf-8") as f:
                code = f.read()
            return self.scan_code(code, filename=filepath)
        except Exception as e:
            return {
                "safe": False,
                "issues": [{
                    "line": 0,
                    "col": 0,
                    "function": "file_error",
                    "severity": "critical",
                    "message": f"读取文件失败: {e}"
                }],
                "imports": [],
                "summary": {"total_issues": 1, "by_severity": {"critical": 1}}
            }
    
    def _audit_tree(self, tree: ast.AST, code: str) -> None:
        """审计 AST 树"""
        # 获取代码行用于片段提取
        code_lines = code.split("\n") if code else []
        
        for node in ast.walk(tree):
            # 检查导入
            if isinstance(node, ast.Import):
                self._check_import(node)
            elif isinstance(node, ast.ImportFrom):
                self._check_from_import(node)
            
            # 检查函数调用
            elif isinstance(node, ast.Call):
                self._check_function_call(node, code_lines)
            
            # 检查属性访问（如 os.system）
            elif isinstance(node, ast.Attribute):
                self._check_attribute_access(node, code_lines)
            
            # 检查名称使用（如 eval）
            elif isinstance(node, ast.Name):
                self._check_name_usage(node, code_lines)
    
    def check_imports(self, tree: ast.AST) -> List[str]:
        """
        检查导入的模块
        
        Args:
            tree: AST 树
            
        Returns:
            导入的模块列表
        """
        imports = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    imports.append(alias.name)
            elif isinstance(node, ast.ImportFrom):
                if node.module:
                    imports.append(node.module)
        return imports
    
    def check_function_calls(self, tree: ast.AST) -> List[dict]:
        """
        检查函数调用
        
        Args:
            tree: AST 树
            
        Returns:
            函数调用列表
        """
        calls = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Call):
                call_info = self._extract_call_info(node)
                if call_info:
                    calls.append(call_info)
        return calls
    
    def _check_import(self, node: ast.Import) -> None:
        """检查 import 语句"""
        for alias in node.names:
            module_name = alias.name.split(".")[0]
            self._imports.add(module_name)
            
            if module_name in self.DANGEROUS_MODULES:
                severity = self.DANGEROUS_MODULES[module_name]
                self._issues.append(SecurityIssue(
                    line=node.lineno,
                    col=node.col_offset,
                    function=f"import {module_name}",
                    severity=severity,
                    message=f"导入潜在危险模块: {module_name}"
                ))
    
    def _check_from_import(self, node: ast.ImportFrom) -> None:
        """检查 from ... import 语句"""
        if node.module:
            module_name = node.module.split(".")[0]
            self._imports.add(module_name)
            
            # 记录从哪个模块导入了什么
            for alias in node.names:
                full_name = f"{node.module}.{alias.name}"
                self._from_imports[alias.name] = node.module
                
                # 检查是否导入危险函数
                if full_name in self.DANGEROUS_FUNCTIONS:
                    severity = self.DANGEROUS_FUNCTIONS[full_name]
                    self._issues.append(SecurityIssue(
                        line=node.lineno,
                        col=node.col_offset,
                        function=full_name,
                        severity=severity,
                        message=f"直接导入危险函数: {full_name}"
                    ))
    
    def _check_function_call(self, node: ast.Call, code_lines: List[str]) -> None:
        """检查函数调用"""
        call_name = self._get_call_name(node)
        
        if call_name and call_name in self.DANGEROUS_FUNCTIONS:
            severity = self.DANGEROUS_FUNCTIONS[call_name]
            
            # 获取代码片段
            snippet = self._get_code_snippet(code_lines, node.lineno)
            
            self._issues.append(SecurityIssue(
                line=node.lineno,
                col=node.col_offset,
                function=call_name,
                severity=severity,
                message=f"调用危险函数: {call_name}",
                code_snippet=snippet
            ))
    
    def _check_attribute_access(self, node: ast.Attribute, code_lines: List[str]) -> None:
        """检查属性访问"""
        # 这个在 Call 检查中已经处理了
        pass
    
    def _check_name_usage(self, node: ast.Name, code_lines: List[str]) -> None:
        """检查名称使用"""
        name = node.id
        
        # 检查是否是危险函数的直接调用（如 eval()）
        if name in self.DANGEROUS_FUNCTIONS:
            severity = self.DANGEROUS_FUNCTIONS[name]
            snippet = self._get_code_snippet(code_lines, node.lineno)
            
            self._issues.append(SecurityIssue(
                line=node.lineno,
                col=node.col_offset,
                function=name,
                severity=severity,
                message=f"使用危险函数: {name}",
                code_snippet=snippet
            ))
    
    def _get_call_name(self, node: ast.Call) -> Optional[str]:
        """获取函数调用的完整名称"""
        if isinstance(node.func, ast.Name):
            return node.func.id
        elif isinstance(node.func, ast.Attribute):
            # 递归获取属性链
            parts = []
            current = node.func
            while isinstance(current, ast.Attribute):
                parts.append(current.attr)
                current = current.value
            if isinstance(current, ast.Name):
                parts.append(current.id)
            parts.reverse()
            return ".".join(parts)
        return None
    
    def _extract_call_info(self, node: ast.Call) -> Optional[dict]:
        """提取调用信息"""
        name = self._get_call_name(node)
        if name:
            return {
                "name": name,
                "line": node.lineno,
                "col": node.col_offset,
                "args_count": len(node.args)
            }
        return None
    
    def _get_code_snippet(self, code_lines: List[str], line_no: int) -> Optional[str]:
        """获取代码片段"""
        if 0 < line_no <= len(code_lines):
            return code_lines[line_no - 1].strip()
        return None
    
    def _generate_summary(self) -> dict:
        """生成摘要"""
        by_severity = {}
        for issue in self._issues:
            severity = issue.severity.value
            by_severity[severity] = by_severity.get(severity, 0) + 1
        
        return {
            "total_issues": len(self._issues),
            "by_severity": by_severity
        }


class SecurityException(Exception):
    """安全异常"""
    
    def __init__(self, issues: List[dict]):
        self.issues = issues
        message = f"发现 {len(issues)} 个安全问题"
        super().__init__(message)


# 便捷函数
def audit_code(code: str) -> dict:
    """快速审计代码"""
    auditor = ASTAuditor()
    return auditor.scan_code(code)


def audit_file(filepath: str) -> dict:
    """快速审计文件"""
    auditor = ASTAuditor()
    return auditor.scan_file(filepath)


if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1:
        filepath = sys.argv[1]
        result = audit_file(filepath)
        
        print(f"\n审计结果: {'安全' if result['safe'] else '有风险'}")
        print(f"导入模块: {', '.join(result['imports'])}")
        print(f"发现问题: {result['summary']['total_issues']}")
        
        for issue in result['issues']:
            print(f"\n  [{issue['severity'].upper()}] 第 {issue['line']} 行")
            print(f"    函数: {issue['function']}")
            print(f"    消息: {issue['message']}")
            if issue['code_snippet']:
                print(f"    代码: {issue['code_snippet']}")
    else:
        # 演示
        test_code = '''
import os
import subprocess

def dangerous_function():
    os.system("ls -la")
    eval("print('hello')")
    subprocess.call(["echo", "test"])
'''
        
        auditor = ASTAuditor()
        result = auditor.scan_code(test_code)
        
        print("审计演示代码:")
        print(f"安全: {result['safe']}")
        print(f"问题数: {len(result['issues'])}")
        for issue in result['issues']:
            print(f"  - 第 {issue['line']} 行: {issue['function']} ({issue['severity']})")
