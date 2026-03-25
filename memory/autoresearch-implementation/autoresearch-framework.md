# Autoresearch 框架实现

> 基于 Karpathy 的 autoresearch 思路
> 核心逻辑：改一个东西 → 打分 → 分高了保留，分低了回滚 → 再改下一个

---

## 🎯 通用迭代框架

### 核心组件

1. **变体生成器**：每次只改一个东西
2. **评估器**：自动打分（0-100）
3. **决策器**：分高了保留，分低了回滚
4. **迭代器**：循环执行，无需人工干预

---

## 📊 应用场景

### 场景 1：Prompt 优化
```
改一条 prompt 规则 → 生成报告 → 打分 → 保留/回滚
```

**打分标准**：
- 准确性（0-40 分）
- 完整性（0-30 分）
- 可读性（0-30 分）

### 场景 2：参数优化
```
改一个参数 → 运行研究 → 打分 → 保留/回滚
```

**打分标准**：
- 速度（0-30 分）
- 成本（0-30 分）
- 质量（0-40 分）

### 场景 3：文案优化
```
改一个标题 → 测点击率 → 打分 → 保留/回滚
```

**打分标准**：
- 点击率（0-50 分）
- 转化率（0-50 分）

---

## 🔧 实现架构

```python
class AutoresearchOptimizer:
    def __init__(self, target, evaluator, max_iterations=100):
        self.target = target  # 要优化的目标
        self.evaluator = evaluator  # 评估函数
        self.max_iterations = max_iterations
        self.best_score = 0
        self.best_version = None
        self.history = []
    
    def generate_variant(self, current):
        """生成变体（只改一个东西）"""
        # 实现变体生成逻辑
        pass
    
    def evaluate(self, variant):
        """评估变体（打分）"""
        return self.evaluator(variant)
    
    def run(self):
        """运行优化循环"""
        current = self.target
        
        for i in range(self.max_iterations):
            # 1. 生成变体
            variant = self.generate_variant(current)
            
            # 2. 评估变体
            score = self.evaluate(variant)
            
            # 3. 决策：保留 or 回滚
            if score > self.best_score:
                self.best_score = score
                self.best_version = variant
                current = variant
                print(f"✅ 迭代 {i}: {score}分（保留）")
            else:
                print(f"❌ 迭代 {i}: {score}分（回滚）")
            
            # 4. 记录历史
            self.history.append({
                'iteration': i,
                'score': score,
                'kept': score > self.best_score
            })
        
        return self.best_version, self.best_score
```

---

## 🚀 快速开始

### 示例 1：Prompt 优化器

```python
def prompt_evaluator(prompt):
    """评估 prompt 质量"""
    # 1. 生成报告
    report = generate_report(prompt)
    
    # 2. 打分
    score = 0
    score += check_accuracy(report) * 40  # 准确性
    score += check_completeness(report) * 30  # 完整性
    score += check_readability(report) * 30  # 可读性
    
    return score

optimizer = AutoresearchOptimizer(
    target=base_prompt,
    evaluator=prompt_evaluator,
    max_iterations=100
)

best_prompt, best_score = optimizer.run()
```

### 示例 2：参数优化器

```python
def param_evaluator(params):
    """评估参数配置"""
    # 1. 运行研究
    result = run_research(params)
    
    # 2. 打分
    score = 0
    score += (1 / result.time) * 30  # 速度
    score += (1 / result.cost) * 30  # 成本
    score += result.quality * 40  # 质量
    
    return score

optimizer = AutoresearchOptimizer(
    target=default_params,
    evaluator=param_evaluator,
    max_iterations=50
)

best_params, best_score = optimizer.run()
```

---

## 💡 核心优势

1. **无需人工**：100 次实验自动运行
2. **智能回滚**：分低了自动还原
3. **持续优化**：每次只改一点，逐步提升
4. **通用框架**：任何能打分的东西都能套进去

---

## 📈 预期效果

- **迭代次数**：50-100 次
- **每次耗时**：1-5 分钟
- **总耗时**：2-8 小时（无需人工干预）
- **提升幅度**：10-30%

---

**下一步**：实现具体的优化器（Prompt 优化器、参数优化器等）
