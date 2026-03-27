#!/usr/bin/env python3
"""
LLM 成本计算器
用于计算和比较不同 LLM 提供商的成本
"""

from typing import Dict, List
from dataclasses import dataclass
import argparse

@dataclass
class LLMProvider:
    """LLM 提供商定义"""
    name: str
    input_price: float  # per 1M tokens
    output_price: float  # per 1M tokens
    context_window: int
    currency: str = "USD"

class LLMCostCalculator:
    """LLM 成本计算器"""
    
    def __init__(self):
        """初始化计算器"""
        self.providers = self._load_providers()
    
    def _load_providers(self) -> Dict[str, LLMProvider]:
        """加载提供商信息"""
        return {
            "gpt-4": LLMProvider(
                name="GPT-4",
                input_price=30.0,
                output_price=60.0,
                context_window=128000,
                currency="USD"
            ),
            "gpt-3.5-turbo": LLMProvider(
                name="GPT-3.5 Turbo",
                input_price=0.5,
                output_price=1.5,
                context_window=16385,
                currency="USD"
            ),
            "claude-3-opus": LLMProvider(
                name="Claude 3 Opus",
                input_price=15.0,
                output_price=75.0,
                context_window=200000,
                currency="USD"
            ),
            "claude-3-sonnet": LLMProvider(
                name="Claude 3 Sonnet",
                input_price=3.0,
                output_price=15.0,
                context_window=200000,
                currency="USD"
            ),
            "glm-5": LLMProvider(
                name="GLM-5",
                input_price=0.1,
                output_price=0.1,
                context_window=128000,
                currency="CNY"
            ),
            "qwen-72b": LLMProvider(
                name="Qwen 72B",
                input_price=0.05,
                output_price=0.05,
                context_window=32768,
                currency="CNY"
            ),
            "deepseek-v3": LLMProvider(
                name="DeepSeek V3",
                input_price=0.1,
                output_price=0.1,
                context_window=64000,
                currency="CNY"
            )
        }
    
    def calculate_cost(
        self,
        provider_name: str,
        input_tokens: int,
        output_tokens: int
    ) -> Dict[str, float]:
        """
        计算成本
        
        Args:
            provider_name: 提供商名称
            input_tokens: 输入 token 数
            output_tokens: 输出 token 数
        
        Returns:
            成本信息
        """
        provider = self.providers[provider_name]
        
        input_cost = (input_tokens / 1_000_000) * provider.input_price
        output_cost = (output_tokens / 1_000_000) * provider.output_price
        total_cost = input_cost + output_cost
        
        return {
            "provider": provider.name,
            "input_tokens": input_tokens,
            "output_tokens": output_tokens,
            "input_cost": input_cost,
            "output_cost": output_cost,
            "total_cost": total_cost,
            "currency": provider.currency
        }
    
    def compare_providers(
        self,
        input_tokens: int,
        output_tokens: int
    ) -> List[Dict]:
        """
        比较所有提供商的成本
        
        Args:
            input_tokens: 输入 token 数
            output_tokens: 输出 token 数
        
        Returns:
            比较结果（按成本排序）
        """
        results = []
        
        for provider_name in self.providers:
            cost_info = self.calculate_cost(
                provider_name,
                input_tokens,
                output_tokens
            )
            results.append(cost_info)
        
        # 按总成本排序
        results.sort(key=lambda x: x["total_cost"])
        
        return results
    
    def print_comparison(self, results: List[Dict]):
        """打印比较结果"""
        print("\n📊 LLM 成本比较")
        print("=" * 80)
        
        for i, result in enumerate(results, 1):
            print(f"\n{i}. {result['provider']}")
            print(f"   输入: {result['input_tokens']:,} tokens = ${result['input_cost']:.4f}")
            print(f"   输出: {result['output_tokens']:,} tokens = ${result['output_cost']:.4f}")
            print(f"   总计: {result['currency']} {result['total_cost']:.4f}")
        
        # 找出最便宜的
        cheapest = results[0]
        most_expensive = results[-1]
        
        print("\n" + "=" * 80)
        print(f"✅ 最便宜: {cheapest['provider']} ({cheapest['currency']} {cheapest['total_cost']:.4f})")
        print(f"❌ 最昂贵: {most_expensive['provider']} ({most_expensive['currency']} {most_expensive['total_cost']:.4f})")
        print(f"💰 节省: {most_expensive['total_cost'] - cheapest['total_cost']:.4f} ({(1 - cheapest['total_cost']/most_expensive['total_cost'])*100:.1f}%)")


def main():
    """主函数"""
    parser = argparse.ArgumentParser(description="LLM 成本计算器")
    parser.add_argument("--input", type=int, required=True, help="输入 token 数")
    parser.add_argument("--output", type=int, required=True, help="输出 token 数")
    parser.add_argument("--provider", type=str, help="指定提供商（可选）")
    
    args = parser.parse_args()
    
    calculator = LLMCostCalculator()
    
    if args.provider:
        # 计算单个提供商
        result = calculator.calculate_cost(
            args.provider,
            args.input,
            args.output
        )
        print(f"\n{result['provider']}: {result['currency']} {result['total_cost']:.4f}")
    else:
        # 比较所有提供商
        results = calculator.compare_providers(args.input, args.output)
        calculator.print_comparison(results)


if __name__ == "__main__":
    main()
