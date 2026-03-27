# Adapter 自动路由系统

## 概述

自动路由系统根据任务特征智能选择最合适的Adapter，实现成本、速度、质量的最优平衡。

---

## 路由架构

```
┌─────────────────────────────────────────────────────────┐
│                   任务输入                                │
│  - task: "Add docstring to hello function"              │
│  - context: {files, language, complexity}               │
└────────────────────┬────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────┐
│              特征提取器（Feature Extractor）             │
│                                                          │
│  1. 语言检测: zh/en/ja/...                              │
│  2. 复杂度分析: simple/medium/complex                   │
│  3. 任务类型: review/fix/test/doc/refactor              │
│  4. 文件数: 1/2-5/>5                                    │
│  5. 变更量: <50/50-200/>200 lines                       │
└────────────────────┬────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────┐
│              路由决策引擎（Routing Engine）              │
│                                                          │
│  规则评估 → 优先级排序 → 成本检查 → 最终选择            │
└────────────────────┬────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────┐
│              Adapter 选择                                │
│                                                          │
│  Codex | GLM-5 | Claude | OpenHands                     │
└─────────────────────────────────────────────────────────┘
```

---

## 特征提取

### 1. 语言检测

```python
def detect_language(task: str) -> str:
    """检测任务语言"""
    chinese_chars = sum(1 for c in task if '\u4e00' <= c <= '\u9fff')
    total_chars = len(task.replace(' ', ''))
    
    if total_chars == 0:
        return 'en'
    
    chinese_ratio = chinese_chars / total_chars
    
    if chinese_ratio > 0.3:
        return 'zh'
    else:
        return 'en'
```

### 2. 复杂度分析

```python
def analyze_complexity(task: str, context: dict) -> str:
    """分析任务复杂度"""
    score = 0
    
    # 关键词检测
    complex_keywords = ['architecture', 'refactor', 'design', 'integration', '架构', '重构']
    for keyword in complex_keywords:
        if keyword in task.lower():
            score += 2
    
    # 文件数
    file_count = context.get('file_count', 1)
    if file_count > 5:
        score += 2
    elif file_count > 2:
        score += 1
    
    # 变更量
    change_lines = context.get('estimated_changes', 50)
    if change_lines > 200:
        score += 2
    elif change_lines > 50:
        score += 1
    
    # 评分
    if score >= 4:
        return 'complex'
    elif score >= 2:
        return 'medium'
    else:
        return 'simple'
```

### 3. 任务类型识别

```python
def identify_task_type(task: str) -> str:
    """识别任务类型"""
    task_lower = task.lower()
    
    if any(kw in task_lower for kw in ['review', '审查', '检查']):
        return 'review'
    elif any(kw in task_lower for kw in ['fix', 'bug', '修复', 'bug']):
        return 'fix'
    elif any(kw in task_lower for kw in ['test', '测试', 'test']):
        return 'test'
    elif any(kw in task_lower for kw in ['doc', 'document', '文档', 'readme']):
        return 'doc'
    elif any(kw in task_lower for kw in ['refactor', '重构', '优化']):
        return 'refactor'
    else:
        return 'general'
```

---

## 路由规则

### 规则配置

```yaml
# configs/routing/rules.yaml
rules:
  # 优先级1：语言检测（最高优先级）
  - id: lang_chinese
    priority: 100
    condition: "language == 'zh'"
    adapter: glm5
    reason: "中文任务使用GLM-5优化"
  
  # 优先级2：任务复杂度
  - id: complexity_high
    priority: 90
    condition: "complexity == 'complex'"
    adapter: claude
    reason: "复杂任务使用Claude高质量推理"
  
  - id: complexity_simple
    priority: 80
    condition: "complexity == 'simple'"
    adapter: codex
    reason: "简单任务使用Codex快速处理"
  
  # 优先级3：任务类型
  - id: task_review
    priority: 70
    condition: "task_type == 'review'"
    adapter: claude
    reason: "代码审查使用Claude深度分析"
  
  - id: task_test
    priority: 70
    condition: "task_type == 'test'"
    adapter: codex
    reason: "测试生成使用Codex快速生成"
  
  - id: task_doc
    priority: 70
    condition: "task_type == 'doc' and language == 'zh'"
    adapter: glm5
    reason: "中文文档使用GLM-5"
  
  # 优先级4：成本优化
  - id: cost_optimize
    priority: 50
    condition: "cost_budget == 'low'"
    adapter: glm5
    reason: "成本敏感场景使用GLM-5"
  
  # 默认规则
  - id: default
    priority: 0
    condition: "true"
    adapter: codex
    reason: "默认使用Codex平衡方案"
```

---

## 路由引擎实现

```python
# src/autoresearch/routing/engine.py

from typing import Dict, List
from dataclasses import dataclass

@dataclass
class TaskFeatures:
    language: str
    complexity: str
    task_type: str
    file_count: int
    estimated_changes: int

@dataclass
class RoutingRule:
    id: str
    priority: int
    condition: str
    adapter: str
    reason: str

class RoutingEngine:
    def __init__(self, rules: List[RoutingRule]):
        self.rules = sorted(rules, key=lambda r: r.priority, reverse=True)
    
    def extract_features(self, task: str, context: dict) -> TaskFeatures:
        """提取任务特征"""
        return TaskFeatures(
            language=detect_language(task),
            complexity=analyze_complexity(task, context),
            task_type=identify_task_type(task),
            file_count=context.get('file_count', 1),
            estimated_changes=context.get('estimated_changes', 50)
        )
    
    def evaluate_condition(self, condition: str, features: TaskFeatures) -> bool:
        """评估条件表达式"""
        # 安全的条件评估（仅支持简单比较）
        try:
            # 替换变量
            expr = condition
            expr = expr.replace('language', f'"{features.language}"')
            expr = expr.replace('complexity', f'"{features.complexity}"')
            expr = expr.replace('task_type', f'"{features.task_type}"')
            
            # 仅允许安全操作
            if any(danger in expr for danger in ['import', 'exec', 'eval', '__']):
                return False
            
            return eval(expr)
        except:
            return False
    
    def route(self, task: str, context: dict = None) -> str:
        """路由到合适的Adapter"""
        context = context or {}
        features = self.extract_features(task, context)
        
        # 按优先级评估规则
        for rule in self.rules:
            if self.evaluate_condition(rule.condition, features):
                print(f"[routing] Selected {rule.adapter}: {rule.reason}")
                return rule.adapter
        
        # 默认
        return 'codex'
    
    def route_with_fallback(self, task: str, context: dict = None) -> List[str]:
        """路由并返回fallback列表"""
        primary = self.route(task, context)
        
        # 根据主选择确定fallback
        fallback_map = {
            'codex': ['claude', 'openhands'],
            'glm5': ['codex', 'openhands'],
            'claude': ['openhands'],
            'openhands': []
        }
        
        return [primary] + fallback_map.get(primary, [])
```

---

## 使用示例

### 基本使用

```python
from autoresearch.routing import RoutingEngine

# 加载规则
engine = RoutingEngine.from_config('configs/routing/rules.yaml')

# 路由任务
task = "添加中文文档到hello函数"
adapter = engine.route(task)

print(f"Selected adapter: {adapter}")  # 输出: glm5
```

### 带上下文

```python
task = "Refactor authentication module"
context = {
    'file_count': 8,
    'estimated_changes': 350
}

adapter = engine.route(task, context)
print(f"Selected adapter: {adapter}")  # 输出: claude（复杂任务）
```

### 带Fallback

```python
adapters = engine.route_with_fallback(task, context)
print(f"Primary: {adapters[0]}, Fallback: {adapters[1:]}")
# 输出: Primary: claude, Fallback: ['openhands']
```

---

## 路由统计

### 统计收集

```python
class RoutingStats:
    def __init__(self):
        self.stats = {
            'codex': 0,
            'glm5': 0,
            'claude': 0,
            'openhands': 0
        }
        self.total = 0
    
    def record(self, adapter: str):
        self.stats[adapter] += 1
        self.total += 1
    
    def get_distribution(self) -> dict:
        return {
            adapter: {
                'count': count,
                'percentage': f"{count/self.total*100:.1f}%"
            }
            for adapter, count in self.stats.items()
        }
```

### 示例输出

```json
{
  "codex": {
    "count": 50,
    "percentage": "50.0%"
  },
  "glm5": {
    "count": 30,
    "percentage": "30.0%"
  },
  "claude": {
    "count": 15,
    "percentage": "15.0%"
  },
  "openhands": {
    "count": 5,
    "percentage": "5.0%"
  }
}
```

---

## 动态调整

### 基于性能调整

```python
class DynamicRouter(RoutingEngine):
    def __init__(self, rules):
        super().__init__(rules)
        self.performance_data = {}
    
    def update_performance(self, adapter: str, success: bool, duration: float):
        """更新性能数据"""
        if adapter not in self.performance_data:
            self.performance_data[adapter] = {
                'success_rate': 0,
                'avg_duration': 0,
                'count': 0
            }
        
        data = self.performance_data[adapter]
        data['count'] += 1
        
        # 滑动窗口平均
        alpha = 0.1
        data['success_rate'] = (
            alpha * (1 if success else 0) + 
            (1 - alpha) * data['success_rate']
        )
        data['avg_duration'] = (
            alpha * duration + 
            (1 - alpha) * data['avg_duration']
        )
    
    def route(self, task: str, context: dict = None) -> str:
        """路由并考虑性能数据"""
        primary = super().route(task, context)
        
        # 如果主要Adapter性能差，降级到备选
        if primary in self.performance_data:
            perf = self.performance_data[primary]
            if perf['success_rate'] < 0.7:  # 成功率<70%
                # 选择备选
                return self.select_backup(primary)
        
        return primary
```

---

## 监控和告警

### 路由监控

```python
def monitor_routing():
    """监控路由决策"""
    while True:
        stats = get_routing_stats()
        
        # 检查分布是否合理
        if stats['openhands']['percentage'] > 30:
            alert("OpenHands使用率过高，检查路由规则")
        
        if stats['codex']['percentage'] < 30:
            alert("Codex使用率过低，可能浪费成本优化机会")
        
        time.sleep(3600)  # 每小时检查
```

---

## 最佳实践

### 1. 规则设计

- ✅ 按优先级从高到低排列
- ✅ 覆盖所有常见场景
- ✅ 提供合理的fallback
- ✅ 定期审查和调整

### 2. 性能优化

- ✅ 缓存特征提取结果
- ✅ 使用并行评估
- ✅ 监控路由延迟

### 3. 成本控制

- ✅ 优先选择低成本Adapter
- ✅ 设置每日成本上限
- ✅ 自动降级机制

---

## 配置示例

### 生产环境

```yaml
# configs/routing/production.yaml
mode: "auto"
optimization: "cost"  # cost | speed | quality

rules:
  - id: chinese_first
    priority: 100
    condition: "language == 'zh'"
    adapter: glm5
  
  - id: complex_to_claude
    priority: 90
    condition: "complexity == 'complex'"
    adapter: claude
  
  - id: default_codex
    priority: 0
    condition: "true"
    adapter: codex

fallback_chain:
  codex: [claude, openhands]
  glm5: [codex, openhands]
  claude: [openhands]
  openhands: []

monitoring:
  enabled: true
  alert_threshold: 0.7
```
