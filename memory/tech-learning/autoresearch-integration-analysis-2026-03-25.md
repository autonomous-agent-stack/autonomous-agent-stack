# Autoresearch 魔改方案分析

## 用户需求
将 Karpathy 的 autoresearch 迭代框架集成到 gpt-researcher 中

## Karpathy Autoresearch 核心逻辑

```
改一个东西 → 打分 → 分高了保留，分低了回滚 → 再改下一个
```

### 关键要素
1. **迭代优化**：每次只改一点
2. **自动打分**：有明确的评估标准
3. **智能回滚**：分低了自动还原
4. **无需人工**：100 次实验自动运行

---

## gpt-researcher 核心功能

### 现有功能
- 🔍 Deep Research（深度研究）
- 🤖 Multi-Agent（多智能体）
- 🍌 图片生成（Nano Banana）
- 🔧 MCP 集成
- 📄 本地文档研究

### 架构
```
用户输入 → Research Agent → 报告生成
```

---

## 魔改方案：将 gpt-researcher 变成 Autoresearch 框架

### 方案 1：Prompt 优化器（最简单）

**核心逻辑**：
```
改一条 prompt 规则 → 生成报告 → 人工/自动打分 → 保留/回滚
```

**实现步骤**：
1. **Prompt 变体生成器**
   - 自动生成 prompt 变体（改标题、结构、语气）
   - 每次只改一个参数

2. **自动打分系统**
   - 报告质量评分（GPT-4 打分）
   - 信息密度评分
   - 可读性评分

3. **迭代优化循环**
   ```python
   best_prompt = initial_prompt
   best_score = 0
   
   for variant in prompt_variants:
       report = generate_report(query, variant)
       score = evaluate_report(report)
       
       if score > best_score:
           best_prompt = variant
           best_score = score
           save_prompt(variant)
       else:
           continue  # 自动回滚（不保存）
   ```

**优势**：
- ✅ 最简单（只改 prompt 层）
- ✅ 不需要改核心代码
- ✅ 立即可用

**劣势**：
- ❌ 只能优化 prompt
- ❌ 无法优化研究流程

---

### 方案 2：研究流程优化器（中等难度）

**核心逻辑**：
```
改一个研究参数 → 执行研究 → 打分 → 保留/回滚
```

**可优化的参数**：
- 搜索结果数量（5 → 10 → 20）
- 信息源权重（维基百科 vs 新闻 vs 论文）
- 报告长度（短/中/长）
- 引用密度（高/低）
- 图片生成频率

**实现步骤**：
1. **参数空间定义**
   ```python
   params = {
       'search_results': [5, 10, 15, 20],
       'source_weights': ['wiki_high', 'news_high', 'paper_high'],
       'report_length': ['short', 'medium', 'long'],
       'citation_density': ['high', 'medium', 'low']
   }
   ```

2. **自动实验循环**
   ```python
   for param in params:
       for value in params[param]:
           config = update_config(param, value)
           report = run_research(query, config)
           score = evaluate_report(report)
           
           if score > best_score:
               best_config[param] = value
               best_score = score
   ```

3. **智能打分**
   - 信息准确性（与 ground truth 对比）
   - 引用质量（权威性评分）
   - 报告可读性（Flesch 分数）

**优势**：
- ✅ 优化整个研究流程
- ✅ 可以找到最佳参数组合
- ✅ 可扩展性强

**劣势**：
- ❌ 需要修改核心代码
- ❌ 运行时间较长

---

### 方案 3：完全魔改版（最强大）

**核心逻辑**：
```
改任何组件 → 执行研究 → 多维度打分 → 保留/回滚
```

**可优化的组件**：
1. **Prompt 生成器**
   - 模板变体
   - 语气调整
   - 结构优化

2. **信息检索器**
   - 搜索策略
   - 来源过滤
   - 排序算法

3. **报告生成器**
   - 结构模板
   - 引用格式
   - 图表生成

4. **评估系统**
   - 多维度打分（准确性、可读性、完整性）
   - A/B 测试集成
   - 用户反馈循环

**架构**：
```
┌─────────────────────────────────────┐
│   Autoresearch Orchestrator         │
│                                     │
│  ┌───────────┐      ┌───────────┐  │
│  │ Prompt    │      │ Retriever │  │
│  │ Optimizer │      │ Optimizer │  │
│  └───────────┘      └───────────┘  │
│                                     │
│  ┌───────────┐      ┌───────────┐  │
│  │ Generator │      │ Evaluator │  │
│  │ Optimizer │      │ System    │  │
│  └───────────┘      └───────────┘  │
│                                     │
│  ┌─────────────────────────────┐   │
│  │   Scoring & Rollback        │   │
│  │   Management System         │   │
│  └─────────────────────────────┘   │
└─────────────────────────────────────┘
```

**优势**：
- ✅ 最全面的优化
- ✅ 可以优化任何组件
- ✅ 真正的"AI 自动优化 AI"

**劣势**：
- ❌ 开发工作量大
- ❌ 需要重构核心架构

---

## 推荐方案：渐进式魔改

### 阶段 1：Prompt 优化器（1-2 天）
- ✅ 最快见效
- ✅ 验证概念
- ✅ 建立打分系统

### 阶段 2：参数优化器（3-5 天）
- ✅ 扩展优化范围
- ✅ 找到最佳配置
- ✅ 建立实验框架

### 阶段 3：完全魔改版（1-2 周）
- ✅ 重构架构
- ✅ 优化所有组件
- ✅ 生产级系统

---

## 具体实现示例（阶段 1）

### 文件结构
```
gpt-researcher/
├── autoresearch/
│   ├── __init__.py
│   ├── prompt_optimizer.py
│   ├── evaluator.py
│   ├── config.py
│   └── runner.py
```

### 核心代码

#### 1. Prompt 变体生成器
```python
# autoresearch/prompt_optimizer.py
import openai

class PromptOptimizer:
    def __init__(self, base_prompt):
        self.base_prompt = base_prompt
        self.variants = []
    
    def generate_variants(self, num_variants=10):
        """生成 prompt 变体"""
        variant_types = [
            'change_tone',
            'restructure',
            'add_examples',
            'simplify',
            'add_constraints'
        ]
        
        for _ in range(num_variants):
            variant_type = random.choice(variant_types)
            variant = self._apply_transformation(
                self.base_prompt,
                variant_type
            )
            self.variants.append(variant)
        
        return self.variants
    
    def _apply_transformation(self, prompt, variant_type):
        """应用变换"""
        if variant_type == 'change_tone':
            return self._change_tone(prompt)
        elif variant_type == 'restructure':
            return self._restructure(prompt)
        # ... 其他变换
```

#### 2. 评估系统
```python
# autoresearch/evaluator.py
class ReportEvaluator:
    def __init__(self):
        self.criteria = [
            'accuracy',
            'completeness',
            'readability',
            'citation_quality'
        ]
    
    def evaluate(self, report, ground_truth=None):
        """多维度评估报告"""
        scores = {}
        
        for criterion in self.criteria:
            scores[criterion] = self._score_criterion(
                report,
                criterion,
                ground_truth
            )
        
        # 加权总分
        total_score = sum(scores.values()) / len(scores)
        
        return {
            'total': total_score,
            'breakdown': scores
        }
    
    def _score_criterion(self, report, criterion, ground_truth):
        """评估单个维度"""
        if criterion == 'readability':
            return self._flesch_score(report)
        elif criterion == 'citation_quality':
            return self._citation_score(report)
        # ... 其他维度
```

#### 3. 迭代优化循环
```python
# autoresearch/runner.py
class AutoresearchRunner:
    def __init__(self, gpt_researcher):
        self.researcher = gpt_researcher
        self.optimizer = PromptOptimizer()
        self.evaluator = ReportEvaluator()
        self.best_config = {
            'prompt': None,
            'score': 0
        }
    
    def run_optimization(self, query, iterations=100):
        """运行优化循环"""
        for i in range(iterations):
            # 生成变体
            prompt = self.optimizer.generate_variant()
            
            # 执行研究
            report = self.researcher.research(
                query,
                prompt=prompt
            )
            
            # 评估报告
            score = self.evaluator.evaluate(report)
            
            # 保留或回滚
            if score['total'] > self.best_config['score']:
                self.best_config = {
                    'prompt': prompt,
                    'score': score['total']
                }
                self._save_progress(i, prompt, score)
                print(f"✅ Iteration {i}: New best score {score['total']}")
            else:
                print(f"❌ Iteration {i}: Score {score['total']} (skipped)")
        
        return self.best_config
```

---

## 使用示例

```python
# 示例：优化"AI 发展趋势"研究报告

from gpt_researcher import GPTResearcher
from autoresearch import AutoresearchRunner

# 初始化
researcher = GPTResearcher()
runner = AutoresearchRunner(researcher)

# 运行优化
query = "2026 年 AI 发展趋势"
best_config = runner.run_optimization(
    query,
    iterations=50  # 50 次迭代
)

# 输出最佳配置
print(f"最佳 Prompt: {best_config['prompt']}")
print(f"最佳分数: {best_config['score']}")
```

---

## 下一步行动

### 立即可做（今天）
1. ✅ Fork gpt-researcher 仓库
2. ✅ 创建 `autoresearch/` 目录
3. ✅ 实现 Prompt 优化器（阶段 1）

### 本周可做
1. 📝 实现评估系统
2. 📝 运行第一次实验（50 次迭代）
3. 📝 分析结果，优化评分标准

### 下周可做
1. 🚀 扩展到参数优化（阶段 2）
2. 🚀 重构核心架构（阶段 3）
3. 🚀 发布开源版本

---

## 总结

**核心洞察**：Karpathy 的 autoresearch 不是一个工具，而是一个**通用优化框架**。

**应用场景**：
- ✅ Prompt 优化（最简单）
- ✅ 参数调优（中等难度）
- ✅ 架构搜索（最复杂）

**gpt-researcher 的优势**：
- ✅ 已有完整的研究流程
- ✅ 已有多 Agent 架构
- ✅ 已有评估基础（引用质量等）

**魔改价值**：
- 🎯 自动找到最佳 prompt
- 🎯 自动优化研究流程
- 🎯 无需人工调参

**大佬，这个魔改方案值得做！我可以帮你实现阶段 1（Prompt 优化器），预计 1-2 天完成。**

