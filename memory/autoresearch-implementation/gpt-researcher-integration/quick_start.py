#!/usr/bin/env python3
"""
快速开始脚本
演示如何使用 Autoresearch 优化器优化 GPT Researcher
"""

from gpt_researcher_optimizer import (
    GPTRsearcherPromptOptimizer,
    GPTRsearcherParamOptimizer,
    GPTRsearcherReportOptimizer
)

def main():
    print("🚀 GPT Researcher Autoresearch 优化器 - 快速开始")
    print("=" * 60)
    
    # 1. Prompt 优化
    print("\n📝 步骤 1：优化研究 Prompt")
    print("-" * 60)
    
    base_prompt = input("请输入研究主题（默认：人工智能在医疗领域的应用）: ").strip()
    if not base_prompt:
        base_prompt = "人工智能在医疗领域的应用"
    
    iterations = input("优化迭代次数（默认：20，推荐：50-100）: ").strip()
    iterations = int(iterations) if iterations else 20
    
    print(f"\n正在优化 Prompt（{iterations} 次迭代）...")
    
    prompt_optimizer = GPTRsearcherPromptOptimizer(
        base_prompt=base_prompt,
        max_iterations=iterations
    )
    
    best_prompt, best_score, _ = prompt_optimizer.optimize(verbose=True)
    
    print(f"\n✨ 最佳 Prompt:")
    print(f"{best_prompt}")
    print(f"分数: {best_score:.1f}")
    
    # 2. 参数优化
    print("\n" + "=" * 60)
    print("⚙️  步骤 2：优化模型参数")
    print("-" * 60)
    
    optimize_params = input("是否优化参数？（y/n，默认：y）: ").strip().lower()
    
    if optimize_params != 'n':
        print(f"\n正在优化参数（{iterations} 次迭代）...")
        
        base_params = {
            'temperature': 0.7,
            'max_tokens': 2000,
            'top_p': 0.9,
            'frequency_penalty': 0.0,
            'presence_penalty': 0.0
        }
        
        param_optimizer = GPTRsearcherParamOptimizer(
            base_params=base_params,
            max_iterations=iterations
        )
        
        best_params, best_score, _ = param_optimizer.optimize(verbose=True)
        
        print(f"\n✨ 最佳参数:")
        for key, value in best_params.items():
            print(f"  {key}: {value}")
        print(f"分数: {best_score:.1f}")
    else:
        best_params = {
            'temperature': 0.17,
            'max_tokens': 527,
            'top_p': 0.9,
            'frequency_penalty': 0.03,
            'presence_penalty': 0.47
        }
        print("\n使用默认最佳参数")
    
    # 3. 生成优化配置
    print("\n" + "=" * 60)
    print("📄 步骤 3：生成优化配置")
    print("-" * 60)
    
    config = f"""
# GPT Researcher 优化配置
# 生成时间: {__import__('datetime').datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

## 最佳 Prompt
{best_prompt}

## 最佳参数
temperature: {best_params.get('temperature', 0.17)}
max_tokens: {best_params.get('max_tokens', 527)}
top_p: {best_params.get('top_p', 0.9)}
frequency_penalty: {best_params.get('frequency_penalty', 0.03)}
presence_penalty: {best_params.get('presence_penalty', 0.47)}

## 使用方法
```python
from gpt_researcher import GPTResearcher

researcher = GPTResearcher(
    prompt=\"\"\"{best_prompt}\"\"\",
    temperature={best_params.get('temperature', 0.17)},
    max_tokens={best_params.get('max_tokens', 527)},
    top_p={best_params.get('top_p', 0.9)},
    frequency_penalty={best_params.get('frequency_penalty', 0.03)},
    presence_penalty={best_params.get('presence_penalty', 0.47)}
)

report = researcher.run()
```
"""
    
    print(config)
    
    # 保存配置
    save = input("\n是否保存配置到文件？（y/n，默认：y）: ").strip().lower()
    
    if save != 'n':
        filename = f"optimized_config_{__import__('datetime').datetime.now().strftime('%Y%m%d_%H%M%S')}.md"
        with open(filename, 'w', encoding='utf-8') as f:
            f.write(config)
        
        print(f"\n✅ 配置已保存: {filename}")
    
    print("\n" + "=" * 60)
    print("🎉 优化完成！")
    print("=" * 60)


if __name__ == "__main__":
    main()
