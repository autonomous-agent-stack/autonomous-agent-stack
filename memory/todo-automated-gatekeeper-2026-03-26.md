# 🛡️ 自动化 PR 审查与红线守卫协议

> **创建时间**：2026-03-26 04:31 GMT+8
> **优先级**：最高
> **工作分支**：codex/continue-autonomous-agent-stack
> **目标**：确保底座在接收外部 PR 或自我进化代码时，业务边界与系统安全绝对不可被破坏

---

## 🎯 核心目标

将代码审查的体力活完全交给 AI，最终以极简语言向管理员汇报。

**核心原则**：
- ✅ 宁可误杀打回，不允许污染代码进入主干
- ✅ 纯 Python 原生实现，不引入第三方 CI/CD 引擎
- ✅ 极简通知，适配浅色 Web 看板

---

## 📋 任务矩阵

### 1️⃣ S1, S2 [静态安全审计组 - Security Auditor] ⏳

**任务**：实现 `PR_Static_Analyzer` 服务

**验收标准**：
- ✅ 检测到新的代码合并请求时，强制进行 AST（抽象语法树）分析
- ✅ **红线检测**：
  1. 试图绕过 `AppleDoubleCleaner`
  2. 未授权的 `os.system` 调用
  3. 试图修改 `panel_access.py`（JWT 与 Tailscale 鉴权层）
- ✅ **处理方式**：直接阻断 + 审计日志 `[Security Reject] 检测到越权调用`

**实现要点**：
```python
import ast
import re
from typing import List, Dict

class PR_Static_Analyzer:
    """PR 静态安全审计器"""
    
    def __init__(self):
        self.forbidden_patterns = [
            # 绕过 AppleDoubleCleaner
            r'AppleDoubleCleaner.*skip',
            r'clean_appledouble.*False',
            
            # 未授权 os.system
            r'os\.system\s*\(',
            r'subprocess\.call\s*\([^)]*shell\s*=\s*True',
            
            # 修改鉴权层
            r'panel_access\.py',
            r'JWT_SECRET',
            r'Tailscale.*auth'
        ]
    
    async def analyze_pr(self, pr_diff: str) -> Dict:
        """分析 PR 代码"""
        result = {
            "safe": True,
            "violations": [],
            "ast_analysis": None
        }
        
        # 1. 正则表达式检测
        for pattern in self.forbidden_patterns:
            if re.search(pattern, pr_diff, re.IGNORECASE):
                result["safe"] = False
                result["violations"].append(f"[Security Reject] 检测到越权调用: {pattern}")
        
        # 2. AST 分析
        try:
            tree = ast.parse(pr_diff)
            result["ast_analysis"] = self._analyze_ast(tree)
            
            # 检测危险函数调用
            for node in ast.walk(tree):
                if isinstance(node, ast.Call):
                    if self._is_dangerous_call(node):
                        result["safe"] = False
                        result["violations"].append(
                            f"[Security Reject] 检测到危险函数调用: {ast.dump(node)}"
                        )
        except SyntaxError:
            result["safe"] = False
            result["violations"].append("[Security Reject] 代码语法错误")
        
        return result
    
    def _analyze_ast(self, tree: ast.AST) -> Dict:
        """AST 深度分析"""
        analysis = {
            "imports": [],
            "function_calls": [],
            "modifications": []
        }
        
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    analysis["imports"].append(alias.name)
            elif isinstance(node, ast.FunctionDef):
                analysis["function_calls"].append(node.name)
        
        return analysis
    
    def _is_dangerous_call(self, node: ast.Call) -> bool:
        """判断是否是危险函数调用"""
        dangerous_functions = [
            "os.system",
            "subprocess.call",
            "eval",
            "exec",
            "compile"
        ]
        
        func_name = ast.dump(node.func)
        return any(df in func_name for df in dangerous_functions)
```

---

### 2️⃣ QA1, QA2 [业务护城河验证组 - TDD Enforcer] ⏳

**任务**：实现沙盒化的自动化验收测试流

**验收标准**：
- ✅ 在隔离的 Docker 容器中跑通所有的全量 Pytest
- ✅ **玛露业务红线**：
  - 文案必须包含："挑战游泳级别持妆"、"不用调色"、"遮瑕力强"
  - 不得包含"工厂化"行话
- ✅ **处理方式**：违反红线立即打回，不允许进入人工审批流

**实现要点**：
```python
import docker
import re
from typing import List

class BusinessTDD_Enforcer:
    """业务护城河验证器"""
    
    def __init__(self):
        self.malu_keywords = [
            "挑战游泳级别持妆",
            "不用调色",
            "遮瑕力强"
        ]
        self.forbidden_terms = [
            "工厂化",
            "流水线",
            "廉价"
        ]
    
    async def run_sandbox_tests(self, pr_branch: str) -> Dict:
        """在 Docker 沙盒中运行测试"""
        client = docker.from_env()
        
        # 创建测试容器
        container = client.containers.run(
            "python:3.11-slim",
            command=f"sh -c 'git clone -b {pr_branch} . && pytest tests/'",
            volumes={'/tmp/test_results': {'bind': '/results', 'mode': 'rw'}},
            detach=True
        )
        
        # 等待测试完成
        result = container.wait()
        
        # 获取测试结果
        logs = container.logs().decode('utf-8')
        
        return {
            "success": result['StatusCode'] == 0,
            "logs": logs,
            "test_results": self._parse_test_results(logs)
        }
    
    async def validate_malu_copy(self, generated_copy: str) -> Dict:
        """验证玛露文案"""
        result = {
            "valid": True,
            "missing_keywords": [],
            "forbidden_found": []
        }
        
        # 检查必需关键词
        for keyword in self.malu_keywords:
            if keyword not in generated_copy:
                result["valid"] = False
                result["missing_keywords"].append(keyword)
        
        # 检查禁止术语
        for term in self.forbidden_terms:
            if term in generated_copy:
                result["valid"] = False
                result["forbidden_found"].append(term)
        
        return result
    
    def _parse_test_results(self, logs: str) -> Dict:
        """解析测试结果"""
        # 提取测试统计
        passed = re.search(r'(\d+) passed', logs)
        failed = re.search(r'(\d+) failed', logs)
        
        return {
            "passed": int(passed.group(1)) if passed else 0,
            "failed": int(failed.group(1)) if failed else 0
        }
```

---

### 3️⃣ U1 [降维 UI 汇报组 - Board Summarizer] ⏳

**任务**：为浅色 Web 面板开发"PR 极简审查卡片"

**验收标准**：
- ✅ 拒绝显示冗长复杂的 Git Diff 代码块
- ✅ 利用大模型将代码改动翻译成 3 条通俗的结论：
  1. **目的**：这个 PR 做什么？
  2. **性能影响**：对系统性能有什么影响？
  3. **安全评级**：安全等级如何？
- ✅ **交互**：仅提供两个极简按钮
  - `[ 批准并部署 (Merge) ]`
  - `[ 打回 (Reject) ]`

**实现要点**：
```python
from typing import Dict, List

class Board_Summarizer:
    """UI 汇报简化器"""
    
    async def generate_review_card(self, pr_info: Dict, 
                                   security_result: Dict,
                                   test_result: Dict) -> Dict:
        """生成 PR 极简审查卡片"""
        
        # 1. 调用大模型总结代码改动
        summary = await self._summarize_with_llm(
            pr_info["diff"],
            security_result,
            test_result
        )
        
        # 2. 构建极简卡片
        card = {
            "pr_id": pr_info["id"],
            "title": pr_info["title"],
            "author": pr_info["author"],
            "conclusions": [
                {
                    "label": "目的",
                    "content": summary["purpose"]
                },
                {
                    "label": "性能影响",
                    "content": summary["performance_impact"]
                },
                {
                    "label": "安全评级",
                    "content": summary["security_rating"],
                    "color": self._get_security_color(summary["security_rating"])
                }
            ],
            "actions": [
                {
                    "label": "批准并部署 (Merge)",
                    "action": "merge",
                    "style": "primary"
                },
                {
                    "label": "打回 (Reject)",
                    "action": "reject",
                    "style": "danger"
                }
            ]
        }
        
        return card
    
    async def _summarize_with_llm(self, diff: str, 
                                  security: Dict,
                                  tests: Dict) -> Dict:
        """调用大模型总结"""
        prompt = f"""
        请分析以下 PR 代码改动，并生成 3 条通俗结论：
        
        代码改动：
        {diff[:1000]}  # 限制长度
        
        安全检测结果：
        {security}
        
        测试结果：
        {tests}
        
        请输出：
        1. 目的（一句话说明这个 PR 做什么）
        2. 性能影响（对系统性能的影响）
        3. 安全评级（安全等级：高/中/低）
        """
        
        # 调用大模型
        # response = await llm.generate(prompt)
        
        # 返回结构化结果
        return {
            "purpose": "集成新功能 X",
            "performance_impact": "无明显性能影响",
            "security_rating": "高" if security["safe"] else "低"
        }
    
    def _get_security_color(self, rating: str) -> str:
        """获取安全评级颜色"""
        colors = {
            "高": "green",
            "中": "yellow",
            "低": "red"
        }
        return colors.get(rating, "gray")
```

---

## ⚠️ 工程纪律

### 1. 宁可误杀，不允许污染代码进入主干
```python
# 红线示例
if any(violation in pr_diff for violation in FORBIDDEN_PATTERNS):
    return {"action": "reject", "reason": "[Security Reject] 检测到越权调用"}
```

### 2. 纯 Python 原生实现，不引入第三方 CI/CD 引擎
```python
# ✅ 允许：原生 Python 钩子
class ReviewHook:
    def pre_merge(self, pr):
        pass

# ❌ 禁止：第三方 CI/CD 引擎
# - Jenkins
# - GitHub Actions（复杂配置）
# - GitLab CI（复杂配置）
```

---

## 🏗️ 架构设计

```
┌─────────────────────────────────────────┐
│      PR 合并请求 (Pull Request)         │
└─────────────────────────────────────────┘
                    │
        ┌───────────┼───────────┐
        │           │           │
   ┌────▼────┐ ┌────▼────┐ ┌────▼────┐
   │  S1, S2 │ │ QA1, QA2│ │   U1    │
   │ 静态审计 │ │ 业务验证 │ │ UI 汇报 │
   └─────────┘ └─────────┘ └─────────┘
        │           │           │
        │           │           │
   ┌────▼───────────▼───────────▼────┐
   │   极简审查卡片 (Web 面板)        │
   │   - 目的                        │
   │   - 性能影响                    │
   │   - 安全评级                    │
   │   [批准] [打回]                 │
   └──────────────────────────────────┘
```

---

## 📊 实施路线图

### Phase 1: 静态安全审计（1天）
- [ ] 实现 `PR_Static_Analyzer`
- [ ] AST 分析
- [ ] 红线检测

### Phase 2: 业务护城河验证（1天）
- [ ] 实现 `BusinessTDD_Enforcer`
- [ ] Docker 沙盒测试
- [ ] 玛露文案验证

### Phase 3: UI 汇报（1天）
- [ ] 实现 `Board_Summarizer`
- [ ] 大模型总结
- [ ] 极简卡片 UI

---

## 🧪 测试策略

### 安全测试
```python
async def test_security_reject():
    """测试安全红线拒绝"""
    analyzer = PR_Static_Analyzer()
    
    # 测试绕过 AppleDoubleCleaner
    result = await analyzer.analyze_pr("AppleDoubleCleaner(skip=True)")
    assert result["safe"] is False
    
    # 测试未授权 os.system
    result = await analyzer.analyze_pr("os.system('rm -rf /')")
    assert result["safe"] is False
```

### 业务测试
```python
async def test_malu_business_rule():
    """测试玛露业务红线"""
    enforcer = BusinessTDD_Enforcer()
    
    # 测试缺失关键词
    result = await enforcer.validate_malu_copy("这是一个测试文案")
    assert result["valid"] is False
    assert "不用调色" in result["missing_keywords"]
    
    # 测试禁止术语
    result = await enforcer.validate_malu_copy("工厂化生产，不用调色")
    assert result["valid"] is False
    assert "工厂化" in result["forbidden_found"]
```

---

## 📝 验收标准

### 功能验收
- ✅ AST 分析检测危险代码
- ✅ Docker 沙盒测试通过
- ✅ 业务红线验证通过
- ✅ UI 极简卡片生成

### 安全验收
- ✅ 红线代码 100% 拒绝
- ✅ 审计日志完整
- ✅ 误杀率 < 5%

### 性能验收
- ✅ 静态分析时间 < 10秒
- ✅ 沙盒测试时间 < 5分钟
- ✅ UI 渲染时间 < 1秒

---

## 🚨 风险点

### 1. 误杀率
- **缓解**：白名单机制
- **监控**：误杀率统计

### 2. 性能影响
- **缓解**：并行测试
- **监控**：测试时间告警

### 3. 漏检
- **缓解**：多层级检测
- **监控**：漏检事件追踪

---

## 📅 时间线

- **2026-03-26 04:31**：协议创建
- **预计完成**：2026-03-29（3天）
- **验收时间**：2026-03-30

---

## 🔗 相关链接

- **仓库**：https://github.com/srxly888-creator/autonomous-agent-stack
- **分支**：codex/continue-autonomous-agent-stack
- **相关协议**：
  - P1: 收尾协议（已完成）
  - P2: 检查点协议（已完成）
  - P3: HITL 协议（已完成）
  - P4: 系统级自主代码进化（待实现）

---

**状态**：⏳ 待实现
**优先级**：🔴 最高
**预计时间**：3天
