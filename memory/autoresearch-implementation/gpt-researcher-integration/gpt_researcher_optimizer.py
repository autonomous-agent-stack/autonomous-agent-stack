#!/usr/bin/env python3
"""
GPT Researcher 专用 Autoresearch 优化器
基于 Karpathy 的 autoresearch 思路：改一个东西 → 打分 → 分高了保留，分低了回滚
"""

import json
import time
import random
import copy
from datetime import datetime
from typing import Callable, Any, Dict, List

# 导入基础优化器
import sys
sys.path.append('..')
from autoresearch_optimizer import AutoresearchOptimizer


class GPTRsearcherPromptOptimizer:
    """GPT Researcher Prompt 优化器"""
    
    def __init__(self, base_prompt: str, max_iterations: int = 50):
        """
        初始化 Prompt 优化器
        
        Args:
            base_prompt: 基础研究 prompt
            max_iterations: 最大迭代次数
        """
        self.base_prompt = base_prompt
        self.max_iterations = max_iterations
        
        # Prompt 变体策略
        self.prompt_strategies = [
            # 添加修饰词
            lambda p: p.replace("研究", "深入研究"),
            lambda p: p.replace("分析", "详细分析"),
            lambda p: p.replace("报告", "完整报告"),
            lambda p: p.replace("调查", "全面调查"),
            
            # 添加要求
            lambda p: p + "\n\n要求：准确、客观、详细",
            lambda p: p + "\n\n注意：提供数据支持",
            lambda p: p + "\n\n重点：分析优缺点",
            lambda p: p + "\n\n目标：提供可操作建议",
            
            # 调整结构
            lambda p: f"请{p}",
            lambda p: f"任务：{p}",
            lambda p: f"研究主题：{p}",
            lambda p: f"深度研究：{p}",
            
            # 添加限制
            lambda p: p + "\n\n限制：不超过 5000 字",
            lambda p: p + "\n\n格式：使用 Markdown",
            lambda p: p + "\n\n结构：包含摘要、正文、结论",
        ]
    
    def evaluate_prompt(self, prompt: str) -> float:
        """
        评估 Prompt 质量
        
        实际应用中，这里应该：
        1. 用 prompt 生成研究报告
        2. 检查报告的准确性、完整性、可读性
        3. 返回综合分数
        
        Args:
            prompt: 要评估的 prompt
        
        Returns:
            分数（0-100）
        """
        # 模拟评分（实际应用中替换为真实逻辑）
        base_score = 50
        
        # 检查 prompt 长度
        if 50 < len(prompt) < 500:
            base_score += 10
        elif len(prompt) >= 500:
            base_score -= 5
        
        # 检查关键词
        positive_keywords = ["详细", "准确", "客观", "深入", "全面", "分析"]
        negative_keywords = ["随便", "简单", "大概"]
        
        for keyword in positive_keywords:
            if keyword in prompt:
                base_score += 5
        
        for keyword in negative_keywords:
            if keyword in prompt:
                base_score -= 10
        
        # 检查结构
        if "要求" in prompt or "目标" in prompt:
            base_score += 10
        
        if "格式" in prompt or "结构" in prompt:
            base_score += 8
        
        # 添加随机性（模拟不同报告的质量波动）
        noise = random.uniform(-5, 5)
        
        return min(100, max(0, base_score + noise))
    
    def generate_prompt_variant(self, prompt: str) -> str:
        """
        生成 Prompt 变体（只改一个东西）
        
        Args:
            prompt: 当前 prompt
        
        Returns:
            变体 prompt
        """
        strategy = random.choice(self.prompt_strategies)
        return strategy(prompt)
    
    def optimize(self, verbose: bool = True) -> tuple:
        """
        运行优化
        
        Args:
            verbose: 是否输出详细日志
        
        Returns:
            (最佳 prompt, 最佳分数, 历史记录)
        """
        optimizer = AutoresearchOptimizer(
            target=self.base_prompt,
            evaluator=self.evaluate_prompt,
            variant_generator=self.generate_prompt_variant,
            max_iterations=self.max_iterations,
            improvement_threshold=0.0
        )
        
        return optimizer.run(verbose=verbose)


class GPTRsearcherParamOptimizer:
    """GPT Researcher 参数优化器"""
    
    def __init__(self, base_params: Dict, max_iterations: int = 50):
        """
        初始化参数优化器
        
        Args:
            base_params: 基础参数配置
            max_iterations: 最大迭代次数
        """
        self.base_params = base_params
        self.max_iterations = max_iterations
        
        # 参数范围
        self.param_ranges = {
            'temperature': (0.1, 1.0),
            'max_tokens': (500, 4000),
            'top_p': (0.5, 1.0),
            'frequency_penalty': (0.0, 2.0),
            'presence_penalty': (0.0, 2.0),
        }
    
    def evaluate_params(self, params: Dict) -> float:
        """
        评估参数配置
        
        实际应用中，这里应该：
        1. 用参数运行研究
        2. 检查速度、成本、质量
        3. 返回综合分数
        
        Args:
            params: 参数配置
        
        Returns:
            分数（0-100）
        """
        base_score = 50
        
        # 检查温度参数
        temp = params.get('temperature', 0.7)
        if 0.3 <= temp <= 0.5:
            base_score += 15  # 适中的温度，平衡创造性和准确性
        elif temp < 0.3:
            base_score += 10  # 更准确，但可能缺乏多样性
        elif temp > 0.8:
            base_score -= 5  # 太随机
        
        # 检查 max_tokens
        max_tokens = params.get('max_tokens', 2000)
        if 1500 <= max_tokens <= 3000:
            base_score += 10  # 合理的输出长度
        elif max_tokens > 3500:
            base_score -= 5  # 可能太长
        
        # 检查 top_p
        top_p = params.get('top_p', 0.9)
        if 0.8 <= top_p <= 0.95:
            base_score += 10  # 合理的范围
        elif top_p < 0.7:
            base_score -= 5  # 可能太严格
        
        # 检查惩罚参数
        freq_penalty = params.get('frequency_penalty', 0.0)
        pres_penalty = params.get('presence_penalty', 0.0)
        
        if 0.5 <= freq_penalty <= 1.0:
            base_score += 5  # 减少重复
        
        if 0.5 <= pres_penalty <= 1.0:
            base_score += 5  # 鼓励多样性
        
        # 模拟成本（token 数越多成本越高）
        cost_penalty = max_tokens / 100
        base_score -= cost_penalty
        
        # 添加随机性
        noise = random.uniform(-5, 5)
        
        return min(100, max(0, base_score + noise))
    
    def generate_param_variant(self, params: Dict) -> Dict:
        """
        生成参数变体（只改一个参数）
        
        Args:
            params: 当前参数
        
        Returns:
            变体参数
        """
        variant = copy.deepcopy(params)
        
        # 随机选择一个参数修改
        param_to_change = random.choice(list(self.param_ranges.keys()))
        min_val, max_val = self.param_ranges[param_to_change]
        
        if isinstance(min_val, int):
            variant[param_to_change] = random.randint(min_val, max_val)
        else:
            variant[param_to_change] = random.uniform(min_val, max_val)
        
        return variant
    
    def optimize(self, verbose: bool = True) -> tuple:
        """
        运行优化
        
        Args:
            verbose: 是否输出详细日志
        
        Returns:
            (最佳参数, 最佳分数, 历史记录)
        """
        optimizer = AutoresearchOptimizer(
            target=self.base_params,
            evaluator=self.evaluate_params,
            variant_generator=self.generate_param_variant,
            max_iterations=self.max_iterations,
            improvement_threshold=0.0
        )
        
        return optimizer.run(verbose=verbose)


class GPTRsearcherReportOptimizer:
    """GPT Researcher 报告质量优化器"""
    
    def __init__(self, research_topic: str, max_iterations: int = 30):
        """
        初始化报告优化器
        
        Args:
            research_topic: 研究主题
            max_iterations: 最大迭代次数
        """
        self.research_topic = research_topic
        self.max_iterations = max_iterations
    
    def evaluate_report(self, report: str) -> float:
        """
        评估报告质量
        
        实际应用中，这里应该：
        1. 检查报告的准确性
        2. 检查报告的完整性
        3. 检查报告的可读性
        4. 返回综合分数
        
        Args:
            report: 研究报告
        
        Returns:
            分数（0-100）
        """
        base_score = 50
        
        # 检查长度
        word_count = len(report.split())
        if 1000 <= word_count <= 3000:
            base_score += 15  # 合理的长度
        elif word_count < 500:
            base_score -= 10  # 太短
        elif word_count > 5000:
            base_score -= 5  # 太长
        
        # 检查结构
        if "摘要" in report or "总结" in report:
            base_score += 10
        
        if "结论" in report or "建议" in report:
            base_score += 10
        
        if "##" in report:  # Markdown 标题
            base_score += 8
        
        # 检查内容质量
        if "数据" in report or "统计" in report:
            base_score += 8
        
        if "研究" in report or "分析" in report:
            base_score += 8
        
        # 检查可读性
        sentences = report.split('。')
        avg_sentence_length = sum(len(s) for s in sentences) / max(len(sentences), 1)
        
        if 20 <= avg_sentence_length <= 50:
            base_score += 10  # 句子长度适中
        elif avg_sentence_length > 80:
            base_score -= 5  # 句子太长
        
        # 添加随机性
        noise = random.uniform(-5, 5)
        
        return min(100, max(0, base_score + noise))
    
    def generate_report_variant(self, report: str) -> str:
        """
        生成报告变体（模拟优化）
        
        实际应用中，这里应该：
        1. 调整报告结构
        2. 添加/删除内容
        3. 优化表达方式
        
        Args:
            report: 当前报告
        
        Returns:
            变体报告
        """
        # 模拟变体生成
        variants = [
            lambda r: f"## 摘要\n\n{r}\n\n## 结论\n\n基于以上分析，我们得出以下结论...",
            lambda r: f"## 研究报告\n\n{r}\n\n## 数据支持\n\n根据最新数据显示...",
            lambda r: f"### 背景\n\n{r}\n\n### 分析\n\n详细分析如下...",
            lambda r: report + "\n\n## 建议\n\n基于研究结果，我们建议...",
        ]
        
        variant_func = random.choice(variants)
        return variant_func(report)
    
    def optimize(self, verbose: bool = True) -> tuple:
        """
        运行优化
        
        Args:
            verbose: 是否输出详细日志
        
        Returns:
            (最佳报告, 最佳分数, 历史记录)
        """
        # 生成初始报告（模拟）
        initial_report = f"关于 {self.research_topic} 的研究报告"
        
        optimizer = AutoresearchOptimizer(
            target=initial_report,
            evaluator=self.evaluate_report,
            variant_generator=self.generate_report_variant,
            max_iterations=self.max_iterations,
            improvement_threshold=0.0
        )
        
        return optimizer.run(verbose=verbose)


# ============ 主程序 ============

def main():
    """演示 GPT Researcher 优化器"""
    
    print("=" * 60)
    print("🚀 GPT Researcher Autoresearch 优化器演示")
    print("=" * 60)
    
    # 示例 1：Prompt 优化
    print("\n📝 示例 1：研究 Prompt 优化")
    print("-" * 60)
    
    base_prompt = "研究人工智能在医疗领域的应用"
    
    optimizer = GPTRsearcherPromptOptimizer(
        base_prompt=base_prompt,
        max_iterations=20
    )
    
    best_prompt, best_score, history = optimizer.optimize(verbose=True)
    
    print(f"\n✨ 最佳 Prompt:")
    print(f"{best_prompt}")
    print(f"分数: {best_score:.1f}")
    
    # 示例 2：参数优化
    print("\n" + "=" * 60)
    print("⚙️  示例 2：研究参数优化")
    print("-" * 60)
    
    base_params = {
        'temperature': 0.7,
        'max_tokens': 2000,
        'top_p': 0.9,
        'frequency_penalty': 0.0,
        'presence_penalty': 0.0
    }
    
    optimizer = GPTRsearcherParamOptimizer(
        base_params=base_params,
        max_iterations=20
    )
    
    best_params, best_score, history = optimizer.optimize(verbose=True)
    
    print(f"\n✨ 最佳参数:")
    for key, value in best_params.items():
        print(f"  {key}: {value}")
    print(f"分数: {best_score:.1f}")
    
    # 示例 3：报告质量优化
    print("\n" + "=" * 60)
    print("📊 示例 3：研究报告质量优化")
    print("-" * 60)
    
    optimizer = GPTRsearcherReportOptimizer(
        research_topic="人工智能在医疗领域的应用",
        max_iterations=10
    )
    
    best_report, best_score, history = optimizer.optimize(verbose=True)
    
    print(f"\n✨ 最佳报告（前 200 字）:")
    print(f"{best_report[:200]}...")
    print(f"分数: {best_score:.1f}")
    
    # 保存历史记录
    history_file = f"gpt_researcher_optimization_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    with open(history_file, 'w') as f:
        json.dump({
            'prompt_history': history,
            'param_history': history,
            'report_history': history
        }, f, indent=2)
    
    print(f"\n💾 历史记录已保存: {history_file}")


if __name__ == "__main__":
    main()
