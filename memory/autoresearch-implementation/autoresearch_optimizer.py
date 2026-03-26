#!/usr/bin/env python3
"""
Autoresearch 优化器
基于 Karpathy 的 autoresearch 思路：改一个东西 → 打分 → 分高了保留，分低了回滚
"""

import json
import time
import random
from datetime import datetime
from typing import Callable, Any, Dict, List

class AutoresearchOptimizer:
    """通用迭代优化器"""
    
    def __init__(self, 
                 target: Any,
                 evaluator: Callable,
                 variant_generator: Callable,
                 max_iterations: int = 100,
                 improvement_threshold: float = 0.0):
        """
        初始化优化器
        
        Args:
            target: 要优化的目标（prompt、参数等）
            evaluator: 评估函数（返回 0-100 分）
            variant_generator: 变体生成函数（每次只改一个东西）
            max_iterations: 最大迭代次数
            improvement_threshold: 改进阈值（分数提升多少才保留）
        """
        self.target = target
        self.evaluator = evaluator
        self.variant_generator = variant_generator
        self.max_iterations = max_iterations
        self.improvement_threshold = improvement_threshold
        
        self.best_score = 0
        self.best_version = target
        self.current_version = target
        self.history = []
    
    def run(self, verbose: bool = True) -> tuple:
        """运行优化循环"""
        print(f"🚀 开始优化（最多 {self.max_iterations} 次迭代）")
        print(f"📊 目标：提升分数 > {self.improvement_threshold}")
        print("-" * 60)
        
        start_time = time.time()
        
        for i in range(self.max_iterations):
            iter_start = time.time()
            
            # 1. 生成变体（只改一个东西）
            variant = self.variant_generator(self.current_version)
            
            # 2. 评估变体（打分）
            try:
                score = self.evaluator(variant)
            except Exception as e:
                print(f"❌ 迭代 {i+1}: 评估失败 - {e}")
                continue
            
            iter_time = time.time() - iter_start
            
            # 3. 决策：保留 or 回滚
            improvement = score - self.best_score
            kept = improvement > self.improvement_threshold
            
            if kept:
                self.best_score = score
                self.best_version = variant
                self.current_version = variant
                status = "✅ 保留"
            else:
                status = "❌ 回滚"
            
            # 4. 记录历史
            self.history.append({
                'iteration': i + 1,
                'score': score,
                'improvement': improvement,
                'kept': kept,
                'time': iter_time
            })
            
            # 5. 输出进度
            if verbose:
                print(f"迭代 {i+1:3d} | {status} | 分数: {score:5.1f} | "
                      f"提升: {improvement:+5.1f} | 耗时: {iter_time:.1f}s")
        
        total_time = time.time() - start_time
        
        print("-" * 60)
        print(f"✅ 优化完成！")
        print(f"📊 最佳分数: {self.best_score:.1f}")
        print(f"⏱️  总耗时: {total_time:.1f}s")
        print(f"📈 迭代次数: {len(self.history)}")
        
        return self.best_version, self.best_score, self.history


# ============ 示例：Prompt 优化器 ============

def prompt_evaluator(prompt: str) -> float:
    """评估 prompt 质量（模拟）"""
    # 实际应用中，这里应该：
    # 1. 用 prompt 生成报告
    # 2. 检查准确性、完整性、可读性
    # 3. 返回综合分数
    
    # 模拟评分（实际应用中替换为真实逻辑）
    base_score = 50
    
    # 检查 prompt 长度
    if len(prompt) > 100:
        base_score += 10
    
    # 检查关键词
    if "详细" in prompt:
        base_score += 15
    if "准确" in prompt:
        base_score += 15
    if "客观" in prompt:
        base_score += 10
    
    # 添加随机性（模拟不同报告的质量波动）
    noise = random.uniform(-5, 5)
    
    return min(100, max(0, base_score + noise))


def prompt_variant_generator(prompt: str) -> str:
    """生成 prompt 变体（只改一个东西）"""
    variants = [
        # 添加修饰词
        lambda p: p.replace("研究", "深入研究"),
        lambda p: p.replace("分析", "详细分析"),
        lambda p: p.replace("报告", "完整报告"),
        
        # 添加要求
        lambda p: p + "\n\n要求：准确、客观、详细",
        lambda p: p + "\n\n注意：提供数据支持",
        lambda p: p + "\n\n重点：分析优缺点",
        
        # 调整结构
        lambda p: f"请{p}",
        lambda p: f"任务：{p}",
        lambda p: f"研究主题：{p}",
    ]
    
    # 随机选择一个变体
    variant_func = random.choice(variants)
    return variant_func(prompt)


# ============ 示例：参数优化器 ============

def param_evaluator(params: Dict) -> float:
    """评估参数配置（模拟）"""
    # 实际应用中，这里应该：
    # 1. 用参数运行研究
    # 2. 检查速度、成本、质量
    # 3. 返回综合分数
    
    base_score = 50
    
    # 检查参数合理性
    if params.get('temperature', 1.0) < 0.5:
        base_score += 15  # 降低随机性
    
    if params.get('max_tokens', 1000) > 2000:
        base_score += 10  # 更详细的输出
    
    if params.get('top_p', 1.0) < 0.9:
        base_score += 10  # 更准确
    
    # 模拟成本（token 数越多成本越高）
    cost_penalty = params.get('max_tokens', 1000) / 100
    base_score -= cost_penalty
    
    # 添加随机性
    noise = random.uniform(-5, 5)
    
    return min(100, max(0, base_score + noise))


def param_variant_generator(params: Dict) -> Dict:
    """生成参数变体（只改一个参数）"""
    import copy
    variant = copy.deepcopy(params)
    
    # 随机选择一个参数修改
    param_to_change = random.choice(['temperature', 'max_tokens', 'top_p'])
    
    if param_to_change == 'temperature':
        variant['temperature'] = random.uniform(0.1, 1.0)
    elif param_to_change == 'max_tokens':
        variant['max_tokens'] = random.randint(500, 4000)
    elif param_to_change == 'top_p':
        variant['top_p'] = random.uniform(0.5, 1.0)
    
    return variant


# ============ 主程序 ============

def main():
    """演示 Autoresearch 优化器"""
    
    print("=" * 60)
    print("🚀 Autoresearch 优化器演示")
    print("=" * 60)
    
    # 示例 1：Prompt 优化
    print("\n📝 示例 1：Prompt 优化")
    print("-" * 60)
    
    base_prompt = "研究人工智能在医疗领域的应用"
    
    optimizer = AutoresearchOptimizer(
        target=base_prompt,
        evaluator=prompt_evaluator,
        variant_generator=prompt_variant_generator,
        max_iterations=20,
        improvement_threshold=0.0
    )
    
    best_prompt, best_score, history = optimizer.run(verbose=True)
    
    print(f"\n✨ 最佳 Prompt:")
    print(f"{best_prompt}")
    print(f"分数: {best_score:.1f}")
    
    # 示例 2：参数优化
    print("\n" + "=" * 60)
    print("⚙️  示例 2：参数优化")
    print("-" * 60)
    
    base_params = {
        'temperature': 0.7,
        'max_tokens': 2000,
        'top_p': 0.9
    }
    
    optimizer = AutoresearchOptimizer(
        target=base_params,
        evaluator=param_evaluator,
        variant_generator=param_variant_generator,
        max_iterations=20,
        improvement_threshold=0.0
    )
    
    best_params, best_score, history = optimizer.run(verbose=True)
    
    print(f"\n✨ 最佳参数:")
    for key, value in best_params.items():
        print(f"  {key}: {value}")
    print(f"分数: {best_score:.1f}")
    
    # 保存历史记录
    history_file = f"autoresearch_history_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    with open(history_file, 'w') as f:
        json.dump(history, f, indent=2)
    
    print(f"\n💾 历史记录已保存: {history_file}")


if __name__ == "__main__":
    main()
